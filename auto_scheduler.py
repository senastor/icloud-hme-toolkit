#!/usr/bin/env python3
"""
iCloud HME Auto Scheduler — 5 HME per hour, continuous until target reached.

Rate limit strategy:
  - Apple iCloud HME has hourly rate limit (not hard cap at 40)
  - Create 5 HME/hour to stay under radar
  - Run 24/7 until target reached

Usage:
    python3 auto_scheduler.py --account andelimit1 --target 500

    # Run in background (screen/tmux recommended)
    screen -S hme-scheduler
    python3 auto_scheduler.py --account andelimit1 --target 500
"""
import sys
import json
import time
import signal
import argparse
from pathlib import Path
from datetime import datetime, timedelta

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from account_manager import AccountManager

# Global flag for graceful shutdown
_shutdown = False

def signal_handler(sig, frame):
    global _shutdown
    print("\n⚠️  Shutdown signal received. Finishing current batch...")
    _shutdown = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def wait_until_next_hour(current_count: int, batch_per_hour: int):
    """Wait until next hour boundary, show countdown."""
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    wait_seconds = (next_hour - now).total_seconds()
    
    print(f"\n⏳ Batch complete ({current_count} created this hour). Waiting until {next_hour.strftime('%H:%M:%S')}...")
    print(f"   Next batch: {batch_per_hour} HME at {next_hour.strftime('%Y-%m-%d %H:%M')}")
    
    # Show countdown every 5 minutes
    last_print = time.time()
    while wait_seconds > 0 and not _shutdown:
        time.sleep(1)
        wait_seconds -= 1
        
        # Print countdown every 5 min
        if time.time() - last_print >= 300 or wait_seconds <= 60:
            mins = int(wait_seconds // 60)
            secs = int(wait_seconds % 60)
            print(f"   ⏰ {mins}m {secs}s remaining...")
            last_print = time.time()
    
    if _shutdown:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="iCloud HME hourly scheduler")
    parser.add_argument("--account", required=True, help="Account name or ID")
    parser.add_argument("--target", type=int, default=500, help="Target total HME count (default: 500)")
    parser.add_argument("--per-hour", type=int, default=5, help="HME to create per hour (default: 5)")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between each HME creation (default: 3)")
    parser.add_argument("--label", default="", help="Label prefix for created HME")
    args = parser.parse_args()

    mgr = AccountManager()

    # Find account
    acc_id = None
    for aid, acc in mgr.accounts.items():
        if aid == args.account or acc.get("name") == args.account:
            acc_id = aid
            break

    if not acc_id:
        print(f"❌ Account '{args.account}' not found")
        return 1

    account = mgr.accounts[acc_id]
    
    print("=" * 60)
    print("🕐 iCloud HME Hourly Scheduler")
    print("=" * 60)
    print(f"📧 Account: {account.get('name')} ({acc_id[:8]}...)")
    print(f"   Current: {account.get('alias_total', 0)} HME")
    print(f"🎯 Target: {args.target} HME")
    print(f"⏱️  Rate: {args.per_hour} HME/hour")
    print(f"   Interval: {args.interval}s between creations")
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    if account.get("status") != "active":
        print(f"❌ Account status is '{account.get('status')}', not 'active'")
        return 1

    hour_number = 0
    total_created_run = 0

    while not _shutdown:
        hour_number += 1
        
        # Refresh account state
        mgr._load()
        account = mgr.accounts[acc_id]
        current_total = account.get("alias_total", 0)

        if current_total >= args.target:
            print(f"\n✅ Target reached: {current_total} >= {args.target}")
            print(f"📊 Total created this run: {total_created_run}")
            print(f"⏱️  Runtime: {hour_number} hours")
            break

        remaining = args.target - current_total
        this_hour_count = min(args.per_hour, remaining)

        print(f"\n{'='*60}")
        print(f"🕐 Hour {hour_number} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Current: {current_total} | Target: {args.target} | Remaining: {remaining}")
        print(f"📦 Creating {this_hour_count} HME this hour...")
        print(f"{'='*60}")

        hour_success = 0
        hour_errors = 0
        rate_limited = False

        for i in range(this_hour_count):
            if _shutdown:
                break

            print(f"  [{i+1}/{this_hour_count}] Creating HME...", end=" ", flush=True)

            try:
                results = mgr.create_aliases_for_account(
                    acc_id,
                    count=1,
                    label=args.label,
                )

                if results and results[0].get("ok"):
                    email = results[0].get("email", "?")
                    print(f"✓ {email}")
                    hour_success += 1
                    total_created_run += 1
                else:
                    err = results[0].get("error", "unknown") if results else "no result"
                    print(f"✗ {err[:80]}")
                    hour_errors += 1

                    # Check for rate limit
                    err_lower = err.lower()
                    if any(kw in err_lower for kw in ("limit", "exceeded", "maximum", "quota", "429", "rate", "throttle", "421")):
                        print(f"   ⚠️  Rate limit detected. Pausing this hour.")
                        rate_limited = True
                        break

            except Exception as e:
                print(f"✗ Exception: {str(e)[:80]}")
                hour_errors += 1

            # Wait between creations (except last one)
            if i < this_hour_count - 1 and args.interval > 0:
                time.sleep(args.interval)

        print(f"\n📊 Hour {hour_number} summary:")
        print(f"   ✓ Success: {hour_success}")
        print(f"   ✗ Errors: {hour_errors}")
        
        # Refresh final count
        mgr._load()
        account = mgr.accounts[acc_id]
        new_total = account.get("alias_total", 0)
        print(f"   📧 New total: {new_total}")

        if new_total >= args.target:
            print(f"\n✅ Target reached!")
            break

        if _shutdown:
            print(f"\n⚠️  Shutdown requested. Exiting gracefully.")
            break

        # Wait until next hour
        if not wait_until_next_hour(hour_success, args.per_hour):
            break

    print(f"\n{'='*60}")
    print(f"🏁 Scheduler stopped")
    print(f"{'='*60}")
    print(f"⏱️  Runtime: {hour_number} hours")
    print(f"✓ Total created this run: {total_created_run}")
    print(f"📧 Final count: {mgr.accounts[acc_id].get('alias_total', 0)}")
    print(f"🕐 Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
