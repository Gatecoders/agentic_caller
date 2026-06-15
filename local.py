"""
local.py — Two local execution modes.

Mode A │ Terminal / Mic  — No frontend needed.
       │ Captures mic audio → Google STT → LLM → Polly plays back on your earphones.
       │ Runs entirely in the terminal.

Mode B │ Local WebSocket  — Frontend running on localhost connects here.
       │ Identical to server.py but bound to 127.0.0.1 and no SSL.

Run:
    python local.py
    … then choose mode A or B at the prompt.
"""

import asyncio
import json
import logging
import os
import tempfile
import time

import websockets
from dotenv import load_dotenv

from generate_response import GenerateResponse
from text_to_speech    import TextToSpeech
from speech_to_text    import ConversationHandler
from config import ENG_FEMALE, ENG_MALE, HINDI_MALE, HINDI_FEMALE

load_dotenv()

log_file = os.getenv("LOG_FILE", "local.log")
logging.basicConfig(
    filename=log_file, level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w', force=True
)

# ──────────────────────────────────────────────────────────────────────────────
# Mode A helpers
# ──────────────────────────────────────────────────────────────────────────────

def capture_mic(timeout: int = 10) -> str:
    """Capture one utterance from the default mic and return transcribed text."""
    try:
        import speech_recognition as sr
    except ImportError:
        print("⚠️  Install SpeechRecognition:  pip install SpeechRecognition pyaudio")
        return ""

    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤  Listening… (speak now)")
        r.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = r.listen(source, timeout=timeout, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            print("⏱️  No speech detected.")
            return ""

    print("🔄  Transcribing…")
    try:
        text = r.recognize_google(audio)
        print(f"You said: {text}")
        return text
    except sr.UnknownValueError:
        print("⚠️  Could not understand audio.")
        return ""
    except sr.RequestError as e:
        print(f"⚠️  STT error: {e}")
        return ""


def list_microphones():
    try:
        import speech_recognition as sr
        print("\nAvailable microphones:")
        for i, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f"  [{i}] {name}")
        print()
    except ImportError:
        print("SpeechRecognition not installed.")


# ──────────────────────────────────────────────────────────────────────────────
# Mode A  — Terminal conversation (no frontend)
# ──────────────────────────────────────────────────────────────────────────────

def run_terminal_mode():
    """Full Eva conversation via mic + terminal, audio played locally."""
    print("\n" + "─" * 60)
    print("  Mode A — Terminal / Mic Conversation")
    print("─" * 60)

    # Optional: choose mic device
    choice = input("List available microphones? [y/N]: ").strip().lower()
    if choice == 'y':
        list_microphones()
        idx = input("Enter mic index (leave blank for default): ").strip()
        mic_index = int(idx) if idx.isdigit() else None
    else:
        mic_index = None

    speaker  = input(f"{ENG_FEMALE}").strip() or "en-IN-Meera:DragonHDLatestNeural"
    user     = input("User name (e.g. John): ").strip() or "User"
    title    = input("Title (e.g. Mr / Ms): ").strip() or "Mr"

    tts = TextToSpeech()
    gr  = GenerateResponse()

    def speak(text: str):
        print(f"\n🔊  Eva: {text}")
        tts.speak_local(text, speaker)

    def listen() -> str:
        try:
            import speech_recognition as sr
        except ImportError:
            return input("Type your reply: ").strip()

        r = sr.Recognizer()
        print("mic_index =", mic_index)
        src = sr.Microphone(device_index=mic_index) if mic_index is not None else sr.Microphone()
        with src as source:
            print("🎤  Listening…")
            r.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = r.listen(source, timeout=10, phrase_time_limit=15)
            except sr.WaitTimeoutError:
                return ""
        try:
            text = r.recognize_google(audio)
            print(f"You: {text}")
            return text
        except Exception:
            return ""

    # ── Conversation flow ────────────────────────────────────────────
    time.sleep(1)
    speak(f"Hello, This is Eva calling. Am I speaking with {title} {user}?")
    response = listen()
    gr.save_conversation(f"Am I speaking with {title} {user}?", response)

    negative_words = {"no", "sorry", "not", "nope", "unfortunately", "pardon", "wrong number"}
    if any(w in response.lower() for w in negative_words):
        speak("Oh, I am so sorry! I must have dialled the wrong number. Thank you and have a nice day.")
        gr.delete_conversation()
        return

    speak(f"Hello {title} {user}! Sorry to call out of the blue. "
          f"I am Eva from {gr.company_name}. How are you doing today?")
    response = listen()
    gr.save_conversation("How are you doing today?", response)

    bad_feeling = {"not good", "not great", "not doing good", "not doing great", "not fine", "not doing fine"}
    prefix  = "Oh, I am so sorry to hear that. " if any(b in response.lower() for b in bad_feeling) else "Great!, "
    speak(prefix + "Is it a good time to talk?")
    response = listen()
    gr.save_conversation("Is it a good time to talk?", response)

    if any(w in response.lower() for w in {"no", "not really", "nope"}):
        speak("I am so sorry for the inconvenience! I will reach out at a better time. Have a great day!")
        gr.delete_conversation()
        return

    speak(f"Thank you, {title} {user}. I am calling to tell you about "
          f"{gr.company_name} and what we offer. Would you like to hear more?")
    response = listen()
    gr.save_conversation("Would you like to hear more?", response)

    if any(w in response.lower() for w in {"no", "nope", "not interested"}):
        speak("I am sorry! Let me know if you change your mind. Have a nice day.")
        gr.delete_conversation()
        return

    # Free-form loop
    intro_prompt = (
        f"Generate a brief intro about {gr.company_name} for the user "
        "and ask if they are interested in it."
    )
    text = gr.get_response("Prompt: Answer in 30 words only for : " + intro_prompt)

    while True:
        speak(text)
        response = listen()
        if not response:
            speak("I did not catch that. Could you please repeat?")
            continue
        if any(w in response.lower() for w in {"bye", "goodbye", "end", "stop", "hang up"}):
            speak("Thank you for your time. Have a wonderful day!")
            gr.delete_conversation()
            break
        text = gr.get_response("Prompt: Answer in 30 words only for : " + response)


# ──────────────────────────────────────────────────────────────────────────────
# Mode B  — Local WebSocket server (frontend on localhost)
# ──────────────────────────────────────────────────────────────────────────────

async def handle_local_ws(websocket):
    """WebSocket handler for a locally-running frontend."""
    logging.info(f"Local WS connection from {websocket.remote_address}")
    handler = ConversationHandler()

    try:
        raw  = await websocket.recv()
        data = json.loads(raw)

        user     = data.get("username", "")
        title    = data.get("title", "")
        provider = data.get("provider", "amazon").lower()
        speaker  = data.get("voice", "Kajal")

        logging.info(f"Local WS handshake — user={title} {user}, provider={provider}, voice={speaker}")
        await handler.handle(websocket, user, title, provider, speaker)

    except websockets.exceptions.ConnectionClosed:
        logging.info("Local WS client disconnected.")
    except json.JSONDecodeError:
        logging.error("Invalid JSON in local WS handshake.")
    except Exception as e:
        logging.error(f"Local WS error: {e}")


def run_local_ws_mode():
    """Start a WebSocket server bound to localhost only."""
    host = "127.0.0.1"
    port = int(os.getenv("LOCAL_PORT", "8000"))

    async def _serve():
        server = await websockets.serve(handle_local_ws, host, port)
        print(f"✅  Local WebSocket server running on ws://{host}:{port}")
        print("    Point your frontend to that address.")
        await server.wait_closed()

    asyncio.run(_serve())


# ──────────────────────────────────────────────────────────────────────────────
# Entry-point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 60)
    print("  Eva AI Caller — Local Mode")
    print("═" * 60)
    print("  A  Terminal + Mic  (no frontend, audio plays on your device)")
    print("  B  Local WebSocket (connect your locally-running frontend)")
    print("─" * 60)

    choice = input("Choose mode [A/B]: ").strip().upper()

    if choice == 'A':
        run_terminal_mode()
    elif choice == 'B':
        run_local_ws_mode()
    else:
        print("Invalid choice. Please run again and enter A or B.")


if __name__ == "__main__":
    main()

    