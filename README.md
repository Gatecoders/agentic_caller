# AI Caller

An intelligent AI-powered voice calling system that conducts automated phone conversations using natural language processing and text-to-speech technologies.

## Overview

AI Caller is a Python-based WebSocket server that simulates human-like phone conversations. It uses multiple AI models (Google Gemini, AWS Bedrock Claude, Meta Llama) for response generation and supports various text-to-speech providers (Google Cloud TTS, Amazon Polly) to create natural-sounding voice interactions.

## Features

- **Multi-Model AI Support**: Integrates with Google Gemini, AWS Bedrock (Claude & Llama), offering flexible response generation
- **Multiple TTS Providers**: Supports Google Cloud Text-to-Speech and Amazon Polly with various voice options
- **Context-Aware Conversations**: Maintains conversation history and context throughout the call
- **Intelligent Call Flow**: Handles greetings, availability checks, and graceful exits
- **Real-time Audio Streaming**: WebSocket-based audio transmission for low-latency communication
- **Secure Connection**: SSL/TLS support for encrypted communications
- **Conversation Logging**: Comprehensive logging of all interactions

## Prerequisites

- Python 3.8 or higher
- AWS Account with Bedrock and Polly access
- Google Cloud Account with Text-to-Speech API enabled
- Google Generative AI API key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-caller
```

2. Install required dependencies:
```bash
pip install asyncio websockets boto3 python-dotenv gtts pydub google-cloud-texttospeech google-generativeai
```

3. Set up environment variables by creating a `.env` file:
```env
# Logging
LOG_FILE=logs/ai_caller.log
PREV_REPLY=data/conversation_history.txt

# Company Configuration
COMPANY_NAME=YourCompanyName
DATA_FILE=data/

# API Keys
GOOGLE_GENAI_API_KEY=your_google_genai_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/google-credentials.json

# AWS Credentials for Claude
AWS_ACCESS_KEY_ID_CLAUDE=your_aws_access_key
AWS_SECRET_ACCESS_KEY_CLAUDE=your_aws_secret_key
```

4. Create required directories:
```bash
mkdir -p logs data
```

5. Create a company data file:
   - Create a text file named `{COMPANY_NAME}.txt` in the `data/` directory
   - Add your company information, products, and services

## Usage

### Starting the Server

Run the server:
```bash
python ai_caller.py
```

The WebSocket server will start on `wss://0.0.0.0:8765`

## Architecture

### Main Components

1. **GenerateResponse**: Handles AI response generation
   - Supports multiple AI models (Google Gemini, Claude, Llama)
   - Manages conversation context and history
   - Loads company-specific data

2. **Text_to_Speech**: Converts text responses to audio
   - Google Cloud TTS integration
   - Amazon Polly integration
   - Audio format conversion and streaming

3. **Speech_to_text**: Manages conversation flow
   - Handles WebSocket connections
   - Orchestrates greeting, introduction, and main conversation
   - Implements retry logic for responses
   - Manages graceful disconnections

### Conversation Flow

1. Initial greeting and name confirmation
2. Wrong number handling
3. Polite introduction
4. Availability check
5. Product/service introduction
6. Open-ended conversation with context awareness
7. Graceful exit handling

## Configuration

### Timeout Settings

Modify timeout values in the `Speech_to_text` class:
```python
self.MAX_ATTEMPTS = 2  # Maximum retry attempts
self.TIMEOUT_SECONDS = 10  # Response timeout in seconds
```

### AI Model Selection

The system defaults to Google Gemini with Claude as fallback. To change the primary model, modify the `process_text` method in the `Speech_to_text` class.

## Logging

All interactions are logged to the file specified in `LOG_FILE`. Logs include:
- Connection events
- Conversation transcripts
- Audio generation metrics
- Error messages

## Security Considerations

- Always use SSL/TLS in production
- Rotate API keys regularly
- Implement rate limiting for production use
- Validate and sanitize all user inputs
- Store credentials securely using environment variables
- Never commit `.env` files or credentials to version control

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure the server is running and firewall allows port 8765
2. **Audio Not Playing**: Verify TTS provider credentials and audio format compatibility
3. **AI Response Errors**: Check API keys and model availability in your region
4. **SSL Errors**: Verify certificate paths and validity

### Debug Mode

Enable detailed logging by changing the log level:
```python
logging.basicConfig(level=logging.DEBUG)
```
## Acknowledgments

- Google Generative AI for Gemini models
- AWS Bedrock for Claude and Llama models
- Google Cloud Text-to-Speech
- Amazon Polly
- WebSocket libraries and community
