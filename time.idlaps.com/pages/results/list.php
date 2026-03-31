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

// Trigger kalkulasi hasil
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'calculate') {
  $itemId = (int) $_POST['item_id'];
  $count = calculateResults($db, $raceId, $itemId);
  setFlash('success', "Kalkulasi selesai. {$count['valid']} sah · {$count['dnf']} DNF · {$count['invalid']} tidak sah.");
  redirect("/pages/results/list.php?race_id={$raceId}");
}

// Filter
$itemId = (int) ($_GET['item_id'] ?? 0);
$gender = $_GET['gender'] ?? '';
$status = $_GET['status'] ?? '';
$items = getItemsByRace($raceId);

$where = 'res.race_id = ?';
$params = [$raceId];
if ($itemId) {
  $where .= ' AND res.item_id = ?';
  $params[] = $itemId;
}
if ($gender) {
  $where .= ' AND ru.gender = ?';
  $params[] = $gender;
}
if ($status) {
  $where .= ' AND res.status = ?';
  $params[] = $status;
}

$results = $db->prepare(
  "SELECT res.*, ru.name, ru.gender, ru.age_group, ru.team, i.title as item_title
     FROM results res
     LEFT JOIN runners ru ON ru.id = res.runner_id
     LEFT JOIN items i ON i.id = res.item_id
     WHERE $where
     ORDER BY res.item_id, res.overall_rank ASC, res.net_time_ms ASC"
);
$results->execute($params);
$results = $results->fetchAll();

// ─────────────────────────────────────────────────────────────────────────────
// FUNGSI KALKULASI HASIL
// ─────────────────────────────────────────────────────────────────────────────
function calculateResults(PDO $db, int $raceId, int $filterItemId = 0): array
{
  $counters = ['valid' => 0, 'dnf' => 0, 'invalid' => 0, 'dsq' => 0];

  $race = $db->prepare('SELECT * FROM races WHERE id = ?');
  $race->execute([$raceId]);
  $race = $race->fetch();
  if (!$race || !$race['gun_time'])
    return $counters;

  $gunTimestamp = (int) (strtotime($race['gun_time']) * 1000); // ms epoch

  // ── Load semua aturan untuk lomba ini ────────────────────────────────────
  $rulesQ = $db->prepare(
    'SELECT tr.*, d.reader_ip
         FROM timing_rules tr
         LEFT JOIN devices d ON d.id = tr.device_id
         JOIN items i ON i.id = tr.item_id
         WHERE i.race_id = ?' . ($filterItemId ? ' AND tr.item_id = ?' : '') . '
         ORDER BY tr.item_id, tr.timing_point'
  );
  $rulesQ->execute($filterItemId ? [$raceId, $filterItemId] : [$raceId]);
  $allRules = $rulesQ->fetchAll();

  // Group aturan per item_id
  $rulesByItem = [];
  foreach ($allRules as $rule) {
    $rulesByItem[$rule['item_id']][] = $rule;
  }

  // ── Load semua runners ────────────────────────────────────────────────────
  $runnersQ = $db->prepare(
    'SELECT r.*, GROUP_CONCAT(rc.epc SEPARATOR ",") as all_epcs
         FROM runners r
         LEFT JOIN runner_chips rc ON rc.runner_id = r.id
         WHERE r.race_id = ?' . ($filterItemId ? ' AND r.item_id = ?' : '') . '
         GROUP BY r.id'
  );
  $runnersQ->execute($filterItemId ? [$raceId, $filterItemId] : [$raceId]);
  $runners = $runnersQ->fetchAll();

  // ── Upsert hasil ─────────────────────────────────────────────────────────
  $upsert = $db->prepare(
    'INSERT INTO results
            (race_id, item_id, runner_id, bib, gun_time_ms, net_time_ms, start_time, finish_time, total_passes, status, calculated_at)
         VALUES (?,?,?,?,?,?,?,?,?,?,NOW())
         ON DUPLICATE KEY UPDATE
            gun_time_ms=VALUES(gun_time_ms), net_time_ms=VALUES(net_time_ms),
            start_time=VALUES(start_time), finish_time=VALUES(finish_time),
            total_passes=VALUES(total_passes), status=VALUES(status), calculated_at=NOW()'
  );

  $itemDistCache = [];

  foreach ($runners as $runner) {
    $itemId_ = $runner['item_id'];
    $bib = $runner['bib'];
    $runnerId = $runner['id'];
    // All EPCs for this runner (multi-chip support)
    $epcs = array_filter(explode(',', $runner['all_epcs'] ?? $runner['epc'] ?? ''));

    $rules = $rulesByItem[$itemId_] ?? [];

    // Klasifikasikan aturan berdasarkan timing point
    $startRules = [];
    $checkpointRules = [];
    $finishRules = [];
    foreach ($rules as $r) {
      if ($r['auto_calculate'] == 0)
        continue; // skip rule yang tidak ikut kalkulasi
      if ($r['timing_point'] === 'start')
        $startRules[] = $r;
      if ($r['timing_point'] === 'checkpoint')
        $checkpointRules[] = $r;
      if ($r['timing_point'] === 'finish')
        $finishRules[] = $r;
    }

    $finishRule = $finishRules[0] ?? null;
    if (!$finishRule)
      continue; // kalau tidak ada aturan finish yang aktif, skip item

    // ── Ambil chip data terbaik dari semua EPC runner (multi-chip) ────────
    // Helper: ambil read terbaik dari semua EPC untuk satu rule
    $getBestRead = function (array $rule, bool $earliest = true) use ($db, $raceId, $gunTimestamp, $epcs): ?array {
      if (empty($epcs))
        return null;
      $openMs = $gunTimestamp + ($rule['open_time'] * 1000);
      $closeMs = $gunTimestamp + ($rule['close_time'] * 1000);
      $sortDir = $earliest ? 'ASC' : 'DESC';

      // Filter per reader jika ditentukan di rule
      $readerCond = $rule['reader_ip'] ? ' AND reader_id = ?' : '';
      $inPlaceholders = implode(',', array_fill(0, count($epcs), '?'));

      $sql = "SELECT * FROM chip_data
                     WHERE race_id = ?
                       AND epc IN ($inPlaceholders)
                       AND read_time BETWEEN ? AND ?
                       $readerCond
                     ORDER BY read_time $sortDir
                     LIMIT " . max(1, (int) $rule['how_many_passes']);

      $bindParams = array_merge(
        [$raceId],
        $epcs,
        [
          date('Y-m-d H:i:s.v', $openMs / 1000),
          date('Y-m-d H:i:s.v', $closeMs / 1000),
        ]
      );
      if ($rule['reader_ip'])
        $bindParams[] = $rule['reader_ip'];

      $stmt = $db->prepare($sql);
      $stmt->execute($bindParams);
      $reads = $stmt->fetchAll();
      return $reads ?: null;
    };

    // ── 1. Cek START (agar jika DNF, waktu start tetap muncul) ───────────
    $startTime = null;
    $startMs = null;
    if ($startRules) {
      $startRule = $startRules[0];
      $startReads = $getBestRead($startRule, $startRule['sort'] !== 'last');
      if ($startReads) {
        $startRead = ($startRule['sort'] === 'last')
          ? $startReads[count($startReads) - 1]
          : $startReads[0];
        $startMs = (int) (strtotime($startRead['read_time']) * 1000);
        $startTime = $startRead['read_time'];
      }
    }

    // ── 2. FINISH ─────────────────────────────────────────────────────────
    $earliest = ($finishRule['sort'] === 'first');
    $finishReads = $getBestRead($finishRule, $earliest);

    if (!$finishReads) {
      // Tidak ada data finish → status tergantung apakah finish must_pass
      $status = $finishRule['must_pass'] ? 'dnf' : 'dns';
      $upsert->execute([$raceId, $itemId_, $runnerId, $bib, null, null, $startTime, null, 0, $status]);

      // Perbarui counter dgn benar
      if (isset($counters[$status]))
        $counters[$status]++;
      continue;
    }

    $finishRead = $earliest ? $finishReads[0] : $finishReads[count($finishReads) - 1];
    $finishMs = (int) (strtotime($finishRead['read_time']) * 1000);
    $gunTimeMs = $finishMs - $gunTimestamp;
    $netTimeMs = $gunTimeMs; // default = gun time

    if ($startTime) {
      $netTimeMs = $finishMs - $startMs;
    } elseif ($startRules && $startRules[0]['must_pass']) {
      // Start wajib tapi tidak ada data → DSQ
      $upsert->execute([$raceId, $itemId_, $runnerId, $bib, $gunTimeMs, null, null, $finishRead['read_time'], count($finishReads), 'dsq']);
      $counters['dsq']++;
      continue;
    }

    // ── 3. MUST_PASS CHECKPOINT validation ───────────────────────────────
    $dsqByCheckpoint = false;
    foreach ($checkpointRules as $cpRule) {
      if (!$cpRule['must_pass'])
        continue; // checkpoint tidak wajib, skip
      $cpReads = $getBestRead($cpRule, true);
      if (!$cpReads) {
        // Checkpoint wajib tidak dilalui → DSQ (jalan pintas!)
        $upsert->execute([$raceId, $itemId_, $runnerId, $bib, $gunTimeMs, $netTimeMs, $startTime, $finishRead['read_time'], count($finishReads), 'dsq']);
        $counters['dsq']++;
        $dsqByCheckpoint = true;
        break;
      }
    }
    if ($dsqByCheckpoint)
      continue;

    // ── 4. Fastest speed validation ───────────────────────────────────────
    if (!isset($itemDistCache[$itemId_])) {
      $d = $db->prepare('SELECT distance FROM items WHERE id = ?');
      $d->execute([$itemId_]);
      $itemDistCache[$itemId_] = (float) $d->fetchColumn();
    }
    $dist = $itemDistCache[$itemId_];
    $status = 'valid';
    if ($dist > 0 && $netTimeMs > 0) {
      $speedMs = $dist / ($netTimeMs / 1000); // m/s
      if ($speedMs > $finishRule['fastest_speed']) {
        $status = 'invalid';
      }
    }

    $upsert->execute([
      $raceId,
      $itemId_,
      $runnerId,
      $bib,
      $gunTimeMs,
      $netTimeMs,
      $startTime,
      $finishRead['read_time'],
      count($finishReads),
      $status
    ]);
    $counters[$status]++;
  }

  // ── 5. Ranking per item per gender ────────────────────────────────────────

  // Kita harus meranking PER KATEGORI (item_id) karena:
  // 1. Ranking harus reset dari 1 untuk tiap kategori.
  // 2. Tipe score (net_time vs gun_time) bisa berbeda tiap kategori.
  $validItems = array_keys($rulesByItem);
  if ($filterItemId)
    $validItems = [$filterItemId];

  foreach ($validItems as $iId) {
    // Cari aturan Finish untuk tau tipe score-nya
    $itemRules = $rulesByItem[$iId] ?? [];
    $finishRule = null;
    foreach ($itemRules as $r) {
      if ($r['timing_point'] === 'finish')
        $finishRule = $r;
    }
    if (!$finishRule)
      continue;

    // Tentukan kolom mana yang dipakai untuk sorting
    $sortCol = ($finishRule['score_type'] === 'gun_time') ? 'res.gun_time_ms' : 'res.net_time_ms';

    // Ranking overall per kategori
    $rankQ = $db->prepare(
      "SELECT res.id FROM results res
             JOIN runners ru ON ru.id = res.runner_id
             WHERE res.race_id = ? AND res.item_id = ? AND res.status = 'valid' AND $sortCol IS NOT NULL
             ORDER BY $sortCol ASC"
    );
    $rankQ->execute([$raceId, $iId]);
    $rank = 1;
    foreach ($rankQ->fetchAll() as $res) {
      $db->prepare('UPDATE results SET overall_rank = ? WHERE id = ?')->execute([$rank++, $res['id']]);
    }

    // Ranking gender per kategori
    $rankGQ = $db->prepare(
      "SELECT res.id, ru.gender FROM results res
             JOIN runners ru ON ru.id = res.runner_id
             WHERE res.race_id = ? AND res.item_id = ? AND res.status = 'valid' AND $sortCol IS NOT NULL
             ORDER BY ru.gender, $sortCol ASC"
    );
    $rankGQ->execute([$raceId, $iId]);
    $genderRanks = [];
    foreach ($rankGQ->fetchAll() as $res) {
      $key = $res['gender'];
      if (!isset($genderRanks[$key]))
        $genderRanks[$key] = 1;
      $db->prepare('UPDATE results SET gender_rank = ? WHERE id = ?')->execute([$genderRanks[$key]++, $res['id']]);
    }
  }
  return $counters;
}

$pageTitle = 'Hasil — ' . e($race['name']);
$currentPage = 'results';
require_once __DIR__ . '/../../includes/header.php';
?>

<div class="breadcrumb">
  <a href="/pages/races/list.php">Lomba</a><span class="breadcrumb-sep">›</span>
  <a href="/pages/races/detail.php?id=<?= $raceId ?>"><?= e($race['name']) ?></a><span class="breadcrumb-sep">›</span>
  <span>Hasil</span>
</div>

<div class="page-header">
  <div>
    <div class="page-title">🏆 Hasil Lomba</div>
    <div class="page-subtitle"><?= count($results) ?> hasil ditampilkan</div>
  </div>
  <div class="page-actions">
    <a href="/pages/results/export.php?race_id=<?= $raceId ?>&item_id=<?= $itemId ?>&gender=<?= urlencode($gender) ?>&status=<?= urlencode($status) ?>"
      class="btn btn-outline" target="_blank">📤 Export Excel</a>
    <form method="POST" style="display:inline">
      <input type="hidden" name="action" value="calculate">
      <input type="hidden" name="item_id" value="<?= $itemId ?>">
      <button type="submit" class="btn btn-success" onclick="return confirm('Hitung ulang semua hasil lomba ini?')">
        ⚙ Kalkulasi Hasil
      </button>
    </form>
  </div>
</div>

<!-- Filter -->
<form method="GET" class="filter-bar">
  <input type="hidden" name="race_id" value="<?= $raceId ?>">
  <input type="text" id="searchBox" class="form-control" placeholder="🔍 Cari Bib / Nama..." style="max-width:200px"
    oninput="filterTable()">
  <select name="item_id" class="form-select" style="max-width:160px" onchange="this.form.submit()">
    <option value="">Semua Kategori</option>
    <?php foreach ($items as $it): ?>
      <option value="<?= $it['id'] ?>" <?= $itemId == $it['id'] ? 'selected' : '' ?>><?= e($it['title']) ?></option>
    <?php endforeach; ?>
  </select>
  <select name="gender" class="form-select" style="max-width:120px" onchange="this.form.submit()">
    <option value="">Semua Gender</option>
    <option value="M" <?= $gender === 'M' ? 'selected' : '' ?>>♂ Putra</option>
    <option value="F" <?= $gender === 'F' ? 'selected' : '' ?>>♀ Putri</option>
  </select>
  <select name="status" class="form-select" style="max-width:140px" onchange="this.form.submit()">
    <option value="">Semua Status</option>
    <option value="valid" <?= $status === 'valid' ? 'selected' : '' ?>>✅ Sah</option>
    <option value="invalid" <?= $status === 'invalid' ? 'selected' : '' ?>>⚡ Terlalu Cepat</option>
    <option value="dnf" <?= $status === 'dnf' ? 'selected' : '' ?>>🔴 DNF</option>
    <option value="dsq" <?= $status === 'dsq' ? 'selected' : '' ?>>⛔ DSQ</option>
    <option value="dns" <?= $status === 'dns' ? 'selected' : '' ?>>⬜ DNS</option>
  </select>
  <?php if ($itemId || $gender || $status): ?>
    <a href="?race_id=<?= $raceId ?>" class="btn btn-outline">Reset</a>
  <?php endif; ?>
</form>

<div class="card">
  <div class="table-wrapper">
    <?php if ($results): ?>
      <table class="table" id="resultsTable">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Rank ♂/♀</th>
            <th>Bib</th>
            <th>Nama</th>
            <th>Kategori</th>
            <th>Gender</th>
            <th>Kel. Umur</th>
            <th>Net Time</th>
            <th>Gun Time</th>
            <th>Start</th>
            <th>Finish</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <?php foreach ($results as $r): ?>
            <tr data-bib="<?= strtolower(e($r['bib'])) ?>" data-name="<?= strtolower(e($r['name'] ?? '')) ?>">
              <td><strong
                  style="font-size:16px;<?= ($r['overall_rank'] ?? 99) <= 3 ? 'color:var(--warning)' : '' ?>"><?= $r['overall_rank'] ?? '-' ?></strong>
              </td>
              <td style="font-size:12px;color:var(--text-muted)"><?= $r['gender_rank'] ?? '-' ?></td>
              <td><?= e($r['bib']) ?></td>
              <td><?= e($r['name'] ?? '-') ?></td>
              <td style="font-size:12px"><?= e($r['item_title'] ?? '-') ?></td>
              <td><?= $r['gender'] === 'M' ? '♂' : '♀' ?></td>
              <td style="font-size:12px"><?= e($r['age_group'] ?? '-') ?></td>
              <td><strong><?= $r['net_time_ms'] ? formatTime((int) $r['net_time_ms']) : '-' ?></strong></td>
              <td style="color:var(--text-muted)"><?= $r['gun_time_ms'] ? formatTime((int) $r['gun_time_ms']) : '-' ?></td>
              <td style="font-size:11px;color:var(--text-muted)">
                <?= $r['start_time'] ? date('H:i:s', strtotime($r['start_time'])) : '-' ?>
              </td>
              <td style="font-size:11px;color:var(--text-muted)">
                <?= $r['finish_time'] ? date('H:i:s', strtotime($r['finish_time'])) : '-' ?>
              </td>
              <td><?= statusBadge($r['status']) ?></td>
              <td>
                <button class="btn btn-outline btn-xs" onclick="openEditModal(<?= htmlspecialchars(json_encode([
                  'id' => $r['id'],
                  'bib' => $r['bib'],
                  'name' => $r['name'] ?? '',
                  'status' => $r['status'],
                  'net_ms' => (int) ($r['net_time_ms'] ?? 0),
                  'gun_ms' => (int) ($r['gun_time_ms'] ?? 0),
                  'start_time' => $r['start_time'] ? date('Y-m-d H:i:s', strtotime($r['start_time'])) : '',
                  'finish_time' => $r['finish_time'] ? date('Y-m-d H:i:s', strtotime($r['finish_time'])) : '',
                ])) ?>)">✏️</button>
              </td>
            </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
    <?php else: ?>
      <div class="empty-state">
        <div class="empty-state-icon">🏆</div>
        <div class="empty-state-title">Belum ada hasil</div>
        <div class="empty-state-desc">Klik "Kalkulasi Hasil" setelah lomba berakhir dan data chip sudah masuk.</div>
      </div>
    <?php endif; ?>
  </div>
</div>

<!-- Edit Result Modal -->
<div id="editModal"
  style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;align-items:center;justify-content:center">
  <div
    style="background:var(--bg-surface);border-radius:var(--radius);padding:28px;width:480px;max-width:95vw;box-shadow:0 20px 60px rgba(0,0,0,0.4)">
    <div style="font-size:16px;font-weight:700;margin-bottom:20px">✏️ Edit Hasil — <span id="editLabel"></span></div>
    <form id="editForm">
      <input type="hidden" id="editResultId">

      <div class="form-group" style="margin-bottom:14px">
        <label class="form-label">Status</label>
        <select id="editStatus" name="status" class="form-select">
          <option value="valid">✅ Sah (Valid)</option>
          <option value="invalid">⚡ Terlalu Cepat (Invalid)</option>
          <option value="dnf">🔴 DNF (Did Not Finish)</option>
          <option value="dsq">⛔ DSQ (Disqualified)</option>
          <option value="dns">⬜ DNS (Did Not Start)</option>
        </select>
      </div>

      <div class="form-group" style="margin-bottom:14px">
        <label class="form-label">Net Time (HH:MM:SS.ms)</label>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 80px;gap:6px">
          <input type="number" id="editNetHH" placeholder="HH" min="0" max="99" class="form-control"
            style="text-align:center">
          <input type="number" id="editNetMM" placeholder="MM" min="0" max="59" class="form-control"
            style="text-align:center">
          <input type="number" id="editNetSS" placeholder="SS" min="0" max="59" class="form-control"
            style="text-align:center">
          <input type="number" id="editNetMS" placeholder="ms" min="0" max="999" class="form-control"
            style="text-align:center">
        </div>
      </div>

      <div class="form-group" style="margin-bottom:14px">
        <label class="form-label">Gun Time (HH:MM:SS.ms)</label>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 80px;gap:6px">
          <input type="number" id="editGunHH" placeholder="HH" min="0" max="99" class="form-control"
            style="text-align:center">
          <input type="number" id="editGunMM" placeholder="MM" min="0" max="59" class="form-control"
            style="text-align:center">
          <input type="number" id="editGunSS" placeholder="SS" min="0" max="59" class="form-control"
            style="text-align:center">
          <input type="number" id="editGunMS" placeholder="ms" min="0" max="999" class="form-control"
            style="text-align:center">
        </div>
      </div>

      <div class="form-group" style="margin-bottom:14px">
        <label class="form-label">Waktu Start</label>
        <input type="datetime-local" id="editStartTime" class="form-control" step="1">
      </div>

      <div class="form-group" style="margin-bottom:20px">
        <label class="form-label">Waktu Finish</label>
        <input type="datetime-local" id="editFinishTime" class="form-control" step="1">
      </div>

      <div style="display:flex;gap:10px;justify-content:flex-end">
        <button type="button" class="btn btn-outline" onclick="closeEditModal()">Batal</button>
        <button type="submit" class="btn btn-primary" id="btnSaveEdit">💾 Simpan</button>
      </div>
    </form>
    <div id="editMsg" style="margin-top:12px;font-size:13px"></div>
  </div>
</div>

<script>
  function filterTable() {
    const q = document.getElementById('searchBox').value.toLowerCase();
    document.querySelectorAll('#resultsTable tbody tr').forEach(tr => {
      const bib = tr.dataset.bib || '';
      const name = tr.dataset.name || '';
      tr.style.display = (!q || bib.includes(q) || name.includes(q)) ? '' : 'none';
    });
  }

  function msToHMSms(ms) {
    const totalSec = Math.floor(ms / 1000);
    const millis = ms % 1000;
    const hh = Math.floor(totalSec / 3600);
    const mm = Math.floor((totalSec % 3600) / 60);
    const ss = totalSec % 60;
    return { hh, mm, ss, millis };
  }

  function openEditModal(data) {
    document.getElementById('editLabel').textContent = `Bib ${data.bib} — ${data.name}`;
    document.getElementById('editResultId').value = data.id;
    document.getElementById('editStatus').value = data.status;

    const t = msToHMSms(data.net_ms || 0);
    document.getElementById('editNetHH').value = t.hh;
    document.getElementById('editNetMM').value = t.mm;
    document.getElementById('editNetSS').value = t.ss;
    document.getElementById('editNetMS').value = t.millis;

    const g = msToHMSms(data.gun_ms || 0);
    document.getElementById('editGunHH').value = g.hh;
    document.getElementById('editGunMM').value = g.mm;
    document.getElementById('editGunSS').value = g.ss;
    document.getElementById('editGunMS').value = g.millis;

    document.getElementById('editStartTime').value = data.start_time ? data.start_time.replace(' ', 'T').substring(0, 19) : '';
    document.getElementById('editFinishTime').value = data.finish_time ? data.finish_time.replace(' ', 'T').substring(0, 19) : '';

    document.getElementById('editMsg').textContent = '';
    document.getElementById('editModal').style.display = 'flex';
  }

  function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
  }

  document.getElementById('editForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const btn = document.getElementById('btnSaveEdit');
    btn.disabled = true;
    btn.textContent = 'Menyimpan...';

    const fd = new FormData();
    fd.append('result_id', document.getElementById('editResultId').value);
    fd.append('status', document.getElementById('editStatus').value);
    fd.append('net_hh', document.getElementById('editNetHH').value);
    fd.append('net_mm', document.getElementById('editNetMM').value);
    fd.append('net_ss', document.getElementById('editNetSS').value);
    fd.append('net_ms', document.getElementById('editNetMS').value);
    fd.append('gun_hh', document.getElementById('editGunHH').value);
    fd.append('gun_mm', document.getElementById('editGunMM').value);
    fd.append('gun_ss', document.getElementById('editGunSS').value);
    fd.append('gun_ms', document.getElementById('editGunMS').value);
    fd.append('start_time', document.getElementById('editStartTime').value.replace('T', ' '));
    fd.append('finish_time', document.getElementById('editFinishTime').value.replace('T', ' '));

    const res = await fetch('/pages/results/edit.php', { method: 'POST', body: fd });
    const json = await res.json();
    const msg = document.getElementById('editMsg');

    if (json.success) {
      msg.style.color = 'var(--success)';
      msg.textContent = '✅ ' + json.message + ' — Halaman akan di-refresh...';
      setTimeout(() => location.reload(), 1500);
    } else {
      msg.style.color = 'var(--danger)';
      msg.textContent = '❌ ' + json.message;
      btn.disabled = false;
      btn.textContent = '💾 Simpan';
    }
  });

  // Close modal on backdrop click
  document.getElementById('editModal').addEventListener('click', function (e) {
    if (e.target === this) closeEditModal();
  });
</script>

<?php require_once __DIR__ . '/../../includes/footer.php'; ?>