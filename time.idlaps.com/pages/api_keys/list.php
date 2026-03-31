<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

$db     = getDB();
$raceId = (int)($_GET['race_id'] ?? 0);

// Generate API Key baru
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action  = $_POST['action'] ?? '';
    $name    = trim($_POST['name'] ?? '');
    $keyRaceId = $_POST['race_id'] ? (int)$_POST['race_id'] : null;

    if ($action === 'generate' && $name) {
        $key = generateApiKey();
        $db->prepare('INSERT INTO api_keys (race_id, name, api_key) VALUES (?,?,?)')
           ->execute([$keyRaceId, $name, $key]);
        setFlash('success', "API Key berhasil dibuat.");
        redirect('/pages/api_keys/list.php' . ($raceId ? "?race_id=$raceId" : ''));
    }
    if ($action === 'revoke') {
        $db->prepare('UPDATE api_keys SET is_active = 0 WHERE id = ?')
           ->execute([(int)$_POST['key_id']]);
        setFlash('success', 'API Key dinonaktifkan.');
        redirect('/pages/api_keys/list.php' . ($raceId ? "?race_id=$raceId" : ''));
    }
    if ($action === 'delete') {
        $db->prepare('DELETE FROM api_keys WHERE id = ?')
           ->execute([(int)$_POST['key_id']]);
        setFlash('success', 'API Key dihapus.');
        redirect('/pages/api_keys/list.php' . ($raceId ? "?race_id=$raceId" : ''));
    }
}

$where  = '1=1';
$params = [];
if ($raceId) { $where .= ' AND (k.race_id = ? OR k.race_id IS NULL)'; $params[] = $raceId; }

$keys = $db->prepare(
    "SELECT k.*, r.name as race_name FROM api_keys k
     LEFT JOIN races r ON r.id = k.race_id
     WHERE $where ORDER BY k.created_at DESC"
);
$keys->execute($params);
$keys = $keys->fetchAll();

$allRaces = getAllRaces();

$pageTitle   = 'API Keys';
$currentPage = 'api_keys';
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="page-header">
  <div class="page-title">🔑 API Keys</div>
</div>

<div style="display:grid;grid-template-columns:1fr 2fr;gap:24px;align-items:start">

<!-- Generate Key -->
<div class="card">
  <div class="card-header"><div class="card-title">Generate API Key Baru</div></div>
  <div class="card-body">
    <form method="POST">
      <input type="hidden" name="action" value="generate">
      <input type="hidden" name="race_id" value="<?= $raceId ?>">
      <div class="form-group" style="margin-bottom:12px">
        <label class="form-label">Nama / Label <span class="form-required">*</span></label>
        <input name="name" class="form-control" placeholder="contoh: IDLAPS Checkpoint Start Gate" required>
      </div>
      <?php if (!$raceId): ?>
      <div class="form-group" style="margin-bottom:12px">
        <label class="form-label">Lomba (opsional)</label>
        <select name="race_id" class="form-select">
          <option value="">— Semua Lomba —</option>
          <?php foreach ($allRaces as $r): ?>
          <option value="<?= $r['id'] ?>"><?= e($r['name']) ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <?php endif; ?>
      <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center">⚡ Generate Key</button>
    </form>

    <div style="margin-top:20px;padding-top:20px;border-top:1px solid var(--border)">
      <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:8px">Cara Penggunaan:</div>
      <div style="font-size:11px;color:var(--text-muted);line-height:1.8">
        Endpoint: <code><?= APP_URL ?>/api/checkpoint.php</code><br>
        Method: <code>POST</code><br>
        Header: <code>X-API-Key: {key}</code><br>
        Body: <code>application/json</code>
      </div>
    </div>
  </div>
</div>

<!-- Daftar Keys -->
<div class="card">
  <div class="card-header"><div class="card-title"><?= count($keys) ?> API Keys</div></div>
  <div class="table-wrapper">
    <?php if ($keys): ?>
    <table class="table">
      <thead><tr><th>Nama</th><th>Lomba</th><th>API Key</th><th>Terakhir Dipakai</th><th>Status</th><th></th></tr></thead>
      <tbody>
        <?php foreach ($keys as $k): ?>
        <tr>
          <td><strong><?= e($k['name']) ?></strong></td>
          <td style="font-size:12px;color:var(--text-muted)"><?= e($k['race_name'] ?? '— Semua —') ?></td>
          <td>
            <div class="api-key-display" data-copy="<?= e($k['api_key']) ?>" style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
              <?= e(substr($k['api_key'],0,20)) ?>...
            </div>
          </td>
          <td style="font-size:12px;color:var(--text-muted)"><?= $k['last_used'] ? formatDate($k['last_used']) : 'Belum dipakai' ?></td>
          <td><?= statusBadge($k['is_active'] ? 'active' : 'inactive') ?></td>
          <td>
            <div class="table-actions">
              <?php if ($k['is_active']): ?>
              <form method="POST">
                <input type="hidden" name="action" value="revoke">
                <input type="hidden" name="key_id" value="<?= $k['id'] ?>">
                <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">
                <button type="submit" class="btn btn-outline btn-xs">Nonaktifkan</button>
              </form>
              <?php endif; ?>
              <form method="POST" onsubmit="return confirm('Hapus API Key ini?')">
                <input type="hidden" name="action" value="delete">
                <input type="hidden" name="key_id" value="<?= $k['id'] ?>">
                <input type="hidden" name="_csrf" value="<?= csrfToken() ?>">
                <button type="submit" class="btn btn-danger btn-xs">Hapus</button>
              </form>
            </div>
          </td>
        </tr>
        <?php endforeach; ?>
      </tbody>
    </table>
    <?php else: ?>
    <div class="empty-state">
      <div class="empty-state-icon">🔑</div>
      <div class="empty-state-title">Belum ada API Key</div>
    </div>
    <?php endif; ?>
  </div>
</div>

</div>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>
