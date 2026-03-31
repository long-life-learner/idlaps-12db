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

$items = getItemsByRace($raceId);
if (!$items) {
  setFlash('danger', 'Tambahkan kategori lomba terlebih dahulu.');
  redirect("/pages/races/edit.php?id={$raceId}");
}

$errors = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $itemId = (int) ($_POST['item_id'] ?? 0);
  $bib = trim($_POST['bib'] ?? '');
  $name = trim($_POST['name'] ?? '');
  $gender = $_POST['gender'] ?? 'M';
  $age = (int) ($_POST['age'] ?? 0);
  $ageGroup = trim($_POST['age_group'] ?? '');
  $team = trim($_POST['team'] ?? '');
  $phone = trim($_POST['phone'] ?? '');
  $email = trim($_POST['email'] ?? '');

  // EPC — bisa multi (nama field "epcs[]" dari form, tiap baris satu EPC)
  $epcRaw = is_array($_POST['epcs']) ? implode(',', $_POST['epcs']) : ($_POST['epcs'] ?? '');
  $epcParts = preg_split('/[,\n\r|;]+/', $epcRaw);
  $epcs = array_values(array_filter(array_map(
    function ($e) {
      return strtoupper(trim(str_replace(["\r", "\n"], '', $e))); },
    $epcParts
  )));


  if (!$itemId)
    $errors[] = 'Pilih kategori.';
  if (!$bib)
    $errors[] = 'Nomor bib wajib diisi.';
  if (!$epcs)
    $errors[] = 'Minimal 1 EPC chip wajib diisi.';

  // Cek duplikat bib
  if (!$errors) {
    $dupBib = $db->prepare('SELECT id FROM runners WHERE race_id = ? AND bib = ?');
    $dupBib->execute([$raceId, $bib]);
    if ($dupBib->fetch())
      $errors[] = "Bib '{$bib}' sudah digunakan peserta lain.";
  }

  // Cek duplikat EPC
  if (!$errors) {
    foreach ($epcs as $epc) {
      $dupEpc = $db->prepare('SELECT rc.epc FROM runner_chips rc WHERE rc.race_id = ? AND rc.epc = ?');
      $dupEpc->execute([$raceId, $epc]);
      if ($dupEpc->fetch()) {
        $errors[] = "EPC '{$epc}' sudah digunakan peserta lain.";
      }
    }
  }

  if (!$errors) {
    $db->beginTransaction();
    try {
      // Simpan runner
      $db->prepare(
        'INSERT INTO runners (race_id, item_id, bib, epc, name, gender, age, age_group, team, phone, email)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
      )->execute([
            $raceId,
            $itemId,
            $bib,
            $epcs[0],   // EPC pertama juga disimpan sebagai primary chip di runners.epc
            $name ?: null,
            in_array($gender, ['M', 'F']) ? $gender : 'M',
            $age ?: null,
            $ageGroup ?: null,
            $team ?: null,
            $phone ?: null,
            $email ?: null,
          ]);
      $runnerId = (int) $db->lastInsertId();

      // Simpan semua EPC ke runner_chips
      $epcLabels = $_POST['epc_labels'] ?? [];
      $chipStmt = $db->prepare(
        'INSERT IGNORE INTO runner_chips (runner_id, race_id, epc, label) VALUES (?,?,?,?)'
      );
      foreach ($epcs as $i => $epc) {
        $label = trim($epcLabels[$i] ?? '') ?: ($i === 0 ? 'Utama' : "Chip " . ($i + 1));
        $chipStmt->execute([$runnerId, $raceId, $epc, $label]);
      }

      $db->commit();
      setFlash('success', "Peserta Bib #{$bib} berhasil ditambahkan.");
      redirect("/pages/runners/list.php?race_id={$raceId}");
    } catch (\Exception $e) {
      $db->rollBack();
      $errors[] = 'Gagal menyimpan: ' . $e->getMessage();
    }
  }
}

$pageTitle = 'Tambah Peserta — ' . e($race['name']);
$currentPage = 'runners';
$raceIdVar = $raceId;
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/pages/races/list.php">Lomba</a><span class="breadcrumb-sep">›</span>
  <a href="/pages/races/detail.php?id=<?= $raceId ?>"><?= e($race['name']) ?></a><span class="breadcrumb-sep">›</span>
  <a href="/pages/runners/list.php?race_id=<?= $raceId ?>">Peserta</a><span class="breadcrumb-sep">›</span>
  <span>Tambah</span>
</div>

<div class="page-title" style="margin-bottom:24px">Tambah Peserta Baru</div>

<?php if ($errors): ?>
  <div class="alert alert-danger"><?= implode('<br>', array_map('e', $errors)) ?></div>
<?php endif; ?>

<div class="card">
  <div class="card-body">
    <form method="POST">
      <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">

      <!-- Info Dasar -->
      <div style="font-weight:700;font-size:14px;margin-bottom:14px;color:var(--text-secondary)">Informasi Dasar</div>
      <div class="form-grid" style="margin-bottom:24px">
        <div class="form-group">
          <label class="form-label">Kategori <span class="form-required">*</span></label>
          <select name="item_id" class="form-select" required>
            <option value="">— Pilih Kategori —</option>
            <?php foreach ($items as $it): ?>
              <option value="<?= $it['id'] ?>" <?= ($_POST['item_id'] ?? '') == $it['id'] ? 'selected' : '' ?>>
                <?= e($it['title']) ?></option>
            <?php endforeach; ?>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Nomor Bib <span class="form-required">*</span></label>
          <input name="bib" class="form-control" placeholder="001" value="<?= e($_POST['bib'] ?? '') ?>" required>
        </div>
        <div class="form-group">
          <label class="form-label">Nama Lengkap</label>
          <input name="name" class="form-control" placeholder="Ahmad Fauzan" value="<?= e($_POST['name'] ?? '') ?>">
        </div>
        <div class="form-group">
          <label class="form-label">Gender</label>
          <select name="gender" class="form-select">
            <option value="M" <?= ($_POST['gender'] ?? 'M') === 'M' ? 'selected' : '' ?>>♂ Putra</option>
            <option value="F" <?= ($_POST['gender'] ?? '') === 'F' ? 'selected' : '' ?>>♀ Putri</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Umur</label>
          <input name="age" type="number" class="form-control" value="<?= e($_POST['age'] ?? '') ?>">
        </div>
        <div class="form-group">
          <label class="form-label">Kelompok Umur</label>
          <input name="age_group" class="form-control" placeholder="M30, W25, dll"
            value="<?= e($_POST['age_group'] ?? '') ?>">
        </div>
        <div class="form-group">
          <label class="form-label">Tim</label>
          <input name="team" class="form-control" placeholder="Nama tim (opsional)"
            value="<?= e($_POST['team'] ?? '') ?>">
        </div>
        <div class="form-group">
          <label class="form-label">No. HP</label>
          <input name="phone" type="tel" class="form-control" value="<?= e($_POST['phone'] ?? '') ?>">
        </div>
        <div class="form-group full">
          <label class="form-label">Email</label>
          <input name="email" type="email" class="form-control" value="<?= e($_POST['email'] ?? '') ?>">
        </div>
      </div>

      <!-- EPC Chips — Multi -->
      <div style="font-weight:700;font-size:14px;margin-bottom:8px;color:var(--text-secondary)">
        📡 RFID Chip (EPC)
        <span style="font-size:12px;font-weight:400;color:var(--text-muted);margin-left:8px">— Peserta boleh memiliki
          lebih dari 1 chip</span>
      </div>
      <div
        style="background:rgba(79,142,247,0.06);border:1px solid var(--border-accent);border-radius:var(--radius);padding:16px;margin-bottom:24px">
        <div id="epc-list">
          <div class="epc-row"
            style="display:grid;grid-template-columns:1fr 1fr auto;gap:10px;margin-bottom:10px;align-items:end">
            <div class="form-group" style="margin:0">
              <label class="form-label">EPC Code <span class="form-required">*</span></label>
              <input name="epcs" class="form-control" placeholder="E2003411B802011833301C01"
                style="font-family:monospace" value="<?= e(explode(',', $_POST['epcs'] ?? '')[0] ?? '') ?>">
            </div>
            <div class="form-group" style="margin:0">
              <label class="form-label">Label</label>
              <input name="epc_labels[]" class="form-control" value="Utama" placeholder="Utama / Bib / Kaki Kiri">
            </div>
            <div style="padding-bottom:0;align-self:flex-end">
              <button type="button" class="btn btn-ghost btn-sm" title="Tidak dapat dihapus"
                style="opacity:0.3;cursor:default">✕</button>
            </div>
          </div>
        </div>
        <button type="button" class="btn btn-outline btn-sm" onclick="addEpc()">+ Tambah Chip / EPC</button>
        <div class="form-hint" style="margin-top:8px">EPC bisa dilihat di sticker chip atau scan menggunakan RFID
          reader. Format: hex uppercase.</div>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary">Simpan Peserta</button>
        <a href="/pages/runners/list.php?race_id=<?= $raceId ?>" class="btn btn-outline">Batal</a>
      </div>
    </form>
  </div>
</div>

<script>
  let epcCount = 1;
  function addEpc() {
    epcCount++;
    const row = `<div class="epc-row" style="display:grid;grid-template-columns:1fr 1fr auto;gap:10px;margin-bottom:10px;align-items:end">
    <div class="form-group" style="margin:0">
      <input name="epcs" class="form-control" placeholder="E2003411B802..." style="font-family:monospace" required>
    </div>
    <div class="form-group" style="margin:0">
      <input name="epc_labels[]" class="form-control" value="Chip ${epcCount}" placeholder="Label chip">
    </div>
    <div style="align-self:flex-end">
      <button type="button" class="btn btn-danger btn-sm" onclick="this.closest('.epc-row').remove()">✕</button>
    </div>
  </div>`;
    document.getElementById('epc-list').insertAdjacentHTML('beforeend', row);
  }
</script>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>