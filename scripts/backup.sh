#\!/bin/bash
# OltinChain Database Backup Script

set -e

BACKUP_DIR="/root/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_CONTAINER="server-postgres-1"
DB_NAME="oltinchain"
DB_USER="postgres"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL
echo "Backing up database..."
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/oltinchain_$DATE.sql.gz"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "oltinchain_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/oltinchain_$DATE.sql.gz"
ls -lh "$BACKUP_DIR/oltinchain_$DATE.sql.gz"
