<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

require_once __DIR__ . '/../../vendor/autoload.php';
use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Writer\Xlsx;
use PhpOffice\PhpSpreadsheet\Style\Fill;
use PhpOffice\PhpSpreadsheet\Style\Alignment;
use PhpOffice\PhpSpreadsheet\Style\Border;

$db     = getDB();
$raceId = (int)($_GET['race_id'] ?? 0);
$itemId = (int)($_GET['item_id'] ?? 0);
$gender = $_GET['gender'] ?? '';
$status = $_GET['status'] ?? '';

if (!$raceId) die('race_id diperlukan.');

$race = $db->prepare('SELECT * FROM races WHERE id = ?');
$race->execute([$raceId]); $race = $race->fetch();
if (!$race) die('Lomba tidak ditemukan.');

// Build query sama seperti results/list.php
$where  = ['res.race_id = ?'];
$params = [$raceId];
if ($itemId) { $where[] = 'res.item_id = ?'; $params[] = $itemId; }
if ($gender) { $where[] = 'ru.gender = ?';    $params[] = $gender; }
if ($status) { $where[] = 'res.status = ?';   $params[] = $status; }

$sql = '
    SELECT res.*, ru.name, ru.gender, ru.age_group, ru.team, i.title AS item_title
    FROM results res
    JOIN runners ru ON ru.id = res.runner_id
    JOIN items   i  ON i.id  = res.item_id
    WHERE ' . implode(' AND ', $where) . '
    ORDER BY res.item_id, res.overall_rank ASC, res.net_time_ms ASC
';
$q = $db->prepare($sql);
$q->execute($params);
$results = $q->fetchAll();

// ── Build Spreadsheet ──────────────────────────────────────────────────────────
$ss = new Spreadsheet();
$sh = $ss->getActiveSheet();
$sh->setTitle('Hasil Lomba');

// Header row
$headers = ['Rank', 'Rank ♂/♀', 'Bib', 'Nama', 'Kategori', 'Gender', 'Kelompok Umur', 'Net Time', 'Gun Time', 'Start', 'Finish', 'Status'];
$sh->fromArray([$headers], null, 'A1');

$headerStyle = [
    'font' => ['bold' => true, 'color' => ['rgb' => 'FFFFFF'], 'size' => 11],
    'fill' => ['fillType' => Fill::FILL_SOLID, 'startColor' => ['rgb' => '4F46E5']],
    'alignment' => ['horizontal' => Alignment::HORIZONTAL_CENTER, 'vertical' => Alignment::VERTICAL_CENTER],
    'borders' => ['allBorders' => ['borderStyle' => Border::BORDER_THIN, 'color' => ['rgb' => '6366F1']]],
];
$sh->getStyle('A1:L1')->applyFromArray($headerStyle);
$sh->getRowDimension(1)->setRowHeight(22);

// Data rows
$rowNum = 2;
foreach ($results as $r) {
    $net   = $r['net_time_ms']  ? formatTime((int)$r['net_time_ms'])  : '-';
    $gun   = $r['gun_time_ms']  ? formatTime((int)$r['gun_time_ms'])  : '-';
    $start = $r['start_time']   ? date('H:i:s', strtotime($r['start_time']))   : '-';
    $fin   = $r['finish_time']  ? date('H:i:s', strtotime($r['finish_time']))  : '-';

    $sh->fromArray([[
        $r['overall_rank'] ?? '-',
        $r['gender_rank']  ?? '-',
        $r['bib'],
        $r['name']        ?? '-',
        $r['item_title']  ?? '-',
        $r['gender'] === 'M' ? 'Putra' : 'Putri',
        $r['age_group']   ?? '-',
        $net,
        $gun,
        $start,
        $fin,
        strtoupper($r['status']),
    ]], null, "A{$rowNum}");

    // Warnai baris top 3
    if (($r['overall_rank'] ?? 99) <= 3) {
        $sh->getStyle("A{$rowNum}:L{$rowNum}")->applyFromArray([
            'fill' => ['fillType' => Fill::FILL_SOLID, 'startColor' => ['rgb' => 'FFF7ED']],
            'font' => ['bold' => true],
        ]);
    }

    // Warnai baris DNF/DSQ
    if (in_array($r['status'], ['dnf', 'dsq', 'dns'])) {
        $sh->getStyle("L{$rowNum}")->applyFromArray([
            'font' => ['color' => ['rgb' => 'EF4444'], 'bold' => true],
        ]);
    }

    $rowNum++;
}

// Auto-size kolom
$colWidths = ['A'=>8,'B'=>10,'C'=>8,'D'=>28,'E'=>16,'F'=>10,'G'=>15,'H'=>14,'I'=>14,'J'=>12,'K'=>12,'L'=>10];
foreach ($colWidths as $col => $width) {
    $sh->getColumnDimension($col)->setWidth($width);
}

// Freeze header row
$sh->freezePane('A2');

// ── Download ───────────────────────────────────────────────────────────────────
$filename = 'Hasil_' . preg_replace('/[^a-zA-Z0-9_\-]/', '_', $race['name']) . '_' . date('Ymd_His') . '.xlsx';

header('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
header('Content-Disposition: attachment;filename="' . $filename . '"');
header('Cache-Control: max-age=0');
(new Xlsx($ss))->save('php://output');
exit;
