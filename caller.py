import os
import json
import logging
import time
from gtts import gTTS
from pydub import AudioSegment
from google.cloud import texttospeech
import boto3
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Setup logging
log_file = os.getenv("LOG_FILE")
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w', force=True)
logging.info("Initializing Local AI Caller...")

# --- GenerateResponse Class ---
class GenerateResponse:
    def __init__(self):
        self.client_google = genai.Client(api_key=os.getenv("GOOGLE_GENAI_API_KEY"))
        self.client_claude = boto3.client(
            'bedrock-runtime',
            region_name='ap-south-1',
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY_CLAUDE'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID_CLAUDE')
        )
        self.model_id_claude = os.getenv("CLAUDE_ID")
        self.talk_file = os.getenv("PREV_REPLY")
        self.company_name = os.getenv("COMPANY_NAME")
        self.data = self.load_data()
        self.prev_talk = self.get_last_two_queries()
        self.context = """Context: You are Eva, an AI assistant for {0}, but you must act human-like so the user doesn't suspect you're AI.
        Keep replies brief unless asked to elaborate. Don’t mention features unless asked. Maintain context from previous interaction: {3}.
        Use natural language and avoid robotic patterns. If the user asks for a real person, provide contact info if available."""

    def load_data(self):
        data_file = os.getenv("DATA_FILE")
        file_path = os.path.join(data_file, self.company_name + '.txt')
        logging.info(f"Loading data from: {file_path}")
        with open(file_path, 'r') as file:
            return file.read()

    def save_conversation(self, query, response):
        with open(self.talk_file, 'a') as f:
            f.write(f"Query: {query}\nResponse: {response}\n")

    def delete_conversation(self):
        with open(self.talk_file, 'w') as f:
            pass

    def get_last_two_queries(self):
        try:
            with open(self.talk_file, "r") as f:
                lines = f.readlines()
            queries_responses = []
            query, response = None, None
            for line in lines:
                if line.startswith("Query: "):
                    query = line.strip()
                elif line.startswith("Response: "):
                    response = line.strip()
                    if query and response:
                        queries_responses.append((query, response))
            return queries_responses[-2:] if len(queries_responses) >= 2 else queries_responses
        except Exception as e:
            logging.error(f"Error reading previous conversation: {e}")
            return []

    def generate_response(self, query):
        message = self.context.format(self.company_name, self.company_name, self.data, self.prev_talk)
        message += f"\n\nGenerate a response for this question: {query}"

        try:
            response = self.client_google.models.generate_content(model='gemini-2.0-flash', contents=message).text
        except Exception as e:
            logging.warning("Google GenAI failed, falling back to Claude.")
            response = self.response_claude(query)

        self.save_conversation(query, response)
        return response

    def response_claude(self, query):
        input_payload = [{"role": "user", "content": [{"text": query}]}]
        response = self.client_claude.converse(modelId=self.model_id_claude, messages=input_payload)
        return response['output']['message']['content'][0]['text']


# --- Text-to-Speech Class ---
class TextToSpeech:
    def __init__(self):
        self.polly_client = boto3.client('polly', region_name='ap-south-1')

    def speak(self, text, provider='google', voice='en-IN-Wavenet-D'):
        print("Eva:", text)
        if provider == 'google':
            self.google_cloud_tts(text, voice)
        elif provider == 'amazon':
            self.polly_tts(text, voice)

    def polly_tts(self, text, voice):
        try:
            response = self.polly_client.synthesize_speech(
                Text=text, VoiceId=voice, OutputFormat='mp3', Engine='neural'
            )
            with open("output.mp3", "wb") as f:
                f.write(response['AudioStream'].read())
            os.system("afplay output.mp3")  # macOS; use 'start' on Windows, 'mpg123' on Linux
        except Exception as e:
            logging.error(f"Polly TTS Error: {e}")

    def google_cloud_tts(self, text, voice):
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice_params = texttospeech.VoiceSelectionParams(language_code="en-IN", name=voice)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        response = client.synthesize_speech(input=synthesis_input, voice=voice_params, audio_config=audio_config)

        with open("output.mp3", "wb") as out:
            out.write(response.audio_content)
        os.system("afplay output.mp3")  # Replace based on OS


# --- Main Simulation Logic ---
def run_local_call():
    tts = TextToSpeech()
    gr = GenerateResponse()

    print("Welcome to the Local AI Caller Demo!")
    user_name = input("Enter your name: ")
    title = input("Enter your title (Mr./Ms./Dr.): ")
    voice = input("Choose voice (e.g., en-IN-Wavenet-D or Kajal): ")

    print("\nStarting simulated call...\n")

    # Step 1: Initial greeting
    intro = f"Hello, This is Eva calling. Am I speaking with {title} {user_name}?"
    tts.speak(intro, voice=voice)
    user_response = input("You: ")

    if any(word in user_response.lower() for word in ["no", "wrong", "not"]):
        tts.speak("Oh, I'm sorry! Wrong number. Have a nice day.", voice=voice)
        return

    # Step 2: Introduction
    intro2 = f"Hello {title} {user_name}! Sorry to call out of the blue. I’m Eva from {gr.company_name}. How are you today?"
    tts.speak(intro2, voice=voice)
    user_response = input("You: ")

    # Step 3: Check availability
    check_time = "Is it a good time to talk?"
    tts.speak(check_time, voice=voice)
    user_response = input("You: ")

    if "no" in user_response.lower():
        tts.speak("I understand. We'll reach out at a better time. Have a great day!", voice=voice)
        return

    # Step 4: Pitch company
    pitch = f"Thank you. The reason I'm calling is to tell you about {gr.company_name}. Would you like to hear more?"
    tts.speak(pitch, voice=voice)
    user_response = input("You: ")

    if "no" in user_response.lower():
        tts.speak("No problem. Feel free to reach out anytime. Have a great day!", voice=voice)
        return

    # Step 5: Continuous conversation loop
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit', 'goodbye']:
            tts.speak("Alright, thank you for your time. Have a great day!", voice=voice)
            break
        ai_response = gr.generate_response(user_input)
        tts.speak(ai_response, voice=voice)


if __name__ == "__main__":
    print("Running local AI caller demo...")
    run_local_call()