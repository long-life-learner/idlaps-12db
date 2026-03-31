<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

$db = getDB();

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['delete_id'])) {
    $id = (int)$_POST['delete_id'];
    $db->prepare('DELETE FROM devices WHERE id = ?')->execute([$id]);
    setFlash('success', 'Device berhasil dihapus.');
    redirect('/pages/devices/list.php');
}

$devices = $db->query(
    'SELECT d.*, r.name as race_name 
     FROM devices d 
     LEFT JOIN races r ON r.id = d.race_id 
     ORDER BY d.id DESC'
)->fetchAll();

$pageTitle   = 'Daftar Device / Reader';
$currentPage = 'devices';
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/">Utama</a><span class="breadcrumb-sep">›</span>
  <span>Pengaturan Device</span>
</div>

<div class="page-header">
  <div>
    <div class="page-title">📡 Device / Reader</div>
    <div class="page-subtitle">Kelola antena RFID fisik yang digunakan dalam lomba</div>
  </div>
  <div class="page-actions">
    <a href="/pages/devices/form.php" class="btn btn-primary">+ Tambah Device</a>
  </div>
</div>

<div class="card">
  <div class="table-wrapper">
    <?php if ($devices): ?>
    <table class="table">
      <thead>
        <tr>
          <th>Nama Device</th>
          <th>Reader IP / ID</th>
          <th>Serial Number (SN)</th>
          <th>Posisi / Lokasi</th>
          <th>Terkait Lomba</th>
          <th>Aksi</th>
        </tr>
      </thead>
      <tbody>
        <?php foreach ($devices as $d): ?>
        <tr>
          <td><strong><?= e($d['name']) ?></strong></td>
          <td style="font-family:monospace;color:var(--accent-light)"><?= e($d['reader_ip'] ?: '-') ?></td>
          <td>
            <?php if (!empty($d['serial_number'])): ?>
              <span style="font-family:monospace;font-size:11px;color:var(--text-secondary)"><?= e($d['serial_number']) ?></span>
              <span class="badge badge-success" style="margin-left:6px;font-size:10px">✅ Zero-Config</span>
            <?php else: ?>
              <span class="badge badge-secondary" style="font-size:10px">— Belum diisi</span>
            <?php endif; ?>
          </td>
          <td><?= e($d['position'] ?: '-') ?></td>
          <td><span class="badge badge-secondary"><?= e($d['race_name'] ?: 'Semua Lomba / Global') ?></span></td>
          <td>
            <div class="table-actions">
              <a href="/pages/devices/form.php?id=<?= $d['id'] ?>" class="btn btn-ghost btn-sm">Edit</a>
              <form method="POST" style="display:inline" onsubmit="confirmDelete(this, '<?= e($d['name']) ?>'); return false;">
                <input type="hidden" name="delete_id" value="<?= $d['id'] ?>">
                <button type="submit" class="btn btn-ghost btn-sm" style="color:var(--danger)">Hapus</button>
              </form>
            </div>
          </td>
        </tr>
        <?php endforeach; ?>
      </tbody>
    </table>
    <?php else: ?>
    <div class="empty-state">
      <div class="empty-state-icon">📡</div>
      <div class="empty-state-title">Belum ada Device</div>
      <div class="empty-state-desc">Tambahkan IP reader Anda untuk menggunakan penugasan titik timing spesifik.</div>
      <a href="/pages/devices/form.php" class="btn btn-primary">+ Tambah Device</a>
    </div>
    <?php endif; ?>
  </div>
</div>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>
