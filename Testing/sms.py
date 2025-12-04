from twilio.rest import Client
import os
import re
import time

# ==== Twilio credentials ====
ACCOUNT_SID = "ACf284367f6a5e480ddcf4b510e8866b71"
AUTH_TOKEN = "68b42ccb9eb60e6fb616e219222f2428"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Twilio Sandbox WhatsApp number
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

# Your bookings file
BOOKINGS_FILE = "bookings_1.txt"

# ==== Helper: clean phone number ====
def format_number(number_str):
    """Extract digits and ensure proper E.164 format for India (+91xxxxxxxxxx)"""
    number = re.sub(r"[^\d]", "", number_str)
    if number.startswith("91"):
        number = "+" + number
    elif number.startswith("0"):
        number = "+91" + number[1:]
    elif not number.startswith("+"):
        number = "+" + number
    return number

# ==== Read bookings from file ====
def read_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        print("❌ No bookings file found.")
        return []

    with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            print("❌ No booking data in file.")
            return []

        parts = content.split("\n" + "="*40 + "\n")
        bookings = []
        for part in parts:
            matches = re.findall(r'"(.*?)":\s*"(.*?)"', part)
            if matches:
                booking = {k: v.strip(". ").strip() for k, v in matches}
                booking['phone_number'] = format_number(booking['phone_number'])
                bookings.append(booking)
        return bookings

# ==== Send WhatsApp message ====
def send_whatsapp(booking):
    to_number = f"whatsapp:{booking['phone_number']}"
    
    message_body = (
        f"Taxi Booking Confirmed ✅\n"
        f"Name: {booking['name']}\n"
        f"Pickup: {booking['pickup_location']}\n"
        f"Drop: {booking['drop_location']}\n"
        f"Date: {booking['pickup_date']}\n"
        f"Time: {booking['pickup_time']}\n"
        f"Passengers: {booking['passenger_count']}\n"
        f"Vehicle: {booking['vehicle_type']}\n"
        f"Phone: {booking['phone_number']}"
    )

    try:
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message_body,
            to=to_number
        )
        print(f"📩 WhatsApp sent to {booking['name']}. SID: {message.sid}")
        time.sleep(1)
    except Exception as e:
        print(f"❌ Failed to send WhatsApp to {booking['name']}: {e}")

# ==== Main execution ====
bookings = read_bookings()
print(f"ℹ️ Found {len(bookings)} booking(s) to send WhatsApp.")

for booking in bookings:
    send_whatsapp(booking)
