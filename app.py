import os
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
import requests

app = Flask(__name__)

LND_REST_URL = os.getenv("LND_REST_URL")
MACAROON = os.getenv("LND_MACAROON")
CERT_PATH = os.getenv("LND_CERT_PATH")
ALLOWED_CALLER = os.getenv("ALLOWED_CALLER")

HEADERS = {
    "Grpc-Metadata-macaroon": MACAROON
}

@app.route("/voice", methods=["POST"])
def voice():
    if request.form.get("From") != ALLOWED_CALLER:
        resp = VoiceResponse()
        resp.say("Access denied.")
        resp.hangup()
        return Response(str(resp), mimetype="application/xml")

    resp = VoiceResponse()
    gather = Gather(num_digits=10, action="/dtmf", finish_on_key="#", method="POST")
    gather.say("Enter command followed by pound.")
    resp.append(gather)
    return Response(str(resp), mimetype="application/xml")

@app.route("/dtmf", methods=["POST"])
def dtmf():
    digits = request.form.get("Digits")
    resp = VoiceResponse()

    try:
        if digits.startswith("3"):
            r = requests.get(f"{LND_REST_URL}/v1/balance/channels", headers=HEADERS, verify=CERT_PATH)
            balance = int(r.json().get("balance", 0))
            resp.say(f"Balance is {balance} satoshis.")
        elif digits.startswith("2"):
            amount = int(digits[1:])
            payload = {"value": amount}
            r = requests.post(f"{LND_REST_URL}/v1/invoices", json=payload, headers=HEADERS, verify=CERT_PATH)
            payreq = r.json().get("payment_request", "error")
            short_payreq = payreq[:40]
            resp.say("Payment request starts with:")
            resp.say(short_payreq)
        else:
            resp.say("Invalid command.")
    except Exception as e:
        resp.say("Error processing command.")
    
    resp.hangup()
    return Response(str(resp), mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)