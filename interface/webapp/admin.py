from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Location, App, PendingUser, UserProfile

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
    fields = ('logto_sub', 'ssh_public_key', 'created_at', 'updated_at')
    readonly_fields = ('logto_sub', 'created_at', 'updated_at')

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'has_ssh_key')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    actions = ['promote_to_admin']

    def has_ssh_key(self, obj):
        return obj.profile.has_ssh_key() if hasattr(obj, 'profile') else False
    has_ssh_key.boolean = True
    has_ssh_key.short_description = 'SSH Key'

    def promote_to_admin(self, request, queryset):
        if not request.user.has_perm('webapp.can_manage_users') and not request.user.is_superuser:
            self.message_user(request, "You don't have permission to promote users.", level='ERROR')
            return

        updated = queryset.update(is_staff=True)
        self.message_user(request, f"{updated} user(s) promoted to admin.")
    promote_to_admin.short_description = "Promote selected users to admin"

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
