#!/bin/bash
export HOME=/Users/igorcleto
export PATH=/Library/Frameworks/Python.framework/Versions/3.8/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin

LOG=/Users/igorcleto/automacoes/barbeiro/cron.log
echo "--- $(date '+%Y-%m-%d %H:%M:%S') ---" >> "$LOG"
/Library/Frameworks/Python.framework/Versions/3.8/bin/python3 \
    /Users/igorcleto/automacoes/barbeiro/schedule_recurring.py >> "$LOG" 2>&1
echo "exit: $?" >> "$LOG"
