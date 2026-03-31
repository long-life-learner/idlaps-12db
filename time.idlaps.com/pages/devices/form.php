<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

$db = getDB();
$id = (int)($_GET['id'] ?? 0);
$device = null;

if ($id) {
    $stmt = $db->prepare('SELECT * FROM devices WHERE id = ?');
    $stmt->execute([$id]);
    $device = $stmt->fetch();
    if (!$device) {
        setFlash('danger', 'Device tidak ditemukan.');
        redirect('/pages/devices/list.php');
    }
}

// Load race list untuk opsi dropdown
$races = $db->query('SELECT id, name FROM races ORDER BY id DESC')->fetchAll();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $name  = trim($_POST['name']);
    $ip    = trim($_POST['reader_ip']);
    $sn    = strtoupper(trim($_POST['serial_number']));
    $pos   = trim($_POST['position']);
    $rId   = !empty($_POST['race_id']) ? (int)$_POST['race_id'] : null;
    $sn    = $sn ?: null; // simpan null jika kosong agar UNIQUE constraint aman

    if ($id) {
        $stmt = $db->prepare('UPDATE devices SET name=?, reader_ip=?, serial_number=?, position=?, race_id=? WHERE id=?');
        $stmt->execute([$name, $ip, $sn, $pos, $rId, $id]);
        setFlash('success', 'Device diperbarui.');
    } else {
        $stmt = $db->prepare('INSERT INTO devices (name, reader_ip, serial_number, position, race_id) VALUES (?,?,?,?,?)');
        $stmt->execute([$name, $ip, $sn, $pos, $rId]);
        setFlash('success', 'Device berhasil ditambahkan.');
    }
    redirect('/pages/devices/list.php');
}

$pageTitle   = ($id ? 'Edit' : 'Tambah') . ' Device';
$currentPage = 'devices';
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/">Utama</a><span class="breadcrumb-sep">›</span>
  <a href="/pages/devices/list.php">Device</a><span class="breadcrumb-sep">›</span>
  <span><?= $id ? 'Edit' : 'Tambah' ?></span>
</div>

<div class="page-title" style="margin-bottom:24px"><?= $id ? 'Edit' : 'Tambah' ?> Device / Reader</div>

<div class="card" style="max-width:600px">
  <div class="card-body">
    <form method="POST">
      <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">
      
      <div class="form-group" style="margin-bottom:16px">
        <label class="form-label">Nama Device <span class="form-required">*</span></label>
        <input type="text" name="name" class="form-control" value="<?= e($device['name'] ?? '') ?>" required placeholder="Contoh: Reader Finish Kiri">
      </div>

      <div class="form-group" style="margin-bottom:16px">
        <label class="form-label">Reader IP / ID Unik</label>
        <input type="text" name="reader_ip" class="form-control" value="<?= e($device['reader_ip'] ?? '') ?>" placeholder="Contoh: 192.168.1.201">
        <div class="form-hint">IP reader yang digunakan sebagai <code>reader_id</code> di laporan tap (untuk filter Live Monitor & Aturan Scoring).</div>
      </div>

      <div class="form-group" style="margin-bottom:16px">
        <label class="form-label" style="display:flex;align-items:center;gap:8px">
          Serial Number Hardware
          <span style="font-size:11px;background:rgba(99,102,241,0.15);color:#a78bfa;padding:2px 8px;border-radius:999px;font-weight:500">Zero-Config Auth</span>
        </label>
        <input type="text" name="serial_number" class="form-control" value="<?= e($device['serial_number'] ?? '') ?>" placeholder="Contoh: 363B37373632010134303837" maxlength="24" style="font-family:monospace;letter-spacing:1px">
        <div class="form-hint">
          Diisi dengan <strong>HEX String 24 karakter</strong> dari Serial Number hardware reader (12 bytes).<br>
          Cara mendapatkannya: di aplikasi IDLAPS Checkpoint desktop, buka koneksi ke reader → menu <strong>Device Info</strong> → salin nilai <em>Serial Number</em> yang tampil sebagai HEX.<br>
          Jika diisi, hardware <strong>tidak perlu API Key</strong> — sistem otomatis mengenali reader dan menentukan race-nya.
        </div>
      </div>

      <div class="form-group" style="margin-bottom:16px">
        <label class="form-label">Terkait Lomba</label>
        <select name="race_id" class="form-select">
          <option value="">— Bisa digunakan di SEMUA Lomba (Global) —</option>
          <?php foreach ($races as $r): ?>
          <option value="<?= $r['id'] ?>" <?= ($device['race_id'] ?? '') == $r['id'] ? 'selected' : '' ?>><?= e($r['name']) ?></option>
          <?php endforeach; ?>
        </select>
        <div class="form-hint">Kosongkan jika antena ini berpindah-pindah antar event.</div>
      </div>

      <div class="form-group" style="margin-bottom:24px">
        <label class="form-label">Posisi (Opsional)</label>
        <input type="text" name="position" class="form-control" value="<?= e($device['position'] ?? '') ?>" placeholder="Misal: Checkpoint 5KM - Jalur Kanan">
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary">Simpan Device</button>
        <a href="/pages/devices/list.php" class="btn btn-outline">Batal</a>
      </div>
    </form>
  </div>
</div>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>
