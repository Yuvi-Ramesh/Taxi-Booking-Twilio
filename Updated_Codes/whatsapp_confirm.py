import re
from twilio.rest import Client
from pymongo import MongoClient
from urllib.parse import quote_plus

# ==== Twilio credentials ====
ACCOUNT_SID = "ACf284367f6a5e480ddcf4b510e8866b71"
AUTH_TOKEN = "68b42ccb9eb60e6fb616e219222f2428"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"  # Twilio Sandbox number
TO_NUMBER = "whatsapp:+919952297502"  # Your WhatsApp number

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ==== MongoDB credentials ====
mongo_username = "yuva2"
mongo_raw_password = "yuva123"
mongo_password = quote_plus(mongo_raw_password)

MONGO_URI = (
    f"mongodb+srv://{mongo_username}:{mongo_password}"
    "@cluster0.lujyqyz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)

# Connect to MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["TaxiBooking"]   # <-- change if your DB name differs
collection = db["Booking"]            # <-- change if your collection name differs

# ==== Function to search booking by phone ====
def find_booking(phone_number):
    try:
        booking = collection.find_one({"phone_number": {"$regex": phone_number}})
        return booking
    except Exception as e:
        print(f"⚠️ MongoDB Error: {e}")
        return None

# ==== Function to send WhatsApp message ====
def send_whatsapp_message(to, message):
    try:
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=to
        )
        print(f"✅ WhatsApp message sent. SID: {msg.sid}")
    except Exception as e:
        print(f"❌ Failed to send WhatsApp message: {e}")

# ==== Main ====
if __name__ == "__main__":
    # Number to search
    search_number = "9952297502"

    # Lookup booking
    booking = find_booking(search_number)

    if booking:
        response_message = (
            f"🚖 Booking Confirmation!\n\n"
            f"📌 Name: {booking['name']}\n"
            f"📞 Phone: {booking['phone_number']}\n"
            f"📍 From: {booking['pickup_location']}\n"
            f"➡️  To: {booking['drop_location']}\n"
            f"📅 Date: {booking['pickup_date']} at {booking['pickup_time']}\n"
            f"👥 Passengers: {booking['passenger_count']}\n"
            f"🚗 Vehicle: {booking['vehicle_type']}\n"
            f"👩‍✈️  Driver: {booking['driver']['name']} ({booking['driver']['phone']})\n"
            f"💰 Cost: ₹{booking['trip_cost']}\n"
        )
        print(response_message)
        send_whatsapp_message(TO_NUMBER, response_message)
    else:
        print("⚠️ No booking found.")
        send_whatsapp_message(TO_NUMBER, "⚠️ No booking found for the given number.")
