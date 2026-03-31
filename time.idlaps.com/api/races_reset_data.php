<?php
require_once __DIR__ . '/../includes/db.php';
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

$race_id = $_POST['race_id'] ?? null;

if (!$race_id) {
    echo json_encode(['success' => false, 'message' => 'Race ID is required.']);
    exit;
}

try {
    $db->beginTransaction();

    // Hapus seluruh riwayat pembacaan karpet UHF
    $stmt1 = $db->prepare("DELETE FROM chip_data WHERE race_id = ?");
    $stmt1->execute([$race_id]);

    // Hapus seluruh papan hasil yang sempat terhitung
    $stmt2 = $db->prepare("DELETE FROM results WHERE race_id = ?");
    $stmt2->execute([$race_id]);

    $db->commit();

    echo json_encode(['success' => true, 'message' => 'Seluruh riwayat pembacaan karpet dan hasil lomba ini telah sukses diriset (dibersihkan).']);
} catch (Exception $e) {
    if ($db->inTransaction()) {
        $db->rollBack();
    }
    echo json_encode(['success' => false, 'message' => 'Gagal meriset data lomba: ' . $e->getMessage()]);
}
