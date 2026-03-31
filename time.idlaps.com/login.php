<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/auth.php';

if (isLoggedIn()) {
    header('Location: /');
    exit;
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';

    if (!$username || !$password) {
        $error = 'Username dan password wajib diisi.';
    } elseif (doLogin($username, $password)) {
        header('Location: /');
        exit;
    } else {
        $error = 'Username atau password salah.';
    }
}
?>
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Masuk — <?= APP_NAME ?></title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
<div class="login-page">
  <div class="login-card">
    <div class="login-logo">
      <div class="login-logo-icon">⏱</div>
      <div class="login-title"><?= APP_NAME ?></div>
      <div class="login-subtitle">Race Scoring System</div>
    </div>

    <?php if ($error): ?>
      <div class="alert alert-danger"><?= htmlspecialchars($error) ?></div>
    <?php endif; ?>

    <form method="POST" action="/login.php">
      <div class="form-group" style="margin-bottom:16px">
        <label class="form-label">Username</label>
        <input type="text" name="username" class="form-control"
               value="<?= htmlspecialchars($_POST['username'] ?? '') ?>"
               placeholder="Masukkan username" autofocus required>
      </div>
      <div class="form-group" style="margin-bottom:24px">
        <label class="form-label">Password</label>
        <input type="password" name="password" class="form-control"
               placeholder="Masukkan password" required>
      </div>
      <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center">
        Masuk
      </button>
    </form>
  </div>
</div>
<script src="/static/js/app.js"></script>
</body>
</html>
