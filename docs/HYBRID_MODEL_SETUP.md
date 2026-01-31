# Hybrid Model Setup Guide

## Overview

The assistant now supports a hybrid model approach:
- **DeepSeek Coder**: For code generation tasks (cheap, fast, specialized)
- **Claude Sonnet 3.5**: For complex reasoning, debugging, explanations (better quality, larger context)

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# OpenAI (for embeddings - required for RAG)
OPENAI_API_KEY=sk-your-openai-key

# DeepSeek Coder (for code generation)
DEEPSEEK_API_KEY=sk-your-deepseek-key
DEEPSEEK_MODEL=deepseek-coder

# Anthropic Claude (for complex tasks)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Hybrid Model Settings
USE_HYBRID_MODELS=true  # Enable automatic routing
DEFAULT_PROVIDER=deepseek  # Fallback if routing fails

# Context Management
MAX_CONTEXT_TOKENS=10000  # For DeepSeek (16K limit)
MAX_CONTEXT_TOKENS_CLAUDE=150000  # For Claude (200K limit)
CONTEXT_SUMMARIZATION_THRESHOLD=0.75  # Summarize at 75% of limit
PRESERVE_RECENT_MESSAGES=8  # Keep last N messages verbatim
ENABLE_MEMORY_DB=true  # Enable persistent memory
```

## How It Works

### Automatic Task Classification

The system automatically classifies tasks:

**Code Generation → DeepSeek Coder:**
- "Create a todo app"
- "Add error handling function"
- "Generate REST API endpoints"
- "Write a Python class"

**Complex Tasks → Claude Sonnet:**
- "Explain this code"
- "Why is this error happening?"
- "Refactor the entire module"
- "Analyze the codebase architecture"
- "Debug this issue"

### Memory Management

The system includes comprehensive memory management:

1. **Token-Based Truncation**: Automatically manages context size
2. **Progressive Summarization**: Summarizes old messages when approaching limits
3. **Facts Extraction**: Extracts and stores key information (files created, decisions made)
4. **Persistent Memory**: Stores conversation summaries and facts in database
5. **Session Management**: Maintains context across WebSocket connections

### Context Limits

- **DeepSeek Coder**: 10K tokens (leaves room for response in 16K limit)
- **Claude Sonnet**: 150K tokens (leaves room for response in 200K limit)

When context approaches limits:
- Old messages are summarized
- Recent messages kept verbatim
- Facts extracted and stored
- Context stays within limits

## Benefits

1. **Cost Efficient**: ~80% of requests use DeepSeek (cheap)
2. **High Quality**: Complex tasks use Claude (better reasoning)
3. **Long Conversations**: Memory management enables 100+ message conversations
4. **Large Codebases**: Can handle projects with 1000+ files
5. **Persistent Memory**: Remembers context across sessions

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up API keys in `.env` file

3. Restart the backend:
```bash
cd web/backend
python app.py
```

## Usage

The system works automatically. Just use the assistant as normal:

- Code generation tasks → automatically use DeepSeek
- Complex tasks → automatically use Claude
- Memory management → automatic

## Monitoring

Check which model was used in the response. The system logs:
- Model used for each request
- Token usage per model
- Cost tracking per model

Type `stats` in chat to see usage statistics.

## Troubleshooting

**No provider available error:**
- Make sure at least one API key is configured
- Check `.env` file has correct keys

**Memory issues:**
- Adjust `MAX_CONTEXT_TOKENS` if needed
- Increase `PRESERVE_RECENT_MESSAGES` for more context
- Check `.memory.db` file size

**Model routing issues:**
- Set `USE_HYBRID_MODELS=false` to use single provider
- Set `DEFAULT_PROVIDER` to force a specific model






