from django.db import models

from django_pg_eventstream.decorators import track_events

@track_events("quantity")
class Product(models.Model):
    name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name
