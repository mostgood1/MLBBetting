import json
from app import app

if __name__ == "__main__":
    # Use Flask test client to hit endpoints
    client = app.test_client()

    # Quick today-games (no network)
    resp = client.get("/api/today-games/quick?no_network=1")
    print("/api/today-games/quick status:", resp.status_code)
    try:
        data = resp.get_json()
        print("quick_count:", data.get("count"))
    except Exception as e:
        print("quick parse error:", e)

    # Full today-games (may perform work; ok if takes a moment)
    resp2 = client.get("/api/today-games")
    print("/api/today-games status:", resp2.status_code)
    try:
        data2 = resp2.get_json()
        print("full_count:", data2.get("count"))
        # Inspect first game's betting_recommendations presence
        games = (data2 or {}).get("games", [])
        if games:
            br = games[0].get("betting_recommendations")
            vb_len = len((br or {}).get("value_bets", []) or []) if br else 0
            print("first_game_value_bets:", vb_len)
        timings = resp2.headers.get("Server-Timing")
        print("server_timing:", timings)
    except Exception as e:
        print("full parse error:", e)
