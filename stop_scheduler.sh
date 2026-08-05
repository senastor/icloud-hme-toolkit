#!/bin/bash
# Stop all HME scheduler screen sessions

echo "🔍 Looking for HME scheduler sessions..."

SESSIONS=$(screen -list | grep "hme-scheduler-" | awk '{print $1}')

if [ -z "$SESSIONS" ]; then
    echo "   No scheduler sessions found"
    exit 0
fi

echo "   Found sessions:"
echo "$SESSIONS" | while read -r session; do
    echo "   - $session"
done

echo ""
read -p "Stop all sessions? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "$SESSIONS" | while read -r session; do
        echo "   Stopping $session..."
        screen -S "$session" -X quit
    done
    echo "✅ All scheduler sessions stopped"
else
    echo "❌ Cancelled"
fi
