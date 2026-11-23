from django.db import models


class SyncEvent(models.Model):
    """Une resynchronisation du registre, déclenchée par GitHub ou par n8n."""

    source = models.CharField(max_length=16)     # github | n8n
    ref = models.CharField(max_length=200, blank=True)
    commit = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16)     # ok | error
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def to_dict(self) -> dict:
        return {"id": self.pk, "source": self.source, "ref": self.ref, "commit": self.commit,
                "status": self.status, "message": self.message,
                "created_at": self.created_at.isoformat() if self.created_at else None}
