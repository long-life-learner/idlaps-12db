<?php
require_once __DIR__ . '/../../config.php';
require_once __DIR__ . '/../../auth.php';
require_once __DIR__ . '/../../db.php';
require_once __DIR__ . '/../../includes/functions.php';
requireLogin();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') redirect('/pages/races/list.php');

$id = (int)($_POST['id'] ?? 0);
$db = getDB();
$db->prepare('DELETE FROM races WHERE id = ?')->execute([$id]);
setFlash('success','Lomba berhasil dihapus.');
redirect('/pages/races/list.php');
