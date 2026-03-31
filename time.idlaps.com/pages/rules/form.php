<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

$db     = getDB();
$raceId = (int)($_GET['race_id'] ?? 0);
$ruleId = (int)($_GET['rule_id'] ?? 0);
if (!$raceId) redirect('/pages/races/list.php');

$race = $db->prepare('SELECT * FROM races WHERE id = ?');
$race->execute([$raceId]); $race = $race->fetch();
if (!$race) { setFlash('danger','Lomba tidak ditemukan.'); redirect('/pages/races/list.php'); }

$items   = getItemsByRace($raceId);
$devices = $db->prepare('SELECT * FROM devices WHERE race_id = ? OR race_id IS NULL ORDER BY name');
$devices->execute([$raceId]);
$devices = $devices->fetchAll();

$rule = null;
if ($ruleId) {
    $s = $db->prepare('SELECT * FROM timing_rules WHERE id = ?');
    $s->execute([$ruleId]); $rule = $s->fetch();
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $itemId      = (int)$_POST['item_id'];
    $deviceId    = $_POST['device_id'] ? (int)$_POST['device_id'] : null;
    $tp          = $_POST['timing_point'];
    $scoreType   = $_POST['score_type'];
    $openH       = (int)$_POST['open_h']; $openM = (int)$_POST['open_m']; $openS = (int)$_POST['open_s'];
    $closeH      = (int)$_POST['close_h'];$closeM= (int)$_POST['close_m'];$closeS=(int)$_POST['close_s'];
    $openTime    = $openH*3600 + $openM*60 + $openS;
    $closeTime   = $closeH*3600+ $closeM*60+ $closeS;
    $fastestSpeed= (float)$_POST['fastest_speed'];
    $sort        = $_POST['sort'];
    $mustPass    = isset($_POST['must_pass']) ? 1 : 0;
    $autoCalc    = isset($_POST['auto_calculate']) ? 1 : 0;
    $liveBcast   = isset($_POST['live_broadcast']) ? 1 : 0;
    $howMany     = max(1,(int)$_POST['how_many_passes']);

    if ($ruleId) {
        $db->prepare(
            'UPDATE timing_rules SET item_id=?,device_id=?,timing_point=?,score_type=?,open_time=?,close_time=?,
             fastest_speed=?,sort=?,must_pass=?,auto_calculate=?,live_broadcast=?,how_many_passes=? WHERE id=?'
        )->execute([$itemId,$deviceId,$tp,$scoreType,$openTime,$closeTime,$fastestSpeed,$sort,$mustPass,$autoCalc,$liveBcast,$howMany,$ruleId]);
        setFlash('success','Aturan berhasil diperbarui.');
    } else {
        $db->prepare(
            'INSERT INTO timing_rules (item_id,device_id,timing_point,score_type,open_time,close_time,
             fastest_speed,sort,must_pass,auto_calculate,live_broadcast,how_many_passes)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?)'
        )->execute([$itemId,$deviceId,$tp,$scoreType,$openTime,$closeTime,$fastestSpeed,$sort,$mustPass,$autoCalc,$liveBcast,$howMany]);
        setFlash('success','Aturan berhasil ditambahkan.');
    }
    redirect("/pages/rules/list.php?race_id={$raceId}");
}

$pageTitle   = ($ruleId ? 'Edit' : 'Tambah') . ' Aturan — ' . e($race['name']);
$currentPage = 'rules';
require_once __DIR__ . '/../../includes/header.php';

// Parse open/close time for existing rule
$openH=$openM=$openS=$closeH=$closeM=$closeS=0;
if ($rule) {
    $openH=intdiv($rule['open_time'],3600); $openM=intdiv($rule['open_time']%3600,60); $openS=$rule['open_time']%60;
    $closeH=intdiv($rule['close_time'],3600);$closeM=intdiv($rule['close_time']%3600,60);$closeS=$rule['close_time']%60;
}
?>

<div class="breadcrumb">
  <a href="/pages/races/list.php">Lomba</a><span class="breadcrumb-sep">›</span>
  <a href="/pages/races/detail.php?id=<?= $raceId ?>"><?= e($race['name']) ?></a><span class="breadcrumb-sep">›</span>
  <a href="/pages/rules/list.php?race_id=<?= $raceId ?>">Aturan</a><span class="breadcrumb-sep">›</span>
  <span><?= $ruleId ? 'Edit' : 'Tambah' ?></span>
</div>

<div class="page-title" style="margin-bottom:24px"><?= $ruleId ? 'Edit' : 'Tambah' ?> Aturan Scoring</div>

<div class="card" style="overflow:visible">
<div class="card-body">
<form method="POST">
  <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">

  <div class="form-grid" style="margin-bottom:20px">
    <div class="form-group">
      <label class="form-label">Kategori <span class="form-required">*</span></label>
      <select name="item_id" class="form-select" required>
        <?php foreach ($items as $it): ?>
        <option value="<?= $it['id'] ?>" <?= ($rule['item_id'] ?? '') == $it['id'] ? 'selected' : '' ?>><?= e($it['title']) ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">Timing Point <span class="form-required">*</span></label>
      <select name="timing_point" class="form-select" required>
        <option value="start"      <?= ($rule['timing_point']??'') === 'start'      ? 'selected':'' ?>>🚀 Start</option>
        <option value="checkpoint" <?= ($rule['timing_point']??'') === 'checkpoint' ? 'selected':'' ?>>📌 Checkpoint</option>
        <option value="finish"     <?= ($rule['timing_point']??'') === 'finish'     ? 'selected':'' ?>>🏁 Finish</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label" style="display:flex;align-items:center;gap:6px">
        Device / Reader
        <span class="flag-card__tooltip-trigger" tabindex="0" style="margin-left:0;font-size:12px;display:inline-flex">❓
          <div class="flag-card__tooltip" style="top:22px;right:0;height:320px;">
            <strong>Device / Reader Spesifik</strong><br><br>
            Tentukan reader mana yang "dipercaya" untuk titik ini.<br><br>
            Jika <strong>dipilih</strong>: titik ini hanya akan menerima data tap dari reader yang dipilih. Sangat berguna jika letak antena berdekatan (misal matras 5KM dan 10KM bersebelahan) untuk mencegah data nyasar ke kategori/checkpoint yang salah.<br><br>
            Jika <strong>Tidak ditentukan</strong>: titik ini menerima data dari SEMUA reader asalkan dilakukan direntang waktu yang benar.
          </div>
        </span>
      </label>
      <select name="device_id" class="form-select">
        <option value="">— Tidak ditentukan —</option>
        <?php foreach ($devices as $d): ?>
        <option value="<?= $d['id'] ?>" <?= ($rule['device_id']??'') == $d['id'] ? 'selected':'' ?>>
          <?= e($d['name']) ?> (<?= e($d['reader_ip']) ?>)
        </option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label" style="display:flex;align-items:center;gap:6px">
        Tipe Score Utama
        <span class="flag-card__tooltip-trigger" tabindex="0" style="margin-left:0;font-size:12px;display:inline-flex">❓
          <div class="flag-card__tooltip" style="top:22px;left:0;height:320px;">
            <strong>Tipe Kalkulasi Pemenang</strong><br><br>
            Status ini menentukan basis pengurutan untuk menentukan juara berdasarkan regulasi lomba:<br><br>
            ⏳ <strong>Gun Time</strong>: Dihitung sejak <em>pistol start diletuskan</em> hingga pelari finish (waktu resmi, siapa cepat melintasi garis finish). Lazim dipakai untuk Podium Overall.<br><br>
            ⏱️ <strong>Net Time (Chip Time)</strong>: Dihitung sejak pelari <em>menginjak karpet start</em> hingga menginjak karpet finish. Lebih fair membandingkan pace murni, lazim untuk Age Group / Personal Best.
          </div>
        </span>
      </label>
      <select name="score_type" class="form-select">
        <option value="net_time" <?= ($rule['score_type']??'net_time')==='net_time'?'selected':'' ?>>Net Time</option>
        <option value="gun_time" <?= ($rule['score_type']??'')==='gun_time'?'selected':'' ?>>Gun Time</option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">Open Time (HH:MM:SS dari gun time)</label>
      <div style="display:flex;gap:6px">
        <input name="open_h" type="number" min="0" max="99" class="form-control" value="<?= $openH ?>" style="width:64px">
        <input name="open_m" type="number" min="0" max="59" class="form-control" value="<?= $openM ?>" style="width:60px">
        <input name="open_s" type="number" min="0" max="59" class="form-control" value="<?= $openS ?>" style="width:60px">
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">Close Time (HH:MM:SS dari gun time)</label>
      <div style="display:flex;gap:6px">
        <input name="close_h" type="number" min="0" max="99" class="form-control" value="<?= $closeH ?>" style="width:64px">
        <input name="close_m" type="number" min="0" max="59" class="form-control" value="<?= $closeM ?>" style="width:60px">
        <input name="close_s" type="number" min="0" max="59" class="form-control" value="<?= $closeS ?>" style="width:60px">
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">Kecepatan Max (m/s)</label>
      <input name="fastest_speed" type="number" step="0.1" class="form-control" value="<?= $rule['fastest_speed'] ?? 10 ?>">
      <div class="form-hint">Filter data tidak valid. Lari = 10 m/s, Sepeda = 20 m/s</div>
    </div>
    <div class="form-group">
      <label class="form-label">Sort</label>
      <select name="sort" class="form-select">
        <option value="first" <?= ($rule['sort']??'first')==='first'?'selected':'' ?>>Rekam Pertama</option>
        <option value="last"  <?= ($rule['sort']??'')==='last'?'selected':'' ?>>Rekam Terakhir</option>
      </select>
      <div class="form-hint">Start = Terakhir, Finish = Pertama (lazimnya)</div>
    </div>
    <div class="form-group">
      <label class="form-label">Banyak Lintas (lap)</label>
      <input name="how_many_passes" type="number" min="1" class="form-control" value="<?= $rule['how_many_passes'] ?? 1 ?>">
    </div>
  </div>

  <div style="display:flex;gap:20px;margin-bottom:20px;flex-wrap:wrap">

    <!-- Must Pass -->
    <label class="flag-card <?= ($rule['must_pass'] ?? 0) ? 'flag-card--on' : '' ?>" id="flag-must-pass">
      <input type="checkbox" name="must_pass" id="cb-must-pass"
             <?= ($rule['must_pass'] ?? 0) ? 'checked' : '' ?>
             onchange="this.closest('.flag-card').classList.toggle('flag-card--on', this.checked)">
      <div class="flag-card__header">
        <span class="flag-card__icon">🚧</span>
        <span class="flag-card__title">Must Pass</span>
        <span class="flag-card__tooltip-trigger" tabindex="0" title="">❓
          <div class="flag-card__tooltip">
            <strong>Must Pass — Wajib Dilalui</strong><br><br>
            Jika <em>aktif</em>: runner yang tidak terdeteksi di titik ini akan diberi status <strong>DNF</strong> (finish) atau <strong>DSQ</strong> (checkpoint).<br><br>
            Jika <em>nonaktif</em>: titik ini bersifat opsional — tidak terdeteksi tidak mempengaruhi keabsahan hasil.<br><br>
            <em>Contoh:</em><br>
            ✅ Start & Finish → aktifkan (wajib)<br>
            ✅ Checkpoint anti-curang → aktifkan<br>
            ❌ Chip bib display-only → nonaktifkan
          </div>
        </span>
      </div>
      <div class="flag-card__desc">Runner tidak terdeteksi = DNF / DSQ</div>
    </label>

    <!-- Auto Kalkulasi -->
    <label class="flag-card <?= ($rule['auto_calculate'] ?? 1) ? 'flag-card--on' : '' ?>" id="flag-auto-calc">
      <input type="checkbox" name="auto_calculate" id="cb-auto-calc"
             <?= ($rule['auto_calculate'] ?? 1) ? 'checked' : '' ?>
             onchange="this.closest('.flag-card').classList.toggle('flag-card--on', this.checked)">
      <div class="flag-card__header">
        <span class="flag-card__icon">⚙️</span>
        <span class="flag-card__title">Auto Kalkulasi</span>
        <span class="flag-card__tooltip-trigger" tabindex="0">❓
          <div class="flag-card__tooltip">
            <strong>Auto Kalkulasi</strong><br><br>
            Jika <em>aktif</em>: data dari timing point ini digunakan untuk menghitung Net Time / Gun Time hasil akhir runner.<br><br>
            Jika <em>nonaktif</em>: data tetap direkam di database, tapi diabaikan dalam proses kalkulasi hasil.<br><br>
            <em>Contoh:</em><br>
            ✅ Start & Finish → aktifkan<br>
            ❌ Reader pantauan saja (monitoring only) → nonaktifkan
          </div>
        </span>
      </div>
      <div class="flag-card__desc">Digunakan dalam hitung waktu akhir</div>
    </label>

    <!-- Live Broadcast -->
    <label class="flag-card <?= ($rule['live_broadcast'] ?? 1) ? 'flag-card--on' : '' ?>" id="flag-live-bcast">
      <input type="checkbox" name="live_broadcast" id="cb-live-bcast"
             <?= ($rule['live_broadcast'] ?? 1) ? 'checked' : '' ?>
             onchange="this.closest('.flag-card').classList.toggle('flag-card--on', this.checked)">
      <div class="flag-card__header">
        <span class="flag-card__icon">📡</span>
        <span class="flag-card__title">Live Broadcast</span>
        <span class="flag-card__tooltip-trigger" tabindex="0">❓
          <div class="flag-card__tooltip">
            <strong>Live Broadcast</strong><br><br>
            Jika <em>aktif</em>: data chip dari titik ini akan ditampilkan di halaman Live Monitor publik (layar race) secara real-time.<br><br>
            Jika <em>nonaktif</em>: data tetap direkam tapi tidak tampil di layar publik — hanya terlihat admin.<br><br>
            <em>Contoh:</em><br>
            ✅ Finish → aktifkan (tampilkan di layar)<br>
            ✅ Checkpoint utama → aktifkan<br>
            ❌ Start (semua berangkat bersamaan) → bisa nonaktifkan
          </div>
        </span>
      </div>
      <div class="flag-card__desc">Tampil di Live Monitor & layar publik</div>
    </label>

  </div>

  <div class="form-actions">
    <button type="submit" class="btn btn-primary">Simpan Aturan</button>
    <a href="/pages/rules/list.php?race_id=<?= $raceId ?>" class="btn btn-outline">Batal</a>
  </div>
</form>
</div>
</div>

<style>
/* ── Flag Cards ─────────────────────────────────────────────────────────────── */
.flag-card {
  display:flex;flex-direction:column;gap:6px;
  background:rgba(255,255,255,0.03);
  border:2px solid var(--border);
  border-radius:var(--radius);
  padding:14px 16px;
  cursor:pointer;
  transition:all .2s;
  min-width:180px;
  position:relative;
  user-select:none;
}
.flag-card input[type=checkbox] { position:absolute;opacity:0;width:0;height:0; }
.flag-card__header { display:flex;align-items:center;gap:8px;font-weight:700;font-size:14px; }
.flag-card__icon { font-size:18px; }
.flag-card__desc { font-size:11px;color:var(--text-muted);margin-left:2px }
.flag-card:hover { border-color:var(--accent);background:rgba(79,142,247,0.06) }
.flag-card--on {
  border-color:var(--accent) !important;
  background:rgba(79,142,247,0.10) !important;
  box-shadow:0 0 0 1px rgba(79,142,247,.3);
}
.flag-card--on .flag-card__title { color:var(--accent-light) }
.flag-card--on::after {
  content:'✓';position:absolute;top:10px;right:12px;
  font-size:12px;font-weight:900;color:var(--accent-light);
}

/* ── Tooltip ────────────────────────────────────────────────────────────────── */
.flag-card__tooltip-trigger {
  margin-left:auto;
  font-size:11px;color:var(--text-muted);
  cursor:help;
  position:relative;
}

.flag-card__tooltip {
  display:none;
  position:absolute;
  left:0;bottom:24px;
  z-index:200;
  width:260px;
  background:var(--card-bg-solid, #1e2538);
  border:1px solid var(--border-accent);
  border-radius:var(--radius);
  padding:14px;
  font-size:11px;font-weight:400;line-height:1.7;
  color:var(--text-primary);
  box-shadow:0 8px 24px rgba(0,0,0,.5);
  pointer-events:none;
}
.flag-card__tooltip-trigger:hover .flag-card__tooltip,
.flag-card__tooltip-trigger:focus .flag-card__tooltip { display:block; 
}
</style>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>

