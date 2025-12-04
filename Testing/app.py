from flask import Flask, request, Response
import json

app = Flask(__name__)

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

@app.route("/voice", methods=['GET', 'POST'])  # ✅ Allow GET and POST
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
        return confirm_booking()


def ask_question(index):
    question_key = questions[index]
    question_text = question_texts[question_key]
    
    # ✅ Correct base URL for Twilio
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

if __name__ == "__main__":
    app.run(port=5000, debug=True)
