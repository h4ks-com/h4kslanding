from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
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


class UserProfile(models.Model):
    class Meta:
        verbose_name_plural = "User Profiles"
        permissions = [
            ("can_manage_users", "Can manage users and promote to admin"),
        ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    logto_sub = models.CharField(max_length=255, unique=True, blank=True, null=True)
    ssh_public_key = models.TextField(blank=True, help_text="SSH public key for h4ks.com access")
    timezone = models.CharField(max_length=64, blank=True, default='', help_text="User's preferred timezone (e.g., America/New_York)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    def has_ssh_key(self):
        return bool(self.ssh_public_key.strip())


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
