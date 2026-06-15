"""
server.py — Production WebSocket server.

Designed for cloud / VPS deployment where the frontend runs on a
different origin (or the same server).  SSL is supported via the
commented-out lines below.

Run:
    python server.py
"""

import asyncio
import json
import logging
import os
# import ssl

import websockets
from dotenv import load_dotenv

from speech_to_text import ConversationHandler

load_dotenv()

log_file = os.getenv("LOG_FILE", "server.log")
logging.basicConfig(
    filename=log_file, level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w', force=True
)

HOST = os.getenv("SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("SERVER_PORT", "8000"))


async def handle_client(websocket):
    """Entry-point for each new WebSocket connection."""
    logging.info(f"New connection from {websocket.remote_address}")
    handler = ConversationHandler()

    try:
        # Expect the first message to be a JSON handshake
        raw  = await websocket.recv()
        data = json.loads(raw)

        user     = data.get("username", "")
        title    = data.get("title", "")
        provider = data.get("provider", "amazon").lower()
        speaker  = data.get("voice", "Kajal")

        logging.info(f"Handshake — user={title} {user}, provider={provider}, voice={speaker}")
        await handler.handle(websocket, user, title, provider, speaker)

    except websockets.exceptions.ConnectionClosed:
        logging.info("Client disconnected during handshake.")
    except json.JSONDecodeError:
        logging.error("Invalid JSON in handshake message.")
    except Exception as e:
        logging.error(f"Unhandled error in handle_client: {e}")


async def main():
    # ── Optional SSL (uncomment for HTTPS/WSS) ──────────────────────
    # ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # ssl_context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    # server = await websockets.serve(handle_client, HOST, PORT, ssl=ssl_context)

    server = await websockets.serve(handle_client, HOST, PORT)
    logging.info(f"Server started — ws://{HOST}:{PORT}")
    print(f"✅  Server running on ws://{HOST}:{PORT}")
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())