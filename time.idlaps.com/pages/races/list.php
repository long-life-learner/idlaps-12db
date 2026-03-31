<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

$db = getDB();
$races = $db->query(
    'SELECT r.*,
        (SELECT COUNT(*) FROM items i WHERE i.race_id = r.id) as item_count,
        (SELECT COUNT(*) FROM runners ru WHERE ru.race_id = r.id) as runner_count,
        (SELECT COUNT(*) FROM chip_data cd WHERE cd.race_id = r.id) as chip_count
     FROM races r ORDER BY r.created_at DESC'
)->fetchAll();

$pageTitle = 'Daftar Lomba';
$currentPage = 'races';
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="page-header">
  <div>
    <div class="page-title">Daftar Lomba</div>
    <div class="page-subtitle"><?= count($races) ?> lomba terdaftar</div>
  </div>
  <div class="page-actions">
    <a href="/pages/races/create.php" class="btn btn-primary">+ Lomba Baru</a>
  </div>
</div>

<?php if ($races): ?>
<div class="race-grid">
  <?php foreach ($races as $r): ?>
  <div class="race-card">
    <div class="race-card-header">
      <div>
        <div class="race-name"><?= e($r['name']) ?></div>
        <div class="race-meta">
          <?= typeLabel($r['type']) ?>
          <?php if ($r['race_date']): ?>
            &nbsp;·&nbsp; <?= formatDate($r['race_date']) ?>
          <?php endif; ?>
        </div>
      </div>
      <?= statusBadge($r['is_active'] ? 'active' : 'inactive') ?>
    </div>

    <?php if ($r['gun_time']): ?>
    <div style="font-size:12px;color:var(--warning);margin-bottom:8px">
      🔫 Gun Time: <?= formatDatetime($r['gun_time']) ?>
    </div>
    <?php endif; ?>

    <div class="race-stats">
      <div class="race-stat">
        <div class="race-stat-value"><?= $r['item_count'] ?></div>
        <div class="race-stat-label">Kategori</div>
      </div>
      <div class="race-stat">
        <div class="race-stat-value"><?= number_format($r['runner_count']) ?></div>
        <div class="race-stat-label">Peserta</div>
      </div>
      <div class="race-stat">
        <div class="race-stat-value"><?= number_format($r['chip_count']) ?></div>
        <div class="race-stat-label">Chip Reads</div>
      </div>
    </div>

    <div class="race-card-actions">
      <a href="/pages/races/detail.php?id=<?= $r['id'] ?>" class="btn btn-primary btn-sm">Detail</a>
      <a href="/pages/races/edit.php?id=<?= $r['id'] ?>" class="btn btn-outline btn-sm">Edit</a>
      <form method="POST" action="/pages/races/delete.php" style="margin:0" onsubmit="return confirm('Hapus lomba ini dan semua datanya?')">
        <input type="hidden" name="id" value="<?= $r['id'] ?>">
        <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">
        <button type="submit" class="btn btn-danger btn-sm">Hapus</button>
      </form>
    </div>
  </div>
  <?php endforeach; ?>
</div>
<?php else: ?>
<div class="empty-state">
  <div class="empty-state-icon">🏅</div>
  <div class="empty-state-title">Belum ada lomba</div>
  <div class="empty-state-desc">Buat lomba pertama Anda untuk mulai menggunakan sistem ini.</div>
  <a href="/pages/races/create.php" class="btn btn-primary">+ Buat Lomba Baru</a>
</div>
<?php endif; ?>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>
