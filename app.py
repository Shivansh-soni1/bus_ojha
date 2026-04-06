from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import os
import requests
import folium

from models import db, User, History
from modules import bus, railway, road, airways

# ✅ NEW IMPORTS (ADDED)
from modules.train_module import (
    get_best_trains,
    load_stations,
    find_nearest,
    get_lat_lon
)

from modules.bus_service import get_buses


app = Flask(__name__)
app.config['SECRET_KEY'] = 'shivam_smart_travel_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_travel.db'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

geolocator = Nominatim(user_agent="smart_travel_project")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =========================
# AUTH ROUTES
# =========================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, password=hashed_pw)

        db.session.add(new_user)
        db.session.commit()

        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Login failed.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def home():
    return render_template('index.html', user=current_user)


# =========================
# LOAD TRAIN DATA (NEW)
# =========================
small_stations = load_stations("all_india_stations_small.csv")
junction_stations = load_stations("final_junction1.csv")


# =========================
# EXISTING SEARCH LOGIC (UNCHANGED)
# =========================
@app.route('/search', methods=['POST'])
@login_required
def search():

    source = request.form.get('source').strip().title()
    dest = request.form.get('destination').strip().title()
    date = request.form.get('date')
    priority = request.form.get('priority', 'balanced')

    src_loc = geolocator.geocode(source + ", India")
    dst_loc = geolocator.geocode(dest + ", India")

    dist_km = 0
    if src_loc and dst_loc:
        dist_km = geodesic(
            (src_loc.latitude, src_loc.longitude),
            (dst_loc.latitude, dst_loc.longitude)
        ).km

    raw_results = []

    try: raw_results.extend(bus.get_buses(source, dest, date, dist_km))
    except: pass

    try: raw_results.extend(railway.get_trains(source, dest, date, dist_km))
    except: pass

    if dist_km > 0:
        raw_results.extend(road.get_road_trip(dist_km))

    if dist_km > 300:
        raw_results.extend(airways.get_flights(source, dest, dist_km))

    # SIMPLE SORT
    raw_results.sort(key=lambda x: float(x.get('duration', 999)))

    # BEST OPTION
    overall_best = raw_results[0] if raw_results else None

    return render_template(
        'results.html',
        results=raw_results,
        overall_best=overall_best,
        user=current_user,
        source=source,
        dest=dest,
        map_html=None,
        priority=priority
    )


# =========================
# ✅ NEW MULTI-STEP PLANNER
# =========================
def plan_journey(from_place, to_place, date):

    routes = []

    from_station, to_station, trains, cols, mode = get_best_trains(
        from_place, to_place, date, small_stations, junction_stations
    )

    if not trains:
        return []

    _, _, first_leg_trains, _, _ = get_best_trains(
        from_place,
        from_station["name"],
        date,
        small_stations,
        junction_stations
    )

    # ROUTE 1: TRAIN + TRAIN
    if first_leg_trains:

        route = []
        step = 1

        route.append({
            "step": step,
            "mode": "TRAIN",
            "from": from_place,
            "to": from_station["name"],
            "data": first_leg_trains[:3]
        })

        step += 1

        route.append({
            "step": step,
            "mode": "TRAIN",
            "from": from_station["name"],
            "to": to_station["name"],
            "data": trains[:3]
        })
        step += 1
        if to_place.lower() != to_station["name"].lower():
            _, _, last_leg_trains, _, _ = get_best_trains(
                to_station["name"],
                to_place,
                date,
                small_stations,
                junction_stations
            )

            if last_leg_trains:
                route.append({
                    "step": step,
                    "mode": "TRAIN",
                    "from": to_station["name"],
                    "to": to_place,
                    "data": last_leg_trains[:3]
                })
        routes.append({
            "route_id": 1,
            "type": "Train + Train",
            "steps": route
        })

    # ROUTE 2: BUS + TRAIN
    route = []
    step = 1

    if from_place.lower() != from_station["name"].lower():

        bus1 = get_buses(from_place, from_station["name"], date)

        if not bus1:
            bus1 = [{"msg": "Take local transport", "price": "₹100-₹300"}]

        route.append({
            "step": step,
            "mode": "BUS",
            "from": from_place,
            "to": from_station["name"],
            "data": bus1
        })

        step += 1

    route.append({
        "step": step,
        "mode": "TRAIN",
        "from": from_station["name"],
        "to": to_station["name"],
        "data": trains[:3]
    })
    step += 1
    if to_place.lower() != to_station["name"].lower():
        bus2 = get_buses(
            to_station["name"],
            to_place,
            date,
            dist_km=to_station.get("distance_km", 0)
        )

        if not bus2:
            bus2 = [{
                "msg": "Take local transport",
                "price": "₹80-₹200"
            }]

        route.append({
            "step": step,
            "mode": "BUS",
            "from": to_station["name"],
            "to": to_place,
            "data": bus2
        })
    routes.append({
        "route_id": len(routes) + 1,
        "type": "Bus + Train",
        "steps": route
    })

    # RANKING
    for route in routes:
        route["score"] = calculate_route_score(route)

    routes = sorted(routes, key=lambda x: x["score"])

    if routes:
        routes[0]["best"] = True

    return routes


def calculate_route_score(route):

    total_time = 0
    total_price = 0
    bus_penalty = 0

    for step in route["steps"]:
        for item in step["data"]:

            if step["mode"] == "TRAIN":
                try:
                    total_time += int(item[2])
                    total_price += 200
                except:
                    pass

            elif step["mode"] == "BUS":
                try:
                    total_time += float(item.get("duration", 2)) * 60
                    total_price += int(str(item.get("price", "100")).replace("₹", "").split("-")[0])
                    bus_penalty += 50
                except:
                    pass

    return total_time + total_price + bus_penalty


# =========================
# NEW ROUTE FOR PLANNER
# =========================
@app.route("/plan")
def plan():

    source = request.args.get("source")
    destination = request.args.get("destination")
    date = request.args.get("date")

    routes = plan_journey(source, destination, date)

    return render_template(
        "result1.html",
        source=source,
        destination=destination,
        routes=routes
    )
@app.route("/result1")
def result1():
    return render_template("result1.html")

# =========================
# RUN
# =========================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)