# iCloud HME Auto Scheduler

Otomatis create 5 HME per jam sampai target tercapai, bypass rate limit Apple iCloud.

## Files

- `auto_scheduler.py` — Main scheduler (5 HME/hour, continuous)
- `auto_batch_create.py` — One-shot batch creator (manual target)
- `start_scheduler.sh` — Launch scheduler in screen session
- `stop_scheduler.sh` — Stop all scheduler sessions

## Quick Start

```bash
cd /root/icloud-hme

# Start scheduler (5 HME/hour sampai 500)
./start_scheduler.sh andelimit1 500 5

# Attach to see logs
screen -r hme-scheduler-andelimit1

# Detach (keep running)
# Ctrl+A then D

# Stop scheduler
./stop_scheduler.sh
```

## Usage

### Auto Scheduler (Recommended)

```bash
# Default: 5 HME/hour sampai 500
python3 auto_scheduler.py --account andelimit1 --target 500

# Custom rate: 3 HME/hour sampai 200
python3 auto_scheduler.py --account andelimit1 --target 200 --per-hour 3

# With label prefix
python3 auto_scheduler.py --account andelimit1 --target 500 --label "auto-2608"
```

**Parameters:**
- `--account` — Account name atau ID (required)
- `--target` — Target total HME (default: 500)
- `--per-hour` — HME per jam (default: 5, stay under radar)
- `--interval` — Detik antar creation (default: 3)
- `--label` — Label prefix untuk HME

**Flow:**
1. Create 5 HME dalam ~15 detik (3s interval)
2. Wait sampai jam berikutnya (countdown tiap 5 menit)
3. Repeat sampai target tercapai atau kena rate limit
4. Graceful shutdown via Ctrl+C

### Batch Creator (One-shot)

```bash
# Create 10 HME sekarang, batch 5, delay 10s
python3 auto_batch_create.py \
  --account andelimit1 \
  --target 10 \
  --batch 5 \
  --delay 10
```

## Screen Session Management

```bash
# List active sessions
screen -list | grep hme-scheduler

# Attach to session
screen -r hme-scheduler-andelimit1

# Detach from session (keep running)
# Press: Ctrl+A then D

# Kill session
screen -S hme-scheduler-andelimit1 -X quit
```

## Rate Limit Strategy

Apple iCloud HME limit berdasarkan thread di https://discussions.apple.com/thread/254455807:
- **Bukan hard cap 40** — bisa sampai 500+
- **Hourly rate limit** — create terlalu cepat → HTTP 421/429
- **Strategy**: 5 HME/hour = 120 HME/hari = ~500 dalam 4 hari
- Auto-stop kalau detect rate limit keywords: `limit`, `exceeded`, `quota`, `421`, `429`

## Monitoring

```bash
# Check current count
cd /root/icloud-hme && python3 << 'EOF'
import json
d = json.load(open('accounts.json'))
for acc_id, a in d['accounts'].items():
    print(f"{a['name']}: {a.get('alias_total', 0)} HME")
EOF

# View latest created emails
tail -20 /root/icloud-hme/results/latest_emails.txt
```

## Example Run

```
🕐 iCloud HME Hourly Scheduler
============================================================
📧 Account: andelimit1 (acc_56df...)
   Current: 40 HME
🎯 Target: 500 HME
⏱️  Rate: 5 HME/hour
   Interval: 3.0s between creations
🕐 Started: 2026-08-01 21:57:00
============================================================

============================================================
🕐 Hour 1 | 2026-08-01 21:57:00
📊 Current: 40 | Target: 500 | Remaining: 460
📦 Creating 5 HME this hour...
============================================================
  [1/5] Creating HME... ✓ abc123_xyz@icloud.com
  [2/5] Creating HME... ✓ def456_uvw@icloud.com
  [3/5] Creating HME... ✓ ghi789_rst@icloud.com
  [4/5] Creating HME... ✓ jkl012_opq@icloud.com
  [5/5] Creating HME... ✓ mno345_lmn@icloud.com

📊 Hour 1 summary:
   ✓ Success: 5
   ✗ Errors: 0
   📧 New total: 45

⏳ Batch complete (5 created this hour). Waiting until 22:00:00...
   Next batch: 5 HME at 2026-08-01 22:00
   ⏰ 55m 0s remaining...
```

## Troubleshooting

**Session not starting:**
```bash
# Check if already running
screen -list | grep hme-scheduler

# Kill stale session
screen -S hme-scheduler-andelimit1 -X quit

# Restart
./start_scheduler.sh andelimit1 500 5
```

**Rate limit hit early:**
- Reduce `--per-hour` dari 5 → 3
- Increase `--interval` dari 3 → 5

**Account status error:**
```bash
# Check account status via web UI: http://194.163.172.100:5050
# Or directly in accounts.json
```
