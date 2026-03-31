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
if (!$race) { setFlash('danger', 'Lomba tidak ditemukan.'); redirect('/pages/races/list.php'); }

$items = getItemsByRace($raceId);

if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'delete') {
    $db->prepare('DELETE FROM runners WHERE id = ? AND race_id = ?')
       ->execute([(int)$_POST['runner_id'], $raceId]);
    setFlash('success', 'Peserta berhasil dihapus.');
    redirect("/pages/runners/list.php?race_id={$raceId}");
}

$page    = max(1, (int)($_GET['page'] ?? 1));
$perPage = 50;
$search  = trim($_GET['q'] ?? '');
$itemId  = (int)($_GET['item_id'] ?? 0);
$offset  = ($page - 1) * $perPage;

$where  = 'r.race_id = ?';
$params = [$raceId];
if ($search) {
    // Cari juga berdasarkan EPC dari runner_chips
    $where .= ' AND (r.bib LIKE ? OR r.name LIKE ? OR EXISTS (
        SELECT 1 FROM runner_chips rc WHERE rc.runner_id = r.id AND rc.epc LIKE ?
    ))';
    $s = "%$search%";
    $params = array_merge($params, [$s, $s, $s]);
}
if ($itemId) { $where .= ' AND r.item_id = ?'; $params[] = $itemId; }

$total = $db->prepare("SELECT COUNT(*) FROM runners r WHERE $where");
$total->execute($params); $total = (int)$total->fetchColumn();

$stmt = $db->prepare(
    "SELECT r.*, i.title as item_title
     FROM runners r
     LEFT JOIN items i ON i.id = r.item_id
     WHERE $where
     ORDER BY CAST(r.bib AS UNSIGNED), r.bib
     LIMIT $perPage OFFSET $offset"
);
$stmt->execute($params);
$runners = $stmt->fetchAll();

// Ambil semua chips sekaligus untuk runner yang tampil (1 query, bukan N+1)
$runnerIds = array_column($runners, 'id');
$chipsByRunner = [];
if ($runnerIds) {
    $in       = implode(',', array_fill(0, count($runnerIds), '?'));
    $chipStmt = $db->prepare("SELECT * FROM runner_chips WHERE runner_id IN ($in) ORDER BY id");
    $chipStmt->execute($runnerIds);
    foreach ($chipStmt->fetchAll() as $chip) {
        $chipsByRunner[$chip['runner_id']][] = $chip;
    }
}

$pageTitle   = 'Peserta — ' . e($race['name']);
$currentPage = 'runners';
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/pages/races/list.php">Lomba</a><span class="breadcrumb-sep">›</span>
  <a href="/pages/races/detail.php?id=<?= $raceId ?>"><?= e($race['name']) ?></a><span class="breadcrumb-sep">›</span>
  <span>Peserta</span>
</div>

<div class="page-header">
  <div>
    <div class="page-title">🏃 Peserta</div>
    <div class="page-subtitle"><?= number_format($total) ?> peserta terdaftar</div>
  </div>
  <div class="page-actions">
    <a href="/pages/runners/import.php?race_id=<?= $raceId ?>" class="btn btn-outline">📥 Import CSV</a>
    <a href="/pages/runners/create.php?race_id=<?= $raceId ?>" class="btn btn-primary">+ Tambah</a>
  </div>
</div>

<div class="filter-bar">
  <form method="GET" style="display:flex;gap:10px;flex:1;flex-wrap:wrap">
    <input type="hidden" name="race_id" value="<?= $raceId ?>">
    <div class="search-input-wrapper">
      <span class="search-icon">🔍</span>
      <input type="text" name="q" class="form-control search-input"
             placeholder="Cari bib, nama, atau EPC..." value="<?= e($search) ?>">
    </div>
    <select name="item_id" class="form-select" style="max-width:160px">
      <option value="">Semua Kategori</option>
      <?php foreach ($items as $it): ?>
      <option value="<?= $it['id'] ?>" <?= $itemId == $it['id'] ? 'selected' : '' ?>><?= e($it['title']) ?></option>
      <?php endforeach; ?>
    </select>
    <button type="submit" class="btn btn-primary">Cari</button>
    <?php if ($search || $itemId): ?>
      <a href="?race_id=<?= $raceId ?>" class="btn btn-outline">Reset</a>
    <?php endif; ?>
  </form>
</div>

<div class="card">
  <div class="table-wrapper">
    <?php if ($runners): ?>
    <table class="table">
      <thead>
        <tr>
          <th>Bib</th>
          <th>Nama</th>
          <th>Kategori</th>
          <th>Gender</th>
          <th>Kel. Umur</th>
          <th>Chip EPC</th>
          <th>Tim</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <?php foreach ($runners as $r): ?>
        <tr>
          <td><strong style="font-size:16px"><?= e($r['bib']) ?></strong></td>
          <td><?= e($r['name'] ?? '-') ?></td>
          <td style="font-size:12px"><?= e($r['item_title'] ?? '-') ?></td>
          <td><?= $r['gender'] === 'M' ? '♂' : '♀' ?></td>
          <td><?= e($r['age_group'] ?? '-') ?></td>
          <td>
            <?php $chips = $chipsByRunner[$r['id']] ?? []; ?>
            <?php if ($chips): ?>
              <?php foreach ($chips as $chip): ?>
                <div style="margin-bottom:2px">
                  <span class="chip-tag" title="<?= e($chip['label'] ?? '') ?>"><?= e(substr($chip['epc'],0,16)) ?>…</span>
                  <?php if ($chip['label']): ?>
                    <span style="font-size:10px;color:var(--text-muted);margin-left:4px"><?= e($chip['label']) ?></span>
                  <?php endif; ?>
                </div>
              <?php endforeach; ?>
            <?php else: ?>
              <span style="color:var(--danger);font-size:12px">⚠ Belum ada chip</span>
            <?php endif; ?>
          </td>
          <td style="font-size:12px"><?= e($r['team'] ?? '-') ?></td>
          <td>
            <div class="table-actions">
              <form method="POST" onsubmit="return confirm('Hapus peserta Bib #<?= $r['bib'] ?>?')">
                <input type="hidden" name="action" value="delete">
                <input type="hidden" name="runner_id" value="<?= $r['id'] ?>">
                <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">
                <button type="submit" class="btn btn-danger btn-xs">Hapus</button>
              </form>
            </div>
          </td>
        </tr>
        <?php endforeach; ?>
      </tbody>
    </table>
    <?= pagination($total, $perPage, $page, "?race_id={$raceId}&q=" . urlencode($search) . "&item_id={$itemId}") ?>

    <?php else: ?>
    <div class="empty-state">
      <div class="empty-state-icon">🏃</div>
      <div class="empty-state-title">Belum ada peserta</div>
      <div class="empty-state-desc">Import dari CSV atau tambahkan satu per satu.</div>
      <a href="/pages/runners/import.php?race_id=<?= $raceId ?>" class="btn btn-primary">📥 Import CSV</a>
    </div>
    <?php endif; ?>
  </div>
</div>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>
