from django.http import HttpResponse, HttpResponseRedirect
from django.http import Http404, HttpResponseServerError

from django.shortcuts import render
from django.template import loader
from django.utils import timezone

from datetime import datetime
from .models import Location
from .models import App

index_template="index.html"

def index(request):
    template = loader.get_template(index_template)
    locations = Location.objects.all()
    apps = App.objects.all()
    context = { "locations": locations, "apps": apps, }
    return HttpResponse(template.render(context, request))
