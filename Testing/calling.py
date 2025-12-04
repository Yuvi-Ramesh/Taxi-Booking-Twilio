from twilio.rest import Client
import json
import time
import os
import re

# ==== Twilio credentials ====
ACCOUNT_SID = "ACf284367f6a5e480ddcf4b510e8866b71"
AUTH_TOKEN = "68b42ccb9eb60e6fb616e219222f2428"
TWILIO_NUMBER = "+17166213120"
MY_PHONE_NUMBER = "+919952297502"  # Destination number for SMS

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ==== NGROK URL ====
NGROK_URL = "https://5ee14cfac0bd.ngrok-free.app"

# ==== Step 1: Make the call ====
call = client.calls.create(
    url=f"{NGROK_URL}/voice",
    to=MY_PHONE_NUMBER,
    from_=TWILIO_NUMBER
)

print(f"📞 Call initiated. SID: {call.sid}")

# Wait for booking collection (you can adjust time)

# ==== Step 2: Read latest booking from bookings.txt ====

def read_latest_booking():
    file_path = "bookings_2.txt"
    if not os.path.exists(file_path):
        print("❌ No bookings.txt file found.")
        return None

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read().strip()
        if not content:
            print("❌ No booking data found in file.")
            return None

        parts = content.split("\n" + "="*40 + "\n")
        latest_booking_str = parts[-1].strip()

        # Extract key-value pairs with regex
        matches = re.findall(r'"(.*?)":\s*"(.*?)"', latest_booking_str)
        if matches:
            booking_dict = {k: v.strip(". ").strip() for k, v in matches}
            return booking_dict
        else:
            print("❌ Failed to extract booking data.")
            return None

booking_data = read_latest_booking()

# ==== Step 3: Send booking confirmation SMS ====
if booking_data:
    message_body = (
        f"Taxi Booking Confirmed ✅\n"
        f"Name: {booking_data['name']}\n"
        f"Pickup: {booking_data['pickup_location']}\n"
        f"Drop: {booking_data['drop_location']}\n"
        f"Date: {booking_data['pickup_date']}\n"
        f"Time: {booking_data['pickup_time']}\n"
        f"Passengers: {booking_data['passenger_count']}\n"
        f"Vehicle: {booking_data['vehicle_type']}\n"
        f"Phone: {booking_data['phone_number']}"
    )

    try:
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_NUMBER,
            to=MY_PHONE_NUMBER
        )
        print(f"📩 SMS sent successfully. SID: {message.sid}")
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}")
else:
    print("⚠️ No valid booking data to send.")
