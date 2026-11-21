#!/bin/sh
# Refresh docs/games.json and push it if it changed (the push redeploys the
# site). Meant to run from cron in a clean clone, e.g. hourly:
#   17 * * * * /path/to/connor_watch/update.sh >> /path/to/update.log 2>&1
set -e
cd "$(dirname "$0")"

echo "== $(date '+%Y-%m-%d %H:%M:%S')"
git pull -q --rebase
python3 scrape.py

if git diff --quiet docs/games.json; then
    echo "No new data"
    exit 0
fi

git add docs/games.json
git commit -q -m "Update game data"
git push -q
echo "Pushed update"
