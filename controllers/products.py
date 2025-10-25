from fastapi import APIRouter
from pydantic import BaseModel
import re
import os
import requests
from model.key import Key
import time
import random
import random
import time
import re
import requests
from math import ceil

router = APIRouter(prefix="/api/product", tags=["Products"])



class SearchRequest(BaseModel):
    name: str


APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN")

@router.post("/search")
async def search_product(request: SearchRequest):
    raw_name = request.name
    clean_name = raw_name.lower()
    clean_name = re.sub(r'[^a-z0-9\s]', '', clean_name)
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    product_name = clean_name.replace(" ", "+")

    search_url = f"https://www.ebay.com/sch/i.html?_nkw={product_name}&_sacat=0&LH_Complete=1&LH_Sold=1"
    actor_url = f"https://api.apify.com/v2/acts/3x1t~ebay-scraper-ppr/runs?token={APIFY_API_TOKEN}"

    apify_payload = {
    "startUrls": [{"url": search_url}],
    "maxItems": 400,
    "extendOutputFunction": "async ({data, item}) => return item;",
    "proxyConfiguration": {"useApifyProxy": True},
    "maxResults": 400,
    "maxPagesPerStartUrl": 50
}


    run_response = requests.post(actor_url, json=apify_payload).json()
    if "data" not in run_response:
        return {"error": "Failed to start Apify Actor", "details": run_response}

    run_id = run_response["data"]["id"]

    for _ in range(600):
        time.sleep(2)
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}"
        status = requests.get(status_url).json()["data"]["status"]
        if status in ["SUCCEEDED", "FAILED"]:
            break

    dataset_url = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_TOKEN}"
    items_response = requests.get(dataset_url).json()

    print(items_response)

    products = []

    for item in items_response:
        title = item.get("title", "")
        price_data = item.get("price", {})
        price_value = None
        if isinstance(price_data, dict):
            current = price_data.get("current", {})
            if isinstance(current, dict) and current.get("value"):
                price_value = float(current["value"])
            elif price_data.get("value"):
                price_value = float(price_data["value"])
        img = item.get("image", {}).get("url", "")
        url = item.get("url", "")
        match = re.search(r'CGC\b(?:\s+(?:SS|Signature\s+Series))?\s*[:\-]?\s*(\d{1,2}(?:\.\d)?)', title, re.IGNORECASE)
        grade = float(match.group(1)) if match else None
        products.append({
            "title": title,
            "price": f"${price_value}" if price_value else 0,
            "price_value": price_value,
            "image": img,
            "item_url": url,
            "cgc_grade": grade
        })
    if not products:
        return {"message": "No sold products found using Apify."}
    grade_ranges = {
        "Mint (M)": (10.0, 10.0),
        "Near Mint/Mint (NM/M)": (9.8, 9.9),
        "Near Mint (NM)": (9.4, 9.6),
        "Very Fine/Near Mint (VF/NM)": (9.0, 9.2),
        "Very Fine (VF)": (7.5, 8.5),
        "Fine (FN)": (6.5, 7.0),
        "Fine/Very Fine (FN/VF)": (5.5, 6.0),
        "Very Good/Fine (VG/FN)": (4.5, 5.0),
        "Very Good (VG)": (3.5, 4.0),
        "Good/Very Good (G/VG)": (2.5, 3.0),
        "Good (G)": (1.8, 2.0),
        "Fair/Good (F/G)": (1.0, 1.5),
        "Fair (F)": (0.5, 1.0),
        "Poor (P)": (0.1, 0.5),
    }
    categorized = {k: [] for k in grade_ranges}
    for product in products:
        grade = product.get("cgc_grade")
        if grade is None:
            continue
        for name, (low, high) in grade_ranges.items():
            if low <= grade <= high:
                product["range"] = f"{name} {low}, {high}"
                categorized[name].append(product)
                break
    result = []
    for name, (low, high) in grade_ranges.items():
        items = categorized[name]
        price = (
            f"${round(sum(p['price_value'] for p in items if p['price_value']) / len(items), 2)}"
            if items else "Not Available"
        )
        result.append({
            "range": f"{name} {low}, {high}",
            "average_price": price,
            "products": items
        })
    return {
        "searched_for": request.name,
        "grades_summary": result,
        "total_products": len(products),
    }
