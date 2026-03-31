<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

$db = getDB();
$id = (int) ($_GET['id'] ?? 0);

$race = $db->prepare('SELECT * FROM races WHERE id = ?');
$race->execute([$id]);
$race = $race->fetch();
if (!$race) {
  setFlash('danger', 'Lomba tidak ditemukan.');
  redirect('/pages/races/list.php');
}

$items = getItemsByRace($id);
$devices = $db->prepare('SELECT * FROM devices WHERE race_id = ? OR race_id IS NULL ORDER BY name');
$devices->execute([$id]);
$devices = $devices->fetchAll();

$chipCount = $db->prepare('SELECT COUNT(*) FROM chip_data WHERE race_id = ?');
$chipCount->execute([$id]);
$chipCount = $chipCount->fetchColumn();

$runnerCount = $db->prepare('SELECT COUNT(*) FROM runners WHERE race_id = ?');
$runnerCount->execute([$id]);
$runnerCount = $runnerCount->fetchColumn();

// Set gun time
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['set_gun_time'])) {
  $gt = trim($_POST['gun_time'] ?? '');
  $db->prepare('UPDATE races SET gun_time = ? WHERE id = ?')->execute([$gt ?: null, $id]);
  setFlash('success', 'Gun time berhasil diperbarui.');
  redirect('/pages/races/detail.php?id=' . $id);
}

$pageTitle = e($race['name']);
$currentPage = 'races';
$raceId = $id;
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/pages/races/list.php">Lomba</a>
  <span class="breadcrumb-sep">›</span>
  <span><?= e($race['name']) ?></span>
</div>

<div class="page-header">
  <div>
    <div class="page-title"><?= e($race['name']) ?></div>
    <div class="page-subtitle"><?= typeLabel($race['type']) ?> ·
      <?= $race['race_date'] ? formatDate($race['race_date']) : 'Tanggal belum ditentukan' ?>
    </div>
  </div>
  <div class="page-actions">
    <a href="/pages/races/edit.php?id=<?= $id ?>" class="btn btn-outline">Edit Lomba</a>
  </div>
</div>

<!-- Stats Bar -->
<div class="stats-grid" style="margin-bottom:24px">
  <div class="stat-card">
    <div class="stat-icon">📦</div>
    <div class="stat-value"><?= count($items) ?></div>
    <div class="stat-label">Kategori</div>
  </div>
  <div class="stat-card">
    <div class="stat-icon">🏃</div>
    <div class="stat-value"><?= number_format($runnerCount) ?></div>
    <div class="stat-label">Peserta</div>
  </div>
  <div class="stat-card">
    <div class="stat-icon">📡</div>
    <div class="stat-value"><?= number_format($chipCount) ?></div>
    <div class="stat-label">Chip Reads</div>
  </div>
  <div class="stat-card">
    <div class="stat-icon">📶</div>
    <div class="stat-value"><?= count($devices) ?></div>
    <div class="stat-label">Reader Terdaftar</div>
  </div>
</div>

<div style="display:grid;grid-template-columns:2fr 1fr;gap:24px;align-items:start">

  <div>
    <!-- Menu Akses Cepat -->
    <div class="card" style="margin-bottom:20px">
      <div class="card-header">
        <div class="card-title">Menu Cepat</div>
      </div>
      <div class="card-body" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
        <a href="/pages/runners/list.php?race_id=<?= $id ?>" class="btn btn-outline"
          style="flex-direction:column;padding:16px;height:80px;justify-content:center">
          <span style="font-size:24px">🏃</span>
          <span>Peserta</span>
        </a>
        <a href="/pages/rules/list.php?race_id=<?= $id ?>" class="btn btn-outline"
          style="flex-direction:column;padding:16px;height:80px;justify-content:center">
          <span style="font-size:24px">📋</span>
          <span>Aturan</span>
        </a>
        <a href="/pages/chip_data/list.php?race_id=<?= $id ?>" class="btn btn-outline"
          style="flex-direction:column;padding:16px;height:80px;justify-content:center">
          <span style="font-size:24px">📡</span>
          <span>Live Monitor</span>
        </a>
        <a href="/pages/results/list.php?race_id=<?= $id ?>" class="btn btn-outline"
          style="flex-direction:column;padding:16px;height:80px;justify-content:center">
          <span style="font-size:24px">🏆</span>
          <span>Hasil</span>
        </a>
        <a href="/pages/runners/import.php?race_id=<?= $id ?>" class="btn btn-outline"
          style="flex-direction:column;padding:16px;height:80px;justify-content:center">
          <span style="font-size:24px">📥</span>
          <span>Import CSV</span>
        </a>
        <a href="/pages/api_keys/list.php?race_id=<?= $id ?>" class="btn btn-outline"
          style="flex-direction:column;padding:16px;height:80px;justify-content:center">
          <span style="font-size:24px">🔑</span>
          <span>API Keys</span>
        </a>
      </div>
    </div>

    <!-- Kategori / Items -->
    <div class="card" style="margin-bottom:20px">
      <div class="card-header">
        <div class="card-title">Kategori Lomba</div>
      </div>
      <?php if ($items): ?>
        <div class="table-wrapper">
          <table class="table">
            <thead>
              <tr>
                <th>Judul</th>
                <th>Jarak</th>
                <th>Tipe</th>
              </tr>
            </thead>
            <tbody>
              <?php foreach ($items as $it): ?>
                <tr>
                  <td style="font-weight:600"><?= e($it['title']) ?></td>
                  <td><?= $it['distance'] ? number_format($it['distance'] / 1000, 1) . ' km' : '-' ?></td>
                  <td><span class="badge badge-primary"><?= ucfirst($it['type']) ?></span></td>
                </tr>
              <?php endforeach; ?>
            </tbody>
          </table>
        </div>
      <?php else: ?>
        <div class="card-body" style="color:var(--text-muted);font-size:13px">Belum ada kategori. <a
            href="/pages/races/edit.php?id=<?= $id ?>">Edit lomba</a> untuk menambahkan.</div>
      <?php endif; ?>
    </div>

    <!-- Reader Terdaftar -->
    <?php if ($devices): ?>
      <div class="card">
        <div class="card-header">
          <div class="card-title">📡 Reader Terdaftar</div>
        </div>
        <div class="table-wrapper">
          <table class="table">
            <thead>
              <tr>
                <th>Nama</th>
                <th>IP / ID</th>
                <th>Serial Number</th>
                <th>Posisi</th>
              </tr>
            </thead>
            <tbody>
              <?php foreach ($devices as $d): ?>
                <tr>
                  <td><strong><?= e($d['name']) ?></strong></td>
                  <td style="font-family:monospace;font-size:12px"><?= e($d['reader_ip'] ?: '-') ?></td>
                  <td style="font-family:monospace;font-size:11px">
                    <?php if ($d['serial_number']): ?>
                      <?= e($d['serial_number']) ?>
                      <span class="badge badge-success" style="font-size:10px;margin-left:4px">✅</span>
                    <?php else: ?>
                      <span style="color:var(--text-muted)">-</span>
                    <?php endif; ?>
                  </td>
                  <td style="font-size:12px">
                    <?= e($d['position'] ?: '-') ?>
                    <?php if (!$d['race_id']): ?>
                      <span class="badge badge-secondary" style="font-size:10px;margin-left:4px">Global</span>
                    <?php endif; ?>
                  </td>
                </tr>
              <?php endforeach; ?>
            </tbody>
          </table>
        </div>
      </div>
    <?php endif; ?>
  </div>

  <!-- Right Panel: Gun Time & Info -->
  <div>
    <div class="card" style="margin-bottom:20px">
      <div class="card-header">
        <div class="card-title">🔫 Gun Time</div>
      </div>
      <div class="card-body">
        <?php if ($race['gun_time']): ?>
          <div style="font-size:20px;font-weight:700;color:var(--warning);margin-bottom:12px">
            <?= formatDatetime($race['gun_time']) ?>
          </div>
        <?php else: ?>
          <div style="color:var(--text-muted);margin-bottom:12px;font-size:13px">Belum diatur — tekan saat pistol start
            ditembakkan.</div>
        <?php endif; ?>
        <form method="POST">
          <input type="hidden" name="set_gun_time" value="1">
          <div class="form-group" style="margin-bottom:10px">
            <input type="datetime-local" name="gun_time" id="gun_time_input" class="form-control" step="1"
              value="<?= $race['gun_time'] ? date('Y-m-d\TH:i:s', strtotime($race['gun_time'])) : '' ?>">
          </div>
          <div style="display:flex;gap:8px">
            <button type="button" class="btn btn-outline btn-sm" onclick="setGunTimeNow()">🔫 Sekarang!</button>
            <button type="submit" class="btn btn-primary btn-sm">Simpan</button>
          </div>
        </form>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">Info Lomba</div>
      </div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:12px;font-size:13px">
        <div><span style="color:var(--text-muted)">ID:</span> <strong><?= $race['id'] ?></strong></div>
        <div><span style="color:var(--text-muted)">Jenis:</span> <strong><?= typeLabel($race['type']) ?></strong></div>
        <div><span style="color:var(--text-muted)">Tanggal:</span>
          <strong><?= $race['race_date'] ? formatDate($race['race_date']) : '-' ?></strong>
        </div>
        <div><span style="color:var(--text-muted)">Waktu Start:</span> <strong><?= $race['race_time'] ?? '-' ?></strong>
        </div>
        <div><span style="color:var(--text-muted)">Dibuat:</span>
          <strong><?= formatDate($race['created_at']) ?></strong>
        </div>
        <?php if ($race['description']): ?>
          <div><span style="color:var(--text-muted)">Keterangan:</span><br><?= nl2br(e($race['description'])) ?></div>
        <?php endif; ?>
      </div>
    </div>

    <div class="card" style="margin-top:20px; border-color:#dc3545">
      <div class="card-header" style="background:#dc3545;color:white">
        <div class="card-title">⚠️ Danger Zone</div>
      </div>
      <div class="card-body">
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">
          Fitur ini akan <strong>menghapus permanen</strong> seluruh riwayat pembacaan reader dan hitungan juara untuk
          lomba ini. Sangat berguna untuk <strong style="color:var(--danger)">Reset Data</strong> setelah Anda selesai
          melakukan sesi uji coba (Testing).
        </p>
        <button class="btn" style="width:100%;background:#dc3545;color:white;border:none"
          onclick="resetRaceData(<?= $id ?>)">🗑️ Kosongkan Data Lomba Ini</button>
      </div>
    </div>
  </div>
</div>

<script>
  function resetRaceData(raceId) {
    if (confirm("🚨 PERINGATAN KERAS 🚨\n\nSeluruh riwayat pembacaan antena dan hasil lomba ini akan terhapus PERMANEN dan tidak bisa dikembalikan.\n\nApakah Anda sungguh yakin ingin meriset / membersihkannya?")) {
      fetch('/api/races_reset_data.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'race_id=' + raceId
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            alert('✅ Berhasil: ' + data.message);
            location.reload();
          } else {
            alert('❌ Gagal: ' + data.message);
          }
        })
        .catch(err => {
          alert('Terjadi kesalahan jaringan.');
          console.error(err);
        });
    }
  }
</script>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>