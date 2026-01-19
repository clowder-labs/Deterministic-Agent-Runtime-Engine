# Example: Basic Chat (stdin/stdout)

This example demonstrates an interactive stdin/stdout chat flow: read lines from stdin, invoke the v2 Kernel-based agent, and print the model response to stdout.

## Dependencies and Environment

```bash
pip install -r requirements.txt
```

Edit `examples/basic-chat/chat.py` to set `MODEL` and `ENDPOINT` (for OpenRouter use `https://openrouter.ai/api/v1`), then export `api_sk` for the API key before running.

```bash
export api_sk=your-key
```

## Run

```bash
python examples/basic-chat/chat.py
```

Type messages and press Enter. Use `/quit` to exit.
