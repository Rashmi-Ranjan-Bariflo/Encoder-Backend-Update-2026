import os
import sys
import time
import json
import threading
import traceback
from datetime import datetime

import paho.mqtt.client as mqtt
from telegram import Bot
from telegram.ext import Updater, CommandHandler

import django
from django.utils import timezone


# ================== Django Setup ==================

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gear_box.settings")
django.setup()

from gearapp.models import GearValue, GearRatio


# ================== Config ==================

MQTT_BROKER = "mqttbroker.bc-pl.com"
MQTT_PORT = 1883

MQTT_TOPICS = [
    "factory/gearbox1/input/rpm",
    "factory/gearbox1/out1/rpm",
    "factory/gearbox1/out2/rpm",
    "factory/gearbox1/out3/rpm",
    "factory/gearbox1/out4/rpm",
]

MQTT_USER = "mqttuser"
MQTT_PASSWORD = "Bfl@2025"

TELEGRAM_BOT_TOKEN = "7119219406:AAHsLe6kqLiQmJMeTPCnYR3rg15__lvr92k"
TELEGRAM_GROUPCHAT_IDS = [-1002559440335]

NO_DATA_THRESHOLD = 10
TELEGRAM_COOLDOWN = 60

# Buffer timeout (seconds)
BUFFER_TIMEOUT = 10


# ================== Topic Mapping ==================

TOPIC_ALIAS = {
    "factory/gearbox1/input/rpm": "Input_rpm",
    "factory/gearbox1/out1/rpm": "Output1_rpm",
    "factory/gearbox1/out2/rpm": "Output2_rpm",
    "factory/gearbox1/out3/rpm": "Output3_rpm",
    "factory/gearbox1/out4/rpm": "Output4_rpm",
}


# ================== Globals ==================

bot = Bot(token=TELEGRAM_BOT_TOKEN)

last_message_time = timezone.now()
last_telegram_alert = 0

# Buffers
data_buffer = {}
buffer_time = {}


# ================== Ratio Calculator ==================

def calculate_ratio_from_row(row):

    input_rpm = row["input"]
    out1 = row["out1"]
    out2 = row["out2"]
    out3 = row["out3"]
    out4 = row["out4"]
    dt = row["time"]

    if input_rpm <= 0:
        print("⚠️ Skipping ratio (input = 0):", dt)
        return

    # Prevent duplicate
    if GearRatio.objects.filter(timestamp=dt).exists():
        print("⚠️ Ratio already exists:", dt)
        return

    r1 = round(out1 / input_rpm, 4)
    r2 = round(out2 / input_rpm, 4)
    r3 = round(out3 / input_rpm, 4)
    r4 = round(out4 / input_rpm, 4)

    GearRatio.objects.create(
        timestamp=dt,
        input_rpm=input_rpm,
        output1_rpm=out1,
        output2_rpm=out2,
        output3_rpm=out3,
        output4_rpm=out4,
        ratio1=r1,
        ratio2=r2,
        ratio3=r3,
        ratio4=r4,
    )

    print("📊 Ratio Saved:", dt)


# ================== Telegram ==================

def send_telegram(msg):

    global last_telegram_alert

    now = time.time()

    if now - last_telegram_alert < TELEGRAM_COOLDOWN:
        return

    last_telegram_alert = now

    for cid in TELEGRAM_GROUPCHAT_IDS:
        try:
            bot.send_message(chat_id=cid, text=msg)
            print("✅ Telegram sent")
        except Exception as e:
            print("❌ Telegram error:", e)


# ================== Payload Parser ==================

def parse_payload(payload):

    # JSON
    try:
        data = json.loads(payload)

        ts = data.get("ts")
        rpm = data.get("rpm")

        if ts is not None and rpm is not None:
            return int(ts), float(rpm)

    except:
        pass

    # Plain float (fallback) - use server time if no timestamp provided
    try:
        rpm = float(payload)
        ts = int(datetime.now().timestamp() * 1000)  # Current time in milliseconds
        return ts, rpm

    except Exception as e:
        print(f"❌ Failed to parse payload '{payload}': {e}")
        return None, None


# ================== MQTT ==================

def on_connect(client, userdata, flags, rc):

    if rc == 0:
        print("✅ MQTT Connected")

        for t in MQTT_TOPICS:
            try:
                client.subscribe(t)
                print(f"✅ Subscribed: {t}")
            except Exception as e:
                print(f"❌ Failed to subscribe to {t}: {e}")

    else:
        error_codes = {
            1: "Incorrect protocol version",
            2: "Invalid client identifier",
            3: "Server unavailable",
            4: "Bad username or password",
            5: "Not authorised",
        }
        error_msg = error_codes.get(rc, f"Unknown error code {rc}")
        print(f"❌ MQTT Connection Failed ({rc}): {error_msg}")


def on_message(client, userdata, msg):

    global last_message_time
    global data_buffer
    global buffer_time

    try:

        payload = msg.payload.decode().strip()

        ts, rpm = parse_payload(payload)

        if rpm is None or ts is None:
            print(f"❌ Invalid payload: {payload} (ts={ts}, rpm={rpm})")
            return


        # Convert timestamp
        device_dt = timezone.make_aware(
            datetime.fromtimestamp(ts / 1000)
        )


        channel = TOPIC_ALIAS.get(msg.topic, msg.topic)


        # Save RPM
        GearValue.objects.create(
            timestamp=device_dt,
            channel=channel,
            rpm=rpm
        )

        print(f"✅ Saved {device_dt} | {channel} | {rpm}")


        # ================= BUFFER =================

        now = time.time()

        # group messages by second
        bucket = ts // 1000

        if bucket not in data_buffer:

            data_buffer[bucket] = {
                "input": None,
                "out1": None,
                "out2": None,
                "out3": None,
                "out4": None,
                "time": device_dt
            }

            buffer_time[bucket] = now


        row = data_buffer[bucket]


        # Store values
        if channel == "Input_rpm":
            row["input"] = rpm

        elif channel == "Output1_rpm":
            row["out1"] = rpm

        elif channel == "Output2_rpm":
            row["out2"] = rpm

        elif channel == "Output3_rpm":
            row["out3"] = rpm

        elif channel == "Output4_rpm":
            row["out4"] = rpm


        # ================= CHECK =================

        if all([
            row["input"] is not None,
            row["out1"] is not None,
            row["out2"] is not None,
            row["out3"] is not None,
            row["out4"] is not None,
        ]):

            calculate_ratio_from_row(row)

            # cleanup
            del data_buffer[bucket]
            del buffer_time[bucket]


        # ================= CLEAN OLD =================

        expired = []

        for k in buffer_time:

            if now - buffer_time[k] > BUFFER_TIMEOUT:
                expired.append(k)

        for k in expired:
            print("🗑️ Removing stale buffer:", k)
            del data_buffer[k]
            del buffer_time[k]


        last_message_time = timezone.now()


    except Exception as e:

        print(f"❌ MQTT error: {e}")
        traceback.print_exc()


# ================== MQTT Thread ==================

def mqtt_thread():

    client = mqtt.Client()

    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print(f"🔗 Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)

    except Exception as e:
        print(f"❌ MQTT connect error: {e}")
        traceback.print_exc()
        raise

    client.loop_start()

    print("🤖 MQTT Loop started")

    while True:
        try:
            diff = (timezone.now() - last_message_time).total_seconds()

            print(f"⏱️  Last data: {diff:.1f}s ago")

            if diff > NO_DATA_THRESHOLD:
                send_telegram("⚠️ MQTT: No data received")

            time.sleep(2)
        except Exception as e:
            print(f"❌ MQTT thread error: {e}")
            traceback.print_exc()
            time.sleep(2)


# ================== MQTT Connect (for Django Management Command) ==================

def mqtt_connect():
    """Start MQTT subscriber (for use in Django management command)"""
    print("=" * 60)
    print("🚀 MQTT SUBSCRIBER STARTING")
    print("=" * 60)
    print(f"📍 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"👤 Username: {MQTT_USER}")
    print(f"📡 Topics: {len(MQTT_TOPICS)} subscriptions")
    for topic in MQTT_TOPICS:
        print(f"   - {topic}")
    print("=" * 60)
    
    t1 = threading.Thread(target=mqtt_thread, daemon=False)  # Non-daemon to keep running
    t1.start()
    
    # Keep the process running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⛔ MQTT Connect stopped by user")
    except Exception as e:
        print(f"❌ MQTT Connect error: {e}")
        traceback.print_exc()
        raise


# ================== Telegram Commands ==================

def get_chat_id(update, context):

    cid = update.effective_chat.id

    update.message.reply_text(f"Chat ID: {cid}")

    print("Chat ID:", cid)

# ================== DB CLEANUP ==================

from datetime import timedelta

from datetime import timedelta

def cleanup_old_rows():

    while True:
        try:
            cutoff = timezone.now() - timedelta(hours=1)

            # Delete old GearValue rows
            deleted_values, _ = GearValue.objects.filter(
                timestamp__lt=cutoff
            ).delete()

            # Delete old GearRatio rows
            deleted_ratios, _ = GearRatio.objects.filter(
                timestamp__lt=cutoff
            ).delete()

            print(f"🧹 Deleted {deleted_values} GearValue rows older than 1 hour")
            print(f"🧹 Deleted {deleted_ratios} GearRatio rows older than 1 hour")

        except Exception as e:
            print("❌ Cleanup error:", e)

        # Run every 5 minutes
        time.sleep(300)

# ================== Main ==================

def main():

    # MQTT thread
    t1 = threading.Thread(target=mqtt_thread, daemon=True)
    t1.start()

    # DB cleanup thread
    t2 = threading.Thread(target=cleanup_old_rows, daemon=True)
    t2.start()

    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("getchatid", get_chat_id))


    print("🤖 Bot running")

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()