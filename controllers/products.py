from fastapi import APIRouter
from pydantic import BaseModel
import re
import os
import requests
from model.key import Key

router = APIRouter(prefix="/api/product", tags=["Products"])


class SearchRequest(BaseModel):
    name: str
    min_grade: float = None
    max_grade: float = None
    category: str = None


@router.post("/search")
async def search_product(request: SearchRequest):
    product_name = request.name
    key = await Key.get_or_none()
    token = key.token if key else None
    api_key = key.api_key if key else None

    if not token and not api_key:
        return {
            "error": "Missing eBay credentials. Please set a token or API key first."
        }

    products = []

    try:
        if token:
            url = f"https://api.ebay.com/buy/browse/v1/item_summary/search?q={product_name}"
            headers = {
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                "Content-Type": "application/json",
            }
            response = requests.get(url, headers=headers)
            data = response.json()
            items = data.get("itemSummaries", [])
            for item in items:
                title = item.get("title", "")
                price_info = item.get("price", {})
                price = price_info.get("value")
                product = {
                    "title": title,
                    "price": f"${price}" if price else "N/A",
                    "price_value": float(price) if price else None,
                    "image": item.get("image", {}).get("imageUrl"),
                    "item_url": item.get("itemWebUrl"),
                }
                match = re.search(r"CGC\s*(\d+\.?\d*)", title)
                product["cgc_grade"] = float(match.group(1)) if match else None
                products.append(product)

        elif api_key:
            url = f"https://svcs.ebay.com/services/search/FindingService/v1"
            headers = {
                "X-EBAY-SOA-SECURITY-APPNAME": api_key,
                "X-EBAY-SOA-OPERATION-NAME": "findItemsByKeywords",
                "X-EBAY-SOA-REQUEST-DATA-FORMAT": "JSON",
                "Content-Type": "application/json",
            }
            payload = {
                "keywords": product_name,
                "paginationInput": {"entriesPerPage": 50, "pageNumber": 1},
            }
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            items = (
                data.get("findItemsByKeywordsResponse", [{}])[0]
                .get("searchResult", [{}])[0]
                .get("item", [])
            )
            for item in items:
                title = item.get("title", [None])[0]
                price_data = item.get("sellingStatus", [{}])[0].get(
                    "currentPrice", [{}]
                )[0]
                price = price_data.get("__value__")
                product = {
                    "title": title,
                    "price": f"${price}" if price else "N/A",
                    "price_value": float(price) if price else None,
                    "image": item.get("galleryURL", [None])[0],
                    "item_url": item.get("viewItemURL", [None])[0],
                }
                match = re.search(r"CGC\s*(\d+\.?\d*)", title or "")
                product["cgc_grade"] = float(match.group(1)) if match else None
                products.append(product)

        if not products:
            return {"message": "No items found for your search."}

    except Exception as e:
        return {"error": str(e)}

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
        "Good/Very Good (G/VG)": (2.5,3.0),
        "Good (G)": (1.8, 2.0),
        "Fair/Good (F/G)": (1.0, 1.5),
        "Fair (F)": (0.5, 1.0),
        "Poor (P)": (0.1, 0.5),
    }

    categorized = {k: [] for k in grade_ranges.keys()}

    for product in products:
        grade = product.get("cgc_grade")
        price = product.get("price_value")
        if grade is None or not price:
            continue
        for name, (low, high) in grade_ranges.items():
            if low <= grade <= high:
                product["range"] = f"{name} {low}, {high}"
                categorized[name].append(product)
                break

    result = []
    for name, items in categorized.items():
        if items:
            avg = round(sum(p["price_value"] for p in items) / len(items), 2)
            range_str = items[0][
                "range"
            ]  # take the range string from the first product
            result.append(
                {"range": range_str, "average_price": f"${avg}", "products": items}
            )

    return {
        "searched_for": product_name,
        "grades_summary": result,
        "total_products": len(products),
    }
