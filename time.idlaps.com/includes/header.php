<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?= e($pageTitle ?? APP_NAME) ?> — <?= APP_NAME ?></title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
<?php $admin = getCurrentAdmin(); ?>
<div class="app-wrapper">
  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="sidebar-brand">
      <div class="brand-icon">⏱</div>
      <div>
        <div class="brand-name"><?= APP_NAME ?></div>
        <div class="brand-version">v<?= APP_VERSION ?></div>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div class="nav-group">
        <div class="nav-label">Utama</div>
        <a href="/" class="nav-item <?= ($currentPage ?? '') === 'dashboard' ? 'active' : '' ?>">
          <span class="nav-icon">📊</span> Dashboard
        </a>
        <a href="/pages/races/list.php" class="nav-item <?= ($currentPage ?? '') === 'races' ? 'active' : '' ?>">
          <span class="nav-icon">🏅</span> Lomba
        </a>
      </div>

      <?php if (!empty($raceId)): ?>
      <div class="nav-group">
        <div class="nav-label">Lomba Ini</div>
        <a href="/pages/runners/list.php?race_id=<?= $raceId ?>" class="nav-item <?= ($currentPage ?? '') === 'runners' ? 'active' : '' ?>">
          <span class="nav-icon">🏃</span> Peserta
        </a>
        <a href="/pages/rules/list.php?race_id=<?= $raceId ?>" class="nav-item <?= ($currentPage ?? '') === 'rules' ? 'active' : '' ?>">
          <span class="nav-icon">📋</span> Aturan Scoring
        </a>
        <a href="/pages/chip_data/list.php?race_id=<?= $raceId ?>" class="nav-item <?= ($currentPage ?? '') === 'chip_data' ? 'active' : '' ?>">
          <span class="nav-icon">📡</span> Live Monitor
        </a>
        <a href="/pages/results/list.php?race_id=<?= $raceId ?>" class="nav-item <?= ($currentPage ?? '') === 'results' ? 'active' : '' ?>">
          <span class="nav-icon">🏆</span> Hasil
        </a>
      </div>
      <?php endif; ?>

      <div class="nav-group">
        <div class="nav-label">Pengaturan</div>
         <a href="/pages/devices/list.php" class="nav-item <?= ($currentPage ?? '') === 'devices' ? 'active' : '' ?>">
          <span class="nav-icon">📡</span> Device / Reader
        </a>
        <a href="/pages/api_keys/list.php" class="nav-item <?= ($currentPage ?? '') === 'api_keys' ? 'active' : '' ?>">
          <span class="nav-icon">🔑</span> API Keys
        </a>
        <a href="/pages/api-tester.php" class="nav-item <?= ($currentPage ?? '') === 'api-tester' ? 'active' : '' ?>">
          <span class="nav-icon">🧪</span> API Tester
        </a>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="admin-info">
        <div class="admin-avatar"><?= strtoupper(substr($admin['name'] ?? 'A', 0, 1)) ?></div>
        <div>
          <div class="admin-name"><?= e($admin['name'] ?? '') ?></div>
          <a href="/logout.php" class="logout-link">Keluar</a>
        </div>
      </div>
    </div>
  </aside>

  <!-- Main Content -->
  <main class="main-content">
    <div class="content-inner">
      <?php $flash = getFlash(); if ($flash): ?>
        <div class="alert alert-<?= $flash['type'] ?>"><?= e($flash['message']) ?></div>
      <?php endif; ?>
