-- ============================================================
-- MIGRATION: Multi-EPC Support + Performance Optimization
-- Jalankan: Get-Content schema_migration.sql | mysql -u root idlaps_time
-- ============================================================

-- 1. Buat tabel runner_chips (1 bib → banyak EPC)
CREATE TABLE IF NOT EXISTS `runner_chips` (
  `id`        INT NOT NULL AUTO_INCREMENT,
  `runner_id` INT NOT NULL,
  `race_id`   INT NOT NULL,  -- denormalisasi untuk lookup cepat
  `epc`       VARCHAR(100) NOT NULL,
  `label`     VARCHAR(50) DEFAULT NULL  COMMENT 'contoh: Chip Kiri, Chip Bib, Cadangan',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_epc_race` (`race_id`, `epc`),
  KEY `idx_runner_id` (`runner_id`),
  KEY `idx_epc`       (`epc`),
  CONSTRAINT `rc_runner_fk` FOREIGN KEY (`runner_id`) REFERENCES `runners` (`id`) ON DELETE CASCADE,
  CONSTRAINT `rc_race_fk`   FOREIGN KEY (`race_id`)   REFERENCES `races`   (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Migrasi EPC yang sudah ada dari tabel runners ke runner_chips
INSERT IGNORE INTO `runner_chips` (`runner_id`, `race_id`, `epc`, `label`)
SELECT `id`, `race_id`, `epc`, 'Utama'
FROM `runners`
WHERE `epc` IS NOT NULL AND `epc` != '';

-- 3. Jadikan runners.epc nullable (primary chip tetap ada sebagai referensi cepat)
ALTER TABLE `runners` MODIFY `epc` VARCHAR(100) DEFAULT NULL;

-- 4. Hapus unique constraint lama di runners.epc (pindah ke runner_chips)
ALTER TABLE `runners` DROP INDEX IF EXISTS `unique_epc`;

-- 5. Tambah UNIQUE constraint di chip_data untuk idempotency (aman retry)
ALTER TABLE `chip_data`
  ADD UNIQUE KEY IF NOT EXISTS `unique_read` (`race_id`, `epc`(50), `read_time`, `reader_id`(20));

-- 6. Index performa tambahan untuk chip_data (kueri ratusan ribu baris)
ALTER TABLE `chip_data`
  ADD INDEX IF NOT EXISTS `idx_race_reader`  (`race_id`, `reader_id`),
  ADD INDEX IF NOT EXISTS `idx_race_created` (`race_id`, `created_at`),
  ADD INDEX IF NOT EXISTS `idx_epc_race`     (`epc`, `race_id`);

-- 7. Index performa di runner_chips untuk lookup EPC → runner
-- (sudah ada dari CREATE TABLE di atas, tapi pastikan)
