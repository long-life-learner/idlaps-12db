<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/includes/functions.php';
requireLogin();

$db = getDB();

// Statistik ringkas
$totalRaces   = $db->query('SELECT COUNT(*) FROM races')->fetchColumn();
$totalRunners = $db->query('SELECT COUNT(*) FROM runners')->fetchColumn();
$totalChips   = $db->query('SELECT COUNT(*) FROM chip_data')->fetchColumn();
$totalKeys    = $db->query('SELECT COUNT(*) FROM api_keys WHERE is_active = 1')->fetchColumn();

// Lomba terbaru (5)
$recentRaces = $db->query(
    'SELECT r.*, 
        (SELECT COUNT(*) FROM items i WHERE i.race_id = r.id) as item_count,
        (SELECT COUNT(*) FROM runners ru WHERE ru.race_id = r.id) as runner_count,
        (SELECT COUNT(*) FROM chip_data cd WHERE cd.race_id = r.id) as chip_count
     FROM races r ORDER BY r.created_at DESC LIMIT 5'
)->fetchAll();

// Data masuk terbaru (chip_data)
$recentChips = $db->query(
    'SELECT cd.*, r.name as race_name 
     FROM chip_data cd 
     LEFT JOIN races r ON r.id = cd.race_id 
     ORDER BY cd.created_at DESC LIMIT 10'
)->fetchAll();

$pageTitle  = 'Dashboard';
$currentPage = 'dashboard';
require_once __DIR__ . '/includes/header.php';
?>

<div class="page-header">
  <div>
    <div class="page-title">Dashboard</div>
    <div class="page-subtitle">Selamat datang kembali, <?= e($admin['name']) ?>!</div>
  </div>
  <div class="page-actions">
    <a href="/pages/races/create.php" class="btn btn-primary">+ Lomba Baru</a>
  </div>
</div>

<!-- Stats -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-icon">🏅</div>
    <div class="stat-value"><?= $totalRaces ?></div>
    <div class="stat-label">Total Lomba</div>
  </div>
  <div class="stat-card">
    <div class="stat-icon">🏃</div>
    <div class="stat-value"><?= number_format($totalRunners) ?></div>
    <div class="stat-label">Total Peserta</div>
  </div>
  <div class="stat-card">
    <div class="stat-icon">📡</div>
    <div class="stat-value"><?= number_format($totalChips) ?></div>
    <div class="stat-label">Total Chip Reads</div>
  </div>
  <div class="stat-card">
    <div class="stat-icon">🔑</div>
    <div class="stat-value"><?= $totalKeys ?></div>
    <div class="stat-label">API Keys Aktif</div>
  </div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start">

<!-- Lomba Terbaru -->
<div class="card">
  <div class="card-header">
    <div class="card-title">🏅 Lomba Terbaru</div>
    <a href="/pages/races/list.php" class="btn btn-outline btn-sm">Semua Lomba</a>
  </div>
  <div class="table-wrapper">
    <?php if ($recentRaces): ?>
    <table class="table">
      <thead>
        <tr>
          <th>Nama Lomba</th>
          <th>Tanggal</th>
          <th>Peserta</th>
          <th>Reads</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <?php foreach ($recentRaces as $r): ?>
        <tr>
          <td>
            <div style="font-weight:600"><?= e($r['name']) ?></div>
            <div style="font-size:11px;color:var(--text-muted)"><?= typeLabel($r['type']) ?></div>
          </td>
          <td><?= $r['race_date'] ? formatDate($r['race_date']) : '-' ?></td>
          <td><?= number_format($r['runner_count']) ?></td>
          <td><?= number_format($r['chip_count']) ?></td>
          <td>
            <a href="/pages/races/detail.php?id=<?= $r['id'] ?>" class="btn btn-ghost btn-xs">Detail →</a>
          </td>
        </tr>
        <?php endforeach; ?>
      </tbody>
    </table>
    <?php else: ?>
    <div class="empty-state" style="padding:40px">
      <div class="empty-state-icon">🏅</div>
      <div class="empty-state-title">Belum ada lomba</div>
      <a href="/pages/races/create.php" class="btn btn-primary btn-sm">+ Buat Lomba</a>
    </div>
    <?php endif; ?>
  </div>
</div>

<!-- Data Masuk Terbaru -->
<div class="card">
  <div class="card-header">
    <div class="card-title">📡 Chip Data Terbaru</div>
    <span class="live-dot">LIVE</span>
  </div>
  <div class="table-wrapper">
    <?php if ($recentChips): ?>
    <table class="table">
      <thead>
        <tr>
          <th>EPC</th>
          <th>Bib</th>
          <th>Reader IP</th>
          <th>Waktu</th>
        </tr>
      </thead>
      <tbody>
        <?php foreach ($recentChips as $c): ?>
        <tr>
          <td><span class="chip-tag"><?= e(substr($c['epc'], 0, 12)) ?>...</span></td>
          <td><strong><?= e($c['bib'] ?? '-') ?></strong></td>
          <td style="color:var(--text-muted);font-size:12px"><?= e($c['reader_id'] ?? '-') ?></td>
          <td style="font-size:12px;color:var(--text-muted)"><?= date('H:i:s', strtotime($c['read_time'])) ?></td>
        </tr>
        <?php endforeach; ?>
      </tbody>
    </table>
    <?php else: ?>
    <div class="empty-state" style="padding:40px">
      <div class="empty-state-icon">📡</div>
      <div class="empty-state-title">Belum ada data</div>
      <div class="empty-state-desc">Data akan muncul saat IDLAPS Checkpoint mengirim reads</div>
    </div>
    <?php endif; ?>
  </div>
</div>

</div>

<?php require_once __DIR__ . '/includes/footer.php'; ?>
