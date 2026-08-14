CREATE DATABASE IF NOT EXISTS pdf_extraction CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'pdf_user'@'localhost' IDENTIFIED BY 'change_me';
GRANT SELECT, INSERT, UPDATE, DELETE ON pdf_extraction.* TO 'pdf_user'@'localhost';
