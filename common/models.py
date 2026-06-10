from django.db import models

class Banner(models.Model):
    image_url = models.URLField()
    order = models.PositiveIntegerField(default=1, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']


class BannerDetail(models.Model):
    banner = models.ForeignKey(Banner, related_name='details', on_delete=models.CASCADE)
    detail_image_url = models.URLField()
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('banner', 'order')]