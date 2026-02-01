"""Run the CLI demo script in non-interactive mode."""
from __future__ import annotations

import asyncio
from pathlib import Path

from cli import main as cli_main


if __name__ == "__main__":
    demo_script = Path(__file__).parent / "demo_script.txt"
    asyncio.run(cli_main(["--demo", str(demo_script)]))
