-- Run this once as the MySQL root user:
--   Command Prompt / Git Bash :  mysql -u root -p < db/setup_mysql.sql
--   PowerShell                :  Get-Content db\setup_mysql.sql | mysql -u root -p
-- Change the password below and use the same one in your .env file.

CREATE DATABASE IF NOT EXISTS ai_email_generator
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'email_user'@'localhost' IDENTIFIED BY 'ChangeThisPassword123!';

GRANT ALL PRIVILEGES ON ai_email_generator.* TO 'email_user'@'localhost';
-- Django creates a temporary "test_" database when you run "python manage.py test".
GRANT ALL PRIVILEGES ON `test_ai_email_generator`.* TO 'email_user'@'localhost';

FLUSH PRIVILEGES;
