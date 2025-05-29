from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from gearapp.models import HourlyGearValueStats, DailyGearValueStats

class Command(BaseCommand):
    help = 'Calculate daily max/min RPM from hourly stats and delete HourlyGearValueStats older than 24 hours'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        # Define time range for the entire 'yesterday' day (midnight to midnight)
        start_time = timezone.make_aware(datetime.combine(yesterday, datetime.min.time()))
        end_time = timezone.make_aware(datetime.combine(today, datetime.min.time()))

        # Get distinct topics from hourly stats
        topics = HourlyGearValueStats.objects.values_list('topic', flat=True).distinct()

        for topic in topics:
            # Get all hourly stats for 'topic' within yesterday's date range
            qs = HourlyGearValueStats.objects.filter(
                topic=topic,
                start_time__gte=start_time,
                end_time__lt=end_time
            )

            if not qs.exists():
                self.stdout.write(self.style.WARNING(f"No hourly stats for '{topic}' on {yesterday}, skipping."))
                continue

            # Calculate max and min RPM from all hourly stats for the day
            max_rpm = qs.order_by('-max_rpm').first().max_rpm
            min_rpm = qs.order_by('min_rpm').first().min_rpm

            # Save or update daily stats record
            DailyGearValueStats.objects.update_or_create(
                topic=topic,
                date=yesterday,
                defaults={
                    'max_rpm': max_rpm,
                    'min_rpm': min_rpm,
                }
            )

            self.stdout.write(self.style.SUCCESS(
                f"Saved daily stats for '{topic}' on {yesterday}: Max={max_rpm}, Min={min_rpm}"
            ))

        # Delete hourly stats older than 24 hours
        cutoff = timezone.now() - timedelta(hours=24)
        deleted_count, _ = HourlyGearValueStats.objects.filter(end_time__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} HourlyGearValueStats older than 24 hours."))
