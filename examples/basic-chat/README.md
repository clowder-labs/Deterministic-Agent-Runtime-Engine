# Example: Basic Chat (stdin/stdout)

This example demonstrates an interactive stdin/stdout chat flow: read lines from stdin, invoke the agent, and print the model response to stdout. It also prints human-readable tracing output from runtime hooks (plan/model/tool events).

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

Type messages and press Enter. Use `/quit` to exit. The output includes tracing lines such as `[plan]`, `[model]`, and `[tool.*]` alongside the final assistant response.
