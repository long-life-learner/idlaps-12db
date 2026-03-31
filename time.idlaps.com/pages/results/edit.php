<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'message' => 'Method Not Allowed']);
    exit;
}

$db       = getDB();
$resultId = (int)($_POST['result_id'] ?? 0);
$status   = $_POST['status'] ?? '';
$netHH    = (int)($_POST['net_hh'] ?? 0);
$netMM    = (int)($_POST['net_mm'] ?? 0);
$netSS    = (int)($_POST['net_ss'] ?? 0);
$netMS    = (int)($_POST['net_ms'] ?? 0);
$gunHH    = (int)($_POST['gun_hh'] ?? 0);
$gunMM    = (int)($_POST['gun_mm'] ?? 0);
$gunSS    = (int)($_POST['gun_ss'] ?? 0);
$gunMS    = (int)($_POST['gun_ms'] ?? 0);
$startTm  = trim($_POST['start_time']  ?? '');
$finishTm = trim($_POST['finish_time'] ?? '');

if (!$resultId) {
    echo json_encode(['success' => false, 'message' => 'result_id tidak valid.']);
    exit;
}

$validStatuses = ['valid', 'invalid', 'dns', 'dnf', 'dsq'];
if (!in_array($status, $validStatuses)) {
    echo json_encode(['success' => false, 'message' => 'Status tidak valid.']);
    exit;
}

$netTimeMs = ($netHH * 3600 + $netMM * 60 + $netSS) * 1000 + $netMS;
$gunTimeMs = ($gunHH * 3600 + $gunMM * 60 + $gunSS) * 1000 + $gunMS;

// Parsing datetime (format H:i:s atau Y-m-d H:i:s)
function parseTimeInput(?string $val): ?string {
    if (!$val) return null;
    // Jika hanya HH:MM:SS, butuh tanggal → simpan sebagai-is untuk ditampilkan
    if (preg_match('/^\d{2}:\d{2}:\d{2}$/', $val)) {
        // Tidak bisa simpan TIME saja ke DATETIME — kembalikan null, biarkan DB tidak berubah
        return null;
    }
    $ts = strtotime($val);
    return $ts ? date('Y-m-d H:i:s', $ts) : null;
}

$startVal  = $startTm  ? (preg_match('/^\d{4}-\d{2}-\d{2}/', $startTm)  ? $startTm  : null) : null;
$finishVal = $finishTm ? (preg_match('/^\d{4}-\d{2}-\d{2}/', $finishTm) ? $finishTm : null) : null;

// recalc gun_time_ms jika start ada
$res = $db->prepare('SELECT r.gun_time, res.gun_time_ms FROM results res JOIN races r ON r.id = res.race_id WHERE res.id = ?');
$res->execute([$resultId]);
$row = $res->fetch();

if (!$row) {
    echo json_encode(['success' => false, 'message' => 'Result tidak ditemukan.']);
    exit;
}

// Update
$db->prepare(
    'UPDATE results SET status=?, net_time_ms=?, gun_time_ms=?, start_time=COALESCE(?,start_time), finish_time=COALESCE(?,finish_time) WHERE id=?'
)->execute([$status, $netTimeMs ?: null, $gunTimeMs ?: null, $startVal, $finishVal, $resultId]);

echo json_encode(['success' => true, 'message' => 'Hasil berhasil diperbarui.']);
