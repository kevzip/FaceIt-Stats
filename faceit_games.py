import requests
import json
import pandas as pd
from datetime import datetime, timezone
import time


class FaceitStatsGrabber:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://open.faceit.com/data/v4"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }

    def find_player_id(self, nickname):
        """Search for a player by nickname to get their player_id."""
        url = f"{self.base_url}/players?nickname={nickname}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("player_id")
            else:
                return {
                    "error": f"Player search failed with status {response.status_code}",
                    "message": response.text
                }
        except requests.RequestException as e:
            return {
                "error": "Player search error",
                "message": str(e)
            }

    def get_match_history(self, player_id, game_id, from_timestamp, to_timestamp, offset=0, limit=100):
        """Fetch match history for a player within a time range."""
        url = f"{self.base_url}/players/{player_id}/history?game={game_id}&from={from_timestamp}&to={to_timestamp}&offset={offset}&limit={limit}"
        print(f"Requesting match history: {url}")  # Debug URL
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"Match history request failed with status {response.status_code}",
                    "message": response.text
                }
        except requests.RequestException as e:
            return {
                "error": "Request error",
                "message": str(e)
            }

    def get_match_stats(self, match_id):
        """Fetch detailed stats for a specific match."""
        url = f"{self.base_url}/matches/{match_id}/stats"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"Match stats request failed with status {response.status_code}",
                    "message": response.text
                }
        except requests.RequestException as e:
            return {
                "error": "Request error",
                "message": str(e)
            }

    def fetch_games(self, player_id, game_id, nickname):
        """Fetch all matches and compile stats."""
        # Define timestamps (Unix, in seconds)
        start_date = int(datetime(2025, 6, 1, 0, 0, 0,
                         tzinfo=timezone.utc).timestamp())
        end_date = int(datetime(2025, 12, 31, 23, 59, 59,
                       tzinfo=timezone.utc).timestamp())

        all_matches = []
        offset = 0
        limit = 100  # Max matches per request (API limit)

        while True:
            # Fetch match history page
            history = self.get_match_history(
                player_id, game_id, start_date, end_date, offset, limit)
            if "error" in history:
                return history

            matches = history.get("items", [])
            if not matches:
                break  # No more matches

            print(f"Fetched {len(matches)} matches (offset: {offset})")

            for match in matches:
                match_id = match.get("match_id")
                match_date = match.get("started_at")
                if not match_id or not match_date:
                    continue

                # Fetch match stats
                stats = self.get_match_stats(match_id)
                if "error" in stats:
                    print(f"Skipping match {match_id}: {stats['message']}")
                    continue

                # Extract player stats for the user
                player_stats = None
                for team in stats.get("rounds", [{}])[0].get("teams", []):
                    for player in team.get("players", []):
                        if player.get("player_id") == player_id:
                            player_stats = player.get("player_stats", {})
                            break
                    if player_stats:
                        break

                if not player_stats:
                    print(f"No stats found for player in match {match_id}")
                    continue

                # Compile match data
                match_data = {
                    "Nickname": nickname,
                    "Match ID": match_id,
                    "Date": datetime.fromtimestamp(match_date, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "Map": stats.get("rounds", [{}])[0].get("round_stats", {}).get("Map", "N/A"),
                    "Score": stats.get("rounds", [{}])[0].get("round_stats", {}).get("Score", "N/A"),
                    "Kills": player_stats.get("Kills", "0"),
                    "Deaths": player_stats.get("Deaths", "0"),
                    "Assists": player_stats.get("Assists", "0"),
                    "K/D Ratio": player_stats.get("K/D Ratio", "0"),
                    "Headshots %": player_stats.get("Headshots %", "0"),
                    "MVPs": player_stats.get("MVPs", "0"),
                    "Result": player_stats.get("Result", "N/A")
                }
                all_matches.append(match_data)

            offset += limit
            # Avoid rate limiting (1000 requests/hour = ~1 per 3.6s)
            time.sleep(1)

        return all_matches

    def export_to_excel(self, matches, nickname):
        """Export match data to an Excel file."""
        if not matches:
            return {"error": "No matches to export"}

        try:
            df = pd.DataFrame(matches)
            filename = f"{nickname}'s faceit_games.xlsx"
            df.to_excel(filename, index=False, engine="openpyxl")
            return {"success": f"Exported {len(matches)} matches to {filename}"}
        except Exception as e:
            return {
                "error": "Export error",
                "message": str(e)
            }


# Example usage
if __name__ == "__main__":
    # Replace with your actual API key
    # Get from https://developers.faceit.com/
    API_KEY = "YOUR_API_KEY"

    # Initialize the stats grabber
    stats_grabber = FaceitStatsGrabber(API_KEY)

    # Replace with your FACEIT nickname
    NICKNAME = "Kevzip"  # e.g., "s1mple"
    GAME_ID = "cs2"  # or "csgo"

    # Step 1: Find player ID
    player_result = stats_grabber.find_player_id(NICKNAME)
    if "error" in player_result:
        print("Player Search Error:", json.dumps(player_result, indent=2))
        exit()

    PLAYER_ID = player_result
    print(f"Found Player ID: {PLAYER_ID}")

    # Step 2: Fetch all games
    matches = stats_grabber.fetch_games(PLAYER_ID, GAME_ID, NICKNAME)
    if "error" in matches:
        print("Match Fetch Error:", json.dumps(matches, indent=2))
        exit()

    # Step 3: Export to Excel
    export_result = stats_grabber.export_to_excel(matches, NICKNAME)
    print(json.dumps(export_result, indent=2))
