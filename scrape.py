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

Key glossary: oppon = opponent abbreviation, home = home game, g/a = goals/
assists, sog = shots on goal, toi = time on ice, ppp = power-play points.

Usage: python3 scrape.py [--season 20262027] [--out games.json]
"""
import argparse
import json
import urllib.request

PLAYER_ID = 8478402  # Connor McDavid
TEAM = "EDM"
GAME_LOG_URL = "https://api-web.nhle.com/v1/player/{pid}/game-log/{season}/2"
SCHEDULE_URL = "https://api-web.nhle.com/v1/club-schedule-season/{team}/{season}"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def build_games(schedule, game_log):
    """One entry per Oilers regular-season game, past and future, in order.

    The player game log only contains games he dressed for, so we walk the
    team schedule; completed games missing from the log are played=false.
    """
    stats = {g["gameId"]: g for g in game_log}
    season = sorted((g for g in schedule if g["gameType"] == 2),
                    key=lambda g: g["startTimeUTC"])

    games = []
    for g in season:
        home = g["homeTeam"]["abbrev"] == TEAM
        us, them = (g["homeTeam"], g["awayTeam"]) if home else (g["awayTeam"], g["homeTeam"])
        s = stats.get(g["id"])
        game = {
            "date": g["gameDate"],
            "oppon": them["abbrev"],
            "home": home,
            "played": s is not None,
        }
        if g["gameState"] in ("OFF", "FINAL"):
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
                "ppp": s["powerPlayPoints"],
            })
        games.append(game)
    return games


def write_games(games, path):
    with open(path, "w") as f:
        json.dump({"games": games}, f, indent=4, ensure_ascii=False)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default="20262027")
    ap.add_argument("--out", default="games.json")
    args = ap.parse_args()

    log = fetch_json(GAME_LOG_URL.format(pid=PLAYER_ID, season=args.season))["gameLog"]
    schedule = fetch_json(SCHEDULE_URL.format(team=TEAM, season=args.season))["games"]
    games = build_games(schedule, log)
    write_games(games, args.out)

    done = [g for g in games if "edm_score" in g]
    played = [g for g in done if g["played"]]
    points = sum(g["g"] + g["a"] for g in played)
    print(f"Wrote {len(games)} games to {args.out}: {len(done)} completed "
          f"({len(played)} played), {len(games) - len(done)} upcoming"
          + (f"; {points} pts through {done[-1]['date']}" if done else ""))


if __name__ == "__main__":
    main()
