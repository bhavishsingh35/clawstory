from django.db import transaction
from django.utils import timezone

from orders.models import WebhookEvent


@transaction.atomic
def record_webhook_event(*, event):
    """
    Idempotently record an incoming webhook event.
    Safe against retries.
    """

    webhook, _ = WebhookEvent.objects.get_or_create(
        event_id=event["id"],
        defaults={
            "gateway": "stripe",
            "event_type": event["type"],
            "payload": event,
            "processed": False,
        },
    )
    return webhook


@transaction.atomic
def mark_webhook_processed(*, webhook):
    """
    Mark webhook as processed exactly once.
    """

    webhook = (
        WebhookEvent.objects
        .select_for_update()
        .get(pk=webhook.pk)
    )

    if webhook.processed:
        return

    webhook.processed = True
    webhook.processed_at = timezone.now()
    webhook.save(update_fields=["processed", "processed_at"])
