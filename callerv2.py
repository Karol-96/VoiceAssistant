from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from google.cloud import speech_v1
from google.cloud import texttospeech
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

# Initialize clients
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)
speech_client = speech_v1.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = Flask(__name__)

@app.route("/", methods=['GET'])
def index():
    """Home page"""
    return "AI Voice Response Server is running!"

@app.route("/answer", methods=['POST'])
def answer_call():
    """Handle incoming calls"""
    response = VoiceResponse()
    
    gather = Gather(
        input='speech',
        action='/process-speech',
        timeout=3,
        language='en-US',
        speechTimeout='auto'
    )
    gather.say(
        "Hello! How can I help you today?",
        voice='neural'
    )
    response.append(gather)
    
    # If no input received
    response.say("I didn't hear anything. Please call back if you need assistance.")
    return str(response)

@app.route("/process-speech", methods=['POST'])
def process_speech():
    """Process speech input and generate AI response"""
    response = VoiceResponse()
    
    # Get speech input
    speech_result = request.values.get('SpeechResult')
    
    if speech_result:
        # Generate AI response using OpenAI
        ai_response = generate_ai_response(speech_result)
        
        # Convert AI response to speech
        audio_content = text_to_speech(ai_response)
        
        # Save audio file temporarily
        temp_audio_file = "temp_response.mp3"
        with open(temp_audio_file, "wb") as f:
            f.write(audio_content)
        
        # Play the response
        response.play(temp_audio_file)
        
        # Continue listening
        gather = Gather(
            input='speech',
            action='/process-speech',
            timeout=3,
            language='en-US',
            speechTimeout='auto'
        )
        gather.say("Is there anything else I can help you with?", voice='neural')
        response.append(gather)
    else:
        response.say("I couldn't understand that. Could you please try again?")
        response.redirect('/answer')
    
    return str(response)

def generate_ai_response(user_input):
    """Generate response using OpenAI"""
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful customer service assistant. Keep responses clear and concise."},
                {"role": "user", "content": user_input}
            ],
            max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return "I apologize, but I'm having trouble processing your request right now."

def text_to_speech(text):
    """Convert text to speech using Google TTS"""
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-F",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return response.audio_content
    except Exception as e:
        print(f"Error in text-to-speech conversion: {e}")
        return None

if __name__ == "__main__":
    # Check required environment variables
    required_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'OPENAI_API_KEY',
        'GOOGLE_APPLICATION_CREDENTIALS'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print("Error: Missing required environment variables:", missing_vars)
        exit(1)
    
    # Run the Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)