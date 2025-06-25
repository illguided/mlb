// This file must be placed in the /api/ directory of your project.

const API_BASE_URL = 'https://statsapi.mlb.com/api/v1';

/**
 * Main handler for the serverless function.
 * Vercel automatically maps this file to the /api/get-stats endpoint.
 */
export default async function handler(request, response) {
  try {
    const today = new Date().toISOString().split('T')[0];
    const scheduleUrl = `${API_BASE_URL}/schedule/games/?sportId=1&date=${today}`;
    
    const scheduleRes = await fetch(scheduleUrl);
    if (!scheduleRes.ok) {
        throw new Error(`Failed to fetch schedule: ${scheduleRes.statusText}`);
    }
    const scheduleData = await scheduleRes.json();

    if (!scheduleData.dates || scheduleData.dates.length === 0) {
      return response.status(200).json([]);
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
    
    // Set headers for caching and CORS (important for Vercel)
    response.setHeader('Access-Control-Allow-Origin', '*');
    response.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate');
    response.status(200).json(finalStats);

  } catch (error) {
    console.error("Error in serverless function:", error);
    response.status(500).json({ error: 'Failed to fetch MLB data', details: error.message });
  }
}

/**
 * Helper function to process all batters from one team against a pitcher.
 */
async function processMatchup(team, pitcher) {
    try {
        const rosterUrl = `${API_BASE_URL}/teams/${team.id}/roster`;
        const rosterResponse = await fetch(rosterUrl);
        if (!rosterResponse.ok) return []; // Silently fail for this team if roster is unavailable
        const rosterData = await rosterResponse.json();
        const batters = rosterData.roster.filter(p => p.position.code !== '1');

        const playerStatPromises = batters.map(async (batter) => {
            try {
                const bvpUrl = `${API_BASE_URL}/people/${batter.person.id}/stats?stats=vsPlayer&group=hitting&opposingPlayerId=${pitcher.id}`;
                const bvpResponse = await fetch(bvpUrl);
                if (!bvpResponse.ok) return null;
                const bvpData = await bvpResponse.json();

                const careerStats = bvpData.stats[0]?.splits[0]?.stat;
                if (careerStats && careerStats.homeRuns > 0) {
                    const gameLogUrl = `${API_BASE_URL}/people/${batter.person.id}/stats?stats=gameLog&limit=20&group=hitting`;
                    const gameLogResponse = await fetch(gameLogUrl);
                    if (!gameLogResponse.ok) return null;
                    const gameLogData = await gameLogResponse.json();
                    
                    let last5 = 0, last10 = 0, last20 = 0;
                    if(gameLogData.stats[0]?.splits) {
                        gameLogData.stats[0].splits.forEach((game, index) => {
                            const hrCount = game.stat.homeRuns || 0;
                            if (index < 5) last5 += hrCount;
                            if (index < 10) last10 += hrCount;
                            last20 += hrCount;
                        });
                    }
                    
                    return {
                        playerName: batter.person.fullName,
                        playerId: batter.person.id,
                        team: team.name,
                        vsPitcher: pitcher.fullName,
                        careerHRs: careerStats.homeRuns,
                        last5,
                        last10,
                        last20
                    };
                }
                return null;
            } catch (e) {
                console.error(`Error processing batter ${batter.person.id}`, e);
                return null; // Don't let one batter fail the whole process
            }
        });
        
        return Promise.all(playerStatPromises);
    } catch (err) {
        console.error(`Failed to process matchup for team ${team.id}`, err);
        return [];
    }
}
