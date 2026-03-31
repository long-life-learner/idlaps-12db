<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
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

$apiKey = $db->prepare(
  'SELECT * FROM api_keys WHERE (race_id = ? OR race_id IS NULL) AND is_active = 1 LIMIT 1'
);
$apiKey->execute([$raceId]);
$apiKey = $apiKey->fetch();

// Daftar reader yang sudah kirim data
$readers = $db->prepare(
  'SELECT DISTINCT reader_id FROM chip_data WHERE race_id = ? AND reader_id IS NOT NULL ORDER BY reader_id'
);
$readers->execute([$raceId]);
$readers = $readers->fetchAll(PDO::FETCH_COLUMN);

$totalReads = $db->prepare('SELECT COUNT(*) FROM chip_data WHERE race_id = ?');
$totalReads->execute([$raceId]);
$totalReads = $totalReads->fetchColumn();

$pageTitle = 'Live Monitor — ' . e($race['name']);
$currentPage = 'chip_data';
$extraScript = '<script>document.addEventListener("DOMContentLoaded",()=>startAutoRefresh(3000));</script>';
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/pages/races/list.php">Lomba</a><span class="breadcrumb-sep">›</span>
  <a href="/pages/races/detail.php?id=<?= $raceId ?>"><?= e($race['name']) ?></a><span class="breadcrumb-sep">›</span>
  <span>Live Monitor</span>
</div>

<div class="page-header">
  <div>
    <div class="page-title">📡 Live Monitor</div>
    <div class="page-subtitle"><?= e($race['name']) ?></div>
  </div>
  <span class="live-dot">AUTO REFRESH 3s</span>
</div>

<!-- Status Bar -->
<div class="status-bar">
  <div class="status-item">
    <div class="status-dot <?= $race['gun_time'] ? 'green' : 'red' ?>"></div>
    <span><?= $race['gun_time'] ? '🔫 ' . date('H:i:s', strtotime($race['gun_time'])) : 'Gun Time belum diatur' ?></span>
  </div>
  <div class="status-item">
    <strong id="total-reads"><?= number_format($totalReads) ?></strong>&nbsp;total reads
  </div>
  <div class="status-item">
    📶 <strong><?= count($readers) ?></strong>&nbsp;reader aktif
  </div>
</div>

<!-- Meta untuk JS -->
<div id="race-id-meta" data-race-id="<?= $raceId ?>" style="display:none"></div>

<!-- Filter -->
<div class="filter-bar">
  <label class="form-label" style="margin:0">Filter Reader:</label>
  <select id="reader-filter" class="form-select" style="max-width:200px" onchange="applyFilter()">
    <option value="">Semua Reader</option>
    <?php foreach ($readers as $r): ?>
      <option value="<?= e($r) ?>"><?= e($r) ?></option>
    <?php endforeach; ?>
  </select>
</div>

<div class="card">
  <div class="table-wrapper">
    <table class="table">
      <thead>
        <tr>
          <th>EPC</th>
          <th>Bib</th>
          <th>Reader IP</th>
          <th>Waktu Baca</th>
          <th>RSSI</th>
        </tr>
      </thead>
      <tbody id="live-tbody">
        <tr>
          <td colspan="5" style="text-align:center;color:var(--text-muted);padding:40px">Memuat data...</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>

<?php if ($apiKey): ?>
  <div class="card" style="margin-top:20px">
    <div class="card-header">
      <div class="card-title">🔑 API Key Aktif</div>
    </div>
    <div class="card-body">
      <p style="font-size:13px;color:var(--text-secondary);margin-bottom:10px">Gunakan key ini di pengaturan IDLAPS
        Checkpoint untuk mengirim data ke lomba ini:</p>
      <div class="api-key-display" data-copy="<?= e($apiKey['api_key']) ?>"><?= e($apiKey['api_key']) ?></div>
      <p style="font-size:11px;color:var(--text-muted);margin-top:8px">Klik untuk menyalin · Endpoint:
        <code><?= APP_URL ?>/api/checkpoint.php</code></p>
    </div>
  </div>
<?php endif; ?>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>