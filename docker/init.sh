#!/bin/bash
set -e

# Initialize all databases for qStack services
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<- 'SQL'
  SELECT 'CREATE DATABASE qstack_api'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'qstack_api')\gexec
  SELECT 'CREATE DATABASE qstack_storage'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'qstack_storage')\gexec
  SELECT 'CREATE DATABASE qstack_network'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'qstack_network')\gexec
  SELECT 'CREATE DATABASE qstack_image'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'qstack_image')\gexec
  SELECT 'CREATE DATABASE qstack_billing'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'qstack_billing')\gexec
  SELECT 'CREATE DATABASE qstack_backup'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'qstack_backup')\gexec
  SELECT 'CREATE DATABASE qstack_ai'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'qstack_ai')\gexec
SQL
