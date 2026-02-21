import csv,json,time
from datetime import datetime,timedelta
from django.http import JsonResponse,HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from gearapp.models import GearValue,GearRatio

INPUT_CHANNEL="Input_rpm"
OUTPUT_CHANNELS=["Output1_rpm","Output2_rpm","Output3_rpm"]
TIME_MATCH_WINDOW_MS=5000

from django.db.models import F
from django.db.models.functions import Abs
from datetime import timedelta
from django.utils import timezone


# def calculate_and_store_ratio():

#     window = timedelta(milliseconds=TIME_MATCH_WINDOW_MS)

#     last_ratio = GearRatio.objects.order_by("-timestamp").first()

#     if last_ratio:
#         start_time = last_ratio.timestamp
#     else:
#         start_time = timezone.now() - timedelta(minutes=30)

#     end_time = timezone.now()


#     inputs = GearValue.objects.filter(
#         channel=INPUT_CHANNEL,
#         timestamp__gt=start_time,
#         timestamp__lte=end_time,
#         rpm__gt=0
#     ).order_by("timestamp")


#     for inp in inputs:

#         start = inp.timestamp - window
#         end = inp.timestamp + window

#         outputs = {}


#         for ch in OUTPUT_CHANNELS:

#             outputs[ch] = (
#                 GearValue.objects.filter(
#                     channel=ch,
#                     timestamp__range=(start, end),
#                     rpm__gt=0
#                 )
#                 # Find nearest timestamp
#                 .annotate(
#                     diff=Abs(F("timestamp") - inp.timestamp)
#                 )
#                 .order_by("diff")
#                 .first()
#             )


#         # Skip if any output missing
#         if not all(outputs.values()):
#             continue


#         # Calculate ratios
#         r1 = round(outputs["Output1_rpm"].rpm / inp.rpm, 4)
#         r2 = round(outputs["Output2_rpm"].rpm / inp.rpm, 4)
#         r3 = round(outputs["Output3_rpm"].rpm / inp.rpm, 4)


#         # Save matched ratio
#         GearRatio.objects.create(
#             timestamp=inp.timestamp,

#             input_rpm=inp.rpm,

#             output1_rpm=outputs["Output1_rpm"].rpm,
#             output2_rpm=outputs["Output2_rpm"].rpm,
#             output3_rpm=outputs["Output3_rpm"].rpm,

#             ratio1=r1,
#             ratio2=r2,
#             ratio3=r3
#         )


#         print(
#             f"✅ Ratio Saved | "
#             f"TS: {inp.timestamp} | "
#             f"In: {inp.rpm} | "
#             f"Out: {[o.rpm for o in outputs.values()]}"
# )

@csrf_exempt
def gear_dashboard_view(request):
    if request.method!="GET":
        return JsonResponse({"error":"Only GET allowed"},status=405)

    try:
        now=timezone.now()
        start_time=now-timedelta(minutes=15)

        rpm_data=GearValue.objects.filter(
            timestamp__range=(start_time,now)
        ).order_by("timestamp")

        ratio_data=GearRatio.objects.filter(
            timestamp__range=(start_time,now)
        ).order_by("timestamp")

        rpm_result=[
            {
                "timestamp":r.timestamp.isoformat(),
                "channel":r.channel,
                "rpm":r.rpm
            } for r in rpm_data
        ]

        ratio_result=[
            {
                "timestamp":r.timestamp.isoformat(),
                "input_rpm":r.input_rpm,
                "output1_rpm":r.output1_rpm,
                "output2_rpm":r.output2_rpm,
                "output3_rpm":r.output3_rpm,
                "ratio1":r.ratio1,
                "ratio2":r.ratio2,
                "ratio3":r.ratio3
            } for r in ratio_data
        ]

        return JsonResponse({
            "status":"running",
            "start_time":start_time.isoformat(),
            "end_time":now.isoformat(),
            "rpm_data":rpm_result,
            "ratio_data":ratio_result
        })

    except Exception as e:
        return JsonResponse({"error":str(e)},status=500)

@csrf_exempt
def filter_gear_value(request):
    if request.method!="GET":
        return JsonResponse({"error":"Only GET allowed"},status=405)

    from_date=request.GET.get("from_date")
    to_date=request.GET.get("to_date")

    if not from_date or not to_date:
        return JsonResponse({"error":"from_date and to_date required"},status=400)

    try:
        start=timezone.make_aware(datetime.strptime(from_date,"%Y-%m-%d"))
        end=timezone.make_aware(datetime.strptime(to_date,"%Y-%m-%d")+timedelta(days=1))
    except:
        return JsonResponse({"error":"Use YYYY-MM-DD format"},status=400)

    data=GearValue.objects.filter(
        timestamp__range=(start,end)
    ).order_by("timestamp")

    if not data.exists():
        return JsonResponse({"error":"No data found"},status=404)

    result=[
        {
            "timestamp":r.timestamp.isoformat(),
            "channel":r.channel,
            "rpm":r.rpm
        } for r in data
    ]

    return JsonResponse(result,safe=False)

@csrf_exempt
def filter_gear_ratio(request):
    if request.method!="GET":
        return JsonResponse({"error":"Only GET allowed"},status=405)

    from_date=request.GET.get("from_date")
    to_date=request.GET.get("to_date")

    if not from_date or not to_date:
        return JsonResponse({"error":"from_date and to_date required"},status=400)

    try:
        start=timezone.make_aware(datetime.strptime(from_date,"%Y-%m-%d"))
        end=timezone.make_aware(datetime.strptime(to_date,"%Y-%m-%d")+timedelta(days=1))
    except:
        return JsonResponse({"error":"Use YYYY-MM-DD format"},status=400)

    data=GearRatio.objects.filter(
        timestamp__range=(start,end)
    ).order_by("timestamp")

    if not data.exists():
        return JsonResponse({"error":"No ratio data found"},status=404)

    result=[
        {
            "timestamp":r.timestamp.isoformat(),
            "input_rpm":r.input_rpm,
            "output1_rpm":r.output1_rpm,
            "output2_rpm":r.output2_rpm,
            "output3_rpm":r.output3_rpm,
            "ratio1":r.ratio1,
            "ratio2":r.ratio2,
            "ratio3":r.ratio3
        } for r in data
    ]

    return JsonResponse(result,safe=False)

@csrf_exempt
def download_gear_value(request):
    if request.method!="GET":
        return JsonResponse({"error":"Only GET allowed"},status=405)

    data=GearValue.objects.all().order_by("-timestamp")

    if not data.exists():
        return JsonResponse({"error":"No data found"},status=404)

    last_time=data.first().timestamp
    start_time=last_time-timedelta(minutes=10)

    rows=data.filter(
        timestamp__range=(start_time,last_time)
    ).order_by("timestamp")

    response=HttpResponse(content_type="text/csv")
    response["Content-Disposition"]='attachment; filename="gear_rpm_data.csv"'

    writer=csv.writer(response)
    writer.writerow(["Timestamp","Channel","RPM"])

    for r in rows:
        writer.writerow([
            r.timestamp.isoformat(),
            r.channel,
            r.rpm
        ])

    return response

@csrf_exempt
def download_gear_ratio(request):
    if request.method!="GET":
        return JsonResponse({"error":"Only GET allowed"},status=405)

    data=GearRatio.objects.all().order_by("-timestamp")

    if not data.exists():
        return JsonResponse({"error":"No ratio data found"},status=404)

    last_time=data.first().timestamp
    start_time=last_time-timedelta(minutes=10)

    rows=data.filter(
        timestamp__range=(start_time,last_time)
    ).order_by("timestamp")

    response=HttpResponse(content_type="text/csv")
    response["Content-Disposition"]='attachment; filename="gear_ratio_data.csv"'

    writer=csv.writer(response)
    writer.writerow([
        "Timestamp",
        "Input RPM",
        "Output1 RPM",
        "Output2 RPM",
        "Output3 RPM",
        "Ratio1",
        "Ratio2",
        "Ratio3"
    ])

    for r in rows:
        writer.writerow([
            r.timestamp.isoformat(),
            r.input_rpm,
            r.output1_rpm,
            r.output2_rpm,
            r.output3_rpm,
            r.ratio1,
            r.ratio2,
            r.ratio3
        ])

    return response