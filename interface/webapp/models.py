from django.db import models


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


