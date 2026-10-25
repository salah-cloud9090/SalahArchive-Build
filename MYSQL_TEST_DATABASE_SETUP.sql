-- Optional manual setup for the isolated test database only.
-- Replace the placeholder password before executing this file in MySQL Workbench.
-- Do not run this against the production database.
CREATE DATABASE IF NOT EXISTS salah_archive_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'archive_test_app'@'localhost'
  IDENTIFIED BY 'REPLACE_WITH_A_LONG_RANDOM_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, REFERENCES
  ON salah_archive_test.* TO 'archive_test_app'@'localhost';
FLUSH PRIVILEGES;
