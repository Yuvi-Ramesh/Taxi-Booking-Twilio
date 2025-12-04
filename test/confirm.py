from flask import Flask, request, Response
import json
from twilio.rest import Client
import os
import re
import time

app = Flask(__name__)

# Twilio credentials
ACCOUNT_SID = "ACf284367f6a5e480ddcf4b510e8866b71"
AUTH_TOKEN = "68b42ccb9eb60e6fb616e219222f2428"
TWILIO_NUMBER = "+17166213120"   # Your Twilio number for SMS
MY_PHONE_NUMBER = "+919952297502"  # Your personal phone number for SMS
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"  # Twilio Sandbox WhatsApp

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Store booking details
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

# Friendly questions for taxi booking
question_texts = {
    "name": "May I know your name?",
    "phone_number": "Please tell me your contact number, including country code.",
    "pickup_location": "Where should we pick you up?",
    "drop_location": "Where would you like to go?",
    "pickup_date": "On which date would you like to travel? For example, say twenty fourth August.",
    "pickup_time": "At what time should the taxi arrive?",
    "passenger_count": "How many passengers will be travelling?",
    "vehicle_type": "What type of vehicle do you prefer? For example, sedan, SUV, or auto."
}

questions = list(booking_data.keys())

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    return ask_question(0)

@app.route("/gather", methods=['GET', 'POST'])
def gather():
    current_index = int(request.values.get('index', 0))
    speech_result = request.values.get('SpeechResult')
    digits_result = request.values.get('Digits')

    answer = (speech_result or digits_result or "").strip()

    if current_index < len(questions):
        booking_data[questions[current_index]] = answer
        print(f"📞 {questions[current_index]}: {answer}")

    if current_index + 1 < len(questions):
        return ask_question(current_index + 1)
    else:
        print("\n📞 Final Booking Data:")
        print(json.dumps(booking_data, indent=2))

        # Save booking to file
        save_booking_to_file()

        # Send confirmation via SMS
        send_booking_sms()

        # Send confirmation via WhatsApp
        send_booking_whatsapp()

        return confirm_booking()

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
    confirmation_message = (
        f"Thank you {booking_data['name']}. "
        f"Your taxi from {booking_data['pickup_location']} to {booking_data['drop_location']} "
        f"on {booking_data['pickup_date']} at {booking_data['pickup_time']} "
        f"for {booking_data['passenger_count']} passenger(s) in a {booking_data['vehicle_type']} "
        f"has been recorded. We will contact you at {booking_data['phone_number']}."
    )
    return Response(f"""
    <Response>
        <Say voice="alice">{confirmation_message}</Say>
        <Hangup/>
    </Response>
    """, mimetype='text/xml')

def save_booking_to_file():
    file_path = "confirm_booking.txt"
    clean_data = {k: (v.strip(". ").strip() if v else "") for k, v in booking_data.items()}
    with open(file_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(clean_data, indent=2))
        file.write("\n" + "="*40 + "\n")
    print(f"📂 Booking saved to {file_path}")

def send_booking_sms():
    """Send booking confirmation via SMS"""
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
        client.messages.create(
            body=message_body,
            from_=TWILIO_NUMBER,
            to=MY_PHONE_NUMBER
        )
        print("📩 Confirmation SMS sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}")

def format_number(number_str):
    """Ensure phone number is in E.164 format for WhatsApp"""
    number = re.sub(r"[^\d]", "", number_str)
    if number.startswith("91"):
        number = "+" + number
    elif number.startswith("0"):
        number = "+91" + number[1:]
    elif not number.startswith("+"):
        number = "+" + number
    return number

def send_booking_whatsapp():
    """Send booking confirmation via WhatsApp"""
    try:
        to_number = f"whatsapp:{format_number(booking_data['phone_number'])}"
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
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message_body,
            to=to_number
        )
        print(f"📩 WhatsApp sent to {booking_data['name']}. SID: {message.sid}")
    except Exception as e:
        print(f"❌ Failed to send WhatsApp to {booking_data['name']}: {e}")

if __name__ == "__main__":
    app.run(port=5000, debug=True)
