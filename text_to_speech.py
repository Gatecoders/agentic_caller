import os
import io
import struct
import logging
import boto3
from pydub import AudioSegment
from google.cloud import texttospeech
from dotenv import load_dotenv

load_dotenv()


class AzureTTS:
    def __init__(self):
        pass

    async def azure_tts(self, websocket, text: str, speaker: str) -> float:
        """Synthesise with Azure Cognitive Speech and stream over websocket."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            SPEECH_KEY    = os.getenv("AZURE_TTS_KEY")
            SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

            speech_config  = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
            speech_config.speech_synthesis_voice_name = speaker or "en-IN-NeerjaNeural"

            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
            )
            # Synthesise to an in-memory stream
            # stream        = speechsdk.audio.AudioOutputStream()   # use when need to run on local
            stream = speechsdk.audio.PullAudioOutputStream()  # use when need to stream over websocket
            audio_config  = speechsdk.audio.AudioOutputConfig(stream=stream)
            synthesizer   = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            result         = synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data
                duration   = TextToSpeech().mp3_duration(audio_data)
                await websocket.send(audio_data)
                logging.info(f"Azure TTS done, {duration:.2f}s")
                return duration
            else:
                logging.error(f"Azure TTS failed: {result.reason}")
                return 0.0
        except Exception as e:
            logging.error(f"Azure TTS error: {e}")
            return 0.0
        

# Amazon TTS
class PollyTTS:
    def __init__(self):
        pass

    async def polly_tts(self, websocket, text: str, speaker: str) -> float:
        """Synthesise with Amazon Polly and stream MP3 bytes over websocket."""
        engine = 'neural' if speaker == 'Kajal' else 'standard'
        try:
            resp = self.polly_client.synthesize_speech(
                TextType='text',
                Text=text,
                Engine=engine,
                LanguageCode="en-IN",
                OutputFormat='mp3',
                VoiceId=speaker
            )
            audio_data = resp['AudioStream'].read()
            duration   = TextToSpeech().mp3_duration(audio_data)
            logging.info(f"Polly TTS — {speaker}, {duration:.2f}s")
            await websocket.send(audio_data)
            return duration
        except Exception as e:
            logging.error(f"Polly TTS error: {e}")
            return 0.0
        

# Google TTS
class GoogleTTS:
    def __init__(self):
        pass

    async def google_cloud_tts(self, websocket, text: str, speaker: str) -> float:
        """Synthesise with Google Cloud TTS and stream MP3 bytes over websocket."""
        try:
            client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-IN",
                name=speaker
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                effects_profile_id=['small-bluetooth-speaker-class-device'],
                speaking_rate=1,
            )
            resp       = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
            audio_data = resp.audio_content
            duration   = TextToSpeech().mp3_duration(audio_data)
            logging.info(f"Google Cloud TTS — {speaker}, {duration:.2f}s")
            await websocket.send(audio_data)
            return duration
        except Exception as e:
            logging.error(f"Google Cloud TTS error: {e}")
            return 0.0



class TextToSpeech:
    def __init__(self):
        self.polly_client = boto3.client('polly', region_name='ap-south-1')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def mp3_duration(audio_bytes: bytes) -> float:
        segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        return len(segment) / 1000.0

    # ------------------------------------------------------------------
    # Local (no websocket) — plays audio directly to speakers/earphones
    # ------------------------------------------------------------------

    def speak_local(self, text: str, speaker: str = "en-IN-Meera:DragonHDLatestNeural") -> float:
        """
        Synthesise with Polly and play directly through the system audio.
        Returns the audio duration in seconds.
        """
        try:
            import pygame
            import tempfile
            import os
            from dotenv import load_dotenv
            import azure.cognitiveservices.speech as speechsdk

            load_dotenv()

            speech_key = os.getenv("AZURE_TTS_KEY")
            service_region = os.getenv("AZURE_SPEECH_REGION")

            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)

            speech_config.speech_synthesis_voice_name = speaker

            # IMPORTANT: ensure WAV output
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
            )

            speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = speech_synthesizer.speak_text_async(text).get()

            audio_data = result.audio_data

            pygame.mixer.init(frequency=22050)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                tmp = f.name

            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            pygame.mixer.music.stop()
            pygame.mixer.quit()

            os.unlink(tmp)
        except Exception as e:
            logging.error(f"Local TTS playback error: {e}")
            return 0.0

    # ------------------------------------------------------------------
    # Dispatcher  (used by server / local-ws modes)
    # ------------------------------------------------------------------

    async def speak(self, websocket, provider: str, text: str, speaker: str) -> float:
        """Route to the correct provider and return audio duration."""
        provider = provider.lower()
        if provider == 'amazon':
            return await PollyTTS().polly_tts(websocket, text, speaker)
        elif provider == 'google':
            return await GoogleTTS().google_cloud_tts(websocket, text, speaker)
        elif provider == 'azure':
            return await AzureTTS().azure_tts(websocket, text, speaker)
        else:
            logging.warning(f"Unknown TTS provider '{provider}', falling back to Azure.")
            return await AzureTTS().azure_tts(websocket, text, speaker)