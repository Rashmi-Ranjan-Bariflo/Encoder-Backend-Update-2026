# from django.contrib import admin
# from .models import gear_value

# @admin.register(gear_value)
# class  gear_valueAdmin(admin.ModelAdmin):
#     list_display = ['date','time','value']


from django.contrib import admin
from .models import gear_value, HourlyGearValueStats, DailyGearValueStats, DataCycle
@admin.register(gear_value)
class gear_valueAdmin(admin.ModelAdmin):
    list_display = ['date', 'time', 'value']
    ordering = ['-date', '-time']
    readonly_fields = ['date', 'time']

@admin.register(HourlyGearValueStats)
class HourlyGearValueStatsAdmin(admin.ModelAdmin):
    list_display = ('hour_start', 'max_rpm', 'min_rpm')
    ordering = ('-hour_start',)

@admin.register(DailyGearValueStats)
class DailyGearValueStatsAdmin(admin.ModelAdmin):
    list_display = ('date', 'max_rpm', 'min_rpm')
    ordering = ('-date',)

@admin.register(DataCycle)
class DataCycleAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'active')
