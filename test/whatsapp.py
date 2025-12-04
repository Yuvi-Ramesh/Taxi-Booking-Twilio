import re
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

# ==== Twilio credentials ====
ACCOUNT_SID = 'ACf284367f6a5e480ddcf4b510e8866b71'
AUTH_TOKEN = '68b42ccb9eb60e6fb616e219222f2428'
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'

# Pre-approved WhatsApp template SID (with 8 placeholders)
TEMPLATE_SID = 'HXb5b62575e6e4ff6129ad7c8efe1f983e'

client = Client(ACCOUNT_SID, AUTH_TOKEN)
app = Flask(__name__)

# In-memory user sessions
user_sessions = {}

# Questions flow
QUESTIONS = [
    ("name", "May I know your name?"),
    ("phone_number", "Please tell me your contact number, including country code."),
    ("pickup_location", "Where should we pick you up?"),
    ("drop_location", "Where would you like to go?"),
    ("pickup_date", "On which date would you like to travel? For example, say twenty fourth August."),
    ("pickup_time", "At what time should the taxi arrive?"),
    ("passenger_count", "How many passengers will be travelling?"),
    ("vehicle_type", "What type of vehicle do you prefer? For example, sedan, SUV, or auto.")
]

# Helper to format phone numbers
def format_number(number_str):
    number = re.sub(r"[^\d]", "", number_str)
    if number.startswith("91"):
        number = "+" + number
    elif number.startswith("0"):
        number = "+91" + number[1:]
    elif not number.startswith("+"):
        number = "+" + number
    return number

# Flask webhook
@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "")

    resp = MessagingResponse()

    # Initialize session if first message or new user
    if from_number not in user_sessions:
        user_sessions[from_number] = {"step": 0, "data": {}}
        _, question = QUESTIONS[0]
        resp.message(question)
        user_sessions[from_number]["step"] = 1
        return str(resp)

    session = user_sessions[from_number]
    step = session["step"]

    # Save previous answer
    if step > 0 and step <= len(QUESTIONS):
        key, _ = QUESTIONS[step - 1]
        answer = incoming_msg
        if key == "phone_number":
            answer = format_number(answer)
        session["data"][key] = answer

    # Ask next question
    if step < len(QUESTIONS):
        _, question = QUESTIONS[step]
        resp.message(question)
        session["step"] += 1
    else:
        data = session["data"]
        # Send booking confirmation using Twilio template API
        try:
            client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                to=data['phone_number'],
                content_sid=TEMPLATE_SID,
                content_variables=f'''{{
                    "1":"{data["name"]}",
                    "2":"{data["phone_number"]}",
                    "3":"{data["pickup_location"]}",
                    "4":"{data["drop_location"]}",
                    "5":"{data["pickup_date"]}",
                    "6":"{data["pickup_time"]}",
                    "7":"{data["passenger_count"]}",
                    "8":"{data["vehicle_type"]}"
                }}'''
            )
            resp.message("✅ Your booking has been confirmed! Check WhatsApp for template confirmation.")
        except Exception as e:
            print(f"Error sending template message: {e}")
            resp.message("❌ Sorry, we could not send your booking confirmation. Please try again.")

        # Reset session
        user_sessions.pop(from_number)

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
