#!/bin/bash
# Lucineer Job Processor — runs continuously, polling every 3 seconds
cd /home/eileen/projects/lucineer-worker
while true; do
    ./process-jobs.sh --once >> processor.log 2>&1
    sleep 3
done
