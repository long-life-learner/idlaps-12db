-- IDLAPS Time - Race Scoring System
-- Database: idlaps_time
-- Charset: utf8mb4

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+07:00";

CREATE DATABASE IF NOT EXISTS `idlaps_time`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE `idlaps_time`;

-- --------------------------------------------------------
-- Admin users
-- --------------------------------------------------------
CREATE TABLE `admins` (
  `id`         INT NOT NULL AUTO_INCREMENT,
  `username`   VARCHAR(50) NOT NULL,
  `password`   VARCHAR(255) NOT NULL,
  `name`       VARCHAR(100) DEFAULT NULL,
  `is_active`  TINYINT NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Default admin: username=admin password=admin123
INSERT INTO `admins` (`username`, `password`, `name`) VALUES
('admin', '$2y$12$YHfCPFgxvHNLNULo4JFkdO7s9aKz0fGPqQXuiG1Tm9KtGiKLr.1Gy', 'Administrator');

-- --------------------------------------------------------
-- Races / Events
-- --------------------------------------------------------
CREATE TABLE `races` (
  `id`          INT NOT NULL AUTO_INCREMENT,
  `name`        VARCHAR(255) NOT NULL,
  `type`        ENUM('running','triathlon','cycling','swimming','other') NOT NULL DEFAULT 'running',
  `race_date`   DATE DEFAULT NULL,
  `race_time`   TIME DEFAULT NULL,
  `gun_time`    DATETIME(3) DEFAULT NULL  COMMENT 'Waktu pistol start ditembakkan',
  `banner`      VARCHAR(255) DEFAULT NULL,
  `description` TEXT DEFAULT NULL,
  `is_active`   TINYINT NOT NULL DEFAULT 1,
  `created_at`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Items (kategori lomba: 1KM, 5KM, 10KM, dsb.)
-- --------------------------------------------------------
CREATE TABLE `items` (
  `id`             INT NOT NULL AUTO_INCREMENT,
  `race_id`        INT NOT NULL,
  `title`          VARCHAR(100) NOT NULL,
  `timing_enabled` TINYINT NOT NULL DEFAULT 1,
  `type`           ENUM('normal','team','relay') NOT NULL DEFAULT 'normal',
  `distance`       FLOAT DEFAULT NULL  COMMENT 'Jarak dalam meter',
  `sort_order`     INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `race_id` (`race_id`),
  CONSTRAINT `items_race_fk` FOREIGN KEY (`race_id`) REFERENCES `races` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Devices (RFID readers yang digunakan)
-- --------------------------------------------------------
CREATE TABLE `devices` (
  `id`            INT NOT NULL AUTO_INCREMENT,
  `race_id`       INT DEFAULT NULL,
  `name`          VARCHAR(100) DEFAULT NULL,
  `reader_ip`     VARCHAR(50) DEFAULT NULL   COMMENT 'IP Address reader / reader_id field dari hardware',
  `serial_number` VARCHAR(24) DEFAULT NULL   COMMENT 'Serial Number HEX dari hardware (12 bytes raw = 24 HEX chars). Pengganti API Key untuk Zero-Config auth.',
  `position`      VARCHAR(100) DEFAULT NULL  COMMENT 'contoh: Start Gate, Finish Line, Checkpoint 5KM',
  `created_at`    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_serial_number` (`serial_number`),
  KEY `race_id` (`race_id`),
  CONSTRAINT `devices_race_fk` FOREIGN KEY (`race_id`) REFERENCES `races` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Timing Rules (aturan scoring per timing point)
-- --------------------------------------------------------
CREATE TABLE `timing_rules` (
  `id`              INT NOT NULL AUTO_INCREMENT,
  `item_id`         INT NOT NULL,
  `device_id`       INT DEFAULT NULL,
  `timing_point`    ENUM('start','checkpoint','finish') NOT NULL,
  `score_type`      ENUM('net_time','gun_time') NOT NULL DEFAULT 'net_time',
  `open_time`       INT NOT NULL DEFAULT 0    COMMENT 'Detik relatif dari gun time',
  `close_time`      INT NOT NULL DEFAULT 86400 COMMENT 'Detik relatif dari gun time',
  `increase_days`   INT NOT NULL DEFAULT 0,
  `auto_calculate`  TINYINT NOT NULL DEFAULT 1,
  `must_pass`       TINYINT NOT NULL DEFAULT 0,
  `fastest_speed`   FLOAT NOT NULL DEFAULT 10  COMMENT 'Kecepatan maksimal valid (m/s)',
  `sort`            ENUM('first','last') NOT NULL DEFAULT 'first',
  `live_broadcast`  TINYINT NOT NULL DEFAULT 1,
  `how_many_passes` INT NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  KEY `device_id` (`device_id`),
  CONSTRAINT `timing_rules_item_fk`   FOREIGN KEY (`item_id`)   REFERENCES `items` (`id`) ON DELETE CASCADE,
  CONSTRAINT `timing_rules_device_fk` FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Runners (peserta)
-- --------------------------------------------------------
CREATE TABLE `runners` (
  `id`        INT NOT NULL AUTO_INCREMENT,
  `race_id`   INT NOT NULL,
  `item_id`   INT NOT NULL,
  `bib`       VARCHAR(20) NOT NULL,
  `epc`       VARCHAR(100) NOT NULL  COMMENT 'EPC code dari RFID chip',
  `name`      VARCHAR(255) DEFAULT NULL,
  `gender`    ENUM('M','F') NOT NULL DEFAULT 'M',
  `age`       INT DEFAULT NULL,
  `age_group` VARCHAR(50) DEFAULT NULL,
  `team`      VARCHAR(100) DEFAULT NULL,
  `phone`     VARCHAR(20) DEFAULT NULL,
  `email`     VARCHAR(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_bib` (`race_id`,`bib`),
  UNIQUE KEY `unique_epc` (`race_id`,`epc`),
  KEY `race_id` (`race_id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `runners_race_fk` FOREIGN KEY (`race_id`) REFERENCES `races` (`id`) ON DELETE CASCADE,
  CONSTRAINT `runners_item_fk` FOREIGN KEY (`item_id`) REFERENCES `items` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Chip Data (raw RFID reads dari IDLAPS Checkpoint)
-- --------------------------------------------------------
CREATE TABLE `chip_data` (
  `id`           BIGINT NOT NULL AUTO_INCREMENT,
  `race_id`      INT NOT NULL,
  `epc`          VARCHAR(100) NOT NULL,
  `bib`          VARCHAR(20) DEFAULT NULL  COMMENT 'Di-resolve dari runners.epc',
  `reader_id`    VARCHAR(50) DEFAULT NULL  COMMENT 'IP Address reader IDLAPS',
  `read_time`    DATETIME(3) NOT NULL      COMMENT 'Timestamp presisi millisecond',
  `rssi`         INT DEFAULT NULL,
  `synced_from`  VARCHAR(50) DEFAULT NULL  COMMENT 'IP sumber IDLAPS Checkpoint app',
  `created_at`   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `epc_time` (`epc`,`read_time`),
  KEY `race_id`  (`race_id`),
  KEY `reader_id`(`reader_id`),
  CONSTRAINT `chip_data_race_fk` FOREIGN KEY (`race_id`) REFERENCES `races` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Results (hasil kalkulasi)
-- --------------------------------------------------------
CREATE TABLE `results` (
  `id`             INT NOT NULL AUTO_INCREMENT,
  `race_id`        INT NOT NULL,
  `item_id`        INT NOT NULL,
  `runner_id`      INT NOT NULL,
  `bib`            VARCHAR(20) DEFAULT NULL,
  `gun_time_ms`    BIGINT DEFAULT NULL  COMMENT 'Gun time dalam millisecond',
  `net_time_ms`    BIGINT DEFAULT NULL  COMMENT 'Net time dalam millisecond',
  `start_time`     DATETIME(3) DEFAULT NULL,
  `finish_time`    DATETIME(3) DEFAULT NULL,
  `total_passes`   INT NOT NULL DEFAULT 0,
  `status`         ENUM('valid','invalid','dns','dnf','dnq') NOT NULL DEFAULT 'valid',
  `overall_rank`   INT DEFAULT NULL,
  `gender_rank`    INT DEFAULT NULL,
  `age_rank`       INT DEFAULT NULL,
  `calculated_at`  TIMESTAMP NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_runner_result` (`race_id`,`item_id`,`runner_id`),
  KEY `race_id`   (`race_id`),
  KEY `item_id`   (`item_id`),
  KEY `runner_id` (`runner_id`),
  CONSTRAINT `results_race_fk`   FOREIGN KEY (`race_id`)   REFERENCES `races`   (`id`),
  CONSTRAINT `results_item_fk`   FOREIGN KEY (`item_id`)   REFERENCES `items`   (`id`),
  CONSTRAINT `results_runner_fk` FOREIGN KEY (`runner_id`) REFERENCES `runners` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- API Keys (untuk autentikasi IDLAPS Checkpoint)
-- --------------------------------------------------------
CREATE TABLE `api_keys` (
  `id`         INT NOT NULL AUTO_INCREMENT,
  `race_id`    INT DEFAULT NULL,
  `name`       VARCHAR(100) NOT NULL,
  `api_key`    VARCHAR(64) NOT NULL,
  `is_active`  TINYINT NOT NULL DEFAULT 1,
  `last_used`  TIMESTAMP NULL DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `api_key` (`api_key`),
  KEY `race_id` (`race_id`),
  CONSTRAINT `api_keys_race_fk` FOREIGN KEY (`race_id`) REFERENCES `races` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
