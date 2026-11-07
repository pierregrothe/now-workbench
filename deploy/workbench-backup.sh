#!/usr/bin/env bash
# deploy/workbench-backup.sh
# Nightly database backup to the Garage bucket on the NAS (ADR-029), run by cron on srv01chambly.
# Author: Pierre Grothe
# Date: 2026-11-07
#
# The internet-facing workbench container is firewalled away from the LAN, so it cannot reach
# Garage. This job runs a separate, short-lived container from the same image on the host
# network: it reads the database volume, uploads one snapshot and exits. It gets only the
# WORKBENCH_BACKUP_S3_* settings, never the master key or the other secrets in .env.
set -euo pipefail

cd "$(dirname "$0")/.."

docker run --rm \
    --network host \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    --env-file <(grep '^WORKBENCH_BACKUP_S3_' .env) \
    -v now-workbench_workbench-data:/app/data \
    --entrypoint workbench \
    now-workbench:latest backup --s3
