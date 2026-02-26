"""Main entry for Example 10 minimal loop."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simple_loop import main as simple_main


async def main() -> None:
    await simple_main(sys.argv[1:])


if __name__ == "__main__":
    asyncio.run(main())
