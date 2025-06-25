import sys
import os
from flask import Flask, jsonify

# This makes sure Vercel can find your 'full' folder
# It adds the parent directory (which will be 'onetwothree') to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTANT: Import your wrapper from the 'full' folder ---
# You will need to replace 'YourApiClass' with the actual class/function name from your wrapper
try:
    from full import YourApiClass
except ImportError as e:
    # This will help you debug if the name is wrong
    print(f"Error importing wrapper from 'full' folder: {e}")
    YourApiClass = None


app = Flask(__name__)

def get_live_mlb_stats():
    """
    This is where your logic goes. Use your Python wrapper to get the data
    and format it as a list of dictionaries.
    """
    if not YourApiClass:
        return [{"error": "API Wrapper could not be imported. Check Vercel logs."}]

    # --- START: REPLACE THIS MOCK DATA WITH YOUR API LOGIC ---
    # api = YourApiClass()
    # stats = api.get_all_the_stats_you_need()
    # return stats
    # --- END: REPLACE ---
    
    # Using placeholder data until you integrate your wrapper
    return [
        {
            "playerName": "Verified Live Player",
            "team": "Live Team",
            "vsPitcher": "Live Pitcher",
            "playerId": 12345,
            "careerHRs": 3,
            "last5": 1,
            "last10": 2,
            "last20": 4
        }
    ]

# This is the single endpoint Vercel will run
@app.route('/api/stats', methods=['GET'])
def handler():
    live_data = get_live_mlb_stats()
    response = jsonify(live_data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
