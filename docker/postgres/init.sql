-- Vocara PostgreSQL Database Initialization Script
-- Executed on initial container volume creation

-- 1. Enable standard cryptographic and UUID extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Configure default encoding and timezone settings
SET client_encoding = 'UTF8';
SET timezone = 'UTC';

-- 3. Grant schema permissions to the default user
GRANT ALL PRIVILEGES ON SCHEMA public TO vocara_user;
