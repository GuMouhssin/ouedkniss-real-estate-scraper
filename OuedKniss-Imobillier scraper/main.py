#imports:
import requests, json, time, csv, re, unicodedata
from datetime import datetime
from charset_normalizer import from_bytes

#variables:
url = "https://api.ouedkniss.com/graphql"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json"
}

query = """
    query MyQuery($page: Int!){
        search(
            filter:{
                categorySlug: "immobilier"
                page: $page
            }
        ){
            announcements{
                data{
                    title
                    createdAt
                    cities{
                        name
                    }
                    store{
                        name
                    }
                    price
                    smallDescription{
                        specification{
                            codename
                        }
                        valueText
                    }
                }
            }
        }
    }
"""
#Config:
delay = 1
Max_retries = 3

#data_cleaning_functions:
def clean_area(area):
    return float(area.replace("م²", "").replace("m²", "").strip())

def clean_room(room):
    if room == "غرفة واحدة":
        return 1
    elif room == "غرفتين":
        return 2
    else:
        try:
            return int(room.replace("غرف", "").replace("F", "").strip())
        except ValueError:
            return "N/A"

def clean_date(date):
    dt = datetime.fromisoformat(date.replace("Z", ""))
    return dt.strftime("%Y-%m-%d %H:%M")

def fix_text(txt):
    return txt.replace("Ã©", "é").replace("Ã¨", "è")


#functions:
def fetch_page(page):
    payload = {
        "operationName": "MyQuery",
        "variables": {
            "page": page
        },
        "query": query
    }
    last_error = None
    for i in range(Max_retries):
        try:
            resp = requests.post(url,json = payload , headers = headers, timeout = 10)
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                print(data["errors"])
                print(f"{i+1} retry for page: {page}")
                time.sleep(delay)
                continue
            data = data["data"]["search"]["announcements"]["data"]
            return data
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            last_error = e
            print(f"{i+1} retry for page: {page}")
            time.sleep(2)
    print(f"ERROR: {last_error}---Page:{page}")
    return None

def parse_desc(desc):
    parsed_desc = {}
    for obj in desc:
        parsed_desc[obj["specification"]["codename"]] = obj["valueText"]
    return parsed_desc

def parse_est(est):
    if est["smallDescription"]:
        desc = parse_desc(est["smallDescription"])
        if desc.get("superficie_terrain") :
            area = clean_area(desc["superficie_terrain"][0])
        elif desc.get("superficie") :
            area = clean_area(desc["superficie"][0])
        else:
            area = "N/A"
        if desc.get("pieces_appartement"):
            rooms = [clean_room(x) for x in desc["pieces_appartement"]]
        else:
            rooms = "N/A"
    else:
        area = "N/A"
        rooms = "N/A"

    return {
        "title": est["title"],
        "price": est["price"] if est["price"] else "N/A",
        "city": est["cities"][0]["name"] if est["cities"] else "N/A",
        "store": est["store"]["name"] if est["store"] else "N/A",
        "createdAt": clean_date(est["createdAt"]),
        "area(m²)": area,
        "rooms": rooms
    }

def scraper(pages):
    print(f"----Scraping----")
    ests = []
    for i in range(pages):
        print(f"Scraping page {i+1}.....")
        data = fetch_page(i+1)
        if not data:
            continue
        print(f"parsing and saving page {i+1} data.....")
        for est in data:
            ests.append(parse_est(est))
        time.sleep(delay)
    return ests
        
def save_json(data, filename = "OuedKniss_Immobilier"):
    if not data or len(data) == 0:
        print("ERROR: there is no data to save")
        return
    with open(filename + ".json", "w") as f:
        json.dump(data, f, indent = 2)

def save_csv(data, filename = "OuedKniss_Immobilier"):
    if not data or len(data) == 0:
        print("ERROR: there is no data to save")
        return
    with open(filename + ".csv", "w", newline = "") as f:
        keys = data[0].keys()
        writer = csv.DictWriter(f, fieldnames = keys)
        writer.writeheader()
        writer.writerows(data)

if __name__ == "__main__":
    data = scraper(50) #select how many pages you want to scrape
    save_csv(data)
    save_json(data)
