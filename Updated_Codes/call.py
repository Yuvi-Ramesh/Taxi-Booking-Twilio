from twilio.rest import Client
import time

account_sid = "ACf284367f6a5e480ddcf4b510e8866b71"
auth_token = "68b42ccb9eb60e6fb616e219222f2428"
client = Client(account_sid, auth_token)
NGROK_URL = "https://4199c7cbcca4.ngrok-free.app"

call = client.calls.create(
    url=f"{NGROK_URL}/voice",
    to="+919952297502",               # Your personal phone number
    from_="+1 716 621 3120"               # Your Twilio number
)

print(call.sid)
time.sleep(120)  # Wait for the call to be established