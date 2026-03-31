<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

$db = getDB();
$id = (int)($_GET['id'] ?? 0);

$race = $db->prepare('SELECT * FROM races WHERE id = ?');
$race->execute([$id]); $race = $race->fetch();
if (!$race) { setFlash('danger','Lomba tidak ditemukan.'); redirect('/pages/races/list.php'); }

$items = getItemsByRace($id);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $name      = trim($_POST['name'] ?? '');
    $type      = $_POST['type'] ?? 'running';
    $race_date = $_POST['race_date'] ?? null;
    $race_time = $_POST['race_time'] ?? null;
    $desc      = trim($_POST['description'] ?? '');

    if ($name) {
        $db->prepare('UPDATE races SET name=?,type=?,race_date=?,race_time=?,description=? WHERE id=?')
           ->execute([$name,$type,$race_date?:null,$race_time?:null,$desc,$id]);

        // Sync items
        $existing = array_column($items,'id');
        $posted   = $_POST['item_id'] ?? [];
        $postedTitles    = $_POST['item_title'] ?? [];
        $postedDistances = $_POST['item_distance'] ?? [];
        $postedTypes     = $_POST['item_type'] ?? [];

        $toDelete = array_diff($existing, array_filter(array_map('intval',$posted)));
        if ($toDelete) {
            $in = implode(',', array_fill(0,count($toDelete),'?'));
            $db->prepare("DELETE FROM items WHERE id IN($in)")->execute(array_values($toDelete));
        }

        foreach ($postedTitles as $idx => $title) {
            $title = trim($title);
            if (!$title) continue;
            $existId = (int)($posted[$idx] ?? 0);
            if ($existId) {
                $db->prepare('UPDATE items SET title=?,type=?,distance=?,sort_order=? WHERE id=?')
                   ->execute([$title,$postedTypes[$idx]??'normal',$postedDistances[$idx]?:(float)0?:null,$idx,$existId]);
            } else {
                $db->prepare('INSERT INTO items (race_id,title,type,distance,sort_order) VALUES (?,?,?,?,?)')
                   ->execute([$id,$title,$postedTypes[$idx]??'normal',$postedDistances[$idx]?:null,$idx]);
            }
        }

        setFlash('success','Lomba berhasil diperbarui.');
        redirect('/pages/races/detail.php?id=' . $id);
    }
}

$pageTitle   = 'Edit — ' . e($race['name']);
$currentPage = 'races';
$raceId      = $id;
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/pages/races/list.php">Lomba</a><span class="breadcrumb-sep">›</span>
  <a href="/pages/races/detail.php?id=<?= $id ?>"><?= e($race['name']) ?></a><span class="breadcrumb-sep">›</span>
  <span>Edit</span>
</div>

<div class="page-title" style="margin-bottom:24px">Edit Lomba</div>

<div class="card"><div class="card-body">
<form method="POST">
  <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">
  <div class="form-grid" style="margin-bottom:24px">
    <div class="form-group full">
      <label class="form-label">Nama Lomba <span class="form-required">*</span></label>
      <input name="name" class="form-control" value="<?= e($race['name']) ?>" required>
    </div>
    <div class="form-group">
      <label class="form-label">Jenis</label>
      <select name="type" class="form-select">
        <?php foreach(['running'=>'Lari','triathlon'=>'Triathlon','cycling'=>'Sepeda','swimming'=>'Renang','other'=>'Lainnya'] as $v=>$l): ?>
        <option value="<?=$v?>" <?=$race['type']===$v?'selected':''?>><?=$l?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">Tanggal</label>
      <input name="race_date" type="date" class="form-control" value="<?= e($race['race_date']??'') ?>">
    </div>
    <div class="form-group">
      <label class="form-label">Waktu Mulai</label>
      <input name="race_time" type="time" class="form-control" value="<?= e($race['race_time']??'') ?>">
    </div>
    <div class="form-group full">
      <label class="form-label">Deskripsi</label>
      <textarea name="description" class="form-textarea"><?= e($race['description']??'') ?></textarea>
    </div>
  </div>

  <div style="margin-bottom:20px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <div style="font-weight:700">Kategori / Items</div>
      <button type="button" class="btn btn-outline btn-sm" onclick="addItem()">+ Tambah</button>
    </div>
    <div id="items-container">
      <?php foreach ($items as $idx => $it): ?>
      <div class="item-row" style="display:grid;grid-template-columns:3fr 1fr 1fr auto;gap:10px;margin-bottom:10px;align-items:end">
        <input type="hidden" name="item_id[]" value="<?= $it['id'] ?>">
        <div class="form-group" style="margin:0"><input name="item_title[]" class="form-control" value="<?= e($it['title']) ?>"></div>
        <div class="form-group" style="margin:0"><input name="item_distance[]" type="number" class="form-control" value="<?= $it['distance'] ?>"></div>
        <div class="form-group" style="margin:0">
          <select name="item_type[]" class="form-select">
            <option value="normal" <?=$it['type']==='normal'?'selected':''?>>Normal</option>
            <option value="team"   <?=$it['type']==='team'?'selected':''?>>Tim</option>
            <option value="relay"  <?=$it['type']==='relay'?'selected':''?>>Estafet</option>
          </select>
        </div>
        <button type="button" class="btn btn-danger btn-sm" onclick="this.closest('.item-row').remove()">✕</button>
      </div>
      <?php endforeach; ?>
    </div>
  </div>

  <div class="form-actions">
    <button type="submit" class="btn btn-primary">Simpan Perubahan</button>
    <a href="/pages/races/detail.php?id=<?= $id ?>" class="btn btn-outline">Batal</a>
  </div>
</form>
</div></div>

<script>
function addItem() {
  document.getElementById('items-container').insertAdjacentHTML('beforeend',`<div class="item-row" style="display:grid;grid-template-columns:3fr 1fr 1fr auto;gap:10px;margin-bottom:10px;align-items:end">
    <input type="hidden" name="item_id[]" value="">
    <div class="form-group" style="margin:0"><input name="item_title[]" class="form-control" placeholder="Judul kategori"></div>
    <div class="form-group" style="margin:0"><input name="item_distance[]" type="number" class="form-control" placeholder="Jarak (m)"></div>
    <div class="form-group" style="margin:0"><select name="item_type[]" class="form-select"><option value="normal">Normal</option><option value="team">Tim</option><option value="relay">Estafet</option></select></div>
    <button type="button" class="btn btn-danger btn-sm" onclick="this.closest('.item-row').remove()">✕</button>
  </div>`);
}
</script>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>
