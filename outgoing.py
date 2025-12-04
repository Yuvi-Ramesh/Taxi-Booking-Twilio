from flask import Flask, request, Response
import json
from twilio.rest import Client
from pymongo import MongoClient
from urllib.parse import quote_plus
import urllib.parse
import re
import datetime
import time
import google.generativeai as genai

app = Flask(__name__)

# Twilio credentials
ACCOUNT_SID = "ACf284367f6a5e480ddcf4b510e8866b71"
AUTH_TOKEN = "68b42ccb9eb60e6fb616e219222f2428"
TWILIO_NUMBER = "+17166213120"
MY_PHONE_NUMBER = "+919952297502"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"
GOOGLE_API_KEY = "AIzaSyAzqaBvcftWKowcFptSmTGntn4_iyTV0DA"

client = Client(ACCOUNT_SID, AUTH_TOKEN)
genai.configure(api_key="AIzaSyCz6m0DKuqtwb_IH0-lj9M-WOcB07xTuj8")

# MongoDB connection
mongo_username = "yuva2"
mongo_raw_password = "yuva123"
mongo_password = quote_plus(mongo_raw_password)

MONGO_CONNECTION_STRING = (
    f"mongodb+srv://{mongo_username}:{mongo_password}"
    "@cluster0.lujyqyz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)

DB_NAME = "TaxiBooking"
BOOKING_COLLECTION = "Booking"
DRIVERS_COLLECTION = "Drivers"

mongo_client = MongoClient(MONGO_CONNECTION_STRING)
db = mongo_client[DB_NAME]
bookings_col = db[BOOKING_COLLECTION]
drivers_col = db[DRIVERS_COLLECTION]

# Store booking details in memory for current call
booking_data = {
    "name": None,
    "phone_number": None,
    "pickup_location": None,
    "drop_location": None,
    "pickup_date": None,
    "pickup_time": None,
    "passenger_count": None,
    "vehicle_type": None
}

# Friendly questions
question_texts = {
    "name": "May I know your name?",
    "phone_number": "Please tell me your contact number, including country code.",
    "pickup_location": "Where should we pick you up?",
    "drop_location": "Where would you like to go?",
    "pickup_date": "On which date would you like to travel?",
    "pickup_time": "At what time should the taxi arrive?",
    "passenger_count": "How many passengers will be travelling?",
    "vehicle_type": "What type of vehicle do you prefer? For example, sedan, SUV, or auto."
}
questions = list(booking_data.keys())

# ---------------- Utility Functions ---------------- #

def build_google_maps_link(pickup: str, drop: str) -> str:
    if not pickup or not drop:
        return ""
    origin = urllib.parse.quote_plus(str(pickup).strip())
    destination = urllib.parse.quote_plus(str(drop).strip())
    return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}"

def estimate_trip_with_gemini(pickup, drop, vehicle_type):
    prompt = f"""
    You are a taxi fare estimator.
    Pickup: {pickup}
    Drop: {drop}
    Vehicle type: {vehicle_type}

    Respond ONLY with valid JSON in this format:
    {{
        "distance_km": <number>,
        "duration_min": <number>
    }}
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        reply = response.text.strip()
        reply = re.sub(r"```json|```", "", reply).strip()
        data = json.loads(reply)
        distance = float(data.get("distance_km", 10))
        duration = float(data.get("duration_min", 20))
        return distance, duration
    except Exception as e:
        print("❌ Gemini estimation error:", e)
        return 10, 20

def calculate_trip_cost(pickup, drop, vehicle_type, pickup_date=None, pickup_time=None):
    if not pickup or not drop or not vehicle_type:
        return None
    base_fare = {"sedan": 200, "suv": 300, "auto": 100}
    per_km_rate = {"sedan": 15, "suv": 20, "auto": 10}
    per_min_rate = {"sedan": 2, "suv": 3, "auto": 1}
    try:
        distance_km, duration_min = estimate_trip_with_gemini(pickup, drop, vehicle_type)
        fare = base_fare.get(vehicle_type.lower(), 150)
        fare += distance_km * per_km_rate.get(vehicle_type.lower(), 12)
        fare += duration_min * per_min_rate.get(vehicle_type.lower(), 1)
        return round(fare, 2)
    except Exception as e:
        print("❌ Error calculating cost:", e)
        return None

def assign_driver():
    driver = list(drivers_col.aggregate([{ "$sample": { "size": 1 } }]))
    if driver:
        return {"name": driver[0].get("name"), "phone": driver[0].get("phone")}
    else:
        return {"name": "Default Driver", "phone": "+919000000000"}

def format_number(number_str):
    if not number_str:
        return ""
    digits = re.sub(r"\D", "", number_str)
    if len(digits) >= 12:
        digits = digits[-12:]  # e.g., 919952297502
    elif len(digits) >= 10:
        digits = "91" + digits[-10:]
    return "+" + digits

def send_booking_whatsapp(booking):
    driver = booking.get("driver", {})
    try:
        to_number = f"whatsapp:{format_number(booking.get('phone_number'))}"
        maps_link = booking.get("maps_link") or build_google_maps_link(
            booking.get("pickup_location"), booking.get("drop_location")
        )
        message_body = (
            f"🚖 *Taxi Booking Confirmed!*\n\n"
            f"👤 Name: {booking.get('name')}\n"
            f"📍 Pickup: {booking.get('pickup_location')}\n"
            f"🏁 Drop: {booking.get('drop_location')}\n"
            f"📅 Date: {booking.get('pickup_date')}\n"
            f"⏰ Time: {booking.get('pickup_time')}\n"
            f"🧑‍🤝‍🧑 Passengers: {booking.get('passenger_count')}\n"
            f"🚘 Vehicle: {booking.get('vehicle_type')}\n"
            f"👨‍✈️ Driver: {driver.get('name')} ({driver.get('phone')})\n"
            f"💰 Cost: {booking.get('trip_cost')} INR\n"
            f"{'🗺️ Route: ' + maps_link if maps_link else ''}"
        ).strip()
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message_body,
            to=to_number
        )
        print(f"📩 WhatsApp sent to {booking.get('name')}. SID: {message.sid}")
    except Exception as e:
        print(f"❌ Failed to send WhatsApp: {e}")

# ---------------- Twilio Call Flow ---------------- #

def ask_question(index):
    question_key = questions[index]
    question_text = question_texts[question_key]
    base_url = request.host_url.rstrip("/")
    twiml = f"""
    <Response>
        <Gather input="speech dtmf" action="{base_url}/gather?index={index}" method="POST" timeout="6">
            <Say voice="alice">{question_text}</Say>
        </Gather>
        <Say voice="alice">I did not hear anything. Let's try again.</Say>
        <Redirect method="POST">{base_url}/voice</Redirect>
    </Response>
    """
    return Response(twiml, mimetype='text/xml')

def confirm_booking():
    driver = booking_data.get("driver", {})
    confirmation_message = (
        f"Thank you {booking_data['name']}. "
        f"Your taxi from {booking_data['pickup_location']} to {booking_data['drop_location']} "
        f"on {booking_data['pickup_date']} at {booking_data['pickup_time']} "
        f"for {booking_data['passenger_count']} passenger(s) in a {booking_data['vehicle_type']} "
        f"is confirmed. Driver {driver.get('name')} ({driver.get('phone')}) "
        f"will contact you. Estimated cost: {booking_data['trip_cost']} rupees."
    )
    # WhatsApp confirmation after call
    send_booking_whatsapp(booking_data)
    return Response(f"""
    <Response>
        <Say voice="alice">{confirmation_message}</Say>
        <Hangup/>
    </Response>
    """, mimetype='text/xml')

@app.route("/", methods=["GET", "POST"])
def index():
    return Response("""
    <Response>
        <Redirect>/voice</Redirect>
    </Response>
    """, mimetype='text/xml')

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    return ask_question(0)

@app.route("/gather", methods=['GET', 'POST'])
def gather():
    current_index = int(request.values.get('index', 0))
    speech_result = request.values.get('SpeechResult')
    digits_result = request.values.get('Digits')
    answer = (speech_result or digits_result or "").strip()

    if questions[current_index] == "phone_number":
        answer = format_number(answer)

    if current_index < len(questions):
        booking_data[questions[current_index]] = answer
        print(f"📞 {questions[current_index]}: {answer}")

    if current_index + 1 < len(questions):
        return ask_question(current_index + 1)
    else:
        driver = assign_driver()
        booking_data["driver"] = driver
        booking_data["trip_cost"] = calculate_trip_cost(
            booking_data["pickup_location"],
            booking_data["drop_location"],
            booking_data["vehicle_type"],
            booking_data["pickup_date"],
            booking_data["pickup_time"]
        )
        booking_data["maps_link"] = build_google_maps_link(
            booking_data.get("pickup_location"),
            booking_data.get("drop_location")
        )
        booking_data["call_history"] = {
            "call_sid": request.values.get("CallSid", ""),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        print("\n📞 Final Booking Data:")
        print(json.dumps(booking_data, indent=2))
        bookings_col.insert_one(dict(booking_data))
        print("✅ Booking saved to MongoDB")
        return confirm_booking()

# ---------------- Outbound Call ---------------- #

@app.route("/call_customer", methods=["POST"])
def call_customer():
    data = request.json or {}
    to_number = data.get("to")
    if not to_number:
        return {"error": "Missing 'to' phone number"}, 400
    try:
        call = client.calls.create(
            to=to_number,
            from_=TWILIO_NUMBER,
            url=request.host_url.rstrip("/") + "/voice"
        )
        return {"status": "Call initiated", "call_sid": call.sid}
    except Exception as e:
        print("❌ Error starting call:", e)
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
