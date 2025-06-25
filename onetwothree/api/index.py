import sys
import os
from flask import Flask, jsonify

# This line is the key: It tells Python to look for modules in the parent directory
# which allows it to find your 'full' folder.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- This now imports the 'statsapi' module from your 'full' folder ---
# Based on your documentation, the main module is named 'statsapi'.
# If your wrapper's main file has a different name, change it here.
try:
    from full import statsapi
except ImportError as e:
    # This will help you debug if the folder/file name is wrong
    print(f"CRITICAL ERROR: Could not import your wrapper. Check folder/file names.")
    print(f"Python sys.path: {sys.path}")
    print(f"Error details: {e}")
    statsapi = None


app = Flask(__name__)

def get_live_mlb_stats():
    """
    This function uses the 'statsapi' wrapper to fetch and process live MLB data.
    It finds all of today's games, checks every batter against the probable starting pitcher,
    and returns a list of players who have hit at least one home run in that matchup.
    """
    if not statsapi:
        return [{"error": "The statsapi wrapper could not be loaded on the server."}]

    print("Fetching live data with 'statsapi' wrapper...")
    final_stats = []
    
    try:
        # 1. Get today's schedule. The statsapi.schedule() function returns a list of game dictionaries.
        today_schedule = statsapi.schedule()
        
        if not today_schedule:
            print("No games scheduled for today.")
            return []

        # 2. Create a set to keep track of processed players to avoid duplicates (e.g., in doubleheaders)
        processed_players = set()

        # 3. Loop through each game scheduled for today
        for game in today_schedule:
            print(f"Processing game: {game['away_name']} vs. {game['home_name']}")

            # Define the teams and pitchers for this game
            teams_and_pitchers = [
                # Away batters vs. Home pitcher
                {
                    "batting_team_id": game['away_id'],
                    "batting_team_name": game['away_name'],
                    "pitcher_id": game.get('home_probable_pitcher_id'),
                    "pitcher_name": game.get('home_probable_pitcher')
                },
                # Home batters vs. Away pitcher
                {
                    "batting_team_id": game['home_id'],
                    "batting_team_name": game['home_name'],
                    "pitcher_id": game.get('away_probable_pitcher_id'),
                    "pitcher_name": game.get('away_probable_pitcher')
                }
            ]

            for matchup in teams_and_pitchers:
                pitcher_id = matchup.get("pitcher_id")
                
                # Skip if the probable pitcher hasn't been announced
                if not pitcher_id:
                    continue

                # 4. Get the roster for the batting team
                roster = statsapi.get('team_roster', {'teamId': matchup['batting_team_id']}).get('roster', [])

                # 5. Loop through each player on the roster
                for player in roster:
                    player_id = player['person']['id']
                    player_name = player['person']['fullName']
                    
                    # Avoid re-processing the same player
                    if player_id in processed_players:
                        continue

                    # 6. Get the career stats for the batter vs. this specific pitcher
                    # IMPORTANT: The wrapper might have a different function name for this.
                    # 'player_vs_pitcher_stats' is a logical guess based on typical wrappers.
                    # You may need to find the correct function in your wrapper's documentation.
                    try:
                        bvp_stats = statsapi.get('person', {'personId': player_id, 'hydrate': f'stats(group=hitting,type=vsPlayer,opposingPlayerId={pitcher_id})'})
                        career_stats = bvp_stats['people'][0]['stats'][0]['splits'][0]['stat']

                        # 7. Check if the matchup is significant (at least 1 career HR)
                        if career_stats and career_stats.get('homeRuns', 0) > 0:
                            print(f"  Found significant matchup: {player_name} vs. {matchup['pitcher_name']}")
                            
                            # 8. Get the player's recent game logs to calculate pace
                            game_log = statsapi.get('person', {'personId': player_id, 'hydrate': 'stats(group=hitting,type=gameLog,limit=20)'})
                            recent_games = game_log['people'][0]['stats'][0]['splits']

                            last5, last10, last20 = 0, 0, 0
                            for i, game_stat in enumerate(recent_games):
                                hr = game_stat['stat'].get('homeRuns', 0)
                                if i < 5:
                                    last5 += hr
                                if i < 10:
                                    last10 += hr
                                last20 += hr

                            # 9. Format the data for the frontend and add it to our list
                            final_stats.append({
                                "playerName": player_name,
                                "playerId": player_id,
                                "team": matchup['batting_team_name'],
                                "vsPitcher": matchup['pitcher_name'],
                                "careerHRs": career_stats.get('homeRuns'),
                                "last5": last5,
                                "last10": last10,
                                "last20": last20
                            })
                            
                            processed_players.add(player_id)

                    except (KeyError, IndexError, TypeError) as e:
                        # This handles cases where a player has no history vs. the pitcher
                        # print(f"  No BvP data for {player_name} vs {matchup['pitcher_name']}. Skipping. Error: {e}")
                        continue
                        
        print(f"Finished processing. Found {len(final_stats)} significant matchups.")
        return final_stats

    except Exception as e:
        print(f"A critical error occurred in get_live_mlb_stats: {e}")
        return [{"error": f"An error occurred in the Python backend: {e}"}]


    except Exception as e:
        print(f"An error occurred inside your stats logic: {e}")
        return [{"error": "An error occurred while fetching stats from the MLB API."}]
        
    # --- END: THIS IS THE SECTION YOU WILL REPLACE ---


# This is the Vercel-compatible API endpoint
@app.route('/api/stats', methods=['GET'])
def handler():
    live_data = get_live_mlb_stats()
    response = jsonify(live_data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

