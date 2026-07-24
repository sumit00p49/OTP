#!/bin/bash
# ============================================================
#  ONE-COMMAND UPDATER for APEX TG SHOP bot
#  Usage:  bash update.sh
#
#  It will:
#    1. Fetch the latest code from GitHub
#    2. Hard-sync the code (never fails on "divergent branches")
#    3. Restart the bot in the background
#
#  Your data is SAFE (never touched):
#    - .env            (secrets/tokens)
#    - bot_database.db (users, orders, balance)
#  These are gitignored, so the update never overwrites them.
# ============================================================

cd "$(dirname "$0")" || exit 1

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'fix/session-management')"

echo "=================================================="
echo "  Updating bot  (branch: $BRANCH)"
echo "=================================================="

echo "==> [1/3] Fetching latest code from GitHub..."
git fetch origin "$BRANCH"

echo "==> [2/3] Applying update (hard sync to origin/$BRANCH)..."
git reset --hard "origin/$BRANCH"

echo "==> [3/3] Restarting the bot..."
# Stop any running bot
pkill -f "bot.py" 2>/dev/null
sleep 2
# Start fresh in the background, logging to bot.log
nohup python3 bot.py > bot.log 2>&1 &
sleep 4

echo ""
echo "=================================================="
echo "  Done! Bot restarted. Recent log below:"
echo "=================================================="
tail -n 18 bot.log
echo ""
echo "Tip: to watch live logs ->  tail -f bot.log"
