def get_flights(source, dest, dist_km):
    duration = 1.5 + (dist_km / 800) 
    cost_low = int(dist_km * 4) + 2000 
    cost_high = int(dist_km * 7) + 2500
    return [{
        "type": "Flight", "operator": "IndiGo / Air India", "bus_type": "Economy",
        "depart": "Flexible", "duration": round(duration, 1), "price": f"{cost_low} - {cost_high}", 
        "rating": "4.2", "punctuality": 90, "icon": "✈️", "link": "https://www.makemytrip.com/flights/"
    }]