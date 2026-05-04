from django.db import models

class Banner(models.Model):
    image_url = models.URLField()
    detail_image_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']