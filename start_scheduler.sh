#!/bin/bash
# Quick launcher for iCloud HME scheduler in screen session

ACCOUNT="${1:-andelimit1}"
TARGET="${2:-500}"
PER_HOUR="${3:-5}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_NAME="hme-scheduler-${ACCOUNT}"

# Check if session already exists
if screen -list | grep -q "$SESSION_NAME"; then
    echo "⚠️  Session '$SESSION_NAME' already running."
    echo "   Attach: screen -r $SESSION_NAME"
    echo "   Kill: screen -S $SESSION_NAME -X quit"
    exit 1
fi

echo "🚀 Starting HME scheduler in screen session: $SESSION_NAME"
echo "   Account: $ACCOUNT"
echo "   Target: $TARGET HME"
echo "   Rate: $PER_HOUR HME/hour"
echo ""
echo "Commands:"
echo "  Attach: screen -r $SESSION_NAME"
echo "  Detach: Ctrl+A then D"
echo "  Stop: Ctrl+C (in attached session)"
echo ""

screen -dmS "$SESSION_NAME" bash -c "cd '$SCRIPT_DIR' && python3 auto_scheduler.py --account '$ACCOUNT' --target $TARGET --per-hour $PER_HOUR"

sleep 1

if screen -list | grep -q "$SESSION_NAME"; then
    echo "✅ Scheduler started successfully"
    echo "   View logs: screen -r $SESSION_NAME"
else
    echo "❌ Failed to start scheduler"
    exit 1
fi
