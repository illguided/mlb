// File: /api/get-stats.js

// This is a serverless function.
// It will fetch MLB data and return it as JSON.

export default async function handler(req, res) {
  const API_BASE_URL = 'https://statsapi.mlb.com/api/v1';

  try {
    // 1. Get today's schedule
    const today = new Date().toISOString().split('T')[0];
    const scheduleUrl = `${API_BASE_URL}/schedule/games/?sportId=1&date=${today}`;
    const scheduleResponse = await fetch(scheduleUrl);
    const scheduleData = await scheduleResponse.json();

    if (!scheduleData.dates || scheduleData.dates.length === 0) {
      res.status(200).json([]); // No games today, return empty array
      return;
    }

    const games = scheduleData.dates[0].games;
    const matchupPromises = [];

    for (const game of games) {
      const homeTeam = { id: game.teams.home.team.id, name: game.teams.home.team.name };
      const awayTeam = { id: game.teams.away.team.id, name: game.teams.away.team.name };
      const homePitcher = game.teams.home.probablePitcher;
      const awayPitcher = game.teams.away.probablePitcher;

      if (homePitcher) {
        matchupPromises.push(processMatchup(awayTeam, homePitcher));
      }
      if (awayPitcher) {
        matchupPromises.push(processMatchup(homeTeam, awayPitcher));
      }
    }

    const results = await Promise.all(matchupPromises);
    const finalStats = results.flat().filter(player => player !== null);

    // --- IMPORTANT ---
    // This allows your frontend to fetch data from this function from any domain.
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate'); // Cache for 1 hour

    // 2. Send the final data as the response
    res.status(200).json(finalStats);

  } catch (error) {
    console.error("Error in serverless function:", error);
    res.status(500).json({ error: 'Failed to fetch MLB data' });
  }
}

// This helper function remains the same
async function processMatchup(team, pitcher) {
    // (The same processMatchup function from the previous HTML file would go here)
    // ... logic to get roster, BvP stats, and recent game logs ...
    // This is simplified for brevity.
    try {
        const rosterUrl = `${API_BASE_URL}/teams/${team.id}/roster`;
        const rosterResponse = await fetch(rosterUrl);
        const rosterData = await rosterResponse.json();
        const batters = rosterData.roster.filter(p => p.position.code !== '1');

        const playerStatPromises = batters.map(async (batter) => {
            const bvpUrl = `${API_BASE_URL}/people/${batter.person.id}/stats?stats=vsPlayer&group=hitting&opposingPlayerId=${pitcher.id}`;
            const bvpResponse = await fetch(bvpUrl);
            const bvpData = await bvpResponse.json();

            const careerStats = bvpData.stats[0]?.splits[0]?.stat;
            if (careerStats && careerStats.homeRuns > 0) {
                // Simplified recent stats for this example
                return {
                    playerName: batter.person.fullName,
                    playerId: batter.person.id,
                    team: team.name,
                    vsPitcher: pitcher.fullName,
                    careerHRs: careerStats.homeRuns,
                    last5: Math.floor(Math.random() * 3), // Placeholder
                    last10: Math.floor(Math.random() * 5), // Placeholder
                    last20: Math.floor(Math.random() * 8)  // Placeholder
                };
            }
            return null;
        });
        
        return Promise.all(playerStatPromises);
    } catch (err) {
        return [];
    }
}