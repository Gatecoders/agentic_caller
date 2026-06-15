import asyncio
import logging
import time
import websockets

from generate_response import GenerateResponse
from text_to_speech import TextToSpeech


class ConversationHandler:
    """
    Encapsulates the full Eva conversation flow.
    Used by both server.py (remote websocket) and local.py (local websocket mode).
    """

    MAX_ATTEMPTS    = 2
    TIMEOUT_SECONDS = 10

    def __init__(self):
        self.tts = TextToSpeech()

    # ------------------------------------------------------------------
    # Low-level send / receive helpers
    # ------------------------------------------------------------------

    async def _speak(self, websocket, provider: str, text: str, speaker: str) -> float:
        """Send TTS audio over websocket and return its duration."""
        return await self.tts.speak(websocket, provider, text, speaker)

    async def _listen(self, websocket, timeout: float) -> str:
        """Wait for the next text message from the client."""
        return await asyncio.wait_for(websocket.recv(), timeout=timeout)

    async def _speak_and_listen(
        self, websocket, provider: str, text: str, speaker: str
    ) -> str:
        """
        Speak `text`, then wait for a reply.
        Retries up to MAX_ATTEMPTS times before giving up.
        """
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            duration = await self._speak(websocket, provider, text, speaker)
            try:
                response = await self._listen(
                    websocket, self.TIMEOUT_SECONDS + (duration or 0)
                )
                if response:
                    return response
            except asyncio.TimeoutError:
                logging.info(f"Timeout waiting for response — attempt {attempt}/{self.MAX_ATTEMPTS}")
        return ""

    # ------------------------------------------------------------------
    # LLM helper
    # ------------------------------------------------------------------

    async def _process(self, websocket, query: str, provider: str, speaker: str) -> str:
        """Generate an LLM reply for `query` (does NOT speak it yet)."""
        if not query:
            return ""
        try:
            prompt   = "Prompt: Answer in 30 words only for : " + query
            response = GenerateResponse().get_response(prompt)
            logging.info(f"LLM response: {response}")
            return response
        except Exception as e:
            logging.error(f"LLM error: {e}")
            return "Sorry, your query cannot be answered due to data unavailability."

    # ------------------------------------------------------------------
    # Main conversation flow
    # ------------------------------------------------------------------

    async def handle(self, websocket, user: str, title: str, provider: str, speaker: str):
        """Run the full Eva calling script for one connected client."""
        gr = GenerateResponse()

        # ── Step 1: Confirm identity ────────────────────────────────────
        time.sleep(1)
        text_init = f"Hello, This is Eva calling. Am I speaking with {title} {user}?"
        logging.info(text_init)
        response = await self._speak_and_listen(websocket, provider, text_init, speaker)
        logging.info(f"User: {response}")
        gr.save_conversation(text_init, response)

        negative_words = {"no", "sorry", "not", "nope", "unfortunately", "pardon", "wrong number"}
        if any(w in response.lower() for w in negative_words):
            await self._speak(websocket, provider,
                "Oh, I am so sorry! I must have dialled the wrong number. "
                "Thank you for your time and have a nice day.", speaker)
            gr.save_conversation("", "Connection Terminated.")
            gr.delete_conversation()
            logging.info("Terminated — wrong person.")
            return

        # ── Step 2: Polite intro ─────────────────────────────────────────
        time.sleep(1)
        polite_intro = (
            f"Hello {title} {user}! Sorry to call out of the blue. "
            f"I am Eva from {gr.company_name}. How are you doing today?"
        )
        logging.info(polite_intro)
        response = await self._speak_and_listen(websocket, provider, polite_intro, speaker)
        gr.save_conversation(polite_intro, response)
        logging.info(f"User: {response}")

        # ── Step 3: Check availability ───────────────────────────────────
        bad_feeling = {"not good", "not great", "not doing good", "not doing great",
                       "not fine", "not doing fine"}
        prefix = "Oh, I am so sorry to hear that. " if any(b in response.lower() for b in bad_feeling) else "Great!, "
        check = prefix + "is it a good time to talk?"
        time.sleep(1)
        logging.info(check)
        response = await self._speak_and_listen(websocket, provider, check, speaker)
        gr.save_conversation(check, response)
        logging.info(f"User: {response}")

        if any(w in response.lower() for w in {"no", "not really", "nope"}):
            await self._speak(websocket, provider,
                "Oh, I am so sorry for the inconvenience! "
                "I will let you go and reach out at a better time. Have a great day ahead!", speaker)
            gr.save_conversation("", "Connection Terminated.")
            gr.delete_conversation()
            logging.info("Terminated — bad time.")
            return

        # ── Step 4: Offer pitch ──────────────────────────────────────────
        time.sleep(1)
        confirmation = (
            f"Thank you, {title} {user}. The reason I am calling is to tell you about "
            f"{gr.company_name} and what we have available. Would you like to hear more?"
        )
        logging.info(confirmation)
        response = await self._speak_and_listen(websocket, provider, confirmation, speaker)
        gr.save_conversation(confirmation, response)

        if any(w in response.lower() for w in {"no", "nope", "not interested"}):
            await self._speak(websocket, provider,
                "Oh, I am so sorry! Let me know if you change your mind. Have a nice day.", speaker)
            gr.save_conversation("", "Connection Terminated.")
            gr.delete_conversation()
            logging.info("Terminated — not interested.")
            return

        # ── Step 5: Free-form conversation loop ──────────────────────────
        text = (
            f"Generate a brief intro about {gr.company_name} for the user "
            "and ask if they are interested in it."
        )
        greeted = False
        while True:
            logging.info("Conversation loop tick.")
            try:
                if not greeted:
                    greeted = True
                    text = await self._process(websocket, text, provider, speaker)

                response = await self._speak_and_listen(websocket, provider, text, speaker)

                if response == "conversation has ended":
                    logging.info("Conversation ended by client.")
                    gr.delete_conversation()
                    break
                if response == "INITIAL_CONNECTION":
                    continue

                text = await self._process(websocket, response, provider, speaker)

            except websockets.exceptions.ConnectionClosed:
                logging.info("Client disconnected.")
                break
            except Exception as e:
                logging.error(f"Conversation loop error: {e}")
                break