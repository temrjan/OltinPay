#!/bin/bash
# OltinChain Database Restore Script

set -e

BACKUP_FILE="$1"
DB_CONTAINER="server-postgres-1"
DB_NAME="oltinchain"
DB_USER="postgres"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Available backups:"
    ls -lh /root/backups/oltinchain_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "WARNING: This will overwrite the current database!"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

echo "Restoring database from $BACKUP_FILE..."

# Drop and recreate database
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;"

# Restore
gunzip -c "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" "$DB_NAME"

echo "Restore completed!"
