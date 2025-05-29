# from django.utils import timezone
# from datetime import timedelta
# from .models import GearValue, HourlyGearValueStats, DailyGearValueStats, DataCycle

# def process_hourly_stats():
#     # Get current active cycle or create one
#     cycle = DataCycle.objects.filter(active=True).first()
#     if not cycle:
#         # No active cycle; start one from now
#         cycle = DataCycle.objects.create(start_time=timezone.now(), active=True)

#     start_time = cycle.start_time
#     now = timezone.now()
#     elapsed = now - start_time

#     # Calculate how many full hours have passed since cycle start
#     full_hours_passed = int(elapsed.total_seconds() // 3600)

#     for hour_index in range(full_hours_passed):
#         hour_start = start_time + timedelta(hours=hour_index)
#         hour_end = hour_start + timedelta(hours=1)

#         # Skip if hourly summary already exists
#         if HourlyGearValueStats.objects.filter(hour_start=hour_start).exists():
#             continue

#         # Get raw data in this hour
#         raw_values = GearValue.objects.filter(timestamp__gte=hour_start, timestamp__lt=hour_end)
#         if not raw_values.exists():
#             # No data for this hour, skip saving summary
#             continue

#         max_rpm = raw_values.order_by('-value').first().value
#         min_rpm = raw_values.order_by('value').first().value

#         # Save hourly summary
#         HourlyGearValueStats.objects.create(
#             hour_start=hour_start,
#             max_rpm=max_rpm,
#             min_rpm=min_rpm
#         )

#         # Delete raw data older than this hour
#         GearValue.objects.filter(timestamp__lt=hour_end).delete()

#     # If 24 hours have passed since cycle start, calculate daily stats and reset cycle
#     if full_hours_passed >= 24:
#         daily_date = start_time.date()
#         hourly_stats = HourlyGearValueStats.objects.filter(hour_start__gte=start_time, hour_start__lt=start_time + timedelta(days=1))

#         if hourly_stats.count() >= 24:
#             max_rpm = max(hs.max_rpm for hs in hourly_stats)
#             min_rpm = min(hs.min_rpm for hs in hourly_stats)

#             DailyGearValueStats.objects.update_or_create(
#                 date=daily_date,
#                 defaults={
#                     'max_rpm': max_rpm,
#                     'min_rpm': min_rpm
#                 }
#             )

#             # End current cycle and start a new one
#             cycle.active = False
#             cycle.save()
