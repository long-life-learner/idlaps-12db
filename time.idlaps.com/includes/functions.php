<?php
require_once __DIR__ . '/../db.php';


// ─── Format waktu ms → HH:MM:SS.mmm ─────────────────────────────────────────
function formatTime(int $ms): string {
    $h   =  intdiv($ms, 3600000);
    $m   =  intdiv($ms % 3600000, 60000);
    $s   =  intdiv($ms % 60000, 1000);
    $mil = $ms % 1000;
    return sprintf('%02d:%02d:%02d.%03d', $h, $m, $s, $mil);
}

// ─── Format tanggal Indonesia ─────────────────────────────────────────────────
function formatDate(string $date): string {
    if (!$date) return '-';
    return date('d M Y', strtotime($date));
}

function formatDatetime(string $dt): string {
    if (!$dt) return '-';
    return date('d M Y H:i:s', strtotime($dt));
}

// ─── Escape HTML ──────────────────────────────────────────────────────────────
function e(string $str): string {
    return htmlspecialchars($str, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

// ─── CSRF Token ───────────────────────────────────────────────────────────────
function csrfToken(): string {
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function verifyCsrf(): void {
    $token = $_POST['_csrf'] ?? '';
    if (!hash_equals($_SESSION['csrf_token'] ?? '', $token)) {
        http_response_code(403);
        die('CSRF token tidak valid.');
    }
}

// ─── Flash message ────────────────────────────────────────────────────────────
function setFlash(string $type, string $message): void {
    $_SESSION['flash'] = ['type' => $type, 'message' => $message];
}

function getFlash(): ?array {
    $flash = $_SESSION['flash'] ?? null;
    unset($_SESSION['flash']);
    return $flash;
}

// ─── Generate API Key ─────────────────────────────────────────────────────────
function generateApiKey(): string {
    return bin2hex(random_bytes(32)); // 64 char hex
}

// ─── Redirect ─────────────────────────────────────────────────────────────────
function redirect(string $url): void {
    header('Location: ' . $url);
    exit;
}

// ─── Ambil semua races (untuk dropdown) ───────────────────────────────────────
function getAllRaces(): array {
    return getDB()->query('SELECT id, name FROM races ORDER BY created_at DESC')->fetchAll();
}

// ─── Ambil items per race ─────────────────────────────────────────────────────
function getItemsByRace(int $raceId): array {
    $stmt = getDB()->prepare('SELECT * FROM items WHERE race_id = ? ORDER BY sort_order, id');
    $stmt->execute([$raceId]);
    return $stmt->fetchAll();
}

// ─── Status badge HTML ────────────────────────────────────────────────────────
function statusBadge(string $status): string {
    $map = [
        'valid'   => ['Sah',     'badge-success'],
        'invalid' => ['Tidak Sah','badge-danger'],
        'dns'     => ['DNS',     'badge-warning'],
        'dnf'     => ['DNF',     'badge-warning'],
        'dnq'     => ['DNQ',     'badge-secondary'],
        'active'  => ['Aktif',   'badge-success'],
        'inactive'=> ['Nonaktif','badge-secondary'],
    ];
    [$label, $class] = $map[$status] ?? [$status, 'badge-secondary'];
    return "<span class=\"badge $class\">$label</span>";
}

// ─── Tipe lomba Indonesia ─────────────────────────────────────────────────────
function typeLabel(string $type): string {
    return match($type) {
        'running'   => 'Lari',
        'triathlon' => 'Triathlon',
        'cycling'   => 'Sepeda',
        'swimming'  => 'Renang',
        default     => 'Lainnya',
    };
}

// ─── Timing point label ───────────────────────────────────────────────────────
function timingPointLabel(string $tp): string {
    return match($tp) {
        'start'      => 'Start',
        'checkpoint' => 'Checkpoint',
        'finish'     => 'Finish',
        default      => $tp,
    };
}

// ─── Pagination helper ────────────────────────────────────────────────────────
function pagination(int $total, int $perPage, int $page, string $baseUrl): string {
    $pages = (int)ceil($total / $perPage);
    if ($pages <= 1) return '';
    $html = '<div class="pagination">';
    for ($i = 1; $i <= $pages; $i++) {
        $active = $i === $page ? ' active' : '';
        $html .= "<a href=\"{$baseUrl}&page={$i}\" class=\"page-btn{$active}\">{$i}</a>";
    }
    $html .= '</div>';
    return $html;
}
