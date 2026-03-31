<?php
require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../auth.php';
require_once __DIR__ . '/../db.php';
require_once __DIR__ . '/../includes/functions.php';
requireLogin();

$pageTitle = 'API Tester';
$currentPage = 'api-tester';
require_once __DIR__ . '/../includes/header.php';

$db = getDB();
$races = $db->query('SELECT id, name FROM races ORDER BY id DESC LIMIT 5')->fetchAll();
$sampleRaceId = $races[0]['id'] ?? 1;

// Template Mode 1: Zero-Config (SN)
$templateSN = json_encode([
  'device_sn' => '363B37373632010134303837',
  'reader_id' => '192.168.1.100',
  'reads' => [
    ['epc' => 'E20000000000000000000001', 'timestamp' => date('Y-m-d\TH:i:s.v'), 'rssi' => -65],
    ['epc' => 'E20000000000000000000002', 'timestamp' => date('Y-m-d\TH:i:s.v', time() + 2), 'rssi' => -70]
  ]
], JSON_PRETTY_PRINT);

// Template Mode 2: API Key
$templateApiKey = json_encode([
  'race_id' => (int) $sampleRaceId,
  'reader_id' => '192.168.1.100',
  'reads' => [
    ['epc' => 'E20000000000000000000001', 'timestamp' => date('Y-m-d\TH:i:s.v'), 'rssi' => -65],
    ['epc' => 'E20000000000000000000002', 'timestamp' => date('Y-m-d\TH:i:s.v', time() + 2), 'rssi' => -70]
  ]
], JSON_PRETTY_PRINT);
?>

<div class="breadcrumb">
  <a href="/">Utama</a><span class="breadcrumb-sep">›</span>
  <span>API Tester</span>
</div>

<div class="page-header">
  <div>
    <div class="page-title">🧪 API Request Tester</div>
    <div class="page-subtitle">Simulasi pengiriman data chip dari hardware ke endpoint <code>/api/checkpoint.php</code>
    </div>
  </div>
</div>

<!-- Mode Switcher -->
<div style="display:flex;gap:10px;margin-bottom:20px">
  <button id="btnModeSN" onclick="switchMode('sn')" class="btn btn-primary" style="gap:8px">
    📡 Mode Zero-Config (SN)
  </button>
  <button id="btnModeKey" onclick="switchMode('apikey')" class="btn btn-outline" style="gap:8px">
    🔑 Mode API Key
  </button>
</div>

<!-- Mode Info Banner -->
<div id="bannerSN" class="mode-banner"
  style="margin-bottom:20px;font-size:13px;padding:12px 16px;border-radius:var(--radius-sm);background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.3);color:var(--text-secondary)">
  <strong>📡 Mode Zero-Config</strong> — Hardware hanya mengirim <code>device_sn</code> (HEX Serial Number). Tidak perlu
  API Key maupun Race ID.
  Server akan otomatis menentukan Lomba berdasarkan mapping di menu <strong>Device / Reader</strong>.
</div>
<div id="bannerKey" class="mode-banner"
  style="margin-bottom:20px;font-size:13px;padding:12px 16px;border-radius:var(--radius-sm);background:rgba(234,179,8,0.1);border:1px solid rgba(234,179,8,0.3);color:var(--text-secondary);display:none">
  <strong>🔑 Mode API Key (Lama)</strong> — Sertakan <code>X-API-Key</code> di header dan <code>race_id</code> di body.
  Kompatibel dengan integrasi lama.
</div>

<div class="form-grid" style="grid-template-columns: 1fr 1fr; gap: 24px;">
  <!-- Kiri: Request Builder -->
  <div class="card">
    <div class="card-header">
      <div class="card-title">1. Susun Request</div>
    </div>
    <div class="card-body">
      <form id="testerForm" onsubmit="sendApiRequest(event)">

        <!-- Mode SN: tidak perlu API Key -->
        <div id="fieldApiKey" style="display:none;margin-bottom:16px">
          <label class="form-label">API Key (Header: X-API-Key)</label>
          <input type="text" id="reqApiKey" class="form-control" placeholder="Masukkan API Key...">
          <div class="form-hint">Dari menu <strong>API Keys</strong> di sidebar.</div>
        </div>

        <div class="form-group" style="margin-bottom:16px">
          <label class="form-label">Endpoint URL</label>
          <div style="display:flex;gap:10px">
            <select id="reqMethod" class="form-select" style="width:100px;font-weight:bold">
              <option value="POST">POST</option>
            </select>
            <input type="text" id="reqEndpoint" class="form-control" value="/api/checkpoint.php">
          </div>
        </div>

        <div class="form-group" style="margin-bottom:20px">
          <label class="form-label" style="display:flex;justify-content:space-between">
            <span>JSON Payload (Body)</span>
            <span style="font-weight:normal;cursor:pointer;color:var(--accent)" onclick="resetPayload()">↺ Reset
              Template</span>
          </label>
          <textarea id="reqPayload" class="form-textarea"
            style="font-family:monospace;font-size:12px;min-height:280px"><?= htmlspecialchars($templateSN) ?></textarea>
        </div>

        <button type="submit" class="btn btn-primary" id="btnSend"
          style="width:100%;justify-content:center;padding:12px">
          🚀 Kirim Request
        </button>

      </form>
    </div>
  </div>

  <!-- Kanan: Response Viewer -->
  <div class="card">
    <div class="card-header">
      <div class="card-title">2. Server Response</div>
      <div id="respStatus" class="badge" style="display:none"></div>
    </div>
    <div class="card-body">

      <div id="emptyResp" style="text-align:center;padding:60px 20px;color:var(--text-muted)">
        <div style="font-size:40px;margin-bottom:16px;opacity:0.5">📡</div>
        <div style="font-size:14px">Respons server akan muncul di sini.</div>
      </div>

      <div id="respContainer" style="display:none">
        <label class="form-label">Response Body (JSON):</label>
        <pre id="respBody"
          style="background:rgba(0,0,0,0.3);padding:16px;border-radius:var(--radius-sm);font-size:12px;color:var(--text-primary);overflow-x:auto;min-height:200px;white-space:pre-wrap"></pre>

        <label class="form-label" style="margin-top:12px">HTTP Headers:</label>
        <pre id="respHeaders"
          style="background:rgba(0,0,0,0.3);padding:12px;border-radius:var(--radius-sm);font-size:11px;color:var(--text-muted);white-space:pre-wrap"></pre>
      </div>

    </div>
  </div>
</div>

<script>
  const templateSN = <?= json_encode($templateSN) ?>;
  const templateApiKey = <?= json_encode($templateApiKey) ?>;
  let currentMode = 'sn';

  function switchMode(mode) {
    currentMode = mode;
    const isSN = mode === 'sn';

    document.getElementById('btnModeSN').className = isSN ? 'btn btn-primary' : 'btn btn-outline';
    document.getElementById('btnModeKey').className = isSN ? 'btn btn-outline' : 'btn btn-primary';
    document.getElementById('bannerSN').style.display = isSN ? '' : 'none';
    document.getElementById('bannerKey').style.display = isSN ? 'none' : '';
    document.getElementById('fieldApiKey').style.display = isSN ? 'none' : 'block';

    // Swap template
    document.getElementById('reqPayload').value = isSN ? templateSN : templateApiKey;
  }

  function resetPayload() {
    document.getElementById('reqPayload').value = currentMode === 'sn' ? templateSN : templateApiKey;
  }

  // Init: Mode SN aktif, hide API Key field
  switchMode('sn');

  async function sendApiRequest(e) {
    e.preventDefault();

    const btn = document.getElementById('btnSend');
    const apiKey = document.getElementById('reqApiKey').value.trim();
    const endpoint = document.getElementById('reqEndpoint').value.trim();
    const method = document.getElementById('reqMethod').value;
    let payloadStr = document.getElementById('reqPayload').value.trim();

    let payloadObj;
    try {
      payloadObj = JSON.parse(payloadStr);
    } catch (err) {
      alert("Format JSON tidak valid!\n" + err.message);
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '⏳ Mengirim...';
    document.getElementById('emptyResp').style.display = 'none';
    document.getElementById('respContainer').style.display = 'block';
    document.getElementById('respBody').innerText = 'Menunggu respons dari server...';
    document.getElementById('respHeaders').innerText = '';
    document.getElementById('respStatus').style.display = 'none';

    try {
      const startTime = performance.now();

      const headers = { 'Content-Type': 'application/json' };
      if (currentMode === 'apikey' && apiKey) {
        headers['X-API-Key'] = apiKey;
      }

      const response = await fetch(endpoint, {
        method,
        headers,
        body: JSON.stringify(payloadObj)
      });

      const duration = Math.round(performance.now() - startTime);
      const statusBadge = document.getElementById('respStatus');
      statusBadge.style.display = 'inline-block';
      statusBadge.innerText = `${response.status} ${response.statusText} (${duration}ms)`;
      statusBadge.className = response.ok ? 'badge badge-success' : 'badge badge-danger';

      let respText = await response.text();
      try {
        document.getElementById('respBody').innerText = JSON.stringify(JSON.parse(respText), null, 2);
      } catch {
        document.getElementById('respBody').innerText = respText;
      }

      let headersDump = '';
      response.headers.forEach((val, key) => { headersDump += `${key}: ${val}\n`; });
      document.getElementById('respHeaders').innerText = headersDump || 'Tidak ada header khusus.';

    } catch (err) {
      document.getElementById('respStatus').style.display = 'inline-block';
      document.getElementById('respStatus').className = 'badge badge-danger';
      document.getElementById('respStatus').innerText = 'Network Error';
      document.getElementById('respBody').innerText = 'Gagal mengirim request: ' + err.message;
    } finally {
      btn.disabled = false;
      btn.innerHTML = '🚀 Kirim Request';
    }
  }
</script>

<?php require_once __DIR__ . '/../includes/footer.php'; ?>