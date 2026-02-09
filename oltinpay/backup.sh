#\!/bin/bash
# OltinPay Daily Backup Script
# Runs daily at 3:00 via cron

set -e

# Config
BACKUP_DIR="/root/backups"
PROJECT_DIR="/root/server/oltinpay"
DATE=$(date +%Y-%m-%d_%H-%M)
BACKUP_NAME="oltinpay_${DATE}"
KEEP_DAYS=7

# Create backup directory
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"
cd "${BACKUP_DIR}/${BACKUP_NAME}"

echo "[$(date)] Starting backup..."

# 1. PostgreSQL dump
echo "[$(date)] Backing up PostgreSQL..."
docker exec server-postgres-1 pg_dump -U postgres oltinpay > postgres_dump.sql
gzip postgres_dump.sql

# 2. Redis dump
echo "[$(date)] Backing up Redis..."
docker exec server-redis-1 redis-cli BGSAVE
sleep 2
docker cp server-redis-1:/data/dump.rdb redis_dump.rdb 2>/dev/null || echo "No Redis dump found"

# 3. Project files (excluding node_modules, __pycache__, .git)
echo "[$(date)] Backing up project files..."
tar -czf project_files.tar.gz \
    --exclude="node_modules" \
    --exclude="__pycache__" \
    --exclude=".git" \
    --exclude=".next" \
    --exclude="*.pyc" \
    -C /root/server oltinpay

# 4. Docker compose config
cp "${PROJECT_DIR}/docker-compose.yml" ./ 2>/dev/null || true

# Create archive
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"

# Cleanup old backups
echo "[$(date)] Cleaning up backups older than ${KEEP_DAYS} days..."
find "${BACKUP_DIR}" -name "oltinpay_*.tar.gz" -mtime +${KEEP_DAYS} -delete

# Show result
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
echo "[$(date)] Backup complete: ${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})"
echo "[$(date)] Location: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
