# Connor Watch

A small static site that tracks Connor McDavid's 2026–27 season and projects his
final point total from his pace so far. Can he become the first player since
Wayne Gretzky to score 200+ points in a season?

The page shows:

- Projected goals, assists and points over the 84-game season
- Current and best point streaks
- The Oilers' next game
- A chart of the projection after each game
- Where the projection ranks among the best single seasons in NHL history
- A game-by-game log

## Running it locally

The page loads `games.json` with `fetch`, so it needs to be served over HTTP
(opening `index.html` directly from disk won't work):

```sh
python3 -m http.server
```

Then open <http://localhost:8000>.

## Updating the data

After each game, refresh `games.json` from the public NHL API:

```sh
python3 scrape.py
```

It only uses the Python standard library. It downloads the Oilers' schedule and
McDavid's game log, then writes one entry per regular-season game. Upcoming games
are placeholders until they're played.

## Files

| File | What it is |
|---|---|
| `index.html` | The whole site: markup, styles and JavaScript |
| `games.json` | Per-game data written by `scrape.py` |
| `scrape.py` | Fetches the data from the NHL API |
| `logos/` | Team logos (light and dark variants) |

### `games.json` keys

To keep the file small it stores only raw facts; the page works out game
numbers, full team names and running totals itself. Keys that don't apply are
left out.

| Key | Meaning |
|---|---|
| `date` | Game date (`YYYY-MM-DD`) |
| `oppon` | Opponent's 3-letter abbreviation |
| `home` | `true` for a home game |
| `played` | `true` if McDavid played (false for upcoming or missed games) |
| `edm_score`, `opp_score` | Final score (only once the game is over) |
| `ot` | `"OT"` or `"SO"` if the game went past regulation |
| `g`, `a` | Goals and assists |
| `sog` | Shots on goal |
| `+/-` | Plus-minus |
| `toi` | Time on ice (`mm:ss`) |
| `ppp` | Power-play points |

## License

The code and data in this repo are released under [CC0](LICENSE).

The team logos in `logos/` are trademarks of the NHL and its teams and are not
covered by that license. This is an unofficial fan site and is not affiliated
with the NHL or the Edmonton Oilers.
