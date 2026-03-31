<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

$db     = getDB();
$raceId = (int)($_GET['race_id'] ?? 0);
if (!$raceId) redirect('/pages/races/list.php');

$race = $db->prepare('SELECT * FROM races WHERE id = ?');
$race->execute([$raceId]); $race = $race->fetch();
if (!$race) { setFlash('danger','Lomba tidak ditemukan.'); redirect('/pages/races/list.php'); }

$items   = getItemsByRace($raceId);
$devices = $db->prepare('SELECT * FROM devices WHERE race_id = ? OR race_id IS NULL ORDER BY name');
$devices->execute([$raceId]);
$devices = $devices->fetchAll();

$rules = $db->prepare(
    'SELECT tr.*, i.title as item_title, d.name as device_name, d.reader_ip
     FROM timing_rules tr
     LEFT JOIN items i ON i.id = tr.item_id
     LEFT JOIN devices d ON d.id = tr.device_id
     WHERE i.race_id = ?
     ORDER BY i.sort_order, tr.timing_point'
);
$rules->execute([$raceId]);
$rules = $rules->fetchAll();

// Delete rule
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'delete') {
    $db->prepare('DELETE FROM timing_rules WHERE id = ?')->execute([(int)$_POST['rule_id']]);
    setFlash('success','Aturan dihapus.');
    redirect("/pages/rules/list.php?race_id={$raceId}");
}

// Group rules by item
$rulesByItem = [];
foreach ($rules as $r) {
    $rulesByItem[$r['item_title']][] = $r;
}

$pageTitle   = 'Aturan Scoring — ' . e($race['name']);
$currentPage = 'rules';
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/pages/races/list.php">Lomba</a><span class="breadcrumb-sep">›</span>
  <a href="/pages/races/detail.php?id=<?= $raceId ?>"><?= e($race['name']) ?></a><span class="breadcrumb-sep">›</span>
  <span>Aturan Scoring</span>
</div>

<div class="page-header">
  <div class="page-title">📋 Aturan Scoring</div>
  <div class="page-actions">
    <a href="/pages/rules/import.php?race_id=<?= $raceId ?>" class="btn btn-outline">📥 Import Excel</a>
    <a href="/pages/rules/form.php?race_id=<?= $raceId ?>" class="btn btn-primary">+ Tambah Aturan</a>
  </div>
</div>

<?php if ($rulesByItem): ?>
  <?php foreach ($rulesByItem as $itemTitle => $itemRules): ?>
  <div class="card" style="margin-bottom:20px">
    <div class="card-header"><div class="card-title">📦 <?= e($itemTitle) ?></div></div>

    <!-- Timing Timeline -->
    <div style="padding:16px 20px;border-bottom:1px solid var(--border)">
      <div class="timing-timeline">
        <?php
        $points = ['start'=>'🚀','checkpoint'=>'📌','finish'=>'🏁'];
        $found  = array_column($itemRules, 'timing_point');
        $first  = true;
        foreach ($points as $pt => $icon):
          if (!$first) echo '<div class="timing-line"></div>';
          $active = in_array($pt, $found) ? $pt : '';
          $first  = false;
        ?>
        <div class="timing-node <?= $active ?>">
          <div class="timing-node-icon <?= $active ?>"><?= $icon ?></div>
          <div class="timing-node-label"><?= ucfirst($pt) ?></div>
        </div>
        <?php endforeach; ?>
      </div>
    </div>

    <div class="table-wrapper">
      <table class="table">
        <thead><tr><th>Titik</th><th>Device/Reader</th><th>Tipe Score</th><th>Buka</th><th>Tutup</th><th>Kec. Maks</th><th>Sort</th><th>Must Pass</th><th></th></tr></thead>
        <tbody>
          <?php foreach ($itemRules as $r): ?>
          <tr>
            <td><span class="badge badge-primary"><?= timingPointLabel($r['timing_point']) ?></span></td>
            <td>
              <?php if ($r['device_name']): ?>
                <div style="font-weight:600"><?= e($r['device_name']) ?></div>
                <div style="font-size:11px;color:var(--text-muted)"><?= e($r['reader_ip']) ?></div>
              <?php else: ?>
                <span style="color:var(--text-muted)">-</span>
              <?php endif; ?>
            </td>
            <td><?= $r['score_type'] === 'net_time' ? 'Net Time' : 'Gun Time' ?></td>
            <td><?= gmdate('H:i:s', $r['open_time']) ?></td>
            <td><?= gmdate('H:i:s', $r['close_time']) ?></td>
            <td><?= $r['fastest_speed'] ?> m/s</td>
            <td><?= $r['sort'] === 'first' ? 'Pertama' : 'Terakhir' ?></td>
            <td><?= $r['must_pass'] ? '<span class="badge badge-success">Ya</span>' : '<span class="badge badge-secondary">Tidak</span>' ?></td>
            <td>
              <div class="table-actions">
                <a href="/pages/rules/form.php?race_id=<?= $raceId ?>&rule_id=<?= $r['id'] ?>" class="btn btn-outline btn-xs">Edit</a>
                <form method="POST" onsubmit="return confirm('Hapus aturan ini?')">
                  <input type="hidden" name="action" value="delete">
                  <input type="hidden" name="rule_id" value="<?= $r['id'] ?>">
                  <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">
                  <button type="submit" class="btn btn-danger btn-xs">Hapus</button>
                </form>
              </div>
            </td>
          </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
    </div>
  </div>
  <?php endforeach; ?>

<?php else: ?>
<div class="empty-state">
  <div class="empty-state-icon">📋</div>
  <div class="empty-state-title">Belum ada aturan scoring</div>
  <div class="empty-state-desc">Tambahkan aturan untuk setiap timing point (Start, Checkpoint, Finish).</div>
  <a href="/pages/rules/form.php?race_id=<?= $raceId ?>" class="btn btn-primary">+ Tambah Aturan</a>
</div>
<?php endif; ?>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>
