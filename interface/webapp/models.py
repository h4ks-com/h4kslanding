from datetime import timedelta

from colorfield.fields import ColorField
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

H4KS_PALETTE = [
    ('#5c9eff', 'Blue'),
    ('#ff8c4b', 'Orange'),
    ('#4ade80', 'Green'),
    ('#a371f7', 'Purple'),
    ('#f7cc71', 'Yellow'),
    ('#e05c5c', 'Red'),
    ('#5865f2', 'Blurple'),
    ('#58a6a0', 'Teal'),
]


class Location(models.Model):
    class Meta:
        ordering = ('weight',)
        verbose_name_plural = "Locations"

    name = models.CharField(max_length=300, null=True, blank=True)
    zone = models.CharField(max_length=300, null=True, blank=True)
    weight = models.IntegerField(default=0, null=True, blank=True)
    color = ColorField(blank=True, null=True, samples=H4KS_PALETTE)

    def __str__(self):
        return self.name

class App(models.Model):
    class Meta:
        ordering = ('weight',)
        verbose_name_plural = "Apps"

    name = models.CharField(max_length=300, null=True, blank=True)
    location = models.CharField(max_length=300, null=True, blank=True)
    weight = models.IntegerField(default=0, null=True, blank=True)
    color = ColorField(blank=True, null=True, samples=H4KS_PALETTE)

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
    timezone = models.CharField(max_length=64, blank=True, default='', help_text="User's preferred timezone (e.g., America/New_York)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class ChatLine(models.Model):
    class Meta:
        ordering = ['created_at']
        verbose_name_plural = "Chat Lines"

    nick = models.CharField(max_length=100)
    message = models.TextField()
    channel = models.CharField(max_length=100, default='#lobby')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"<{self.nick}> {self.message[:60]}"


class Announcement(models.Model):
    class Meta:
        ordering = ['-pinned', '-created_at']
        verbose_name_plural = "Announcements"

    SOURCE_CHOICES = [('admin', 'Admin'), ('bot', 'Bot')]

    body = models.TextField()
    author = models.CharField(max_length=100)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='admin')
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.author}] {self.body[:60]}"


class FeaturedProject(models.Model):
    class Meta:
        ordering = ['weight']
        verbose_name_plural = "Featured Projects"

    name = models.CharField(max_length=100)
    url = models.CharField(max_length=500)
    github_url = models.CharField(max_length=500, blank=True, help_text="GitHub repository URL, e.g. https://github.com/h4ks-com/CloudBot")
    description = models.TextField()
    tech_tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags, e.g. python, IRC, asyncio")
    image = models.ImageField(upload_to='projects/', blank=True, null=True, help_text="Project screenshot or logo")
    color = ColorField(blank=True, default='', samples=H4KS_PALETTE)
    weight = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def tags_list(self):
        return [t.strip() for t in self.tech_tags.split(',') if t.strip()]


class ApiToken(models.Model):
    class Meta:
        verbose_name_plural = "API Tokens"

    name = models.CharField(max_length=100)
    token_hash = models.CharField(max_length=64, db_index=True, help_text="SHA-256 hash of the raw token")
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
