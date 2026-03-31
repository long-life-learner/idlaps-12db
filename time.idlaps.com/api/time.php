<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Menyediakan Unix Timestamp Server dengan akurasi mikrodetik
// Berguna untuk meng-offset waktu laptop Python agar persis dengan Server
echo json_encode(['server_time' => microtime(true)]);
