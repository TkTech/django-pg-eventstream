from django.db import models
from django.conf import settings

class Event(models.Model):
    class Type(models.IntegerChoices):
        CREATE = 1, "Create"
        UPDATE = 2, "Update"
        DELETE = 3, "Delete"

    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.IntegerField(choices=Type.choices)
    model = models.CharField(max_length=100)
    object_pk = models.TextField()
    payload = models.JSONField()

    class Meta:
        db_table = getattr(settings, 'PG_EVENTSTREAM_TABLE', 'event_stream')
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['model']),
        ]