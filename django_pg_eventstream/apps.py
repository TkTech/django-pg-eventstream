from django.apps import AppConfig
from django.db.models.signals import post_migrate

class EventStreamConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_pg_eventstream'
