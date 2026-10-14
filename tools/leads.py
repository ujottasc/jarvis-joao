"""Real business leads from OpenStreetMap, website-checked -> leads.json + leads.xlsx.

Usage: python leads.py [amenity] [per_country]     e.g. python leads.py dentist 100
Each country's lookup goes through that country's proxy when .env.local has
credentials, and directly otherwise.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor

import requests
from openpyxl import Workbook

from competitor_pricing import UA, proxies_for

# Public Overpass servers are often overloaded, so try several; the one that
# answered last goes first.
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
# ponytail: fixed city list; country-wide Overpass queries time out. Add cities for more volume.
CITIES = {
    "US": ("us", [("New York, NY", 40.73, -73.99), ("Los Angeles, CA", 34.05, -118.25), ("Chicago, IL", 41.88, -87.63),
                  ("Houston, TX", 29.76, -95.37), ("Seattle, WA", 47.61, -122.33), ("Denver, CO", 39.74, -104.99),
                  ("Boston, MA", 42.36, -71.06), ("San Francisco, CA", 37.77, -122.42), ("Austin, TX", 30.27, -97.74),
                  ("Portland, OR", 45.52, -122.68), ("Minneapolis, MN", 44.98, -93.27), ("Washington, DC", 38.90, -77.04)]),
    "Canada": ("ca", [("Toronto, ON", 43.65, -79.38), ("Vancouver, BC", 49.28, -123.12), ("Montréal, QC", 45.50, -73.57),
                      ("Calgary, AB", 51.05, -114.07), ("Ottawa, ON", 45.42, -75.70), ("Edmonton, AB", 53.55, -113.49),
                      ("Winnipeg, MB", 49.90, -97.14), ("Québec, QC", 46.81, -71.21), ("Victoria, BC", 48.43, -123.37),
                      ("Halifax, NS", 44.65, -63.57)]),
}


def query(amenity, lat, lon):
    return (f'[out:json][timeout:60];nwr["amenity"="{amenity}"]["name"]'
            f'(around:25000,{lat},{lon});out tags center;')


def tag(t, *keys):
    return next((t[k] for k in keys if t.get(k)), "")


def to_lead(t, country, city):
    site = tag(t, "website", "contact:website")
    if site and not site.startswith("http"):
        site = "https://" + site
    return {"country": country, "name": t.get("name", ""), "city": tag(t, "addr:city") or city.split(",")[0],
            "area": city, "phone": tag(t, "phone", "contact:phone"), "website": site,
            "email": tag(t, "email", "contact:email"),
            "address": " ".join(filter(None, [t.get("addr:housenumber"), t.get("addr:street")]))}


def fetch(amenity, code, lat, lon):
    """Overpass elements for one city, through the country's proxy if one is set."""
    proxies = proxies_for(code)
    for url in list(OVERPASS):
        try:
            r = requests.post(url, data={"data": query(amenity, lat, lon)},
                              headers={"User-Agent": "leads/1.0"}, proxies=proxies, timeout=45)
            r.raise_for_status()
            els = r.json()["elements"]
            OVERPASS.remove(url)
            OVERPASS.insert(0, url)
            return els, "proxy" if proxies else "direct"
        except (requests.RequestException, ValueError):
            continue
    return [], "failed"


def site_ok(lead):
    try:
        r = requests.get(lead["website"], headers={"User-Agent": UA}, timeout=10, stream=True)
        return r.status_code < 400
    except requests.RequestException:
        return False


def main(amenity, per_country):
    leads = []
    for country, (code, cities) in CITIES.items():
        ok, seen = [], set()
        for city, lat, lon in cities:
            if len(ok) >= per_country:
                break
            els, via = fetch(amenity, code, lat, lon)
            new = [to_lead(e.get("tags", {}), country, city) for e in els]
            new = [l for l in new if l["phone"] and l["website"] and l["website"] not in seen]
            seen.update(l["website"] for l in new)
            with ThreadPoolExecutor(24) as ex:
                live = [l for l, good in zip(new, ex.map(site_ok, new)) if good]
            ok += live
            print(f"{country} {city}: {len(els)} listed, {len(new)} with phone+website, "
                  f"{len(live)} with a live site ({via})", flush=True)
        leads += ok[:per_country]
    json.dump(leads, open("leads.json", "w"), ensure_ascii=False, indent=1)
    wb = Workbook()
    ws = wb.active
    ws.append(list(leads[0].keys()) if leads else ["no leads"])
    for l in leads:
        ws.append(list(l.values()))
    wb.save("leads.xlsx")
    print(f"saved {len(leads)} leads to leads.json and leads.xlsx")


def demo():
    l = to_lead({"name": "A", "contact:website": "a.com", "phone": "1"}, "US", "Austin, TX")
    assert l["website"] == "https://a.com" and l["city"] == "Austin" and l["phone"] == "1"


if __name__ == "__main__":
    demo()
    main(sys.argv[1] if len(sys.argv) > 1 else "dentist", int(sys.argv[2]) if len(sys.argv) > 2 else 100)
