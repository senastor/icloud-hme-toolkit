#!/usr/bin/env python3
"""
Auto batch HME creation — loop sampai limit tercapai.

Usage:
    python3 auto_batch_create.py --account andelimit1 --target 100 --batch 5 --interval 3

Flow:
  1. Check current alias count
  2. Loop create `batch` HME per iteration, interval `interval` seconds between accounts
  3. Stop when:
     - Total created >= target
     - Rate limit error detected
     - Account reaches hard limit (e.g., 40 for iCloud)
"""
import sys
import json
import time
import argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from account_manager import AccountManager


def main():
    parser = argparse.ArgumentParser(description="Auto batch HME creation loop")
    parser.add_argument("--account", required=True, help="Account name or ID")
    parser.add_argument("--target", type=int, default=100, help="Target total HME count")
    parser.add_argument("--batch", type=int, default=5, help="HME per batch iteration")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between accounts in batch")
    parser.add_argument("--delay", type=float, default=10.0, help="Seconds between batch iterations")
    parser.add_argument("--label", default="", help="Label prefix for created HME")
    args = parser.parse_args()

    mgr = AccountManager()

    # Find account by name or ID
    acc_id = None
    for aid, acc in mgr.accounts.items():
        if aid == args.account or acc.get("name") == args.account:
            acc_id = aid
            break

    if not acc_id:
        print(f"❌ Account '{args.account}' not found")
        return 1

    account = mgr.accounts[acc_id]
    print(f"🎯 Target: {args.target} HME")
    print(f"📦 Batch size: {args.batch}")
    print(f"⏱️  Interval: {args.interval}s between accounts, {args.delay}s between batches")
    print(f"📧 Account: {account.get('name')} ({acc_id[:8]}...)")
    print(f"   Current: {account.get('alias_total', 0)} total, {account.get('alias_active', 0)} active")
    print()

    if account.get("status") != "active":
        print(f"❌ Account status is '{account.get('status')}', not 'active'")
        return 1

    iteration = 0
    total_created = 0
    total_errors = 0

    while True:
        iteration += 1
        current_total = account.get("alias_total", 0)

        if current_total >= args.target:
            print(f"\n✅ Target reached: {current_total} >= {args.target}")
            break

        remaining = args.target - current_total
        batch_count = min(args.batch, remaining)

        print(f"[Iteration {iteration}] Creating {batch_count} HME... (current: {current_total})")

        try:
            results = mgr.create_aliases_for_account(
                acc_id,
                count=batch_count,
                label=args.label,
            )

            success = sum(1 for r in results if r.get("ok"))
            errors = sum(1 for r in results if not r.get("ok"))
            total_created += success
            total_errors += errors

            print(f"   ✓ {success} success, ✗ {errors} errors")

            # Check for rate limit / hard limit errors
            for r in results:
                if not r.get("ok"):
                    err = r.get("error", "").lower()
                    if any(kw in err for kw in ("limit", "exceeded", "maximum", "quota", "429", "rate", "throttle")):
                        print(f"\n⚠️  Rate/Hard limit detected: {r.get('error')[:100]}")
                        print(f"   Stopping. Total created this run: {total_created}")
                        return 0

            # If no success in this batch, might be a persistent error
            if success == 0:
                print(f"\n⚠️  No success in this batch. Stopping.")
                print(f"   Last error: {results[-1].get('error', 'unknown')[:150]}")
                return 0

        except Exception as e:
            print(f"\n❌ Exception: {e}")
            return 1

        # Refresh account state
        account = mgr.accounts[acc_id]
        new_total = account.get("alias_total", 0)
        print(f"   New total: {new_total}")

        if new_total >= args.target:
            print(f"\n✅ Target reached: {new_total} >= {args.target}")
            break

        # Wait before next batch
        if args.delay > 0:
            print(f"   Waiting {args.delay}s before next batch...")
            time.sleep(args.delay)

    print(f"\n📊 Summary:")
    print(f"   Iterations: {iteration}")
    print(f"   Created this run: {total_created}")
    print(f"   Errors: {total_errors}")
    print(f"   Final total: {mgr.accounts[acc_id].get('alias_total', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
