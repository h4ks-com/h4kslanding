from django.contrib import admin

from django.contrib import admin

admin.site.site_header = "h4ks Landing Page";
admin.site.site_title = "h4ks Landing Page";

from .models import Location
from .models import App

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

