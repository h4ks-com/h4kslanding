import hashlib
import secrets

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.shortcuts import render

from .models import Location, App, PendingUser, UserProfile, Announcement, FeaturedProject, ApiToken, ChatLine


class BulkSetMixin:
    """Adds bulk-set actions for color and weight fields."""

    def _bulk_set(self, request, queryset, field_name, field_label, input_type, default=''):
        if 'apply' in request.POST:
            value = request.POST.get(field_name, default)
            if input_type == 'number':
                try:
                    value = int(value)
                except ValueError:
                    value = 0
            count = queryset.update(**{field_name: value})
            self.message_user(request, f"Updated {field_label} on {count} item(s).")
            return None
        return render(request, 'admin/bulk_set.html', {
            'field_name': field_name,
            'field_label': field_label,
            'input_type': input_type,
            'current_value': default,
            'action': f'bulk_set_{field_name}',
            'selected_ids': list(queryset.values_list('id', flat=True)),
            'count': queryset.count(),
        })

    def bulk_set_color(self, request, queryset):
        return self._bulk_set(request, queryset, 'color', 'Color', 'color', '#5c9eff')
    bulk_set_color.short_description = 'Set color'

    def bulk_set_weight(self, request, queryset):
        return self._bulk_set(request, queryset, 'weight', 'Weight', 'number', '0')
    bulk_set_weight.short_description = 'Set weight'

admin.site.site_header = "h4ks Admin"
admin.site.site_title = "h4ks Admin"

@admin.register(Location)
class LocationAdmin(BulkSetMixin, admin.ModelAdmin):
    list_display = ('name', 'zone', 'weight', 'color')
    list_filter = ('zone',)
    fields = ('name', 'zone', 'weight', 'color')
    actions = ['bulk_set_color', 'bulk_set_weight']

@admin.register(App)
class AppAdmin(BulkSetMixin, admin.ModelAdmin):
    list_display = ('name', 'location', 'weight', 'color')
    list_filter = ('location',)
    fields = ('name', 'location', 'weight', 'color')
    actions = ['bulk_set_color', 'bulk_set_weight']

@admin.register(PendingUser)
class PendingUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'expires_at', 'is_expired')
    list_filter = ('created_at', 'expires_at')
    readonly_fields = ('token_hash', 'created_at', 'expires_at')
    fields = ('email', 'recovery_email', 'token_hash', 'created_at', 'expires_at')

    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('logto_sub', 'timezone', 'created_at', 'updated_at')
    readonly_fields = ('logto_sub', 'created_at', 'updated_at')

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    actions = ['promote_to_admin']

    def promote_to_admin(self, request, queryset):
        if not request.user.has_perm('webapp.can_manage_users') and not request.user.is_superuser:
            self.message_user(request, "You don't have permission to promote users.", level='ERROR')
            return

        updated = queryset.update(is_staff=True)
        self.message_user(request, f"{updated} user(s) promoted to admin.")
    promote_to_admin.short_description = "Promote selected users to admin"

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('author', 'source', 'pinned', 'created_at', 'short_body')
    list_filter = ('pinned', 'source', 'created_at')
    search_fields = ('body', 'author')
    readonly_fields = ('created_at',)

    def short_body(self, obj):
        return obj.body[:80]
    short_body.short_description = 'Body'


@admin.register(FeaturedProject)
class FeaturedProjectAdmin(BulkSetMixin, admin.ModelAdmin):
    list_display = ('name', 'active', 'weight', 'url', 'github_url', 'tech_tags')
    list_filter = ('active',)
    search_fields = ('name', 'description')
    actions = ['bulk_set_color', 'bulk_set_weight']


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'created_at')
    list_filter = ('active',)
    readonly_fields = ('created_at',)
    fields = ('name', 'active', 'created_at')

    def save_model(self, request, obj, form, change):
        if not change:
            raw_token = secrets.token_hex(32)
            obj.token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            super().save_model(request, obj, form, change)
            self.message_user(
                request,
                f"API token created. Copy it now — it won't be shown again: {raw_token}",
            )
        else:
            super().save_model(request, obj, form, change)


@admin.register(ChatLine)
class ChatLineAdmin(admin.ModelAdmin):
    list_display = ('nick', 'channel', 'created_at', 'short_message')
    list_filter = ('channel', 'created_at')
    search_fields = ('nick', 'message')
    readonly_fields = ('created_at',)

    def short_message(self, obj):
        return obj.message[:80]
    short_message.short_description = 'Message'
