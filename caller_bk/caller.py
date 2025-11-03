import asyncio
import websockets
import logging
import numpy as np
from TTS.api import TTS
import re
import os
import json
import boto3
from dotenv import load_dotenv
import io
import time
from gtts import gTTS
from pydub import AudioSegment
import struct
import torch
import torchaudio
import urllib.request
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from pathlib import Path

# Load environment variables
load_dotenv()
log_file = os.getenv("LOG_FILE")
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w', force=True)
logging.info("Initializing AI Caller...")

# Define model paths
MODEL_DIR = Path(__file__).parent / "models/xtts_v2"
SAMPLE_AUDIO_PATH = Path(__file__).parent / "sample_audio-trimmed.wav"

# Download XTTS model if not already present
def download_model():
    """Download XTTS model if not already present"""
    if MODEL_DIR.exists():
        return  # Skip download if already present
    print("Downloading XTTS v2 model...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_url = "https://huggingface.co/coqui/XTTS-v2/resolve/main/model.pth"
    config_url = "https://huggingface.co/coqui/XTTS-v2/resolve/main/config.json"
    vocab_url = "https://huggingface.co/coqui/XTTS-v2/resolve/main/vocab.json"
    urllib.request.urlretrieve(model_url, MODEL_DIR / "model.pth")
    urllib.request.urlretrieve(config_url, MODEL_DIR / "config.json")
    urllib.request.urlretrieve(vocab_url, MODEL_DIR / "vocab.json")
    print("Model files downloaded successfully!")

download_model()

# Optimize CPU threading
torch.set_num_threads(max(1, os.cpu_count() - 1))
torch.set_grad_enabled(False)

# Load model configuration
print("Loading XTTS model...")
CONFIG = XttsConfig()
CONFIG.load_json(str(MODEL_DIR / "config.json"))

# Optimize inference parameters
CONFIG.inference_noise_scale = 0.3
CONFIG.length_penalty = 1.0
CONFIG.top_k = 20

# Use CPU explicitly
DEVICE = torch.device('cpu')
print(f"Using device: {DEVICE}")

# Initialize and load model
MODEL = Xtts.init_from_config(CONFIG)
MODEL.load_checkpoint(CONFIG, checkpoint_dir=str(MODEL_DIR), use_deepspeed=False)
MODEL.to(DEVICE)
MODEL.eval()

# Compute speaker latents (if sample audio exists)
GPT_COND_LATENT = None
SPEAKER_EMBEDDING = None
if SAMPLE_AUDIO_PATH.exists():
    print(f"Computing speaker latents from: {SAMPLE_AUDIO_PATH}")
    GPT_COND_LATENT, SPEAKER_EMBEDDING = MODEL.get_conditioning_latents(audio_path=[str(SAMPLE_AUDIO_PATH)])
else:
    print(f"Warning: Sample audio file not found at {SAMPLE_AUDIO_PATH}")
    MODEL = None  # Disable model if no sample audio

# Cache common phrases
CACHED_RESPONSES = {}

def cache_common_phrases():
    """Cache frequently used phrases to speed up inference"""
    global CACHED_RESPONSES
    common_phrases = [
        "Yes", "No", "Okay", "I understand",
        "Could you repeat that?", "Thank you",
        "I'm thinking", "One moment please",
        "Hello", "Goodbye", "Sorry"
    ]
    print("Caching common phrases...")
    for phrase in common_phrases:
        try:
            out = MODEL.inference(
                phrase,
                "en",
                GPT_COND_LATENT,
                SPEAKER_EMBEDDING,
                temperature=0.65
            )
            CACHED_RESPONSES[phrase.lower()] = np.array(out["wav"], dtype=np.float32)
        except Exception as e:
            print(f"Error caching phrase '{phrase}': {e}")

cache_common_phrases()

class GenerateResponse:
    def __init__(self):
        self.client_meta = boto3.client('bedrock-runtime', region_name='ap-south-1')
        self.model_id_meta = "meta.llama3-70b-instruct-v1:0"
        self.client_claude = boto3.client(
            'bedrock-runtime',
            region_name='ap-south-1',
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY_CLAUDE'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID_CLAUDE')
        )
        self.talk_file = os.getenv("PREV_REPLY")
        self.model_id_claude = "arn:aws:bedrock:ap-south-1:144023344931:inference-profile/apac.anthropic.claude-3-5-sonnet-20240620-v1:0"
        self.data = self.load_data()
        self.prev_talk = self.get_last_two_queries()
        self.question_template = "Generate a response based on the information available in Context for Question: {}"
        self.context = """ Context : You are Eva, an AI assistant for Duplex Builders but you have to act like a human so user should not know that you are an AI.
        You are the one calling the user to tell the user about the duplex builders, properties available and why user should buy them. So you should try to prusue them in buying the properties.
        If the user wants to talk to the person then you should provide the user with the contact details of the a human agent. The contact number is 9012345678.
        You provide information about properties, prices, locations, and amenities that Duplex Builders sells or rents.
        Answer the user in brief, unless the user asks you to explain and be specific instead of giving lengthy answers.
        Do not provide all the information to the user about the property like amenities and other features until and unless asked by the user specifically.
        Also do not generate points, just provide answer in paragraph and do not generate abbrevations like instead of I'm use I am or I would instead of I'd. 
        Also if you are giving contact number then give it in english text like Nine Zero Three Four One instad of 90341.
        If the property is not available at the location in the provided data
        then you should generate the answer like 'Currently, at this location, they do not have any property.'
        I will also provide you with the reply generated by you to the user's query so that you are able to maintain the context of the conversation.
        Here is the data that you have: {}
        Here is the previous reply generated by you: {}
        """

    def load_data(self):
        file_path = os.getenv('DATA_FILE')
        with open(file_path, 'r') as file:
            data = file.read()
            return data

    def get_last_two_queries(self):
        with open(self.talk_file, "r", encoding="utf-8") as file:
            lines = file.readlines()
        # Extract queries and responses
        queries_responses = []
        query, response = None, None
        for line in lines:
            if line.startswith("Query: "):
                query = line.strip()
            elif line.startswith("Response: "):
                response = line.strip()
                if query and response:
                    queries_responses.append((query, response))
        # Get the last two query-response pairs
        last_two = queries_responses[-2:] if len(queries_responses) >= 2 else queries_responses
        return last_two

    def response_claude(self, query):
        question = self.question_template.format(query)
        message = question + self.context.format(self.data, self.prev_talk)
        input_payload = [
            {
                "role": "user",
                "content": [
                    {"text": message},
                ],
            }
        ]
        response_claude = self.client_claude.converse(
            modelId=self.model_id_claude,
            messages=input_payload,
        )
        response = response_claude['output']['message']['content'][0]['text']
        with open(self.talk_file, 'a') as file:
            file.write(f"Query: {query}\nResponse: {response}\n")
        return response

    def response_meta(self, query):
        question = self.question_template.format(query)
        input_payload = {"prompt": question + "\n" + self.context}
        response = self.client_meta.invoke_model(
            modelId=self.model_id_meta,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(input_payload)
        )
        response_body = response['body'].read().decode('utf-8')
        result = json.loads(response_body)
        return result.get("generation", "No response generated")


class XTTSWrapper:
    def __init__(self, websocket, text):
        """Initialize the XTTS model wrapper"""
        self.websocket = websocket
        self.text = text
        self.model = MODEL  # Use preloaded model
        self.gpt_cond_latent = GPT_COND_LATENT
        self.speaker_embedding = SPEAKER_EMBEDDING
        self.cached_responses = CACHED_RESPONSES
        # Audio queue setup
        self.audio_queue = asyncio.Queue()
        self.is_playing = False
        self.lock = asyncio.Lock()
        # Create thread pool
        self.executor = ThreadPoolExecutor(max_workers=2)
        print("XTTSWrapper initialized")

    async def play_audio_from_queue(self):
        """Send audio data over WebSocket"""
        self.is_playing = True
        while not self.audio_queue.empty():
            audio_data, sample_rate = await self.audio_queue.get()
            try:
                output_audio = np.array(audio_data, dtype=np.float32)
                await self.websocket.send(output_audio.tobytes())
            except Exception as e:
                print(f"Error playing audio: {e}")
            self.audio_queue.task_done()
        self.is_playing = False

    async def queue_audio(self, audio_data, sample_rate=24000):
        """Add audio to queue and start playback if needed"""
        async with self.lock:
            await self.audio_queue.put((audio_data, sample_rate))
            if not self.is_playing:
                asyncio.create_task(self.play_audio_from_queue())

    def split_text(self, text, max_length=150):
        """Split text into manageable chunks"""
        if len(text) <= max_length:
            return [text]
        chunks = []
        sentences = text.replace("...", ".").split(". ")
        for sentence in sentences:
            if len(sentence) > max_length:
                chunks.extend([sentence[i:i + max_length] for i in range(0, len(sentence), max_length)])
            else:
                chunks.append(sentence)
        return chunks

    def process_text_chunk(self, chunk):
        """Generate audio from text"""
        try:
            out = self.model.inference(
                chunk,
                "en",
                self.gpt_cond_latent,
                self.speaker_embedding,
                temperature=0.65
            )
            return np.array(out["wav"], dtype=np.float32)
        except Exception as e:
            print(f"Error processing chunk: {e}")
            return None

    async def coquiTTS(self, text, wait=True):
        """Convert text to speech"""
        if text.lower() in self.cached_responses:
            audio = self.cached_responses[text.lower()]
            await self.queue_audio(audio)
            if wait:
                await self.audio_queue.join()
            return None if wait else audio
        chunks = self.split_text(text)
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(self.executor, self.process_text_chunk, chunk) for chunk in chunks]
        all_audio = await asyncio.gather(*tasks)
        combined_audio = np.concatenate([audio for audio in all_audio if audio is not None])
        await self.queue_audio(combined_audio)  # Add combined audio to queue
        if wait:
            await self.audio_queue.join()
        else:
            return combined_audio
        return None


class Speech_to_text:
    async def process_text(self, websocket, text):
        if text:
            logging.info(f"Received text: {text}")
            try:
                text = "Prompt: Answer in 30 words only for : " + text
                generate_response = GenerateResponse()
                response = generate_response.response_claude(text)
                logging.info(f"Response: {response}")
                xtts = XTTSWrapper(websocket, response)
                await xtts.coquiTTS(response)
            except Exception as e:
                logging.error(f"Error processing text: {str(e)}")
                await websocket.send("Error processing your request.".encode())

    # WebSocket handler for text input
    async def handle_text(self, websocket):
        logging.info("New client connected.")
        text = "Generate a brief intro about yourself, duplex builders and the properties for the user."
        greeted = False
        flag = 1
        while True:
            try:
                if flag and not greeted:
                    logging.info("Entered in greeting section.")
                    greeted = True
                    await self.process_text(websocket, text)
                text = await websocket.recv()
                if text == "conversation has ended":
                    logging.info("Connection Terminated.")
                    break
                if text == "INITIAL_CONNECTION":
                    continue
                await self.process_text(websocket, text)
            except websockets.exceptions.ConnectionClosed:
                logging.info("Client disconnected.")
                break
            except Exception as e:
                logging.error(f"WebSocket error: {str(e)}")
                break

    async def google_speech_recognizer(self, websocket):
        recognizer = sr.Recognizer()
        while True:
            with sr.Microphone() as source:
                # Adjust for ambient noise and record audio
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source)
                try:
                    # Recognize speech using Google Speech Recognition
                    text = recognizer.recognize_google(audio)
                except Exception as e:
                    text = ""
                await self.process_text(text)


async def main():
    start_server = await websockets.serve(Speech_to_text().handle_text, "0.0.0.0", 8765)
    logging.info("WebSocket server started on ws://0.0.0.0:8765")
    await start_server.wait_closed()
    logging.info("Connection Terminated.")


if __name__ == "__main__":
    logging.info("AI Caller is running.")
    print("AI Caller is running.")
    asyncio.run(main())
