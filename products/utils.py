from django.utils import timezone
from django.db.models import F
from products.models import Product, ProductDailyView

def record_view(product: Product):
    # 누적 증가
    Product.objects.filter(id=product.id).update(viewCount=F("viewCount") + 1)

    today = timezone.now().date()
    daily_view, created = ProductDailyView.objects.get_or_create(
        product=product, date=today
    )
    daily_view.views = F("views") + 1
    daily_view.save()
