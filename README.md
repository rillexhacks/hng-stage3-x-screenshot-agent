# 🐦 Twitter Screenshot Generator Agent

A powerful FastAPI-based agent that generates realistic Twitter screenshots from natural language requests using the A2A (Agent-to-Agent) communication protocol.

**Live:** [Click here to see it in action](https://hng-stage3-x-screenshot-agent.onrender.com/)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-5.0.1-red.svg)](https://redis.io)

## 🚀 Features

- **Natural Language Processing**: Parse requests like "create a tweet for john saying hello world"
- **Realistic Tweet Screenshots**: Generate pixel-perfect Twitter-style images with proper styling
- **A2A Protocol Support**: Full JSON-RPC 2.0 implementation for agent communication via Telex
- **Redis Persistence**: Store generated images and metadata with automatic expiration
- **Flexible Deployment**: Deploy easily on Render or any cloud platform
- **Comprehensive Metrics**: Support for likes, retweets, replies, and views
- **Verification Badges**: Generate verified account screenshots
- **Custom Fonts & Icons**: High-quality Inter fonts and Twitter-style icons



### Prerequisites

- Python 3.8+
- Redis (local or cloud)
- Git

### Local Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd stage3-twitter-screenshot-agent
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run the application**
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## ⚙️ Configuration

Create a `.env` file with the following variables:

```env
# Redis Configuration
REDIS_URL=rediss://your-redis-url  # For cloud Redis (Upstash)
REDIS_HOST=localhost               # For local Redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Agent Configuration
AGENT_URL=https://your-domain.com
AGENT_NAME=Twitter Screenshot Generator
AGENT_ID=twitter_screenshot_agent
LOG_LEVEL=INFO
```

## 🌐 Deployment

### Render Deployment

1. **Connect your repository** to Render
2. **Create a new Web Service**
3. **Configure build settings**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python -m uvicorn src.main:app --host 0.0.0.0 --port $PORT`
4. **Add environment variables** from your `.env` file
5. **Deploy** 🚀

### Other Platforms

The application is containerizable and can be deployed on:
- Heroku
- AWS ECS/Lambda
- Google Cloud Run
- Azure Container Instances

## 📡 API Usage

### Health Check
```bash
GET /
```

### A2A Communication
```bash
POST /a2a
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": "request-id",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "create a verified tweet for john saying Hello world! with 100 likes"
        }
      ]
    }
  }
}
```

### Image Retrieval
```bash
GET /image/{image_id}
```

## 🎯 Supported Request Patterns

The agent understands various natural language patterns:

```
✅ "create a tweet for john saying hello world"
✅ "generate a verified tweet for alice saying test message"
✅ "tweet for bob saying hello with 100 likes and 50 retweets"
✅ "saying hello world username ekene ogukwe"
✅ "for ekene ogukwe saying hello world"
✅ "hello world for john"
✅ "create tweet saying test with 1k likes"
```

### Supported Metrics
- **Likes**: `with 100 likes`, `1k likes`, `1.5m likes`
- **Retweets**: `50 retweets`, `2k retweets`
- **Replies**: `10 replies`, `500 replies`
- **Views**: `1000 views`, `1.2m views`
- **Verification**: `verified tweet`

## 🔧 Development

### Project Structure

- **[`handlers.py`](src/handlers.py)**: Core A2A message processing with robust text extraction
- **[`utils.py`](src/utils.py)**: Tweet screenshot generation using PIL/Pillow
- **[`schemas.py`](src/schemas.py)**: Complete A2A protocol implementation with Pydantic
- **[`router.py`](src/router.py)**: FastAPI routes with comprehensive error handling
- **[`dependencies.py`](src/dependencies.py)**: Redis client with fallback configuration

### Running Tests

```bash
# Start the development server
uvicorn src.main:app --reload

# Test with curl
curl -X POST "http://localhost:8000/a2a" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"test","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"create tweet for test saying hello world"}]}}}'
```

## 🔄 Redis Integration

The agent uses Redis for:
- **Image Storage**: Base64-encoded PNG images with 24-hour TTL
- **Tweet Metadata**: JSON-encoded tweet parameters
- **Performance**: Fast retrieval and automatic cleanup

### Redis Schema
```
image:{image_id} -> base64_encoded_image_data (TTL: 86400s)
tweet:{image_id} -> {"username": "...", "tweet_text": "...", ...}
```

## 🛡️ A2A Protocol Implementation

Full compliance with Agent-to-Agent JSON-RPC 2.0 specification:

- **Message Handling**: Robust text extraction from complex message structures
- **Task Management**: Complete task lifecycle with proper status tracking
- **Artifact Generation**: Structured artifact creation with metadata
- **Error Handling**: Comprehensive error responses with proper codes

## 📊 Performance Features

- **Async/Await**: Non-blocking request processing
- **Image Optimization**: Efficient PNG compression and caching
- **Memory Management**: Automatic cleanup of temporary files
- **Logging**: Comprehensive logging for debugging and monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

