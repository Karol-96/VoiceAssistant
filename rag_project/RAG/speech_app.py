# app.py
import os
import json
import base64
import pyaudio
import numpy as np
import websocket
import streamlit as st
from dotenv import load_dotenv
import threading
import time
from typing import Optional

class AudioHandler:
    def __init__(self):
        self.SAMPLE_RATE = 16000
        self.CHANNELS = 1
        self.AUDIO_FORMAT = pyaudio.paInt16
        self.p = pyaudio.PyAudio()
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None
        self.is_recording = False

    def base64_encode_audio(self, int16_array: np.ndarray) -> str:
        """Encodes an int16 array to a base64 string."""
        pcm_bytes = int16_array.tobytes()
        return base64.b64encode(pcm_bytes).decode('ascii')

    def play_audio(self, audio_array: np.ndarray) -> None:
        """Plays audio using PyAudio."""
        try:
            if not self.output_stream:
                self.output_stream = self.p.open(
                    format=self.AUDIO_FORMAT,
                    channels=self.CHANNELS,
                    rate=self.SAMPLE_RATE,
                    output=True
                )
            self.output_stream.write(audio_array.tobytes())
        except Exception as e:
            st.error(f"Error playing audio: {e}")

    def cleanup(self):
        """Cleanup audio resources."""
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        self.p.terminate()

class RealTimeChatbot:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        
        self.url = "wss://api.openai.com/v2/realtime?model=gpt-4o-realtime-preview-2024-12-17"
        self.headers = [
            f"Authorization: Bearer {self.api_key}",
            "OpenAI-Beta: realtime=v1"
        ]
        self.audio_handler = AudioHandler()
        self.ws: Optional[websocket.WebSocketApp] = None
        self.conversation_history = []

    def on_open(self, ws):
        """WebSocket open event handler."""
        st.session_state.connection_status = "Connected"
        event = {
            "type": "response.create",
            "response": {
                "modalities": ["audio", "text"],
                "language": "ne",  # Nepali language code
                "instructions": "Please assist the user with speech in Nepali."
            }
        }
        ws.send(json.dumps(event))

    def on_message(self, ws, message):
        """WebSocket message event handler."""
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "response.audio.delta":
                audio_data = base64.b64decode(data.get("delta"))
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                self.audio_handler.play_audio(audio_array)

            elif message_type == "response.text.delta":
                delta_text = data.get("delta", "")
                if "response_text" not in st.session_state:
                    st.session_state.response_text = ""
                st.session_state.response_text += delta_text
                # Update the text area with the accumulated text
                if "text_area" in st.session_state:
                    st.session_state.text_area.text(st.session_state.response_text)

            elif message_type == "response.done":
                if "response_text" in st.session_state:
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": st.session_state.response_text
                    })
                    st.session_state.response_text = ""

        except Exception as e:
            st.error(f"Error processing message: {e}")

    def on_error(self, ws, error):
        """WebSocket error event handler."""
        st.error(f"WebSocket error: {error}")
        st.session_state.connection_status = "Error"

    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket close event handler."""
        st.warning("Connection closed")
        st.session_state.connection_status = "Disconnected"

    def record_audio_callback(self, in_data, frame_count, time_info, status):
        """Audio recording callback."""
        if self.ws and self.audio_handler.is_recording:
            try:
                int16_data = np.frombuffer(in_data, dtype=np.int16)
                base64_chunk = self.audio_handler.base64_encode_audio(int16_data)
                event = {
                    "type": "input_audio_buffer.append",
                    "audio": base64_chunk
                }
                self.ws.send(json.dumps(event))
            except Exception as e:
                st.error(f"Error in audio callback: {e}")
        return (in_data, pyaudio.paContinue)

    def start_recording(self):
        """Start recording audio."""
        self.audio_handler.is_recording = True
        self.audio_handler.input_stream = self.audio_handler.p.open(
            format=self.audio_handler.AUDIO_FORMAT,
            channels=self.audio_handler.CHANNELS,
            rate=self.audio_handler.SAMPLE_RATE,
            input=True,
            stream_callback=self.record_audio_callback
        )
        self.audio_handler.input_stream.start_stream()

    def stop_recording(self):
        """Stop recording and send final messages."""
        self.audio_handler.is_recording = False
        if self.ws:
            self.ws.send(json.dumps({"type": 'input_audio_buffer.commit'}))
            self.ws.send(json.dumps({"type": 'response.create'}))

    def run(self):
        """Initialize and run the WebSocket connection."""
        self.ws = websocket.WebSocketApp(
            self.url,
            header=self.headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        # Start WebSocket connection in a separate thread
        ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        ws_thread.start()

def main():
    st.set_page_config(page_title="Nepali Speech-to-Speech Chatbot", layout="wide")
    st.title("Nepali Speech-to-Speech Chatbot")

    # Initialize session state variables
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = RealTimeChatbot()
        st.session_state.connection_status = "Disconnected"

    # Display connection status
    st.markdown(f"Status: **{st.session_state.connection_status}**")

    # Create columns for button layout
    col1, col2, col3 = st.columns(3)

    # Start button
    if col1.button("Start Recording"):
        if st.session_state.connection_status == "Disconnected":
            st.session_state.chatbot.run()
        st.session_state.chatbot.start_recording()
        st.session_state.recording = True

    # Stop button
    if col2.button("Stop Recording"):
        if hasattr(st.session_state, 'recording') and st.session_state.recording:
            st.session_state.chatbot.stop_recording()
            st.session_state.recording = False

    # Clear button
    if col3.button("Clear Conversation"):
        st.session_state.chatbot.conversation_history = []
        if "response_text" in st.session_state:
            st.session_state.response_text = ""

    # Display conversation history
    st.subheader("Conversation History")
    for message in st.session_state.chatbot.conversation_history:
        role = "🤖 Assistant" if message["role"] == "assistant" else "🗣️ You"
        st.markdown(f"**{role}**: {message['content']}")

    # Create a placeholder for real-time response text
    if "text_area" not in st.session_state:
        st.session_state.text_area = st.empty()

    # Display current response (if any)
    if "response_text" in st.session_state and st.session_state.response_text:
        st.session_state.text_area.text(st.session_state.response_text)

if __name__ == "__main__":
    main()