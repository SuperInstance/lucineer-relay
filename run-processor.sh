#!/bin/bash
# Lucineer Job Processor v2 — runs continuously, polling every 2 seconds.
# This wrapper is kept for backward compatibility; the production path uses
# systemd (lucineer-processor.service) instead.
cd /home/eileen/projects/lucineer-worker
exec python3 process_v2.py --loop --interval 2 >> processor.log 2>&1
