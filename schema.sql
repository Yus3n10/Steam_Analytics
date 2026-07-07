-- Run this in phpMyAdmin's SQL tab, or via the mysql CLI

CREATE DATABASE IF NOT EXISTS steam_analytics;
USE steam_analytics;

-- Raw table: exactly what the API gives us, untouched
CREATE TABLE IF NOT EXISTS games_raw (
    id INT AUTO_INCREMENT PRIMARY KEY,
    app_id INT NOT NULL,
    name VARCHAR(255),
    genres VARCHAR(500),
    price_usd DECIMAL(10,2),
    is_free BOOLEAN,
    release_date VARCHAR(50),
    developer VARCHAR(255),
    current_players INT,
    pulled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_pull (app_id, pulled_at)
);

-- Clean table: we'll build this later once we see what needs fixing
CREATE TABLE IF NOT EXISTS games_clean (
    id INT AUTO_INCREMENT PRIMARY KEY,
    app_id INT NOT NULL,
    name VARCHAR(255),
    genre VARCHAR(100),
    price_usd DECIMAL(10,2),
    is_free BOOLEAN,
    release_date DATE,
    developer VARCHAR(255),
    current_players INT,
    pulled_at DATETIME,
    UNIQUE KEY unique_clean (app_id, genre, pulled_at)
);