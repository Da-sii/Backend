"""
Dasii Backend - read-only API 성능 baseline 측정 스크립트

- 애플리케이션 코드(views/serializers/models)는 전혀 수정하지 않는다.
- 측정 구간 전체를 하나의 실제 트랜잭션(transaction.atomic())으로 감싸고 끝에서
  transaction.set_rollback(True) 로 강제 rollback 해서 원래 DB 상태로 되돌린다.
- 5개 엔드포인트가 끝날 때마다, 메인 트랜잭션과 완전히 분리된 별도 DB 커넥션("checkpoint" 별칭)으로
  product.viewCount / product_daily_view 총 행수를 읽어서 baseline과 일치하는지 확인한다.
  (같은 트랜잭션 안에서 읽으면 우리 자신의 uncommitted 변경이 보여서 의미가 없으므로 반드시 별도 커넥션 사용)
- 체크포인트 불일치나 DB 커넥션 에러가 발생하면 즉시 중단하고, 별도 커넥션으로 다시 한 번
  최종 상태를 확인한 뒤 지금까지의 결과와 함께 보고한다. 자동 재시도는 하지 않는다.
- 인증이 필요한 엔드포인트(user_reviews, random_products)는 비밀번호 로그인을 쓰지 않고,
  전용 벤치마크 테스트 계정을 ORM으로 get_or_create 한 뒤 users.utils.generate_jwt_tokens_with_metadata
  로 서버와 동일한 방식의 JWT를 직접 발급해서 사용한다. 이 테스트 계정 생성/재사용은
  (재사용 목적으로) 별도의 커밋되는 트랜잭션에서 실행되어 rollback 대상이 아니다.
- POST/PUT/DELETE류, 쿠팡 리다이렉트(외부 API)는 이번 측정 대상에서 제외한다.

실행 (DB는 환경변수로 override, .env는 건드리지 않음):
    cd /Users/kimjeongyun/Desktop/Dasii/Backend
    source .venv/bin/activate
    DB_NAME=postgres DB_USER=postgres.xxx DB_PASSWORD=xxx \
        DB_HOST=aws-1-ap-northeast-2.pooler.supabase.com DB_PORT=5432 \
        python tmp/perf_baseline/benchmark_endpoints.py [--label before]
"""
import os
import re
import sys
import json
import time
import io
import argparse
import contextlib
import statistics

PROJECT_ROOT = "/Users/kimjeongyun/Desktop/Dasii/Backend"
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dasii_backend.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection, connections, transaction  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402
from django.db.models import Count  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from products.models import Product, ProductDailyView, IngredientGuide  # noqa: E402
from review.models import Review  # noqa: E402
from users.utils import generate_jwt_tokens_with_metadata  # noqa: E402

WARMUP = 3
ITERATIONS = 30
N1_TEMPLATE_THRESHOLD = 3  # 같은 형태의 쿼리가 이 횟수 이상 반복되면 N+1 의심
CHECKPOINT_EVERY = 5  # 몇 개 엔드포인트마다 외부 커넥션으로 스냅샷 검증할지

BENCHMARK_USER_EMAIL = "benchmark.baseline@dasii.local"

client = APIClient(SERVER_NAME="127.0.0.1")


def normalize_sql(sql):
    sql = re.sub(r"'[^']*'", "?", sql)
    sql = re.sub(r"\b\d+\b", "?", sql)
    return sql.strip()


def detect_n1(queries):
    templates = {}
    for q in queries:
        key = normalize_sql(q["sql"])
        templates[key] = templates.get(key, 0) + 1
    suspects = [(tpl, cnt) for tpl, cnt in templates.items() if cnt >= N1_TEMPLATE_THRESHOLD]
    suspects.sort(key=lambda x: -x[1])
    return suspects


def percentile(sorted_vals, pct):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * pct
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def run_endpoint(name, method, path, auth_headers=None, params=None):
    extra = dict(auth_headers) if auth_headers else {}
    call = getattr(client, method.lower())
    quiet = io.StringIO()

    with contextlib.redirect_stdout(quiet):
        for _ in range(WARMUP):
            call(path, params or {}, **extra)

    durations = []
    query_counts = []
    query_times = []
    last_queries = []
    status_code = None

    for _ in range(ITERATIONS):
        with CaptureQueriesContext(connection) as ctx:
            t0 = time.perf_counter()
            with contextlib.redirect_stdout(quiet):
                resp = call(path, params or {}, **extra)
            durations.append((time.perf_counter() - t0) * 1000)
        status_code = resp.status_code
        qlist = ctx.captured_queries
        query_counts.append(len(qlist))
        query_times.append(sum(float(q["time"]) for q in qlist) * 1000)
        last_queries = qlist

    durations.sort()
    n1_suspects = detect_n1(last_queries)

    return {
        "name": name,
        "method": method,
        "path": path,
        "status_code": status_code,
        "avg_ms": round(statistics.mean(durations), 2),
        "p50_ms": round(percentile(durations, 0.50), 2),
        "p95_ms": round(percentile(durations, 0.95), 2),
        "avg_query_count": round(statistics.mean(query_counts), 1),
        "avg_query_time_ms": round(statistics.mean(query_times), 2),
        "n1_suspects": [{"template": t, "count": c} for t, c in n1_suspects[:3]],
    }


def get_or_create_benchmark_user():
    User = get_user_model()
    user, created = User.objects.get_or_create(
        email=BENCHMARK_USER_EMAIL,
        defaults={
            "nickname": "benchmark_baseline",
            "phone_number": "010-0000-0000",
            "is_terms_agreed": True,
            "is_active": True,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user, created


def get_auth_headers():
    user, created = get_or_create_benchmark_user()
    if created:
        print(f"[INFO] 벤치마크 전용 테스트 계정 신규 생성: {user.email} (id={user.id})")
    else:
        print(f"[INFO] 기존 벤치마크 전용 테스트 계정 재사용: {user.email} (id={user.id})")
    tokens = generate_jwt_tokens_with_metadata(user, token_type="email")
    return {"HTTP_AUTHORIZATION": f"Bearer {tokens['access']}"}


def pick_fixture_ids():
    ids = {}
    product = (
        Product.objects.annotate(rc=Count("reviews"))
        .order_by("-rc", "id")
        .first()
    )
    ids["product_id"] = product.id if product else None

    review = Review.objects.order_by("-id").first()
    ids["review_id"] = review.id if review else None

    guide = IngredientGuide.objects.select_related("ingredient").first()
    ids["guide_id"] = guide.id if guide else None

    return ids


def ensure_checkpoint_alias():
    """
    메인 트랜잭션과 완전히 분리된 DB 커넥션 별칭을 하나 추가한다.
    같은 접속 정보를 쓰지만 별도의 물리 커넥션이라, 메인 트랜잭션이 아직
    커밋/롤백되지 않은 상태에서도 '외부에서 지금 보이는 실제 값'을 읽을 수 있다.
    """
    if "checkpoint" not in settings.DATABASES:
        settings.DATABASES["checkpoint"] = dict(settings.DATABASES["default"])


def external_snapshot(product_id):
    ensure_checkpoint_alias()
    try:
        product = Product.objects.using("checkpoint").get(id=product_id)
        daily_count = ProductDailyView.objects.using("checkpoint").count()
        return {"view_count": product.viewCount, "daily_view_row_count": daily_count}
    finally:
        connections["checkpoint"].close()


def checkpoint_matches(snap_a, snap_b):
    return snap_a == snap_b


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="before", help="결과 파일 라벨 (예: before / after)")
    args = parser.parse_args()

    results = []
    checkpoints = []
    skipped = []
    aborted = False
    abort_reason = None

    # 1) 테스트 계정 생성/조회: 완전히 별도로 커밋되는 트랜잭션 (재사용 목적으로 실제 영속화)
    with transaction.atomic():
        auth_headers = get_auth_headers()

    ids = pick_fixture_ids()
    print(f"[INFO] 사용 fixture ids: {ids}")

    baseline_snapshot = None
    if ids["product_id"] is not None:
        baseline_snapshot = external_snapshot(ids["product_id"])
        print(f"[INFO] 체크포인트 baseline (별도 커넥션으로 측정): {baseline_snapshot}")
    else:
        print("[WARN] Product가 없어 체크포인트 검증을 건너뜁니다.")

    # 2) 엔드포인트 실행 계획을 먼저 통째로 만든 뒤, 하나의 atomic 블록 안에서 순서대로 실행
    endpoint_plan = [
        ("product_ranking", "GET", "/products/ranking/", {"period": "daily"}, False),
        ("product_ranking_category", "GET", "/products/ranking/category/", {}, False),
        ("product_list", "GET", "/products/list/", {}, False),
        ("product_category", "GET", "/products/category/", {}, False),
        ("product_search", "GET", "/products/search/", {}, False),
        ("product_main", "GET", "/products/main/", {}, False),
        ("banner_list", "GET", "/banners/", {}, False),
        ("ingredient_guide_list", "GET", "/ingredients/guides/", {}, False),
        ("mypage_user_info", "GET", "/auth/mypage/", {}, False),
    ]

    if ids["product_id"] is not None:
        pid = ids["product_id"]
        endpoint_plan += [
            ("product_detail", "GET", f"/products/{pid}/", {}, False),
            ("review_list", "GET", f"/review/product/{pid}/reviews/0/", {}, False),
            ("review_product_images", "GET", f"/review/product/{pid}/images/0/", {}, False),
            ("review_rating_stats", "GET", f"/review/product/{pid}/rating/", {}, False),
            ("review_user_check", "GET", f"/review/product/{pid}/check/", {}, False),
        ]
    else:
        skipped.append("product_detail/review_* : DB에 Product 없음")

    if ids["guide_id"] is not None:
        gid = ids["guide_id"]
        endpoint_plan.append(
            ("ingredient_guide_detail", "GET", f"/ingredients/guides/{gid}/", {}, False)
        )
    else:
        skipped.append("ingredient_guide_detail : DB에 IngredientGuide 없음")

    if ids["review_id"] is not None:
        rid = ids["review_id"]
        endpoint_plan.append(("review_detail", "GET", f"/review/detail/{rid}/", {}, False))
    else:
        skipped.append("review_detail : DB에 Review 없음")

    endpoint_plan.append(("user_reviews", "GET", "/review/myReviews/0/", {}, True))
    endpoint_plan.append(("random_products", "GET", "/review/random-products/", {}, True))

    skipped.append("product_coupang_redirect : 실제 외부 쿠팡 API 호출이라 baseline에서 제외")
    skipped.append("POST/PUT/DELETE류(리뷰 작성/수정/삭제, 회원가입, 로그인 등) : 반복 호출 시 데이터 오염 유발이라 제외")

    total = len(endpoint_plan)

    # 3) 측정 구간 전체를 하나의 실제 트랜잭션으로 감싼다.
    #    주의: transaction.savepoint()/savepoint_rollback()는 atomic() 없이 단독 호출하면
    #    Django 기본 autocommit 모드에서 아무 일도 하지 않고 조용히 무시된다(과거 스크립트의 버그).
    #    반드시 transaction.atomic() 안에서 set_rollback(True)를 써야 실제로 롤백된다.
    try:
        with transaction.atomic():
            for idx, (name, method, path, params, use_auth) in enumerate(endpoint_plan, start=1):
                print(f"[RUN {idx}/{total}] {name}")
                headers = auth_headers if use_auth else None
                results.append(run_endpoint(name, method, path, auth_headers=headers, params=params))

                if baseline_snapshot is not None and idx % CHECKPOINT_EVERY == 0:
                    snap = external_snapshot(ids["product_id"])
                    ok = checkpoint_matches(baseline_snapshot, snap)
                    checkpoints.append({"after_n": idx, "snapshot": snap, "ok": ok})
                    print(f"[CHECKPOINT after {idx}/{total}] {snap} vs baseline {baseline_snapshot} "
                          f"-> {'OK' if ok else 'MISMATCH!!'}")
                    if not ok:
                        raise RuntimeError(
                            f"체크포인트 불일치 감지 (endpoint #{idx}: {name}): "
                            f"baseline={baseline_snapshot}, now={snap}"
                        )

            transaction.set_rollback(True)

    except Exception as e:
        aborted = True
        abort_reason = f"{type(e).__name__}: {e}"
        print(f"\n[ERROR] 측정 중단됨: {abort_reason}")
        print(f"[INFO] 완료된 엔드포인트: {len(results)}/{total} (이후 항목은 미실행)")
        print("[INFO] atomic 블록을 벗어나며 지금까지의 DB 변경은 Django에 의해 자동 rollback 됩니다 "
              "(연결 자체가 끊긴 경우 Postgres가 세션 종료 시 uncommitted 트랜잭션을 서버 측에서 폐기하므로 별도 조치가 불필요합니다).")

    # 4) 최종 상태를 별도 커넥션으로 다시 확인
    final_snapshot = None
    final_ok = None
    if baseline_snapshot is not None:
        try:
            final_snapshot = external_snapshot(ids["product_id"])
            final_ok = checkpoint_matches(baseline_snapshot, final_snapshot)
        except Exception as e:
            print(f"[WARN] 최종 체크포인트 확인 실패: {e}")

    if final_ok is True:
        print(f"[INFO] 최종 확인: DB 상태가 baseline과 완전히 동일합니다 ({final_snapshot}). rollback 정상.")
    elif final_ok is False:
        print(f"[FAIL] 최종 확인: DB 상태가 baseline과 다릅니다! baseline={baseline_snapshot}, final={final_snapshot}")

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, f"benchmark_results_{args.label}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "label": args.label,
                "status": "aborted" if aborted else "completed",
                "abort_reason": abort_reason,
                "completed_count": len(results),
                "planned_count": total,
                "baseline_snapshot": baseline_snapshot,
                "checkpoints": checkpoints,
                "final_snapshot": final_snapshot,
                "final_snapshot_ok": final_ok,
                "results": results,
                "skipped": skipped,
            },
            f, ensure_ascii=False, indent=2,
        )
    print(f"\n[INFO] 결과 저장: {out_path}")

    if not results:
        return

    print("\n=== 응답시간 느린 순 ===")
    print(f"{'name':28s} {'status':>6s} {'avg(ms)':>9s} {'p50(ms)':>9s} {'p95(ms)':>9s} {'qcount':>7s} {'qtime(ms)':>10s}  n1")
    for r in sorted(results, key=lambda x: -x["avg_ms"]):
        n1_flag = "N+1?" if r["n1_suspects"] else ""
        warn = "" if 200 <= r["status_code"] < 300 else " <<< NON-2xx!"
        print(f"{r['name']:28s} {r['status_code']:6d} {r['avg_ms']:9.2f} {r['p50_ms']:9.2f} {r['p95_ms']:9.2f} "
              f"{r['avg_query_count']:7.1f} {r['avg_query_time_ms']:10.2f}  {n1_flag}{warn}")

    print("\n=== 쿼리 개수 많은 순 ===")
    print(f"{'name':28s} {'qcount':>7s} {'qtime(ms)':>10s} {'avg(ms)':>9s}  n1")
    for r in sorted(results, key=lambda x: -x["avg_query_count"]):
        n1_flag = "N+1?" if r["n1_suspects"] else ""
        print(f"{r['name']:28s} {r['avg_query_count']:7.1f} {r['avg_query_time_ms']:10.2f} "
              f"{r['avg_ms']:9.2f}  {n1_flag}")

    if skipped:
        print("\n=== 건너뛴/제외 항목 ===")
        for s in skipped:
            print(f"- {s}")

    if aborted:
        print(f"\n[SUMMARY] 중단됨: {abort_reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
