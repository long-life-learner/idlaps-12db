<?php
// ─── API Middleware: API Key Authentication ───────────────────────────────────
require_once __DIR__ . '/../db.php';

function apiResponse(int $code, array $data): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=UTF-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function apiAuth(): array {
    $key = $_SERVER['HTTP_X_API_KEY'] ?? $_GET['api_key'] ?? '';
    if (!$key) {
        apiResponse(401, ['success' => false, 'message' => 'API Key tidak ditemukan. Sertakan header X-API-Key.']);
    }

    $db   = getDB();
    $stmt = $db->prepare('SELECT * FROM api_keys WHERE api_key = ? AND is_active = 1 LIMIT 1');
    $stmt->execute([$key]);
    $row = $stmt->fetch();

    if (!$row) {
        apiResponse(401, ['success' => false, 'message' => 'API Key tidak valid atau sudah dinonaktifkan.']);
    }

    // Update last_used
    $db->prepare('UPDATE api_keys SET last_used = NOW() WHERE id = ?')->execute([$row['id']]);

    return $row;
}

function jsonBody(): array {
    $raw  = file_get_contents('php://input');
    $data = json_decode($raw, true);
    if (!is_array($data)) {
        apiResponse(400, ['success' => false, 'message' => 'Request body harus berupa JSON yang valid.']);
    }
    return $data;
}
