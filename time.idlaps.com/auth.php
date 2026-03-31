<?php
require_once __DIR__ . '/config.php';

function startSession(): void {
    if (session_status() === PHP_SESSION_NONE) {
        session_name(SESSION_NAME);
        session_set_cookie_params(['lifetime' => SESSION_LIFETIME, 'path' => '/']);
        session_start();
    }
}

function isLoggedIn(): bool {
    startSession();
    return isset($_SESSION['admin_id']);
}

function requireLogin(): void {
    if (!isLoggedIn()) {
        header('Location: /login.php');
        exit;
    }
}

function getCurrentAdmin(): ?array {
    startSession();
    return $_SESSION['admin'] ?? null;
}

function doLogin(string $username, string $password): bool {
    require_once __DIR__ . '/db.php';
    $db   = getDB();
    $stmt = $db->prepare('SELECT * FROM admins WHERE username = ? AND is_active = 1 LIMIT 1');
    $stmt->execute([$username]);
    $admin = $stmt->fetch();

    if ($admin && password_verify($password, $admin['password'])) {
        startSession();
        session_regenerate_id(true);
        $_SESSION['admin_id'] = $admin['id'];
        $_SESSION['admin']    = [
            'id'       => $admin['id'],
            'username' => $admin['username'],
            'name'     => $admin['name'],
        ];
        return true;
    }
    return false;
}

function doLogout(): void {
    startSession();
    session_destroy();
    header('Location: /login.php');
    exit;
}
