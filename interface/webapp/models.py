from django.db import models
from django.utils import timezone
from datetime import timedelta


class Location(models.Model):
    class Meta:
        ordering = ('weight',)
        verbose_name_plural = "Locations"

    name = models.CharField(max_length=300, null=True, blank=True)
    zone = models.CharField(max_length=300, null=True, blank=True)
    weight = models.IntegerField(default=0, null=True, blank=True)
    color = models.CharField(max_length=300, null=True, blank=True)

    #def f(x):
    #    x

    def __str__(self):
        return self.name

class App(models.Model):
    class Meta:
        ordering = ('weight',)
        verbose_name_plural = "Apps"

    name = models.CharField(max_length=300, null=True, blank=True)
    location = models.CharField(max_length=300, null=True, blank=True)
    #zone = models.CharField(max_length=300, null=True, blank=True)
    weight = models.IntegerField(default=0, null=True, blank=True)
    color = models.CharField(max_length=300, null=True, blank=True)

    #def f(x):
    #    x

    def __str__(self):
        return self.name


class PendingUser(models.Model):
    class Meta:
        verbose_name_plural = "Pending Users"

    email = models.EmailField(unique=True)
    token_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    recovery_email = models.EmailField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    @classmethod
    def cleanup_expired(cls):
        return cls.objects.filter(expires_at__lt=timezone.now()).delete()

    def __str__(self):
        return f"{self.email} (expires: {self.expires_at})"
