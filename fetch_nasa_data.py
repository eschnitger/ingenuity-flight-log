# fetch_nasa_data.py
# Downloads the two Ingenuity layers behind NASA's "Where is Perseverance?" map
# into data/raw/. The files are already committed; run this only to refresh them.
import json
import os
import urllib.request

BASE = "https://mars.nasa.gov/mmgis-maps/M20/Layers/json"
FILES = ["m20_heli_waypoints.json", "m20_heli_flight_path.json"]

if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    for name in FILES:
        req = urllib.request.Request(f"{BASE}/{name}",
                                     headers={"User-Agent": "ingenuity-flight-log"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
        features = json.loads(body)["features"]      # fails loudly on an error page
        with open(f"data/raw/{name}", "wb") as f:
            f.write(body)
        print(f"✓ {name}: {len(features)} features, {len(body)/1024:.0f} KB")
