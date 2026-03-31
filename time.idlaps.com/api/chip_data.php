<?php
// GET /api/chip_data.php — data untuk live monitor (dipanggil oleh JS auto-refresh)
require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../auth.php';
require_once __DIR__ . '/../db.php';
requireLogin(); // Gunakan Session browser, bukan API Key

header('Content-Type: application/json');

$db       = getDB();
$raceId   = (int)($_GET['race_id'] ?? 0);
$readerId = trim($_GET['reader_id'] ?? '');
$limit    = min((int)($_GET['limit'] ?? 50), 200);

if (!$raceId) {
    echo json_encode(['success'=>false,'message'=>'race_id wajib diisi.']);
    exit;
}

$where = 'cd.race_id = ?';
$params = [$raceId];
if ($readerId) { $where .= ' AND cd.reader_id = ?'; $params[] = $readerId; }

$rows = $db->prepare(
    "SELECT cd.epc, cd.bib, cd.reader_id, cd.read_time, cd.rssi
     FROM chip_data cd WHERE {$where} ORDER BY cd.read_time DESC LIMIT {$limit}"
);
$rows->execute($params);

$total = $db->prepare("SELECT COUNT(*) FROM chip_data WHERE race_id = ?");
$total->execute([$raceId]);

echo json_encode([
    'success' => true,
    'data'    => $rows->fetchAll(PDO::FETCH_ASSOC),
    'total'   => (int)$total->fetchColumn(),
]);
