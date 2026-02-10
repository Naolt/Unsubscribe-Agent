# LLM Configuration Guide

The unsubscribe agent now supports configurable LLM providers for both email processing and browser automation through environment variables.

## Quick Setup

1. Copy the environment template:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` with your preferred LLM provider and API key

3. Test your configuration:
   ```bash
   uv run example_usage.py
   ```

## Environment Variables

Create a `.env` file in your project root with the following variables:

### LLM Configuration

```bash
# Email Processing LLM Configuration
LLM_MODEL_PROVIDER=google_genai  # or openai, anthropic
LLM_MODEL_NAME=gemini-2.5-flash  # varies by provider

# API Keys (only set the one for your chosen provider)
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Browser Automation LLM Configuration
BROWSER_LLM_PROVIDER=ollama  # or gemini
BROWSER_MODEL_NAME=tinyllama:1.1b  # Model for browser automation

# Logging
LOG_LEVEL=INFO
```

## Supported Providers and Models

### Email Processing Providers

#### Google Gemini
```bash
LLM_MODEL_PROVIDER=google_genai
LLM_MODEL_NAME=gemini-2.5-flash  # or gemini-1.5-pro, gemini-1.5-flash
GOOGLE_API_KEY=your_key_here
```

#### OpenAI GPT
```bash
LLM_MODEL_PROVIDER=openai
LLM_MODEL_NAME=gpt-4  # or gpt-4-turbo, gpt-3.5-turbo
OPENAI_API_KEY=your_key_here
```

#### Anthropic Claude
```bash
LLM_MODEL_PROVIDER=anthropic
LLM_MODEL_NAME=claude-3-sonnet-20240229  # or claude-3-haiku-20240307, claude-3-opus-20240229
ANTHROPIC_API_KEY=your_key_here
```

### Browser Automation Providers

#### Ollama (Local Models)
```bash
BROWSER_LLM_PROVIDER=ollama
BROWSER_MODEL_NAME=tinyllama:1.1b  # Fast, lightweight model
# BROWSER_MODEL_NAME=llama3.2:3b    # Better quality, larger model
# BROWSER_MODEL_NAME=qwen2.5:3b     # Alternative high-quality model
```

**Popular Ollama Models:**
- `tinyllama:1.1b` - Fastest, smallest model (default)
- `llama3.2:3b` - Good balance of speed and quality
- `llama3.2:1b` - Faster than 3b, better than tinyllama
- `qwen2.5:3b` - High-quality alternative to Llama
- `phi3:mini` - Microsoft's efficient model

#### Google Gemini (Browser Automation)
```bash
BROWSER_LLM_PROVIDER=gemini
BROWSER_MODEL_NAME=gemini-2.5-flash  # or gemini-1.5-pro, gemini-1.5-flash
GOOGLE_API_KEY=your_key_here
```

## Example .env File

```bash
# Using Google Gemini for both email processing and browser automation
LLM_MODEL_PROVIDER=google_genai
LLM_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=AIzaSyDUcc3lVUzIV6_xRRZUbN_hnmTT-KW8b5Q
BROWSER_LLM_PROVIDER=gemini
BROWSER_MODEL_NAME=gemini-2.5-flash
LOG_LEVEL=INFO
```

## Using the Template

The project includes an `env.example` file with all configuration options. To use it:

1. Copy the template to create your `.env` file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` to uncomment and configure your preferred provider and Ollama model:

## Model Selection Guide

### For External LLM Providers (Email Processing)
- **Google Gemini**: Best for general email processing, good balance of cost and quality
- **OpenAI GPT-4**: Highest quality but more expensive
- **Anthropic Claude**: Good alternative with strong reasoning capabilities

### For Local Ollama Models (Browser Automation)
- **tinyllama:1.1b**: Fastest, good for simple tasks, minimal resource usage
- **llama3.2:3b**: Better quality for complex browser interactions
- **qwen2.5:3b**: Alternative high-quality model with good performance

### Hybrid Setup (Recommended)
Use an external provider for email processing and a local Ollama model for browser automation:
```bash
# External provider for email analysis
LLM_MODEL_PROVIDER=google_genai
LLM_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your_key_here

# Local model for browser automation
BROWSER_LLM_PROVIDER=ollama
BROWSER_MODEL_NAME=llama3.2:3b
```

### All-Gemini Setup
Use Gemini for both email processing and browser automation:
```bash
# Gemini for email processing
LLM_MODEL_PROVIDER=google_genai
LLM_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your_key_here

# Gemini for browser automation
BROWSER_LLM_PROVIDER=gemini
```

### All-Local Setup
Use Ollama for browser automation (email processing still needs external provider):
```bash
# External provider for email analysis (required)
LLM_MODEL_PROVIDER=google_genai
LLM_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your_key_here

# Local model for browser automation
BROWSER_LLM_PROVIDER=ollama
BROWSER_MODEL_NAME=llama3.2:3b
```

## Switching Providers

To switch providers, simply update your `.env` file:

1. Change `LLM_MODEL_PROVIDER` to your desired provider
2. Set the appropriate `LLM_MODEL_NAME` for that provider
3. Set the corresponding API key
4. Restart your application

## Benefits

- **Flexibility**: Switch between different LLM providers easily
- **Cost optimization**: Use different models based on your needs
- **Performance tuning**: Choose models based on speed vs accuracy trade-offs
- **Fallback options**: Switch providers if one is unavailable
- **Local privacy**: Use Ollama for browser automation without sending data externally
