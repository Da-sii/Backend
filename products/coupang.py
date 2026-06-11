import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import urlencode, quote

import requests
from django.conf import settings

_BASE_URL = "https://api-gateway.coupang.com"
_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/search"

def _build_authorization(method: str, query_string: str) -> tuple[str, str]:
    datetime_str = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    message = datetime_str + method + _PATH + query_string

    signature = hmac.new(
        settings.COUPANG_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    authorization = (
        f"CEA algorithm=HmacSHA256, access-key={settings.COUPANG_ACCESS_KEY}, "
        f"signed-date={datetime_str}, signature={signature}"
    )

    return authorization, datetime_str

def search_top_product_url(keyword: str) -> str | None:
    params = {"keyword": keyword, "limit": "1"}
    query_string = urlencode(sorted(params.items()), quote_via=quote)
    full_url = f"{_BASE_URL}{_PATH}?{query_string}"
    authorization, _ = _build_authorization("GET", query_string)

    response = requests.get(full_url, headers={"Authorization": authorization}, timeout=5)

    if response.status_code != 200:
        return None

    data = response.json()
    products = data.get("data", {}).get("productData", [])

    if not products:
        return None

    return products[0].get("productUrl")

def debug_search(keyword: str) -> dict:
    params = {"keyword": keyword}
    query_string = urlencode(sorted(params.items()), quote_via=quote)
    full_url = f"{_BASE_URL}{_PATH}?{query_string}"
    authorization, datetime_str = _build_authorization("GET", query_string)

    response = requests.get(full_url, headers={"Authorization": authorization}, timeout=5)

    return {
        "request": {
            "url": full_url,
            "signed_datetime": datetime_str,
            "authorization": authorization,
        },
        "response": {
            "status_code": response.status_code,
            "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
        },
    }
