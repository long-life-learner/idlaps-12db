<?php
// ─── POST /api/checkpoint.php ─────────────────────────────────────────────────
// Endpoint utama: menerima data chip RFID dari IDLAPS Checkpoint hardware
//
// ── MODE 1: Zero-Config (direkomendasikan, tidak butuh API Key) ──
// Body (JSON):
// {
//   "device_sn": "363B37373632010134303837",   ← HEX dari Serial Number hardware
//   "reader_id": "192.168.1.201",              ← opsional, untuk filter Live Monitor
//   "reads": [
//     { "epc": "E2003411B802...", "timestamp": "2026-04-26T07:18:25.000", "rssi": -65 }
//   ]
// }
// race_id diambil OTOMATIS dari device yang ter-mapping di tabel devices.
//
// ── MODE 2: API Key (backward-compat, pengguna lama) ────────────
// Header: X-API-Key: {api_key}
// Body (JSON):
// {
//   "race_id": 1,
//   "reader_id": "192.168.1.201",
//   "reads": [...]
// }
//
// PERFORMA: Mendukung ratusan ribu reads via bulk INSERT.
// Duplikat (same race+epc+time+reader) diabaikan secara otomatis (INSERT IGNORE).

require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../db.php';
require_once __DIR__ . '/middleware.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Headers: X-API-Key, Content-Type, X-Device-SN');
header('Access-Control-Allow-Methods: POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    apiResponse(405, ['success' => false, 'message' => 'Method tidak didukung. Gunakan POST.']);
}

$db         = getDB();
$body       = jsonBody();
$reads      = $body['reads'] ?? [];
$readerId   = trim($body['reader_id'] ?? '');
$syncedFrom = $_SERVER['REMOTE_ADDR'] ?? '';

// ── Deteksi Mode Autentikasi ──────────────────────────────────────────────────
$deviceSn   = strtoupper(trim($body['device_sn'] ?? ''));
$raceId     = 0;
$deviceRow  = null;
$authMode   = 'none';

if ($deviceSn) {
    // MODE 1: Zero-Config — lookup device by SN
    $snStmt = $db->prepare(
        'SELECT d.*, r.id as mapped_race_id
         FROM devices d
         LEFT JOIN races r ON r.id = d.race_id
         WHERE d.serial_number = ? LIMIT 1'
    );
    $snStmt->execute([$deviceSn]);
    $deviceRow = $snStmt->fetch();

    if (!$deviceRow) {
        apiResponse(401, [
            'success' => false,
            'message' => "Serial Number '{$deviceSn}' tidak dikenali. Daftarkan device ini di menu Device / Reader terlebih dahulu.",
        ]);
    }
    if (!$deviceRow['race_id']) {
        apiResponse(422, [
            'success' => false,
            'message' => "Device '{$deviceRow['name']}' belum dikaitkan ke Lomba manapun. Hubungkan device ke lomba aktif melalui dashboard.",
        ]);
    }

    $raceId   = (int)$deviceRow['race_id'];
    $authMode = 'sn';

    // Gunakan reader_ip dari device sebagai reader_id jika tidak disertakan di body
    if (!$readerId && $deviceRow['reader_ip']) {
        $readerId = $deviceRow['reader_ip'];
    }
} else {
    // MODE 2: API Key — backward compatible
    $keyRow = apiAuth(); // melempar 401 jika gagal
    $raceId = (int)($body['race_id'] ?? 0);
    $authMode = 'apikey';

    if (!$raceId) {
        apiResponse(400, ['success' => false, 'message' => 'Field race_id wajib diisi (Mode API Key).']);
    }
}

// Validasi payload reads
if (!is_array($reads) || count($reads) === 0) {
    apiResponse(400, ['success' => false, 'message' => 'Field reads harus berupa array tidak kosong.']);
}
if (count($reads) > 5000) {
    apiResponse(400, ['success' => false, 'message' => 'Maksimal 5000 reads per request. Bagi menjadi beberapa batch.']);
}

// Validasi race
$raceCheck = $db->prepare('SELECT id FROM races WHERE id = ? LIMIT 1');
$raceCheck->execute([$raceId]);
if (!$raceCheck->fetch()) {
    apiResponse(404, ['success' => false, 'message' => "Race ID {$raceId} tidak ditemukan."]);
}

// ── Preload EPC → bib map dari runner_chips (sekali load, cepat) ──────────────
// Menggunakan runner_chips untuk mendukung 1 bib multi-EPC
$chipStmt = $db->prepare(
    'SELECT rc.epc, ru.bib
     FROM runner_chips rc
     JOIN runners ru ON ru.id = rc.runner_id
     WHERE rc.race_id = ?'
);
$chipStmt->execute([$raceId]);
// Normalisasi EPC uppercase untuk matching
$epcToBib = [];
foreach ($chipStmt->fetchAll() as $row) {
    $epcToBib[strtoupper($row['epc'])] = $row['bib'];
}

// ── Parse & Validasi semua reads ──────────────────────────────────────────────
$validRows  = [];
$skipped    = 0;
$parseErrors = [];

foreach ($reads as $idx => $read) {
    $epc       = strtoupper(trim($read['epc'] ?? ''));
    $timestamp = trim($read['timestamp'] ?? '');
    $rssi      = isset($read['rssi']) ? (int)$read['rssi'] : null;

    if (!$epc || !$timestamp) {
        $parseErrors[] = "Read #{$idx}: epc dan timestamp wajib diisi.";
        $skipped++;
        continue;
    }

    // Normalisasi timestamp → DATETIME(3)
    // Mendukung: ISO8601 (2025-06-15T08:32:01.543), spasi separator, dengan/tanpa timezone
    $dt = str_replace('T', ' ', $timestamp);
    $dt = preg_replace('/[+\-]\d{2}:\d{2}$/', '', $dt); // hapus timezone offset
    $dt = preg_replace('/Z$/', '', $dt);                  // hapus Z
    $dt = substr($dt, 0, 23);                             // max YYYY-MM-DD HH:MM:SS.mmm

    $validRows[] = [
        'epc'       => $epc,
        'bib'       => $epcToBib[$epc] ?? null,
        'read_time' => $dt,
        'rssi'      => $rssi,
    ];
}

if (empty($validRows)) {
    apiResponse(400, [
        'success'  => false,
        'inserted' => 0,
        'skipped'  => $skipped,
        'errors'   => $parseErrors,
        'message'  => 'Tidak ada read yang valid untuk disimpan.',
    ]);
}

// ── BULK INSERT dengan chunking (1000 rows per eksekusi) ──────────────────────
// Jauh lebih cepat dari loop individual, aman untuk puluhan ribu rows sekaligus
$CHUNK_SIZE = 1000;
$inserted   = 0;
$chunks     = array_chunk($validRows, $CHUNK_SIZE);

$db->beginTransaction();
try {
    foreach ($chunks as $chunk) {
        $placeholders = implode(', ', array_fill(0, count($chunk), '(?,?,?,?,?,?,?)'));
        $sql = "INSERT IGNORE INTO chip_data
                    (race_id, epc, bib, reader_id, read_time, rssi, synced_from)
                VALUES {$placeholders}";

        $params = [];
        foreach ($chunk as $row) {
            array_push($params,
                $raceId,
                $row['epc'],
                $row['bib'],
                $readerId ?: null,
                $row['read_time'],
                $row['rssi'],
                $syncedFrom
            );
        }

        $stmt = $db->prepare($sql);
        $stmt->execute($params);
        $inserted += $stmt->rowCount();
    }
    $db->commit();
} catch (\Exception $e) {
    $db->rollBack();
    apiResponse(500, ['success' => false, 'message' => 'Error menyimpan data: ' . $e->getMessage()]);
}

apiResponse(200, [
    'success'     => true,
    'auth_mode'   => $authMode,
    'device_name' => $deviceRow['name'] ?? null,
    'race_id'     => $raceId,
    'received'    => count($reads),
    'inserted'    => $inserted,
    'skipped'     => $skipped + (count($validRows) - $inserted),
    'errors'      => $parseErrors,
    'message'     => "{$inserted} reads baru berhasil disimpan.",
]);
