"""
Search Code Tool

验证点：
1. 复杂输出的 schema 如何定义？
2. 搜索类工具的 produces_assertions 应该是什么？
"""

from typing import Any
from pathlib import Path
import re

from dare_framework.components import BaseComponent
from dare_framework.errors import ToolError
from dare_framework.models import Evidence, RunContext, ToolResult, ToolRiskLevel, ToolType, new_id


class SearchCodeTool(BaseComponent):
    """
    代码搜索工具

    功能：在代码库中搜索文本或正则表达式
    风险级别：READ_ONLY
    """

    def __init__(self, workspace: str = "."):
        self._workspace = Path(workspace).resolve()

    @property
    def name(self) -> str:
        return "search_code"

    @property
    def description(self) -> str:
        return """Search for patterns in code files.

Use this tool when you need to:
- Find function definitions
- Locate usages of a variable or function
- Search for specific code patterns
"""

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Search pattern (supports regex)"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: workspace root)"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File glob pattern (e.g., '*.py')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 50
                },
                "context_lines": {
                    "type": "integer",
                    "description": "Lines of context around matches",
                    "default": 2
                }
            },
            "required": ["pattern"]
        }

    @property
    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "matches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "line": {"type": "integer"},
                            "content": {"type": "string"},
                            "context_before": {"type": "array", "items": {"type": "string"}},
                            "context_after": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "total_matches": {"type": "integer"},
                "truncated": {"type": "boolean"}
            }
        }

    @property
    def risk_level(self) -> ToolRiskLevel:
        return ToolRiskLevel.READ_ONLY

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 20

    @property
    def produces_assertions(self) -> list:
        return [{"type": "search_results", "produces": {"pattern": "*"}}]

    @property
    def is_work_unit(self) -> bool:
        return False

    async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult:
        """执行搜索"""
        pattern = input["pattern"]
        search_path = input.get("path", ".")
        file_pattern = input.get("file_pattern", "*")
        max_results = input.get("max_results", 50)
        context_lines = input.get("context_lines", 2)

        matches = []
        regex = re.compile(pattern)

        search_dir = self._workspace / search_path
        for file_path in search_dir.rglob(file_pattern):
            if file_path.is_file() and not self._should_ignore(file_path):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    lines = content.splitlines()

                    for i, line in enumerate(lines):
                        if regex.search(line):
                            matches.append({
                                "file": str(file_path.relative_to(self._workspace)),
                                "line": i + 1,
                                "content": line.strip(),
                                "context_before": lines[max(0, i-context_lines):i],
                                "context_after": lines[i+1:i+1+context_lines],
                            })

                            if len(matches) >= max_results:
                                break
                except OSError as exc:
                    raise ToolError(code="READ_FAILED", message=str(exc)) from exc

            if len(matches) >= max_results:
                break

        return ToolResult(
            success=True,
            output={
                "matches": matches,
                "total_matches": len(matches),
                "truncated": len(matches) >= max_results,
            },
            evidence=[
                Evidence(
                    evidence_id=new_id("evidence"),
                    kind="search_matches",
                    payload={"match_count": len(matches)},
                )
            ],
        )

    def _should_ignore(self, path: Path) -> bool:
        """检查是否应该忽略此文件"""
        ignore_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv"}
        return any(part in ignore_dirs for part in path.parts)
