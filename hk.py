import requests
import re
import json
import os
from collections import defaultdict
from datetime import datetime

URL = "https://cinema.com.hk/en/movie/ticketing"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

BASE_DIR = "data"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

DB_FILE = os.path.join(BASE_DIR, "movies.json")


def fetch_page():
    r = requests.get(URL, headers=HEADERS)
    text = r.text
    text = text.replace('\\"', '"')
    return text


def extract_shows(text):

    shows = re.split(r'(?=\{"id":\d+,"published")', text)

    data = []

    for show in shows:

        movie_m = re.search(r'"movie":\{"id":(\d+).*?"name":"([^"]+)"', show)
        price_m = re.search(r'"price":(\d+)', show)
        seats_m = re.search(r'"seats":(\d+)', show)
        sold_m = re.search(r'"sold":(\d+)', show)

        site_m = re.search(r'"site":\{.*?"name":"([^"]+)"', show)
        house_m = re.search(r'"house":\{.*?"name":"([^"]+)"', show)
        date_m = re.search(r'"date":"([^"]+)"', show)

        if not movie_m:
            continue

        movie_name = movie_m.group(2)

        price = int(price_m.group(1)) if price_m else 0
        seats = int(seats_m.group(1)) if seats_m else 0
        sold = int(sold_m.group(1)) if sold_m else 0

        site = site_m.group(1) if site_m else "Unknown"
        house = house_m.group(1) if house_m else "Unknown"
        date = date_m.group(1)[:10] if date_m else "Unknown"

        # REMOVE UNKNOWN DATES
        if date == "Unknown":
            continue

        gross = sold * price

        show_id = f"{movie_name}_{date}_{site}_{house}"

        data.append({
            "id": show_id,
            "movie": movie_name,
            "date": date,
            "site": site,
            "house": house,
            "sold": sold,
            "seats": seats,
            "price": price,
            "gross": gross
        })

    return data


def load_database():

    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                pass

    return {
        "last_updated": None,
        "movies": {}
    }


def save_database(db):

    db["last_updated"] = datetime.utcnow().isoformat()

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


def update_database(shows):

    db = load_database()
    movies = db["movies"]

    for show in shows:

        movie = show["movie"]
        show_id = show["id"]

        if movie not in movies:
            movies[movie] = {
                "shows": {},
                "dates": {},
                "total": {"shows": 0, "sold": 0, "seats": 0, "gross": 0}
            }

        movie_data = movies[movie]

        # Update show safely
        movie_data["shows"][show_id] = show

    # Recalculate statistics
    for movie, movie_data in movies.items():

        date_stats = defaultdict(lambda: {"shows": 0, "sold": 0, "seats": 0, "gross": 0})

        for show in movie_data["shows"].values():

            d = show["date"]

            date_stats[d]["shows"] += 1
            date_stats[d]["sold"] += show["sold"]
            date_stats[d]["seats"] += show["seats"]
            date_stats[d]["gross"] += show["gross"]

        movie_data["dates"] = dict(date_stats)

        totals = {"shows": 0, "sold": 0, "seats": 0, "gross": 0}

        for d in movie_data["dates"].values():
            totals["shows"] += d["shows"]
            totals["sold"] += d["sold"]
            totals["seats"] += d["seats"]
            totals["gross"] += d["gross"]

        movie_data["total"] = totals

    save_database(db)

    print("\nDatabase updated:", DB_FILE)
    print("Movies tracked:", len(movies))


def print_summary(shows):

    summary = defaultdict(lambda: {"shows": 0, "sold": 0, "seats": 0, "gross": 0})

    for s in shows:
        key = (s["movie"], s["date"])

        summary[key]["shows"] += 1
        summary[key]["sold"] += s["sold"]
        summary[key]["seats"] += s["seats"]
        summary[key]["gross"] += s["gross"]

    print("\nCURRENT SCRAPE SUMMARY\n")

    for (movie, date), stats in summary.items():

        print(
            f"{movie} | {date} | "
            f"Shows:{stats['shows']} "
            f"Sold:{stats['sold']} "
            f"Seats:{stats['seats']} "
            f"Gross:{stats['gross']:,}"
        )


def main():

    print("Fetching ticketing page...")

    text = fetch_page()

    shows = extract_shows(text)

    print("Shows parsed:", len(shows))

    update_database(shows)

    print_summary(shows)


if __name__ == "__main__":
    main()