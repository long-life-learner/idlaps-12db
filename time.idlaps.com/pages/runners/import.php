<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
require_once __DIR__ . '/../../vendor/autoload.php';

use PhpOffice\PhpSpreadsheet\IOFactory;

requireLogin();

$db = getDB();
$raceId = (int) ($_GET['race_id'] ?? 0);
if (!$raceId)
  redirect('/pages/races/list.php');

$race = $db->prepare('SELECT * FROM races WHERE id = ?');
$race->execute([$raceId]);
$race = $race->fetch();
if (!$race) {
  setFlash('danger', 'Lomba tidak ditemukan.');
  redirect('/pages/races/list.php');
}

$items = getItemsByRace($raceId);
if (!$items) {
  setFlash('danger', 'Tambahkan kategori lomba terlebih dahulu.');
  redirect("/pages/races/edit.php?id={$raceId}");
}

// ─── Download Template ───────────────────────────────────────────────────────
if (isset($_GET['template'])) {
  $spreadsheet = new \PhpOffice\PhpSpreadsheet\Spreadsheet();
  $sheet = $spreadsheet->getActiveSheet();
  $sheet->setTitle('Peserta');

  // Header
  $headers = ['bib', 'epc', 'name', 'gender', 'item', 'age', 'age_group', 'team'];
  $sheet->fromArray([$headers], NULL, 'A1');

  // Contoh data
  $exampleItem = $items[0]['title'] ?? '5KM';
  $sheet->fromArray([
    ['001', 'E2003411B802011833301C01', 'Ahmad Fauzan', 'M', $exampleItem, 28, 'M30', 'Team Alpha'],
    ['002', 'E2003411B802011833301C02', 'Siti Rahayu', 'F', $exampleItem, 25, 'W25', 'Team Beta'],
    ['003', 'E2003411B802011833301C04', 'Budi Santoso', 'M', $exampleItem, 35, 'M35', ''],
  ], NULL, 'A2');

  // Style header
  $headerStyle = [
    'font' => ['bold' => true, 'color' => ['rgb' => 'FFFFFF']],
    'fill' => ['fillType' => 'solid', 'startColor' => ['rgb' => '1a73e8']],
  ];
  $sheet->getStyle('A1:H1')->applyFromArray($headerStyle);
  foreach (range('A', 'H') as $col) {
    $sheet->getColumnDimension($col)->setAutoSize(true);
  }

  // Format kolom bib sebagai teks agar '001' tidak jadi '1'
  $sheet->getStyle('A2:A10000')->getNumberFormat()->setFormatCode('@');
  $sheet->getStyle('B2:B10000')->getNumberFormat()->setFormatCode('@');

  header('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  header('Content-Disposition: attachment; filename="template_peserta_' . date('Ymd') . '.xlsx"');
  header('Cache-Control: max-age=0');

  $writer = IOFactory::createWriter($spreadsheet, 'Xlsx');
  $writer->save('php://output');
  exit;
}

// ─── Proses Upload ───────────────────────────────────────────────────────────
$submitted = $_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['import_file']);
$results = ['inserted' => 0, 'skipped' => 0, 'errors' => [], 'total_rows' => 0];

if ($submitted) {
  $file = $_FILES['import_file'];

  if ($file['error'] !== UPLOAD_ERR_OK || $file['size'] === 0) {
    $results['errors'][] = 'File gagal diupload (kode: ' . $file['error'] . ').';
  } else {
    try {
      // PhpSpreadsheet otomatis deteksi format: .xlsx, .xls, .csv, .ods
      $spreadsheet = IOFactory::load($file['tmp_name']);
      $sheet = $spreadsheet->getActiveSheet();
      $rows = $sheet->toArray(null, true, true, false);

      if (empty($rows)) {
        $results['errors'][] = 'File kosong atau tidak ada data yang bisa dibaca.';
        goto render;
      }

      // Baris pertama = header, lowercase & trim
      $rawHeader = array_shift($rows);
      $header = array_map(fn($h) => strtolower(trim((string) $h)), $rawHeader);

      // Validasi kolom wajib
      if (!in_array('bib', $header) || !in_array('epc', $header)) {
        $results['errors'][] = 'Kolom wajib "bib" dan/atau "epc" tidak ditemukan. '
          . 'Header terbaca: [' . implode(', ', $header) . ']';
        goto render;
      }

      // Build item map
      $itemMap = [];
      foreach ($items as $it) {
        $itemMap[strtolower(trim($it['title']))] = $it['id'];
      }
      $defaultItemId = $items[0]['id'];

      // Prepare statements
      $runnerStmt = $db->prepare(
        'INSERT INTO runners (race_id, item_id, bib, epc, name, gender, age, age_group, team)
                 VALUES (?,?,?,?,?,?,?,?,?)
                 ON DUPLICATE KEY UPDATE item_id=VALUES(item_id), epc=VALUES(epc),
                 name=VALUES(name), gender=VALUES(gender), age=VALUES(age),
                 age_group=VALUES(age_group), team=VALUES(team)'
      );
      $chipStmt = $db->prepare(
        'INSERT IGNORE INTO runner_chips (runner_id, race_id, epc, label) VALUES (?,?,?,?)'
      );
      $findRunner = $db->prepare('SELECT id FROM runners WHERE race_id=? AND bib=?');

      $rowNum = 1;
      $db->beginTransaction();
      try {
        foreach ($rows as $row) {
          $rowNum++;

          // Skip baris kosong
          if (empty($row) || trim(implode('', array_map('strval', $row))) === '')
            continue;
          $results['total_rows']++;

          // Map kolom ke nilai
          $row = array_pad(array_map('strval', $row), count($header), '');
          $data = array_combine($header, array_slice($row, 0, count($header)));
          if ($data === false) {
            $results['errors'][] = "Baris $rowNum: jumlah kolom tidak cocok.";
            $results['skipped']++;
            continue;
          }

          $bib = trim($data['bib'] ?? '');
          $name = trim($data['name'] ?? '');
          $gender = strtoupper(trim($data['gender'] ?? 'M'));
          $item = strtolower(trim($data['item'] ?? ''));

          // Multi-EPC: pisah dengan | didalam satu sel
          $epcRaw = trim($data['epc'] ?? '');
          $epcs = [];
          foreach (preg_split('/[|]+/', $epcRaw) as $ep) {
            $ep = strtoupper(preg_replace('/[^A-F0-9]/i', '', trim($ep)));
            if ($ep !== '')
              $epcs[] = $ep;
          }

          if ($bib === '' || empty($epcs)) {
            $results['errors'][] = "Baris $rowNum — bib='{$bib}' epc='{$epcRaw}' wajib diisi, dilewati.";
            $results['skipped']++;
            continue;
          }

          $itemId = $itemMap[$item] ?? $defaultItemId;

          try {
            $runnerStmt->execute([
              $raceId,
              $itemId,
              $bib,
              $epcs[0],
              $name ?: null,
              in_array($gender, ['M', 'F']) ? $gender : 'M',
              ((int) ($data['age'] ?? 0)) ?: null,
              ($data['age_group'] ?? '') ?: null,
              ($data['team'] ?? '') ?: null,
            ]);

            $runnerId = (int) $db->lastInsertId();
            if (!$runnerId) {
              $findRunner->execute([$raceId, $bib]);
              $runnerId = (int) $findRunner->fetchColumn();
            }

            foreach ($epcs as $i => $epc) {
              $chipStmt->execute([
                $runnerId,
                $raceId,
                $epc,
                $i === 0 ? 'Utama' : 'Chip ' . ($i + 1),
              ]);
            }
            $results['inserted']++;
          } catch (\Exception $ex) {
            $results['errors'][] = "Baris $rowNum (Bib=$bib): " . $ex->getMessage();
            $results['skipped']++;
          }
        }
        $db->commit();
      } catch (\Exception $ex) {
        $db->rollBack();
        $results['errors'][] = 'Error fatal saat proses data: ' . $ex->getMessage();
      }

    } catch (\Exception $ex) {
      $results['errors'][] = 'Gagal membaca file: ' . $ex->getMessage()
        . ' — Pastikan format file adalah .xlsx, .xls, atau .csv.';
    }
  }
}

render:
$pageTitle = 'Import Peserta — ' . e($race['name']);
$currentPage = 'runners';
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/pages/races/list.php">Lomba</a><span class="breadcrumb-sep">›</span>
  <a href="/pages/races/detail.php?id=<?= $raceId ?>"><?= e($race['name']) ?></a><span class="breadcrumb-sep">›</span>
  <span>Import Peserta</span>
</div>

<div class="page-header">
  <div class="page-title">📥 Import Peserta</div>
</div>

<?php if ($submitted): ?>
  <?php if ($results['inserted'] > 0): ?>
    <div class="alert alert-success">✅ <?= $results['inserted'] ?> peserta berhasil diimpor dari
      <?= $results['total_rows'] ?> baris data.
    </div>
  <?php elseif (empty($results['errors'])): ?>
    <div class="alert alert-warning">⚠️ Tidak ada data baru yang diimpor.</div>
  <?php endif; ?>

  <?php if ($results['skipped'] > 0): ?>
    <div class="alert alert-warning">⚠️ <?= $results['skipped'] ?> baris dilewati.</div>
  <?php endif; ?>

  <?php if ($results['errors']): ?>
    <div class="card" style="margin-bottom:20px">
      <div class="card-header">
        <div class="card-title">⚠ Detail Error</div>
      </div>
      <div class="card-body" style="max-height:300px;overflow-y:auto">
        <?php foreach ($results['errors'] as $err): ?>
          <div style="font-size:12px;color:var(--danger);padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04)">
            <?= e($err) ?>
          </div>
        <?php endforeach; ?>
      </div>
    </div>
  <?php endif; ?>
<?php endif; ?>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">

  <div class="card">
    <div class="card-header">
      <div class="card-title">Upload File</div>
    </div>
    <div class="card-body">
      <form method="POST" enctype="multipart/form-data">
        <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">
        <div class="form-group" style="margin-bottom:16px">
          <label class="form-label">File Excel atau CSV <span class="form-required">*</span></label>
          <input type="file" name="import_file" class="form-control" accept=".xlsx,.xls,.csv,.ods" required>
          <div class="form-hint">
            Mendukung: <strong>.xlsx</strong> (Excel), <strong>.xls</strong>, <strong>.csv</strong>,
            <strong>.ods</strong>
          </div>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">📥 Import Sekarang</button>
          <a href="?race_id=<?= $raceId ?>&template=1" class="btn btn-outline">⬇ Download Template .xlsx</a>
        </div>
      </form>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <div class="card-title">📋 Format & Petunjuk</div>
    </div>
    <div class="card-body">
      <div class="alert alert-info" style="font-size:12px;margin-bottom:16px">
        💡 Download template Excel, edit langsung di Excel, lalu upload kembali.
      </div>
      <table class="table" style="font-size:12px">
        <thead>
          <tr>
            <th>Kolom</th>
            <th>Wajib</th>
            <th>Keterangan</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>bib</code></td>
            <td>✅</td>
            <td>Nomor bib unik</td>
          </tr>
          <tr>
            <td><code>epc</code></td>
            <td>✅</td>
            <td>EPC chip RFID. Multi-chip pisah dengan <code>|</code> contoh: <code>ABCD|EFG1</code></td>
          </tr>
          <tr>
            <td><code>name</code></td>
            <td>–</td>
            <td>Nama peserta</td>
          </tr>
          <tr>
            <td><code>gender</code></td>
            <td>–</td>
            <td>M atau F</td>
          </tr>
          <tr>
            <td><code>item</code></td>
            <td>–</td>
            <td>Kategori: <strong><?= implode(', ', array_column($items, 'title')) ?></strong></td>
          </tr>
          <tr>
            <td><code>age</code></td>
            <td>–</td>
            <td>Umur (angka)</td>
          </tr>
          <tr>
            <td><code>age_group</code></td>
            <td>–</td>
            <td>Kelompok umur, misal M30</td>
          </tr>
          <tr>
            <td><code>team</code></td>
            <td>–</td>
            <td>Nama tim</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

</div>

<div style="margin-top:16px">
  <a href="/pages/runners/list.php?race_id=<?= $raceId ?>" class="btn btn-outline">← Kembali ke Daftar Peserta</a>
</div>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>