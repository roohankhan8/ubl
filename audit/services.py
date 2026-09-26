from .models import AuditLog


def record_event(*, user, action, entity, metadata=None):
    return AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity.__class__.__name__,
        entity_id=str(entity.pk),
        metadata=metadata or {},
    )
