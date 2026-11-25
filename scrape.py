#!/usr/bin/env python3
"""Fetch Connor McDavid's regular-season game log and write games.json.

The nhl.com player stats page is rendered client-side from the public NHL API,
so we read that API directly rather than scraping HTML.

games.json holds only raw per-game facts; anything derivable is computed in
index.html (game number = list position, full team names, running points
total). Keys are omitted rather than set to null/default:

  upcoming game:  date, oppon, home, played=false
  completed game: + edm_score, opp_score, ot ("OT"/"SO" only)
  played game:    + played=true, g, a, sog, +/-, toi, ppp
  tentative game: + tentative=true; stats taken from the game's box score
                  because his game log hasn't caught up yet (no ppp, which
                  the box score lacks). Replaced once the log has the game.

Key glossary: oppon = opponent abbreviation, home = home game, g/a = goals/
assists, sog = shots on goal, toi = time on ice, ppp = power-play points.

Usage: python3 scrape.py [--season 20262027] [--out docs/games.json]
"""
import argparse
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

PLAYER_ID = 8478402  # Connor McDavid
TEAM = "EDM"
GAME_LOG_URL = "https://api-web.nhle.com/v1/player/{pid}/game-log/{season}/2"
SCHEDULE_URL = "https://api-web.nhle.com/v1/club-schedule-season/{team}/{season}"
BOXSCORE_URL = "https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"

# The schedule marks a game final before the player's game log includes it.
# For this long after puck drop, a final game missing from the log (and from
# the box score) is treated as not finished yet, rather than as a game he
# missed.
LOG_LAG = timedelta(hours=12)


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_boxscore_stats(game_id):
    """His line from a game's box score, in game-log field names, or None if
    he isn't in it (didn't dress) or the box score can't be fetched."""
    try:
        box = fetch_json(BOXSCORE_URL.format(game_id=game_id))
    except (OSError, ValueError):
        return None
    for team in box.get("playerByGameStats", {}).values():
        for group in team.values():
            for p in group:
                if p.get("playerId") == PLAYER_ID:
                    return {
                        "goals": p["goals"],
                        "assists": p["assists"],
                        "shots": p["sog"],
                        "plusMinus": p["plusMinus"],
                        "toi": p["toi"],
                    }
    return None


def build_games(schedule, game_log, now=None, boxscore=fetch_boxscore_stats):
    """One entry per Oilers regular-season game, past and future, in order.

    The player game log only contains games he dressed for, so we walk the
    team schedule. A final game missing from the log falls back to the box
    score (marked tentative); if he isn't there either it's played=false,
    except within LOG_LAG of puck drop, when it's left as upcoming.

    Returns (games, tentative, pending): final games filled from the box
    score, and final games left as upcoming.
    """
    now = now or datetime.now(timezone.utc)
    stats = {g["gameId"]: g for g in game_log}
    tentative, pending = [], []
    season = sorted((g for g in schedule if g["gameType"] == 2),
                    key=lambda g: g["startTimeUTC"])

    games = []
    for g in season:
        home = g["homeTeam"]["abbrev"] == TEAM
        us, them = (g["homeTeam"], g["awayTeam"]) if home else (g["awayTeam"], g["homeTeam"])
        s = stats.get(g["id"])
        final = g["gameState"] in ("OFF", "FINAL")
        from_boxscore = False
        if final and s is None:
            s = boxscore(g["id"])
            from_boxscore = s is not None
        game = {
            "date": g["gameDate"],
            "oppon": them["abbrev"],
            "home": home,
            "played": s is not None,
        }
        if final and s is None:
            start = datetime.fromisoformat(g["startTimeUTC"].replace("Z", "+00:00"))
            if now - start < LOG_LAG:
                final = False
                pending.append(game)
        if final:
            game["edm_score"] = us["score"]
            game["opp_score"] = them["score"]
            period = (g.get("gameOutcome") or {}).get("lastPeriodType")
            if period in ("OT", "SO"):
                game["ot"] = period
        if s:
            game.update({
                "g": s["goals"],
                "a": s["assists"],
                "sog": s["shots"],
                "+/-": s["plusMinus"],
                "toi": s["toi"],
            })
            if "powerPlayPoints" in s:
                game["ppp"] = s["powerPlayPoints"]
        if from_boxscore:
            game["tentative"] = True
            tentative.append(game)
        games.append(game)
    return games, tentative, pending


def write_games(games, path):
    with open(path, "w") as f:
        json.dump({"games": games}, f, indent=4, ensure_ascii=False)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default="20262027")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "games.json"))
    args = ap.parse_args()

    log = fetch_json(GAME_LOG_URL.format(pid=PLAYER_ID, season=args.season))["gameLog"]
    schedule = fetch_json(SCHEDULE_URL.format(team=TEAM, season=args.season))["games"]
    games, tentative, pending = build_games(schedule, log)
    write_games(games, args.out)

    done = [g for g in games if "edm_score" in g]
    played = [g for g in done if g["played"]]
    points = sum(g["g"] + g["a"] for g in played)
    print(f"Wrote {len(games)} games to {args.out}: {len(done)} completed "
          f"({len(played)} played), {len(games) - len(done)} upcoming"
          + (f"; {points} pts through {done[-1]['date']}" if done else ""))
    for g in tentative:
        print(f"{g['date']} vs {g['oppon']} is not in the game log yet; "
              "stats taken from the box score (tentative)")
    for g in pending:
        print(f"{g['date']} vs {g['oppon']} is final but not in the game log yet; "
              "left as upcoming")


if __name__ == "__main__":
    main()
