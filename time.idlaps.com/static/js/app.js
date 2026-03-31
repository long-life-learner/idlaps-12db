// IDLAPS Time — App JavaScript

// ── Copy to clipboard ─────────────────────────────────────────────────────────
function copyText(el) {
  const text = el.dataset.copy || el.textContent.trim();
  navigator.clipboard.writeText(text).then(() => {
    const orig = el.textContent;
    el.textContent = 'Tersalin!';
    el.style.color = '#22c55e';
    setTimeout(() => { el.textContent = orig; el.style.color = ''; }, 1500);
  });
}

// ── Confirm delete ──────────────────────────────────────────────────────────── 
function confirmDelete(form, name) {
  if (confirm(`Hapus "${name}"? Tindakan ini tidak dapat diurungkan.`)) {
    form.submit();
  }
}

// ── Auto-refresh (untuk Live Monitor) ─────────────────────────────────────────
let autoRefreshTimer = null;
function startAutoRefresh(intervalMs = 3000) {
  autoRefreshTimer = setInterval(() => {
    const tbody = document.getElementById('live-tbody');
    const raceId = document.getElementById('race-id-meta')?.dataset.raceId;
    const readerId = document.getElementById('reader-filter')?.value || '';
    if (!tbody || !raceId) return;

    fetch(`/api/chip_data.php?race_id=${raceId}&reader_id=${readerId}&limit=50`)
      .then(r => r.json())
      .then(data => {
        if (!data.data) return;
        tbody.innerHTML = data.data.map(row => `
          <tr>
            <td><span class="chip-tag">${escHtml(row.epc)}</span></td>
            <td><strong>${escHtml(row.bib || '-')}</strong></td>
            <td>${escHtml(row.reader_id || '-')}</td>
            <td>${escHtml(row.read_time)}</td>
            <td>${escHtml(row.rssi != null ? row.rssi + ' dBm' : '-')}</td>
          </tr>
        `).join('');
        document.getElementById('data-in-wait').textContent = data.total_unsynced ?? '-';
        document.getElementById('total-reads').textContent  = data.total ?? '-';
      })
      .catch(() => {});
  }, intervalMs);
}

function stopAutoRefresh() {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
}

// ── Set filter & refresh ───────────────────────────────────────────────────────
function applyFilter() {
  stopAutoRefresh();
  startAutoRefresh(3000);
}

// ── Escape HTML ───────────────────────────────────────────────────────────────
function escHtml(str) {
  if (str == null) return '-';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Gun Time setter ───────────────────────────────────────────────────────────
function setGunTimeNow() {
  const input = document.getElementById('gun_time_input');
  if (!input) return;
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  const str = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} ` +
              `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  input.value = str;
}

// ── Flash message auto-dismiss ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(a => {
    setTimeout(() => {
      a.style.transition = 'opacity 0.5s';
      a.style.opacity = '0';
      setTimeout(() => a.remove(), 500);
    }, 5000);
  });

  // API key copy
  document.querySelectorAll('.api-key-display').forEach(el => {
    el.title = 'Klik untuk menyalin';
    el.addEventListener('click', () => copyText(el));
  });
});
