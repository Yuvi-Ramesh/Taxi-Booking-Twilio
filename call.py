from twilio.rest import Client
import time

account_sid = "ACd121c55f997586e39a4912616b4326ad"
auth_token = "f60f16466e36d3100f3e64cde1e3e065"
client = Client(account_sid, auth_token)
NGROK_URL = "https://209b090b0aa4.ngrok-free.app"

call = client.calls.create(
    url=f"{NGROK_URL}/voice",
    to="+919952297502",               # Your personal phone number
    from_="+12495015490"               # Your Twilio number
)

print(call.sid)
time.sleep(120)  # Wait for the call to be established