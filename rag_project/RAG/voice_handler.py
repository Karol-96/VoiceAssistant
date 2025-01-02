import os
import tempfile
from gtts import gTTS
import pygame
import speech_recognition as sr
from deep_translator import GoogleTranslator
import logging
import time

logger = logging.getLogger(__name__)

class AudioHandler:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Initialize pygame mixer
        pygame.mixer.init()
        
    def text_to_speech(self, text, lang='en'):
        """Convert text to speech and play it"""
        try:
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            temp_filename = os.path.join(temp_dir, f'speech_{int(time.time())}.mp3')
            
            # Generate speech file
            tts = gTTS(text=text, lang=lang)
            tts.save(temp_filename)
            
            try:
                # Play the audio
                pygame.mixer.music.load(temp_filename)
                pygame.mixer.music.play()
                
                # Wait for audio to finish
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    
            finally:
                # Cleanup
                pygame.mixer.music.unload()
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                    
        except Exception as e:
            logger.error(f"Error in text to speech: {str(e)}")
            raise

    def speech_to_text(self, language='en-US'):
        """Convert speech to text"""
        try:
            with sr.Microphone() as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                logger.info("Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                if language == 'ne-NP':
                    # For Nepali, first recognize in English then translate
                    text = self.recognizer.recognize_google(audio)
                    translated = self.translate_text(text, 'ne')
                    return translated
                else:
                    return self.recognizer.recognize_google(audio, language=language)
                    
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Could not request results: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error in speech to text: {str(e)}")
            return None

    def translate_text(self, text, target_lang='ne'):
        """Translate text to target language"""
        try:
            translator = GoogleTranslator(source='auto', target=target_lang)
            return translator.translate(text)
        except Exception as e:
            logger.error(f"Error in translation: {str(e)}")
            return text