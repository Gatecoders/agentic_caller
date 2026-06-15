import os
import queue
import threading

class AzureFoundaryLLM:
    def __init__(self):
        # HARDCODED CONFIGURATION VALUES
        self.api_key = "YOUR_AI_FOUNDARY_API_KEY"      # <-- Paste your actual API Key here
        self.end_point = "YOUR_AI_FOUNDARY_END_POINT"  # <-- Paste your Endpoint URL here
        self.text_model = "gpt-4o"                     # <-- Set your hardcoded LLM deployment name here

    def _text_generation_worker(self, message, sentence_queue):
        """Streams text from your LLM and breaks it down by sentences."""
        from openai import OpenAI
        client = OpenAI(base_url=self.end_point, api_key=self.api_key)
        
        system_instruction = "You are a helpful voice assistant. Keep answers natural, brief, and conversational."
        
        text_stream = client.chat.completions.create(
            model=self.text_model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": message}
            ],
            stream=True
        )
        
        sentence_accumulator = ""
        
        for chunk in text_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                sentence_accumulator += token
                
                # Drop completed phrases/sentences into the pipeline instantly
                if any(punc in token for punc in [".", "!", "?", "\n"]):
                    clean_sentence = sentence_accumulator.strip()
                    if clean_sentence:
                        sentence_queue.put(clean_sentence)
                    sentence_accumulator = ""
                    
        # Grab any remaining string left over at the end
        if sentence_accumulator.strip():
            sentence_queue.put(sentence_accumulator.strip())
            
        # Signal to the audio generator thread that text production has finished
        sentence_queue.put(None)

    def stream_cascaded_audio(self, message, voice_choice="nova"):
        """Consumes generated sentences and instantly converts them to an audio byte stream."""
        from openai import OpenAI
        client = OpenAI(base_url=self.end_point, api_key=self.api_key)
        
        sentence_queue = queue.Queue()
        
        # Start the background text generator thread
        text_thread = threading.Thread(
            target=self._text_generation_worker, 
            args=(message, sentence_queue)
        )
        text_thread.start()
        
        # Pull text blocks as they arrive and process them through the voice profile immediately
        while True:
            sentence = sentence_queue.get()
            if sentence is None: 
                break
                
            with client.audio.speech.with_streaming_response.create(
                model="tts-1",  # Replace with your specific Azure TTS deployment name if unique
                voice=voice_choice,
                input=sentence,
                response_format="mp3"
            ) as response:
                for audio_chunk in response.iter_bytes(chunk_size=1024):
                    yield audio_chunk

if __name__ == "__main__":
    # Swap out text prompt to test
    text = "why the color of the sky is blue?"
    
    llm = AzureFoundaryLLM()
    output_filename = "cascaded_voice.mp3"
    
    print("Streaming live cascading audio stream using the 'nova' profile...")
    print("========================================================================")
    
    with open(output_filename, "wb") as audio_file:
        for chunk in llm.stream_cascaded_audio(text, voice_choice="nova"):
            # Real-time binary bytes are hitting your system here!
            print("⚡", end="", flush=True)
            audio_file.write(chunk)
            
    print(f"\n========================================================================")
    print(f"🎉 Done! Audio binary successfully compiled directly to {output_filename}")