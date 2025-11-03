import asyncio
import websockets
import logging
import json
import boto3
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from TTS.api import TTS
import time

# Configure logging
logging.basicConfig(filename='/home/ubuntu/ai_caller/caller.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w', force=True)

logging.info("Initializing AI Caller...")

# Load TTS models
tts = TTS(model_name="tts_models/en/ljspeech/vits").to("cpu")
logging.info("TTS model loaded successfully.")

# AWS Bedrock (Llama 3) response generator
def generate_response(formatted_prompt):
    client = boto3.client('bedrock-runtime', region_name='ap-south-1')
    model_id = "meta.llama3-70b-instruct-v1:0"
    input_payload = {"prompt": formatted_prompt}
    
    try:
        response = client.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(input_payload)
        )
        response_body = response['body'].read().decode('utf-8')
        result = json.loads(response_body)
        logging.info("AI response generated successfully.")
        return result.get("generation", "Sorry, I couldn't process your request.")
    except Exception as e:
        logging.error(f"Error generating AI response: {str(e)}")
        return "Sorry, but I am unable to process your query."

# Convert text to speech and send it to the client
async def coquiTTS(websocket, text):
    try:
        print('-----------------------------------------------------',text,'-----------------------------------------------------------')
        output_audio = tts.tts(text=text, speed=1.2, energy=1, pitch=1)
        output_audio = np.array(output_audio, dtype=np.float32)
        await websocket.send(output_audio.tobytes())  # Send audio data to client
        logging.info("TTS response sent successfully.")
    except Exception as e:
        logging.error(f"Error in TTS processing: {str(e)}")

# Process text and generate AI response
async def process_text(websocket, text):
    if text:
        logging.info(f"Received text: {text}")
        try:
            print("+++++++++++++++++++++++++++++",text,"++++++++++++++++++++++++++++")
            if text!="Error in speech recognition" and\
             text!="Speech recognition could not understand the audio" :
                print("=============================redirecting_to_AI============================")
                response = generate_response(text)
            else:
                response=text
            await coquiTTS(websocket, response)
        except Exception as e:
            logging.error(f"Error processing text: {str(e)}")
            await websocket.send("Error processing your request.")

# WebSocket handler with improved silence detection
async def process_audio(websocket):
    buffer = b""
    is_speaking = False
    silence_start = None
    timeout = 2.0  # 2-second silence detection
    logging.info("New client connected.")

    while True:
        try:
            audio_data = await websocket.recv()
            
            # Check if this chunk contains speech (simplified approach: check average amplitude)
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            current_amplitude = np.abs(audio_np).mean()
            
            # Threshold for speech detection (may need adjustment)
            speech_threshold = 500
            
            if current_amplitude > speech_threshold:
                # Speech detected
                if not is_speaking:
                    logging.info("Speech started")
                is_speaking = True
                silence_start = None
                buffer += audio_data
            else:
                # Silence or low volume
                if is_speaking and silence_start is None:
                    silence_start = time.time()
                    logging.info("Silence detected, starting silence timer")
                
                # If still in a conversation, keep buffering during brief silences
                if is_speaking:
                    buffer += audio_data
                
                # Check if silence has lasted long enough to process
                if silence_start and (time.time() - silence_start > timeout) and is_speaking:
                    logging.info(f"Processing speech after {timeout}s silence")
                    is_speaking = False
                    if buffer:
                        recognizer = sr.Recognizer()
                        audio_data_np = np.frombuffer(buffer, dtype=np.int16)
                        audio_data_sr = sr.AudioData(audio_data_np.tobytes(), 16000, 1)  # Changed to 1 channel
                        
                        try:
                            text = recognizer.recognize_google(audio_data_sr)
                            logging.info(f"Speech recognized: {text}")
                            # await process_text(websocket, text)
                        except sr.UnknownValueError:
                            logging.warning("Speech recognition could not understand the audio.")
                            # await websocket.send("Sorry, I could not understand the audio.".encode())
                            text="Speech recognition could not understand the audio"
                        except Exception as e:
                            logging.error(f"Error in speech recognition: {str(e)}")
                            text="Error in speech recognition"
                        
                        await process_text(websocket, text)
                        buffer = b""  # Clear buffer after processing
                        silence_start = None
        
        except websockets.exceptions.ConnectionClosed:
            logging.info("Client disconnected.")
            break
        except Exception as e:
            logging.error(f"WebSocket error: {str(e)}")
            break

# Start WebSocket server
async def main():
    start_server = await websockets.serve(process_audio, "0.0.0.0", 8765)
    logging.info("WebSocket server started on ws://0.0.0.0:8765")
    await start_server.wait_closed()

if __name__ == "__main__":
    logging.info("AI Caller is running.")
    print("AI Caller is running.")
    asyncio.run(main())
