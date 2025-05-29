from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

class gear_value(models.Model):
    date = models.DateField(auto_now_add=True)  
    time = models.TimeField(auto_now_add=True,null=True,blank=True)  
    value = models.CharField(max_length=450)  
       

    def __str__(self):
        return f"{self.date} {self.time} {self.value}"

class HourlyGearValueStats(models.Model):
    hour_start = models.DateTimeField()
    max_rpm = models.FloatField()
    min_rpm = models.FloatField()

    def __str__(self):
        return f"Hourly stats starting at {self.hour_start}: max={self.max_rpm}, min={self.min_rpm}"

class DailyGearValueStats(models.Model):
    date = models.DateField(unique=True)  # Use date instead of datetime for uniqueness
    max_rpm = models.FloatField()
    min_rpm = models.FloatField()

    def __str__(self):
        return f"Daily stats for {self.date}: max={self.max_rpm}, min={self.min_rpm}"

class DataCycle(models.Model):
    start_time = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return f"DataCycle active: {self.active} starting at {self.start_time}"
