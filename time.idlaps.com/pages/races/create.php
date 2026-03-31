<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

$db  = getDB();
$errors = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $name      = trim($_POST['name'] ?? '');
    $type      = $_POST['type'] ?? 'running';
    $race_date = $_POST['race_date'] ?? null;
    $race_time = $_POST['race_time'] ?? null;
    $desc      = trim($_POST['description'] ?? '');

    if (!$name) $errors[] = 'Nama lomba wajib diisi.';

    // Items
    $itemTitles    = $_POST['item_title'] ?? [];
    $itemDistances = $_POST['item_distance'] ?? [];
    $itemTypes     = $_POST['item_type'] ?? [];

    if (!$errors) {
        $stmt = $db->prepare(
            'INSERT INTO races (name, type, race_date, race_time, description) VALUES (?,?,?,?,?)'
        );
        $stmt->execute([$name, $type, $race_date ?: null, $race_time ?: null, $desc]);
        $raceId = (int)$db->lastInsertId();

        // Items
        $si = $db->prepare(
            'INSERT INTO items (race_id, title, type, distance, sort_order) VALUES (?,?,?,?,?)'
        );
        foreach ($itemTitles as $idx => $title) {
            $title = trim($title);
            if (!$title) continue;
            $si->execute([
                $raceId,
                $title,
                $itemTypes[$idx] ?? 'normal',
                $itemDistances[$idx] ? (float)$itemDistances[$idx] : null,
                $idx,
            ]);
        }

        setFlash('success', "Lomba \"{$name}\" berhasil dibuat.");
        redirect('/pages/races/detail.php?id=' . $raceId);
    }
}

$pageTitle   = 'Buat Lomba Baru';
$currentPage = 'races';
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/pages/races/list.php">Lomba</a>
  <span class="breadcrumb-sep">›</span>
  <span>Buat Baru</span>
</div>

<div class="page-header">
  <div class="page-title">Buat Lomba Baru</div>
</div>

<?php if ($errors): ?>
  <div class="alert alert-danger"><?= implode('<br>', array_map('e', $errors)) ?></div>
<?php endif; ?>

<div class="card">
  <div class="card-body">
    <form method="POST">
      <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">

      <div class="form-grid" style="margin-bottom:24px">
        <div class="form-group full">
          <label class="form-label">Nama Lomba <span class="form-required">*</span></label>
          <input name="name" class="form-control" placeholder="contoh: IDLAPS Fun Run 2025"
                 value="<?= e($_POST['name'] ?? '') ?>" required>
        </div>
        <div class="form-group">
          <label class="form-label">Jenis Lomba</label>
          <select name="type" class="form-select">
            <?php foreach (['running'=>'Lari','triathlon'=>'Triathlon','cycling'=>'Sepeda','swimming'=>'Renang','other'=>'Lainnya'] as $v=>$l): ?>
            <option value="<?= $v ?>" <?= ($_POST['type'] ?? 'running') === $v ? 'selected' : '' ?>><?= $l ?></option>
            <?php endforeach; ?>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Tanggal Lomba</label>
          <input name="race_date" type="date" class="form-control" value="<?= e($_POST['race_date'] ?? '') ?>">
        </div>
        <div class="form-group">
          <label class="form-label">Waktu Mulai</label>
          <input name="race_time" type="time" class="form-control" value="<?= e($_POST['race_time'] ?? '') ?>">
        </div>
        <div class="form-group full">
          <label class="form-label">Deskripsi</label>
          <textarea name="description" class="form-textarea" rows="3"><?= e($_POST['description'] ?? '') ?></textarea>
        </div>
      </div>

      <!-- Items -->
      <div style="margin-bottom:20px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <div style="font-weight:700;font-size:15px">Kategori / Items</div>
          <button type="button" class="btn btn-outline btn-sm" onclick="addItem()">+ Tambah Kategori</button>
        </div>
        <div id="items-container">
          <div class="item-row" style="display:grid;grid-template-columns:3fr 1fr 1fr auto;gap:10px;margin-bottom:10px;align-items:end">
            <div class="form-group" style="margin:0">
              <label class="form-label">Judul</label>
              <input name="item_title[]" class="form-control" placeholder="contoh: 5KM">
            </div>
            <div class="form-group" style="margin:0">
              <label class="form-label">Jarak (m)</label>
              <input name="item_distance[]" type="number" class="form-control" placeholder="5000">
            </div>
            <div class="form-group" style="margin:0">
              <label class="form-label">Tipe</label>
              <select name="item_type[]" class="form-select">
                <option value="normal">Normal</option>
                <option value="team">Tim</option>
                <option value="relay">Estafet</option>
              </select>
            </div>
            <button type="button" class="btn btn-danger btn-sm" style="margin-bottom:0;align-self:flex-end" onclick="this.closest('.item-row').remove()">✕</button>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary">Simpan Lomba</button>
        <a href="/pages/races/list.php" class="btn btn-outline">Batal</a>
      </div>
    </form>
  </div>
</div>

<script>
function addItem() {
  const tpl = `<div class="item-row" style="display:grid;grid-template-columns:3fr 1fr 1fr auto;gap:10px;margin-bottom:10px;align-items:end">
    <div class="form-group" style="margin:0"><input name="item_title[]" class="form-control" placeholder="contoh: 10KM"></div>
    <div class="form-group" style="margin:0"><input name="item_distance[]" type="number" class="form-control" placeholder="10000"></div>
    <div class="form-group" style="margin:0">
      <select name="item_type[]" class="form-select">
        <option value="normal">Normal</option>
        <option value="team">Tim</option>
        <option value="relay">Estafet</option>
      </select>
    </div>
    <button type="button" class="btn btn-danger btn-sm" onclick="this.closest('.item-row').remove()">✕</button>
  </div>`;
  document.getElementById('items-container').insertAdjacentHTML('beforeend', tpl);
}
</script>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>
