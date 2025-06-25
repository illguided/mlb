import sys
import os
from flask import Flask, jsonify
import traceback

# --- This block ensures Vercel can find your local 'full' folder ---
# It adds the project's root directory ('onetwothree') to Python's path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --------------------------------------------------------------------

# --- We will now try to import your wrapper and catch any errors ---
try:
    # Based on your files, the main module is in the 'full' directory
    # and is called with 'statsapi'
    from full import statsapi
    STATSAPI_IMPORTED = True
except ImportError as e:
    STATSAPI_IMPORTED = False
    IMPORT_ERROR_MESSAGE = f"CRITICAL: Failed to import 'statsapi' from the 'full' folder. Error: {e}"

app = Flask(__name__)

# This is the Vercel-compatible API endpoint
@app.route('/api/stats', methods=['GET'])
def handler():
    # 1. Immediately check if the import failed
    if not STATSAPI_IMPORTED:
        return jsonify({"error": IMPORT_ERROR_MESSAGE, "details": traceback.format_exc()})

    # 2. Try to run the simplest possible command from your wrapper
    try:
        # We will only call statsapi.schedule() to test the connection.
        # This is the simplest test to see if the wrapper works online.
        print("Attempting to fetch today's schedule...")
        today_schedule = statsapi.schedule() # Uses the default date
        print("Successfully fetched schedule.")
        
        # If it succeeds, we return the raw schedule data.
        # This proves the wrapper works in the Vercel environment.
        response = jsonify(today_schedule)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        # If ANY error happens, we catch it and return it for debugging
        print(f"--- SERVER-SIDE CRASH ---")
        print(f"Error during statsapi call: {e}")
        error_details = traceback.format_exc()
        print(error_details)
        print("-------------------------")
        
        response = jsonify({"error": f"The Python script crashed: {e}", "details": error_details})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500
