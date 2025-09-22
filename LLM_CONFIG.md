# LLM Configuration Guide

The unsubscribe agent now supports configurable LLM providers through environment variables.

## Quick Setup

1. Copy the environment template:
   ```bash
   cp env.template .env
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
# LLM Provider and Model
LLM_MODEL_PROVIDER=google_genai  # or openai, anthropic
LLM_MODEL_NAME=gemini-2.5-flash  # varies by provider

# API Keys (only set the one for your chosen provider)
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Logging
LOG_LEVEL=INFO
```

## Supported Providers and Models

### Google Gemini
```bash
LLM_MODEL_PROVIDER=google_genai
LLM_MODEL_NAME=gemini-2.5-flash  # or gemini-1.5-pro, gemini-1.5-flash
GOOGLE_API_KEY=your_key_here
```

### OpenAI GPT
```bash
LLM_MODEL_PROVIDER=openai
LLM_MODEL_NAME=gpt-4  # or gpt-4-turbo, gpt-3.5-turbo
OPENAI_API_KEY=your_key_here
```

### Anthropic Claude
```bash
LLM_MODEL_PROVIDER=anthropic
LLM_MODEL_NAME=claude-3-sonnet-20240229  # or claude-3-haiku-20240307, claude-3-opus-20240229
ANTHROPIC_API_KEY=your_key_here
```

## Example .env File

```bash
# Using Google Gemini (default)
LLM_MODEL_PROVIDER=google_genai
LLM_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=AIzaSyDUcc3lVUzIV6_xRRZUbN_hnmTT-KW8b5Q
LOG_LEVEL=INFO
```

## Using the Template

The project includes an `env.example` file with all configuration options. To use it:

1. Copy the template to create your `.env` file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` to uncomment and configure your preferred provider:
   ```bash
   # For Google Gemini (default)
   LLM_MODEL_PROVIDER=google_genai
   LLM_MODEL_NAME=gemini-2.5-flash
   GOOGLE_API_KEY=your_actual_api_key_here
   
   # For OpenAI (uncomment these lines)
   # LLM_MODEL_PROVIDER=openai
   # LLM_MODEL_NAME=gpt-4
   # OPENAI_API_KEY=your_actual_api_key_here
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
