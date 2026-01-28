# Example: Basic Chat (stdin/stdout)

This example demonstrates interactive stdin/stdout chat flows using the canonical `dare_framework` package.

## Dependencies and Environment

```bash
pip install -r requirements.txt
```

Edit `examples/basic-chat/chat_simple.py` (or `chat_env.py` / `chat_builder.py`) to set `MODEL` and `ENDPOINT` (for OpenRouter use `https://openrouter.ai/api/v1`), then export `api_sk` for the API key before running.

```bash
export api_sk=your-key
```

## Run

```bash
python examples/basic-chat/chat_simple.py
```

Type messages and press Enter. Use `/quit` to exit.

## Available variants

- `chat_simple.py`: minimal builder-based chat with inline configuration.
- `chat_env.py`: builder-based configuration via environment variables (and optional debug context logging).
- `chat_builder.py`: explicit builder wiring with the same chat flow.
