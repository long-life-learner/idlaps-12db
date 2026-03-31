<?php
// ============================================================
// IDLAPS Time — Konfigurasi Aplikasi
// ============================================================

// Database
define('DB_HOST',    'localhost');
define('DB_NAME',    'idlaps_time');
define('DB_USER',    'root');
define('DB_PASS',    '');
define('DB_CHARSET', 'utf8mb4');

// Aplikasi
define('APP_NAME',    'IDLAPS Time');
define('APP_VERSION', '1.0.0');
define('APP_URL',     'http://time.idlaps.com');

// Session
define('SESSION_NAME',     'idlaps_session');
define('SESSION_LIFETIME', 86400); // 24 jam

// Timezone
date_default_timezone_set('Asia/Jakarta');
