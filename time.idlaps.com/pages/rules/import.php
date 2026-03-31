<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
require_once __DIR__ . '/../../vendor/autoload.php';

use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Writer\Xlsx;
use PhpOffice\PhpSpreadsheet\Style\Fill;
use PhpOffice\PhpSpreadsheet\IOFactory;

requireLogin();

$db     = getDB();
$raceId = (int)($_GET['race_id'] ?? 0);
if (!$raceId) redirect('/pages/races/list.php');

$race = $db->prepare('SELECT * FROM races WHERE id = ?');
$race->execute([$raceId]); $race = $race->fetch();
if (!$race) { setFlash('danger', 'Lomba tidak ditemukan.'); redirect('/pages/races/list.php'); }

$items   = getItemsByRace($raceId);
$itemMap = array_column($items, 'id', 'title'); // ['21KM' => 5, '10KM' => 6, ...]
$devices = $db->prepare('SELECT * FROM devices WHERE race_id = ? OR race_id IS NULL ORDER BY name');
$devices->execute([$raceId]);
$devices  = $devices->fetchAll();
$deviceMap = array_column($devices, 'id', 'name'); // ['Reader A' => 2, ...]

// ── Template download ──────────────────────────────────────────────────────────
if (($_GET['action'] ?? '') === 'template') {

    $ss  = new Spreadsheet();
    $sh  = $ss->getActiveSheet();
    $sh->setTitle('Aturan Scoring');

    $headers = [
        'item_title', 'timing_point', 'score_type', 'open_hh', 'open_mm', 'open_ss',
        'close_hh', 'close_mm', 'close_ss', 'fastest_speed', 'sort', 'must_pass',
        'auto_calculate', 'live_broadcast', 'device_name'
    ];

    // Style header
    $headerStyle = [
        'font' => ['bold' => true, 'color' => ['rgb' => 'FFFFFF']],
        'fill' => ['fillType' => Fill::FILL_SOLID, 'startColor' => ['rgb' => '4F46E5']],
    ];
    $sh->fromArray([$headers], null, 'A1');
    $sh->getStyle('A1:O1')->applyFromArray($headerStyle);

    // Contoh baris
    $examples = [];
    foreach ($items as $item) {
        $examples[] = [$item['title'], 'start',      'net_time', 0, 0, 0, 1, 0, 0, 10, 'first', 1, 1, 0, ''];
        $examples[] = [$item['title'], 'finish',     'net_time', 1, 0, 0, 8, 0, 0, 10, 'first', 1, 1, 1, ''];
    }
    $sh->fromArray($examples, null, 'A2');

    // Notes sheet
    $noteSh = $ss->createSheet();
    $noteSh->setTitle('Petunjuk');
    $notes = [
        ['Kolom',           'Nilai yang Valid'],
        ['item_title',      implode(', ', array_keys($itemMap)) ?: '(sesuai kategori lomba)'],
        ['timing_point',    'start | checkpoint | finish'],
        ['score_type',      'net_time | gun_time'],
        ['open_hh/mm/ss',   'Jam/Menit/Detik buka gate (0-23, 0-59, 0-59)'],
        ['close_hh/mm/ss',  'Jam/Menit/Detik tutup gate'],
        ['fastest_speed',   'Dalam m/s (contoh: 10 = 10 m/s ≈ 36 km/h)'],
        ['sort',            'first | last'],
        ['must_pass',       '1 (Ya) | 0 (Tidak)'],
        ['auto_calculate',  '1 (Ya) | 0 (Tidak)'],
        ['live_broadcast',  '1 (Ya) | 0 (Tidak)'],
        ['device_name',     implode(', ', array_keys($deviceMap)) ?: '(kosongkan jika semua reader)'],
    ];
    $noteSh->fromArray($notes, null, 'A1');
    $noteSh->getStyle('A1:B1')->getFont()->setBold(true);
    $noteSh->getColumnDimension('A')->setWidth(18);
    $noteSh->getColumnDimension('B')->setWidth(60);

    header('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    header('Content-Disposition: attachment;filename="Template_Aturan_' . preg_replace('/\s+/', '_', $race['name']) . '.xlsx"');
    header('Cache-Control: max-age=0');
    (new Xlsx($ss))->save('php://output');
    exit;
}

// ── Process Upload ─────────────────────────────────────────────────────────────
$importErrors  = [];
$importSuccess = 0;
$previewRows   = [];
$imported      = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!isset($_FILES['import_file']) || $_FILES['import_file']['error'] !== 0) {
        $importErrors[] = 'File tidak valid atau tidak diupload.';
    } else {
        try {
            $spreadsheet = IOFactory::load($_FILES['import_file']['tmp_name']);
            $rows = $spreadsheet->getActiveSheet()->toArray(null, true, true, false);

            $header = array_map('strtolower', array_map('trim', $rows[0]));

            $validTP     = ['start', 'checkpoint', 'finish'];
            $validST     = ['net_time', 'gun_time'];
            $validSort   = ['first', 'last'];

            $toInsert = [];

            for ($i = 1; $i < count($rows); $i++) {
                $row = array_combine($header, $rows[$i]);
                $lineNo = $i + 1;

                // Skip kosong
                if (empty(trim((string)($row['item_title'] ?? '')))) continue;

                $itemTitle = trim((string)$row['item_title']);
                $tp        = strtolower(trim((string)($row['timing_point'] ?? '')));
                $st        = strtolower(trim((string)($row['score_type'] ?? 'net_time')));
                $oph       = (int)($row['open_hh']  ?? 0);
                $opm       = (int)($row['open_mm']  ?? 0);
                $ops       = (int)($row['open_ss']  ?? 0);
                $clh       = (int)($row['close_hh'] ?? 8);
                $clm       = (int)($row['close_mm'] ?? 0);
                $cls       = (int)($row['close_ss'] ?? 0);
                $spd       = (float)($row['fastest_speed'] ?? 10);
                $sort      = strtolower(trim((string)($row['sort'] ?? 'first')));
                $must      = (int)(bool)($row['must_pass']      ?? 0);
                $auto      = (int)(bool)($row['auto_calculate'] ?? 1);
                $live      = (int)(bool)($row['live_broadcast'] ?? 0);
                $devName   = trim((string)($row['device_name'] ?? ''));

                // Validasi
                if (!array_key_exists($itemTitle, $itemMap)) {
                    $importErrors[] = "Baris {$lineNo}: item_title '{$itemTitle}' tidak cocok dengan kategori lomba.";
                    continue;
                }
                if (!in_array($tp, $validTP)) {
                    $importErrors[] = "Baris {$lineNo}: timing_point '{$tp}' tidak valid (start|checkpoint|finish).";
                    continue;
                }
                if (!in_array($st, $validST)) {
                    $st = 'net_time';
                }
                if (!in_array($sort, $validSort)) {
                    $sort = 'first';
                }

                $openSec  = $oph * 3600 + $opm * 60 + $ops;
                $closeSec = $clh * 3600 + $clm * 60 + $cls;
                $itemId   = $itemMap[$itemTitle];
                $deviceId = $devName && isset($deviceMap[$devName]) ? $deviceMap[$devName] : null;

                $toInsert[] = [
                    'item_id'        => $itemId,
                    'device_id'      => $deviceId,
                    'timing_point'   => $tp,
                    'score_type'     => $st,
                    'open_time'      => $openSec,
                    'close_time'     => $closeSec,
                    'fastest_speed'  => $spd,
                    'sort'           => $sort,
                    'must_pass'      => $must,
                    'auto_calculate' => $auto,
                    'live_broadcast' => $live,
                    'item_title'     => $itemTitle,
                    'device_name'    => $devName,
                ];
            }

            if (empty($toInsert) && empty($importErrors)) {
                $importErrors[] = 'Tidak ada baris data yang ditemukan dalam file.';
            }

            if (!empty($toInsert) && empty($importErrors)) {
                foreach ($toInsert as $row) {
                    $db->prepare(
                        'INSERT INTO timing_rules (item_id, device_id, timing_point, score_type, open_time, close_time,
                         fastest_speed, sort, must_pass, auto_calculate, live_broadcast)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?)'
                    )->execute([
                        $row['item_id'], $row['device_id'], $row['timing_point'], $row['score_type'],
                        $row['open_time'], $row['close_time'], $row['fastest_speed'], $row['sort'],
                        $row['must_pass'], $row['auto_calculate'], $row['live_broadcast']
                    ]);
                    $importSuccess++;
                }
                $imported = true;
                $previewRows = $toInsert;
            } else {
                $previewRows = $toInsert;
            }

        } catch (\Exception $e) {
            $importErrors[] = 'Gagal membaca file: ' . $e->getMessage();
        }
    }
}

$pageTitle   = 'Import Aturan — ' . e($race['name']);
$currentPage = 'rules';
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/pages/races/list.php">Lomba</a><span class="breadcrumb-sep">›</span>
  <a href="/pages/races/detail.php?id=<?= $raceId ?>"><?= e($race['name']) ?></a><span class="breadcrumb-sep">›</span>
  <a href="/pages/rules/list.php?race_id=<?= $raceId ?>">Aturan Scoring</a><span class="breadcrumb-sep">›</span>
  <span>Import</span>
</div>

<div class="page-header">
  <div>
    <div class="page-title">📥 Import Aturan Scoring</div>
    <div class="page-subtitle">Upload file Excel untuk membuat banyak aturan sekaligus</div>
  </div>
  <div class="page-actions">
    <a href="?race_id=<?= $raceId ?>&action=template" class="btn btn-outline">⬇ Download Template .xlsx</a>
    <a href="/pages/rules/list.php?race_id=<?= $raceId ?>" class="btn btn-ghost">← Kembali</a>
  </div>
</div>

<?php if ($imported): ?>
<div class="alert alert-success">
  ✅ <strong><?= $importSuccess ?> aturan berhasil diimpor!</strong>
  <a href="/pages/rules/list.php?race_id=<?= $raceId ?>" style="margin-left:16px">Lihat Aturan →</a>
</div>
<?php endif; ?>

<?php if ($importErrors): ?>
<div class="alert alert-danger" style="white-space:pre-line">
  <strong>⚠ Ditemukan masalah:</strong><br>
  <?= implode("\n", array_map('htmlspecialchars', $importErrors)) ?>
</div>
<?php endif; ?>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start">
  <div class="card">
    <div class="card-header"><div class="card-title">Upload File</div></div>
    <div class="card-body">
      <form method="POST" enctype="multipart/form-data">
        <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">
        <div class="form-group" style="margin-bottom:20px">
          <label class="form-label">File Excel (.xlsx / .xls)</label>
          <input type="file" name="import_file" class="form-control" accept=".xlsx,.xls,.ods,.csv" required>
          <div class="form-hint">
            Download dan isi template terlebih dahulu.<br>
            Kategori yang tersedia: <strong><?= implode(', ', array_keys($itemMap)) ?: '-' ?></strong>
          </div>
        </div>
        <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center">📥 Proses Import</button>
      </form>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><div class="card-title">💡 Panduan Kolom</div></div>
    <div class="card-body" style="font-size:13px">
      <table style="width:100%;border-collapse:collapse">
        <tr><th style="text-align:left;padding:4px 8px;color:var(--text-muted)">Kolom</th><th style="text-align:left;padding:4px 8px;color:var(--text-muted)">Nilai</th></tr>
        <tr><td style="padding:4px 8px"><code>item_title</code></td><td style="padding:4px 8px"><?= implode(', ', array_keys($itemMap)) ?></td></tr>
        <tr><td style="padding:4px 8px"><code>timing_point</code></td><td style="padding:4px 8px">start | checkpoint | finish</td></tr>
        <tr><td style="padding:4px 8px"><code>score_type</code></td><td style="padding:4px 8px">net_time | gun_time</td></tr>
        <tr><td style="padding:4px 8px"><code>open/close_hh/mm/ss</code></td><td style="padding:4px 8px">Angka (0–23, 0–59, 0–59)</td></tr>
        <tr><td style="padding:4px 8px"><code>fastest_speed</code></td><td style="padding:4px 8px">m/s (mis: 10)</td></tr>
        <tr><td style="padding:4px 8px"><code>must_pass</code></td><td style="padding:4px 8px">1 (Ya) | 0 (Tidak)</td></tr>
        <tr><td style="padding:4px 8px"><code>device_name</code></td><td style="padding:4px 8px"><?= implode(', ', array_keys($deviceMap)) ?: '(biarkan kosong)' ?></td></tr>
      </table>
    </div>
  </div>
</div>

<?php if ($previewRows): ?>
<div class="card" style="margin-top:24px">
  <div class="card-header"><div class="card-title">Preview Aturan <?= $imported ? '(Sudah Diimpor ✅)' : '(Gagal Diimpor)' ?></div></div>
  <div class="table-wrapper">
    <table class="table">
      <thead><tr><th>Kategori</th><th>Titik</th><th>Score</th><th>Buka</th><th>Tutup</th><th>Kec. Maks</th><th>Sort</th><th>Must Pass</th><th>Device</th></tr></thead>
      <tbody>
        <?php foreach ($previewRows as $r): ?>
        <tr>
          <td><?= e($r['item_title']) ?></td>
          <td><span class="badge badge-primary"><?= e($r['timing_point']) ?></span></td>
          <td><?= $r['score_type'] ?></td>
          <td><?= gmdate('H:i:s', $r['open_time']) ?></td>
          <td><?= gmdate('H:i:s', $r['close_time']) ?></td>
          <td><?= $r['fastest_speed'] ?> m/s</td>
          <td><?= $r['sort'] ?></td>
          <td><?= $r['must_pass'] ? '✅' : '—' ?></td>
          <td><?= e($r['device_name'] ?: '—') ?></td>
        </tr>
        <?php endforeach; ?>
      </tbody>
    </table>
  </div>
</div>
<?php endif; ?>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>
