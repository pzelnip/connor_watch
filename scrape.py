#!/usr/bin/env python3
"""Fetch Connor McDavid's regular-season game log and write games.json.

The nhl.com player stats page is rendered client-side from the public NHL API,
so we read that API directly rather than scraping HTML.

Usage: python3 scrape.py [--season 20262027] [--out games.json]
"""
import argparse
import json
import urllib.request

PLAYER_ID = 8478402  # Connor McDavid
TEAM = "EDM"
GAME_LOG_URL = "https://api-web.nhle.com/v1/player/{pid}/game-log/{season}/2"
SCHEDULE_URL = "https://api-web.nhle.com/v1/club-schedule-season/{team}/{season}"
TEAMS_URL = "https://api.nhle.com/stats/rest/en/team"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def full_team_name(abbrev, common_name, teams):
    """Resolve e.g. ('PHI', 'Flyers') -> 'Philadelphia Flyers'.

    The team list contains historical franchises that share tricodes
    (e.g. UTA = Utah Hockey Club / Utah Mammoth), so match on common name too.
    """
    candidates = [t["fullName"] for t in teams if t["triCode"] == abbrev]
    for name in candidates:
        if name.endswith(common_name):
            return name
    return candidates[-1] if candidates else common_name


def build_games(schedule, game_log, teams):
    """One entry per Oilers regular-season game, past and future.

    The player game log only contains games he dressed for, so we walk the
    team schedule and mark completed games missing from the log as
    played=False (stats 0). Games not yet played are placeholders with
    played=False and null stats.
    """
    stats = {g["gameId"]: g for g in game_log}
    season = sorted((g for g in schedule if g["gameType"] == 2),
                    key=lambda g: g["startTimeUTC"])

    games = []
    total = 0
    for num, g in enumerate(season, start=1):
        home = g["homeTeam"]["abbrev"] == TEAM
        opp = g["awayTeam"] if home else g["homeTeam"]
        s = stats.get(g["id"])
        final = g["gameState"] in ("OFF", "FINAL")
        if final:
            goals = s["goals"] if s else 0
            assists = s["assists"] if s else 0
            total += goals + assists
            total_to_date = total
        else:
            goals = assists = total_to_date = None
        us, them = (g["homeTeam"], g["awayTeam"]) if home else (g["awayTeam"], g["homeTeam"])
        last_period = (g.get("gameOutcome") or {}).get("lastPeriodType")
        games.append({
            "game_num": num,
            "opponent_abbrev": opp["abbrev"],
            "opponent_full": full_team_name(
                opp["abbrev"], opp["commonName"]["default"], teams),
            "goals": goals,
            "assists": assists,
            "date": g["gameDate"],
            "total_points_to_date": total_to_date,
            "home_game": home,
            "played": s is not None,
            # Game result (null until the game is final).
            "oilers_score": us.get("score") if final else None,
            "opponent_score": them.get("score") if final else None,
            "decided_in": last_period if final else None,  # "REG", "OT" or "SO"
            # Extra per-game stats (null if he didn't play or game not final).
            "shots": s["shots"] if s else None,
            "plus_minus": s["plusMinus"] if s else None,
            "toi": s["toi"] if s else None,
            "power_play_points": s["powerPlayPoints"] if s else None,
        })
    return games


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default="20262027")
    ap.add_argument("--out", default="games.json")
    args = ap.parse_args()

    log = fetch_json(GAME_LOG_URL.format(pid=PLAYER_ID, season=args.season))["gameLog"]
    schedule = fetch_json(SCHEDULE_URL.format(team=TEAM, season=args.season))["games"]
    teams = fetch_json(TEAMS_URL)["data"]
    games = build_games(schedule, log, teams)

    with open(args.out, "w") as f:
        json.dump({"games": games}, f, indent=4)
        f.write("\n")
    done = [g for g in games if g["goals"] is not None]
    played = sum(g["played"] for g in done)
    print(f"Wrote {len(games)} games to {args.out}: {len(done)} completed "
          f"({played} played), {len(games) - len(done)} upcoming"
          + (f"; {done[-1]['total_points_to_date']} pts through {done[-1]['date']}" if done else ""))


if __name__ == "__main__":
    main()
