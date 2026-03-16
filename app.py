from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import os
import folium

from models import db, User, History
from modules import bus, railway, road, airways

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
            flash('Login failed. Check username and password.', 'danger')
            
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

@app.route('/search', methods=['POST'])
@login_required
def search():
    source = request.form.get('source').strip().title()
    dest = request.form.get('destination').strip().title()
    date = request.form.get('date')

    dist_km = 0
    src_loc, dst_loc = None, None
    try:
        src_loc = geolocator.geocode(source + ", India", timeout=5)
        dst_loc = geolocator.geocode(dest + ", India", timeout=5)
        if src_loc and dst_loc:
            dist_km = geodesic((src_loc.latitude, src_loc.longitude), 
                               (dst_loc.latitude, dst_loc.longitude)).km
    except:
        pass 

    # 1. GENERATE FOLIUM MAP
    map_html = None
    if src_loc and dst_loc:
        mid_lat = (src_loc.latitude + dst_loc.latitude) / 2
        mid_lon = (src_loc.longitude + dst_loc.longitude) / 2
        m = folium.Map(location=[mid_lat, mid_lon], zoom_start=6, tiles="CartoDB positron")
        folium.Marker([src_loc.latitude, src_loc.longitude], tooltip=f"Start: {source}", icon=folium.Icon(color="green", icon="play")).add_to(m)
        folium.Marker([dst_loc.latitude, dst_loc.longitude], tooltip=f"End: {dest}", icon=folium.Icon(color="red", icon="stop")).add_to(m)
        folium.PolyLine([(src_loc.latitude, src_loc.longitude), (dst_loc.latitude, dst_loc.longitude)], color="blue", weight=4, opacity=0.6, dash_array="10").add_to(m)
        map_html = m._repr_html_()

    # 2. GATHER ALL DATA
    raw_results = []
    try: raw_results.extend(bus.get_buses(source, dest, date, dist_km))
    except: pass
    try: raw_results.extend(railway.get_trains(source, dest, date, dist_km))
    except: pass
    if dist_km > 0: raw_results.extend(road.get_road_trip(dist_km))
    if dist_km > 300: raw_results.extend(airways.get_flights(source, dest, dist_km))

    # 3. SMART FILTER: TOP 1 PER MODE + GROUPING OTHERS
    top_results = []
    def get_base_price(p):
        try:
            if isinstance(p, str) and '-' in p: return int(p.split('-')[0].strip().replace('₹', '').replace(',', ''))
            return int(float(p))
        except: return 99999

    modes = ['Flight', 'Train', 'Bus', 'Car/Taxi']
    for mode in modes:
        mode_options = [r for r in raw_results if r['type'] == mode]
        if mode_options:
            mode_options.sort(key=lambda x: (float(x.get('duration', 999)), get_base_price(x.get('price', 99999))))
            best_option = mode_options[0] 
            
            if mode == 'Train': best_option['tag'] = "🏆 Most Reliable"
            if mode == 'Flight': best_option['tag'] = "⚡ Fastest Route"
            if mode == 'Bus': best_option['tag'] = "💰 Budget Friendly"
            if mode == 'Car/Taxi': best_option['tag'] = "🚗 Door-to-Door"
            
            best_option['other_options'] = mode_options[1:]
            top_results.append(best_option)

    top_results.sort(key=lambda x: float(x.get('duration', 999)))

    # 4. FIND THE SINGLE "AI OVERALL RECOMMENDATION"
    overall_best = None
    if top_results:
        overall_best = max(top_results, key=lambda x: x.get('punctuality', 0) - (float(x.get('duration', 999)) * 2))

    return render_template('results.html', results=top_results, overall_best=overall_best, user=current_user, source=source, dest=dest, map_html=map_html)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)