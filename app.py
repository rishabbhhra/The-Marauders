from flask import Flask, render_template, request, redirect, url_for, flash
import os, webbrowser
import pandas as pd
import folium

app = Flask(__name__)
app.secret_key = "replace-this-with-random-key"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MAP_FILE = os.path.join(BASE_DIR, "static", "fra_map.html")

STATES = ["Madhya Pradesh", "Tripura", "Odisha", "Telangana"]

from flask import Flask, render_template, request, redirect, url_for, flash
import os, webbrowser
import pandas as pd
import folium

app = Flask(__name__)
app.secret_key = "replace-this-with-random-key"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MAP_FILE = os.path.join(BASE_DIR, "static", "fra_map.html")

STATES = ["Madhya Pradesh", "Tripura", "Odisha", "Telangana"]

@app.route("/reports")
def reports_page():
    return render_template("reports.html")

@app.route("/settings")
def settings_page():
    return render_template("settings.html")


# Simple color mapping for rights_status
def status_color(s):
    s = str(s).strip().lower()
    return {"approved":"green","pending":"orange","rejected":"red"}.get(s, "blue")

# Ensure sample CSVs exist
def ensure_sample_csvs():
    claims_path = os.path.join(BASE_DIR, "claims.csv")
    settlements_path = os.path.join(BASE_DIR, "settlements.csv")

    if not os.path.exists(claims_path):
        sample_claims = [
            "id,name,state,lat,lon,rights_status",
            "1,Claim_MP_1,Madhya Pradesh,23.5,77.5,Approved",
            "2,Claim_OD_1,Odisha,20.9517,85.0985,Pending",
            "3,Claim_TG_1,Telangana,17.1232,79.2088,Rejected",
            "4,Claim_TR_1,Tripura,23.9408,91.9882,Pending",
        ]
        with open(claims_path, "w") as f:
            f.write("\n".join(sample_claims))

    if not os.path.exists(settlements_path):
        sample_settlements = [
            "id,name,state,lat,lon,pop",
            "1,Settlement_MP_1,Madhya Pradesh,23.3,77.4,1200",
            "2,Settlement_OD_1,Odisha,20.9,85.0,800",
            "3,Settlement_TG_1,Telangana,17.1,79.2,500",
            "4,Settlement_TR_1,Tripura,23.94,91.99,600",
        ]
        with open(settlements_path, "w") as f:
            f.write("\n".join(sample_settlements))

# Small sample forest polygons (for demo)
FOREST_POLYGONS = {
    "Madhya Pradesh":[[23.7,77.0],[23.7,77.8],[22.9,77.8],[22.9,77.0]],
    "Odisha":[[21.4,84.5],[21.4,85.7],[20.6,85.7],[20.6,84.5]],
    "Telangana":[[18.0,78.6],[18.0,79.8],[16.6,79.8],[16.6,78.6]],
    "Tripura":[[24.4,91.6],[24.4,92.4],[23.4,92.4],[23.4,91.6]],
}

def load_data():
    ensure_sample_csvs()
    claims = pd.read_csv(os.path.join(BASE_DIR, "claims.csv"))
    settlements = pd.read_csv(os.path.join(BASE_DIR, "settlements.csv"))
    # sanitize
    claims['state'] = claims['state'].astype(str).str.strip()
    settlements['state'] = settlements['state'].astype(str).str.strip()
    return claims, settlements

def generate_map(selected_states=None, show_forest=True, show_claims=True, show_settlements=True):
    # selected_states: list or None -> if None use all
    if selected_states is None or len(selected_states)==0:
        selected_states = STATES

    claims, settlements = load_data()

    # Base map
    m = folium.Map(location=[22.9734, 78.6569], zoom_start=5, tiles="CartoDB positron")

    # For each state, add layers (Forest / Claims / Settlements)
    for state in STATES:
        if state not in selected_states:
            continue

        # Forest polygon layer
        if show_forest and state in FOREST_POLYGONS:
            fg = folium.FeatureGroup(name=f"{state} - Forest Areas", show=False)
            folium.Polygon(
                locations=FOREST_POLYGONS[state],
                popup=f"{state} (sample forest polygon)",
                color="green", weight=2, fill=True, fill_opacity=0.25
            ).add_to(fg)
            fg.add_to(m)

        # Claims layer
        if show_claims:
            fg_claims = folium.FeatureGroup(name=f"{state} - Claims", show=True)
            dfc = claims[claims['state'] == state]
            for _, r in dfc.iterrows():
                popup_html = f"<b>{r.get('name','-')}</b><br>State: {r.get('state','-')}<br>Status: {r.get('rights_status','-')}"
                folium.Marker(
                    location=[r['lat'], r['lon']],
                    popup=folium.Popup(popup_html, max_width=300),
                    icon=folium.Icon(color=status_color(r.get('rights_status','')), icon="info-sign")
                ).add_to(fg_claims)
            fg_claims.add_to(m)

        # Settlements layer
        if show_settlements:
            fg_set = folium.FeatureGroup(name=f"{state} - Settlements", show=False)
            dfs = settlements[settlements['state'] == state]
            for _, r in dfs.iterrows():
                popup_html = f"<b>{r.get('name','-')}</b><br>Pop: {r.get('pop','-')}"
                folium.CircleMarker(
                    location=[r['lat'], r['lon']],
                    radius=6,
                    popup=folium.Popup(popup_html, max_width=250),
                    fill=True, fill_opacity=0.8
                ).add_to(fg_set)
            fg_set.add_to(m)

    # overlay: all claims (global)
    fg_all = folium.FeatureGroup(name="All Claims (overlay)", show=False)
    for _, r in claims.iterrows():
        folium.Marker(
            location=[r['lat'], r['lon']],
            popup=f"{r.get('name','-')} ({r.get('state','-')}) - {r.get('rights_status','-')}",
            icon=folium.Icon(color=status_color(r.get('rights_status','')), icon="info-sign")
        ).add_to(fg_all)
    fg_all.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Ensure static dir exists
    static_dir = os.path.join(BASE_DIR, "static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)

    m.save(MAP_FILE)
    return MAP_FILE

@app.route("/", methods=["GET", "POST"])
def index():
    # default choices
    chosen_states = request.form.getlist("state") or STATES
    show_forest = request.form.get("forest") == "on" or True
    show_claims = request.form.get("claims") == "on" or True
    show_settlements = request.form.get("settlements") == "on" or True

    # If POST and file upload present, save uploaded CSVs
    if request.method == "POST":
        # handle file uploads
        claims_file = request.files.get("claims_file")
        if claims_file and claims_file.filename:
            claims_file.save(os.path.join(BASE_DIR, "claims.csv"))
            flash("Uploaded claims.csv", "success")
        settle_file = request.files.get("settlements_file")
        if settle_file and settle_file.filename:
            settle_file.save(os.path.join(BASE_DIR, "settlements.csv"))
            flash("Uploaded settlements.csv", "success")

        # form checkboxes
        chosen_states = request.form.getlist("state")
        show_forest = request.form.get("forest") == "on"
        show_claims = request.form.get("claims") == "on"
        show_settlements = request.form.get("settlements") == "on"

    # Generate map with chosen options
    generate_map(selected_states=chosen_states, show_forest=show_forest, show_claims=show_claims, show_settlements=show_settlements)
    # open map automatically in browser only in dev (optional)
    # webbrowser.open("file://" + MAP_FILE)

    return render_template("index.html", states=STATES, chosen_states=chosen_states,
                           show_forest=show_forest, show_claims=show_claims, show_settlements=show_settlements)

# A simple route to directly view the map (iframe)
@app.route("/map")
def map_iframe():
    # ensure map exists
    if not os.path.exists(MAP_FILE):
        generate_map()
    # we render a template which includes the saved map HTML via iframe
    return render_template("map_iframe.html", map_url=url_for('static', filename='fra_map.html'))

if __name__ == "__main__":
    # create sample csvs if missing
    ensure_sample_csvs()
    # start app
    app.run(debug=True, port=5000)


# Simple color mapping for rights_status
def status_color(s):
    s = str(s).strip().lower()
    return {"approved":"green","pending":"orange","rejected":"red"}.get(s, "blue")

# Ensure sample CSVs exist
def ensure_sample_csvs():
    claims_path = os.path.join(BASE_DIR, "claims.csv")
    settlements_path = os.path.join(BASE_DIR, "settlements.csv")

    if not os.path.exists(claims_path):
        sample_claims = [
            "id,name,state,lat,lon,rights_status",
            "1,Claim_MP_1,Madhya Pradesh,23.5,77.5,Approved",
            "2,Claim_OD_1,Odisha,20.9517,85.0985,Pending",
            "3,Claim_TG_1,Telangana,17.1232,79.2088,Rejected",
            "4,Claim_TR_1,Tripura,23.9408,91.9882,Pending",
        ]
        with open(claims_path, "w") as f:
            f.write("\n".join(sample_claims))

    if not os.path.exists(settlements_path):
        sample_settlements = [
            "id,name,state,lat,lon,pop",
            "1,Settlement_MP_1,Madhya Pradesh,23.3,77.4,1200",
            "2,Settlement_OD_1,Odisha,20.9,85.0,800",
            "3,Settlement_TG_1,Telangana,17.1,79.2,500",
            "4,Settlement_TR_1,Tripura,23.94,91.99,600",
        ]
        with open(settlements_path, "w") as f:
            f.write("\n".join(sample_settlements))

# Small sample forest polygons (for demo)
FOREST_POLYGONS = {
    "Madhya Pradesh":[[23.7,77.0],[23.7,77.8],[22.9,77.8],[22.9,77.0]],
    "Odisha":[[21.4,84.5],[21.4,85.7],[20.6,85.7],[20.6,84.5]],
    "Telangana":[[18.0,78.6],[18.0,79.8],[16.6,79.8],[16.6,78.6]],
    "Tripura":[[24.4,91.6],[24.4,92.4],[23.4,92.4],[23.4,91.6]],
}

def load_data():
    ensure_sample_csvs()
    claims = pd.read_csv(os.path.join(BASE_DIR, "claims.csv"))
    settlements = pd.read_csv(os.path.join(BASE_DIR, "settlements.csv"))
    # sanitize
    claims['state'] = claims['state'].astype(str).str.strip()
    settlements['state'] = settlements['state'].astype(str).str.strip()
    return claims, settlements

def generate_map(selected_states=None, show_forest=True, show_claims=True, show_settlements=True):
    # selected_states: list or None -> if None use all
    if selected_states is None or len(selected_states)==0:
        selected_states = STATES

    claims, settlements = load_data()

    # Base map
    m = folium.Map(location=[22.9734, 78.6569], zoom_start=5, tiles="CartoDB positron")

    # For each state, add layers (Forest / Claims / Settlements)
    for state in STATES:
        if state not in selected_states:
            continue

        # Forest polygon layer
        if show_forest and state in FOREST_POLYGONS:
            fg = folium.FeatureGroup(name=f"{state} - Forest Areas", show=False)
            folium.Polygon(
                locations=FOREST_POLYGONS[state],
                popup=f"{state} (sample forest polygon)",
                color="green", weight=2, fill=True, fill_opacity=0.25
            ).add_to(fg)
            fg.add_to(m)

        # Claims layer
        if show_claims:
            fg_claims = folium.FeatureGroup(name=f"{state} - Claims", show=True)
            dfc = claims[claims['state'] == state]
            for _, r in dfc.iterrows():
                popup_html = f"<b>{r.get('name','-')}</b><br>State: {r.get('state','-')}<br>Status: {r.get('rights_status','-')}"
                folium.Marker(
                    location=[r['lat'], r['lon']],
                    popup=folium.Popup(popup_html, max_width=300),
                    icon=folium.Icon(color=status_color(r.get('rights_status','')), icon="info-sign")
                ).add_to(fg_claims)
            fg_claims.add_to(m)

        # Settlements layer
        if show_settlements:
            fg_set = folium.FeatureGroup(name=f"{state} - Settlements", show=False)
            dfs = settlements[settlements['state'] == state]
            for _, r in dfs.iterrows():
                popup_html = f"<b>{r.get('name','-')}</b><br>Pop: {r.get('pop','-')}"
                folium.CircleMarker(
                    location=[r['lat'], r['lon']],
                    radius=6,
                    popup=folium.Popup(popup_html, max_width=250),
                    fill=True, fill_opacity=0.8
                ).add_to(fg_set)
            fg_set.add_to(m)

    # overlay: all claims (global)
    fg_all = folium.FeatureGroup(name="All Claims (overlay)", show=False)
    for _, r in claims.iterrows():
        folium.Marker(
            location=[r['lat'], r['lon']],
            popup=f"{r.get('name','-')} ({r.get('state','-')}) - {r.get('rights_status','-')}",
            icon=folium.Icon(color=status_color(r.get('rights_status','')), icon="info-sign")
        ).add_to(fg_all)
    fg_all.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Ensure static dir exists
    static_dir = os.path.join(BASE_DIR, "static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)

    m.save(MAP_FILE)
    return MAP_FILE

@app.route("/", methods=["GET", "POST"])
def index():
    # default choices
    chosen_states = request.form.getlist("state") or STATES
    show_forest = request.form.get("forest") == "on" or True
    show_claims = request.form.get("claims") == "on" or True
    show_settlements = request.form.get("settlements") == "on" or True

    # If POST and file upload present, save uploaded CSVs
    if request.method == "POST":
        # handle file uploads
        claims_file = request.files.get("claims_file")
        if claims_file and claims_file.filename:
            claims_file.save(os.path.join(BASE_DIR, "claims.csv"))
            flash("Uploaded claims.csv", "success")
        settle_file = request.files.get("settlements_file")
        if settle_file and settle_file.filename:
            settle_file.save(os.path.join(BASE_DIR, "settlements.csv"))
            flash("Uploaded settlements.csv", "success")

        # form checkboxes
        chosen_states = request.form.getlist("state")
        show_forest = request.form.get("forest") == "on"
        show_claims = request.form.get("claims") == "on"
        show_settlements = request.form.get("settlements") == "on"

    # Generate map with chosen options
    generate_map(selected_states=chosen_states, show_forest=show_forest, show_claims=show_claims, show_settlements=show_settlements)
    # open map automatically in browser only in dev (optional)
    # webbrowser.open("file://" + MAP_FILE)

    return render_template("index.html", states=STATES, chosen_states=chosen_states,
                           show_forest=show_forest, show_claims=show_claims, show_settlements=show_settlements)

# A simple route to directly view the map (iframe)
@app.route("/map")
def map_iframe():
    # ensure map exists
    if not os.path.exists(MAP_FILE):
        generate_map()
    # we render a template which includes the saved map HTML via iframe
    return render_template("map_iframe.html", map_url=url_for('static', filename='fra_map.html'))

if __name__ == "__main__":
    # create sample csvs if missing
    ensure_sample_csvs()
    # start app
    app.run(debug=True, port=5000)
