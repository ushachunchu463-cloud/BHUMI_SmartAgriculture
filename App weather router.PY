# ─────────────────────────────────────────────
# ADD THIS ROUTE to app.py
# Place it right after your existing:
# @app.route('/api/market-prices')
# ─────────────────────────────────────────────

@app.route('/api/weather/<state>/<district>')
@login_required
def api_weather_district(state, district):
    """Live weather for any district — called by frontend JS every 30s"""
    data = get_weather(state, district)
    return jsonify(data)

@app.route('/api/weather/<state>')
@login_required  
def api_weather_state(state):
    """Live weather for a state — fallback"""
    data = get_weather(state)
    return jsonify(data)

# ─────────────────────────────────────────────
# ALSO ADD the farm-weather page route:
# ─────────────────────────────────────────────

@app.route('/farm-weather')
@login_required
def farm_weather():
    return render_template(
        'farm_weather_monitor.html',
        states=list(STATES_DISTRICTS.keys()),
        districts=STATES_DISTRICTS
    )