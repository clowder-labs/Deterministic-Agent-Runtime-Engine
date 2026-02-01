"""DARE Coding Agent Example (CLI entry point)."""
from __future__ import annotations

import asyncio

from cli import main as cli_main


if __name__ == "__main__":
    asyncio.run(cli_main())
