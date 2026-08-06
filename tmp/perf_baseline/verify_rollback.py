"""
서울 리전 Supabase DB에 실제로 rollback이 안전하게 동작하는지 확인하는 안전 검증 스크립트.
product_detail (GET /products/<id>/) 을 33회 호출하면 products.utils.record_view() 가
Product.viewCount 증가 + ProductDailyView row upsert를 수행한다.
이 스크립트는 transaction.atomic() + set_rollback(True) 로 감싼 뒤,
실행 전/후 스냅샷을 비교해서 정말로 변화가 없는지 검증한다.
애플리케이션 코드는 수정하지 않는다.
"""
import os
import sys

PROJECT_ROOT = "/Users/kimjeongyun/Desktop/Dasii/Backend"
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dasii_backend.settings")

import django  # noqa: E402

django.setup()

from django.db import connection, transaction  # noqa: E402
from django.utils import timezone  # noqa: E402
from django.db.models import Count  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from products.models import Product, ProductDailyView  # noqa: E402

client = APIClient(SERVER_NAME="127.0.0.1")


def snapshot(product_id):
    today = timezone.now().date()
    product = Product.objects.get(id=product_id)
    daily = ProductDailyView.objects.filter(product_id=product_id, date=today).first()
    return {
        "db_host": connection.settings_dict["HOST"],
        "product_view_count": product.viewCount,
        "daily_view_row_exists": daily is not None,
        "daily_view_value": daily.views if daily else None,
        "product_table_count": Product.objects.count(),
        "product_daily_view_table_count": ProductDailyView.objects.count(),
    }


def main():
    product = (
        Product.objects.annotate(rc=Count("reviews")).order_by("-rc", "id").first()
    )
    if product is None:
        print("[FAIL] DB에 Product가 없습니다.")
        return
    pid = product.id

    before = snapshot(pid)
    print(f"[INFO] 대상 product_id={pid}, DB host={before['db_host']}")
    print(f"[BEFORE] {before}")

    with transaction.atomic():
        for i in range(33):
            resp = client.get(f"/products/{pid}/")
            if resp.status_code != 200:
                print(f"[WARN] 요청 {i} status={resp.status_code}")
        # 이 블록에서 발생한 모든 변경을 강제로 rollback
        transaction.set_rollback(True)

    after = snapshot(pid)
    print(f"[AFTER]  {after}")

    diffs = {k: (before[k], after[k]) for k in before if before[k] != after[k]}
    if diffs:
        print(f"\n[FAIL] rollback 후에도 차이가 있습니다: {diffs}")
    else:
        print("\n[PASS] 33회 호출 후에도 DB 상태가 완전히 동일합니다. rollback 정상 동작 확인.")


if __name__ == "__main__":
    main()
