"""Rule-based, grounded planner. Every item comes from the dataset by id; prices are never invented."""
import re
from data_loader import load_items

ITEMS = load_items()
BY_ID = {i["id"]: i for i in ITEMS}
CITIES = {"cairo": "Cairo", "alexandria": "Alexandria", "luxor": "Luxor", "aswan": "Aswan", "dahab": "Dahab",
          "القاهرة": "Cairo", "اسكندرية": "Alexandria", "الاسكندرية": "Alexandria", "الإسكندرية": "Alexandria",
          "الأقصر": "Luxor", "الاقصر": "Luxor", "اقصر": "Luxor", "أسوان": "Aswan", "اسوان": "Aswan", "دهب": "Dahab"}
INTERESTS = {"food": "food", "eat": "food", "اكل": "food", "أكل": "food", "history": "history", "تاريخ": "history",
             "museum": "history", "متاحف": "history", "sea": "sea", "beach": "sea", "snorkel": "sea", "بحر": "sea",
             "nature": "nature", "طبيعة": "nature", "relax": "relax", "culture": "culture", "ثقافة": "culture",
             "adventure": "adventure", "evening": "evening", "nightlife": "evening", "free": "free"}
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def parse_request(msg):
    m = msg.lower().translate(AR_DIGITS)
    city = next((v for k, v in CITIES.items() if k in m), None)
    days = None
    d = re.search(r"(\d+)\s*(?:-?\s*day|days|يوم|ايام|أيام)", m)
    if d: days = int(d.group(1))
    budget = None
    b = re.search(r"(\d[\d,]*)\s*(?:egp|le|l\.e|جنيه|جنية|pound)", m) or re.search(r"(?:egp|budget|ميزانية)\D{0,5}(\d[\d,]*)", m)
    if b: budget = int(b.group(1).replace(",", ""))
    else:
        nums = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", m)]
        big = [n for n in nums if n >= 100]
        if big: budget = big[0]
    interests = sorted({v for k, v in INTERESTS.items() if k in m})
    return {"city": city, "days": days, "budget": budget, "interests": interests}

def _score(item, interests):
    return len(set(item["interests"]) & set(interests))

def pick(city, cat, interests, exclude=(), cheapest=False, paid_only=False):
    pool = [i for i in ITEMS if i["city"] == city and i["category"] == cat and i["id"] not in exclude]
    if paid_only: pool = [i for i in pool if i["price_egp"] > 0]
    key = (lambda i: i["price_egp"]) if cheapest else (lambda i: (-_score(i, interests), i["price_egp"]))
    return sorted(pool, key=key)

def min_cost(city, days):
    nights = max(days - 1, 1)
    stay = min(i["price_egp"] for i in ITEMS if i["city"] == city and i["category"] == "stay")
    meal = min(i["price_egp"] for i in ITEMS if i["city"] == city and i["category"] == "meal")
    return stay * nights + meal * 2 * days

def build_plan(c, locked=(), rejected=()):
    """Returns list of {'item_id','day','role'}; keeps locked ids, skips rejected ids, stays within budget."""
    city, days, budget, ints = c["city"], c["days"], c["budget"], c["interests"]
    nights = max(days - 1, 1)
    used = set(rejected); plan = []; total = 0
    def add(item, day, role, mult=1):
        nonlocal total
        cost = item["price_egp"] * mult
        if total + cost <= budget:
            plan.append({"item_id": item["id"], "day": day, "role": role, "qty": mult}); used.add(item["id"]); total += cost; return True
        return False
    stays = pick(city, "stay", ints, used, paid_only=True)
    afford = [s for s in stays if s["price_egp"] * nights <= budget * 0.45]
    st = (afford or sorted(stays, key=lambda i: i["price_egp"]))[:1]
    if st: add(st[0], 1, "stay", nights)
    for day in range(1, days + 1):
        for meal in pick(city, "meal", ints, used)[:2]:
            add(meal, day, "meal")
        attr = pick(city, "free attraction", ints, used)[:1] + pick(city, "paid attraction", ints, used)[:1]
        for a in attr: add(a, day, "attraction")
        for t in pick(city, "transport", ints, used, cheapest=True)[:1]: add(t, day, "transport")
    return plan


def total_of(items):
    return sum(BY_ID[x["item_id"]]["price_egp"] * x.get("qty", 1) for x in items)


def alternatives(item_id, exclude=()):
    it = BY_ID[item_id]
    pool = [i for i in ITEMS if i["city"] == it["city"] and i["category"] == it["category"]
            and i["id"] != item_id and i["id"] not in exclude and i["price_egp"] > 0 == (it["price_egp"] == 0) or
            (i["city"] == it["city"] and i["category"] == it["category"] and i["id"] != item_id and i["id"] not in exclude)]
    pool = [i for i in pool if i["id"] != item_id and i["id"] not in exclude]
    return sorted(pool, key=lambda i: abs(i["price_egp"] - it["price_egp"]))[:3]
