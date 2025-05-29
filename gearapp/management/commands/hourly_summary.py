from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from gearapp.models import gear_value, HourlyGearValueStats

class Command(BaseCommand):
    help = 'Calculate hourly min/max RPM and delete raw GearValue data older than 1 hour'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)

        # Get unique topics — assumes 'topic' field exists on gear_value model
        topics = gear_value.objects.values_list('topic', flat=True).distinct()

        for topic in topics:
            # Get last hour's data for this topic — assumes 'timestamp' field exists on gear_value model
            data_qs = gear_value.objects.filter(topic=topic, timestamp__gte=one_hour_ago, timestamp__lt=now)

            if not data_qs.exists():
                self.stdout.write(self.style.WARNING(f"No data for topic '{topic}' in the last hour."))
                continue

            # Convert values to float for min/max calculation
            values = [float(item.value) for item in data_qs if item.value.replace('.', '', 1).isdigit()]
            if not values:
                self.stdout.write(self.style.WARNING(f"No valid numeric 'value' for topic '{topic}' in the last hour."))
                continue

            max_rpm = max(values)
            min_rpm = min(values)

            # Save to hourly stats
            HourlyGearValueStats.objects.create(
                hour_start=one_hour_ago,
                max_rpm=max_rpm,
                min_rpm=min_rpm,
            )

            self.stdout.write(self.style.SUCCESS(
                f"Hourly stats saved for '{topic}' — Max: {max_rpm}, Min: {min_rpm}"))

        # Delete raw data older than 1 hour — assumes 'timestamp' field exists on gear_value model
        old_data = gear_value.objects.filter(timestamp__lt=one_hour_ago)
        deleted_count, _ = old_data.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} GearValue entries older than 1 hour."))
