def get_live_mlb_stats():
    """
    This function uses YOUR 'statsapi' wrapper to fetch and process live MLB data.
    It finds all of today's games, checks every batter against the probable starting pitcher,
    and returns a list of players who have hit at least one career home run in that matchup.
    """
    if not statsapi:
        # This will be returned if the initial import of your wrapper failed.
        return [{"error": "The statsapi wrapper could not be loaded on the server."}]

    print("Fetching live data with your 'statsapi' wrapper...")
    final_stats = []
    
    try:
        # 1. Get today's schedule using your wrapper's schedule() function.
        today_schedule = statsapi.schedule()
        
        if not today_schedule:
            print("No games scheduled for today.")
            return []

        processed_players = set()
        print(f"Found {len(today_schedule)} games. Processing matchups...")

        # 2. Loop through each game scheduled for today.
        for game in today_schedule:
            # This inner loop handles both matchups in a single game
            # (Away Batters vs. Home Pitcher, and Home Batters vs. Away Pitcher)
            for matchup_type in ['away', 'home']:
                
                pitcher_id = game.get(f'{"home" if matchup_type == "away" else "away"}_probable_pitcher_id')
                pitcher_name = game.get(f'{"home" if matchup_type == "away" else "away"}_probable_pitcher')
                batting_team_id = game.get(f'{matchup_type}_id')
                batting_team_name = game.get(f'{matchup_type}_name')

                if not pitcher_id:
                    continue # Skip if no probable pitcher is announced for this side.
                
                # 3. Get the roster for the batting team.
                roster_data = statsapi.get('team_roster', {'teamId': batting_team_id})
                roster = roster_data.get('roster', [])

                # 4. Loop through each player on the roster.
                for player in roster:
                    player_id = player['person']['id']

                    # Skip if we've already processed this player today (e.g., doubleheader)
                    if player_id in processed_players:
                        continue
                        
                    # 5. Get career stats for this batter vs. this specific pitcher.
                    # This uses the correct function call based on your wrapper's structure.
                    try:
                        bvp_data = statsapi.get('person', {
                            'personId': player_id,
                            'hydrate': f'stats(group=hitting,type=vsPlayer,opposingPlayerId={pitcher_id})'
                        })
                        
                        # Navigate the nested JSON to get the stats dictionary
                        career_stats = bvp_data['people'][0]['stats'][0]['splits'][0]['stat']

                        # 6. Check if the matchup is significant (at least 1 career HR).
                        if career_stats.get('homeRuns', 0) > 0:
                            player_name = player['person']['fullName']
                            print(f"  --> Found significant matchup: {player_name} vs. {pitcher_name}")
                            
                            # 7. Get the player's recent game logs.
                            game_log_data = statsapi.get('person', {'personId': player_id, 'hydrate': 'stats(group=hitting,type=gameLog,limit=20)'})
                            recent_games = game_log_data['people'][0].get('stats', [{}])[0].get('splits', [])

                            last5, last10, last20 = 0, 0, 0
                            for i, game_stat in enumerate(recent_games):
                                hr = game_stat['stat'].get('homeRuns', 0)
                                if i < 5: last5 += hr
                                if i < 10: last10 += hr
                                last20 += hr
                            
                            # 8. Add the formatted data to our final list.
                            final_stats.append({
                                "playerName": player_name,
                                "playerId": player_id,
                                "team": batting_team_name,
                                "vsPitcher": pitcher_name,
                                "careerHRs": career_stats.get('homeRuns'),
                                "last5": last5,
                                "last10": last10,
                                "last20": last20
                            })
                            
                            processed_players.add(player_id)

                    except (KeyError, IndexError):
                        # This is not an error. It just means the player has no history against the pitcher. We can safely skip them.
                        continue
                        
        print(f"Finished processing. Found {len(final_stats)} significant matchups.")
        return final_stats

    except Exception as e:
        # This will catch any other unexpected errors during the process.
        print(f"A critical error occurred in get_live_mlb_stats: {e}")
        return [{"error": f"An error occurred in the Python backend: {e}"}]
