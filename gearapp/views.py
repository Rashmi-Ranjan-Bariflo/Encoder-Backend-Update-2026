import json
import csv
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import gear_value
from django.http import JsonResponse
from django.utils.timezone import now, make_aware
from datetime import datetime
from datetime import timedelta
from gearapp.models import gear_value


@csrf_exempt
def gear_value_view(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method allowed'}, status=405)

    try:
        latest_entry = gear_value.objects.order_by('-date', '-time').first()
        if not latest_entry:
            return JsonResponse({'error': 'No gear_value data available.'}, status=404)

        # Build latest datetime from date and time
        latest_time = latest_entry.time or datetime.min.time()
        last_data_time = datetime.combine(latest_entry.date, latest_time)

        # Current system time (timezone-naive)
        current_time = now().replace(tzinfo=None)

        # Determine if machine is running (data received within last 2 minutes)
        time_difference = (current_time - last_data_time).total_seconds()
        is_running = time_difference <= 120  # within 2 minutes

        # If publish is running, fetch data from now - 15min to now
        # If publish is stopped, fetch data from last_data_time - 15min to last_data_time
        if is_running:
            end_time = current_time
        else:
            end_time = last_data_time  # use last known data timestamp

        start_time = end_time - timedelta(minutes=15)

        # Fetch entries that fall in this time window
        data_entries = gear_value.objects.filter(
            date__gte=start_time.date(),
            date__lte=end_time.date()
        ).order_by('date', 'time')

        result = []
        for entry in data_entries:
            entry_time = entry.time or datetime.min.time()
            entry_datetime = datetime.combine(entry.date, entry_time)

            if start_time <= entry_datetime <= end_time:
                result.append({
                    'date': entry.date.isoformat(),
                    'time': entry_time.strftime('%H:%M:%S'),
                    'value': entry.value
                })

        return JsonResponse({
            'status': 'running' if is_running else 'stopped',
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'end_time': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'data': result
        }, safe=False)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)
    



@csrf_exempt
def filter_gear_value(request):
    if request.method == 'GET':
        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')
        print(from_date_str,to_date_str)


        if not from_date_str or not to_date_str:
            return JsonResponse({'error': 'Both "from_date" and "to_date" are required.'}, status=400)

        try:
            start = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            print("111111111")
            end = datetime.strptime(to_date_str, '%Y-%m-%d').date()
            print("2222222")
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use yyyy-MM-dd.'}, status=400)

        values = gear_value.objects.filter(date__gte=start, date__lte=end).order_by('date', 'time')

        if not values.exists():
            return JsonResponse({'error': 'No data found for the selected date range.'}, status=404)

        result = [
            {
                'date': item.date.isoformat(),
                'time': item.time.strftime('%H:%M:%S'),
                'value': item.value 
            }
            for item in values
        ]

        return JsonResponse(result, safe=False)

    return JsonResponse({'error': 'Only GET allowed'}, status=405)


@csrf_exempt
def download_gear_value(request):
    if request.method == 'GET':
        # Get all gear values ordered by datetime
        all_data = gear_value.objects.all().order_by('-date', '-time')

        #latest time when the last data before stop
        if not all_data.exists():
            return JsonResponse({'error': 'No gear value data found.'}, status=404)

        # Get the most recent timestamp before machine stop
        last_item = all_data.first()
        stop_time = make_aware(datetime.combine(last_item.date, last_item.time))

        # Define the time range: 10 minutes before the machain stop
        start_time = stop_time - timedelta(minutes=10)

        # Filter data within this 10m 
        filtered = []
        for item in all_data:
            item_datetime = make_aware(datetime.combine(item.date, item.time))
            if start_time <= item_datetime <= stop_time:
                filtered.append((item.date, item.time, item.value))

        filtered.sort(key=lambda x: datetime.combine(x[0], x[1]))

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="gear_values_before_stop.csv"'

        writer = csv.writer(response)
        writer.writerow(['Date', 'Time', 'Value'])

        for date, time, value in filtered:
            writer.writerow([date.isoformat(), time.strftime('%H:%M:%S'), value])

        return response

    return JsonResponse({'error': 'Only GET allowed'}, status=405)
