from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Twilio client
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

app = Flask(__name__)

@app.route("/", methods=['GET'])
def index():
    """Home page"""
    return "Twilio Voice Response Server is running!"

@app.route("/answer", methods=['POST'])
def answer_call():
    """Handle incoming calls"""
    response = VoiceResponse()
    
    gather = Gather(
        input='speech dtmf',
        action='/handle-response',
        timeout=3,
        num_digits=1,
        language='en-US'
    )
    gather.say(
        "Welcome to our service. Press 1 for sales, 2 for support, or speak your query.",
        voice='alice'
    )
    response.append(gather)
    
    response.say("We didn't receive any input. Goodbye!")
    return str(response)

@app.route("/handle-response", methods=['POST'])
def handle_response():
    """Handle user's input"""
    response = VoiceResponse()
    
    choice = request.values.get('Digits', None)
    speech = request.values.get('SpeechResult', None)
    
    if choice:
        if choice == '1':
            response.say("Connecting you to sales. Please hold.")
            # Replace with your actual sales phone number
            response.dial(os.getenv('SALES_PHONE_NUMBER', '+1234567890'))
        elif choice == '2':
            response.say("Connecting you to support. Please hold.")
            # Replace with your actual support phone number
            response.dial(os.getenv('SUPPORT_PHONE_NUMBER', '+1234567890'))
    elif speech:
        response.say(f"You said: {speech}. Let me process that.")
        response.say("Thank you for your query. We'll process it and get back to you.")
    else:
        response.say("Sorry, I didn't catch that. Please try again.")
        response.redirect('/answer')
    
    return str(response)

if __name__ == "__main__":
    # Check if required environment variables are set
    if not all([os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN')]):
        print("Error: Missing required environment variables. Please check your .env file.")
        print("Required variables: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN")
        exit(1)
    
    # Run the Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)