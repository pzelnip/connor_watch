#!/bin/sh
# Serve docs/ locally (the page fetches games.json, so it can't be opened from disk).

cd "$(dirname "$0")/docs" || exit 1
python3 -m http.server 9297 &
SERVER_PID=$!
trap "kill $SERVER_PID" EXIT
sleep 1
open http://localhost:9297/
wait $SERVER_PID
