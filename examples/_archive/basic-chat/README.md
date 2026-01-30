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

## Prompt management

By default the builder loads prompts from `.dare/_prompts.json` in the workspace (repo root) and user home directory, then falls back to the built-in `base.system` prompt. You can override prompt selection in three ways:

1) `CHAT_PROMPT_OVERRIDE` (builder only): inline system prompt content (highest priority).
2) `CHAT_PROMPT_ID`: select a prompt id from the prompt store.
3) `CHAT_DEFAULT_PROMPT_ID`: set the default prompt id in config if no override is provided.

You can change the manifest location with `CHAT_PROMPT_STORE_PATTERN` (defaults to `.dare/_prompts.json`).

Example prompt manifest (`.dare/_prompts.json`):

```json
{
  "prompts": [
    {
      "prompt_id": "base.system",
      "role": "system",
      "content": "You are a concise assistant.",
      "supported_models": ["*"],
      "order": 0
    }
  ]
}
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
