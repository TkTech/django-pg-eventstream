def track_events(*fields, pk='id'):
    def decorator(cls):
        if not hasattr(cls, '_eventstream_meta'):
            cls._eventstream_meta = {
                'tracked_fields': fields,
                'pk_field': pk
            }
        return cls
    return decorator
