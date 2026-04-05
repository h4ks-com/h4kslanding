from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Location, App, PendingUser, UserProfile, Announcement, FeaturedProject, ApiToken, ChatLine

admin.site.site_header = "h4ks Admin"
admin.site.site_title = "h4ks Admin"

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name','zone','weight','color',)
    list_filter = ('name','zone','weight','color',)
    fields = ('name', 'zone','weight','color',)

@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ('name','location','weight','color',)
    list_filter = ('name','location','weight','color',)
    fields = ('name', 'location','weight','color',)

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
class FeaturedProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'weight', 'url', 'github_url', 'tech_tags')
    list_filter = ('active',)
    search_fields = ('name', 'description')


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'created_at')
    list_filter = ('active',)
    readonly_fields = ('token_hash', 'created_at')
    fields = ('name', 'active', 'token_hash', 'created_at')


@admin.register(ChatLine)
class ChatLineAdmin(admin.ModelAdmin):
    list_display = ('nick', 'channel', 'created_at', 'short_message')
    list_filter = ('channel', 'created_at')
    search_fields = ('nick', 'message')
    readonly_fields = ('created_at',)

    def short_message(self, obj):
        return obj.message[:80]
    short_message.short_description = 'Message'
