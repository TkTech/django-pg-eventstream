import pytest
from django_pg_eventstream.models import Event

from product.models import Product


@pytest.mark.django_db
def test_creation():
    p = Product.objects.create(name="Test Product", quantity=10, price=100)

    print(p)
    print(Event.objects.count())