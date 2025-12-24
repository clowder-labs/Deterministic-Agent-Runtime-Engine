"""
Write File Tool

验证点：
1. IDEMPOTENT_WRITE 级别的工具如何处理？
2. 补偿操作（compensate）如何实现？
"""

from typing import Any
from pathlib import Path

from dare_framework.components import BaseComponent
from dare_framework.errors import ToolError
from dare_framework.models import Evidence, RunContext, ToolResult, ToolRiskLevel, ToolType, new_id


class WriteFileTool(BaseComponent):
    """
    写入文件工具

    功能：写入或更新文件内容
    风险级别：IDEMPOTENT_WRITE（幂等写入，可安全重试）
    """

    def __init__(self, workspace: str = "."):
        self._workspace = Path(workspace).resolve()

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return """Write content to a file.

Use this tool when you need to:
- Create new files
- Update existing files
- Save generated code

The file will be created if it doesn't exist.
Parent directories will be created automatically.
"""

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to write to (relative to workspace)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                },
                "mode": {
                    "type": "string",
                    "enum": ["overwrite", "append"],
                    "description": "Write mode",
                    "default": "overwrite"
                },
                "create_dirs": {
                    "type": "boolean",
                    "description": "Create parent directories if needed",
                    "default": True
                }
            },
            "required": ["path", "content"]
        }

    @property
    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "bytes_written": {"type": "integer"},
                "created": {"type": "boolean", "description": "Whether file was created"}
            }
        }

    @property
    def risk_level(self) -> ToolRiskLevel:
        return ToolRiskLevel.IDEMPOTENT_WRITE

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def requires_approval(self) -> bool:
        return False  # 幂等操作，不需要审批

    @property
    def timeout_seconds(self) -> int:
        return 10

    @property
    def produces_assertions(self) -> list:
        return [
            {"type": "file_modified", "produces": {"path": "*"}}
        ]

    @property
    def is_work_unit(self) -> bool:
        return False

    async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult:
        """执行写入"""
        path = input["path"]
        content = input["content"]
        mode = input.get("mode", "overwrite")
        create_dirs = input.get("create_dirs", True)

        abs_path = self._resolve_path(path)
        created = not abs_path.exists()

        if create_dirs:
            abs_path.parent.mkdir(parents=True, exist_ok=True)

        write_mode = "w" if mode == "overwrite" else "a"
        try:
            with open(abs_path, write_mode, encoding="utf-8") as handle:
                bytes_written = handle.write(content)
        except OSError as exc:
            raise ToolError(code="WRITE_FAILED", message=str(exc), retryable=False) from exc

        return ToolResult(
            success=True,
            output={
                "path": str(abs_path),
                "bytes_written": bytes_written,
                "created": created,
            },
            evidence=[
                Evidence(
                    evidence_id=new_id("evidence"),
                    kind="file_write",
                    payload={"path": str(abs_path), "created": created},
                )
            ],
        )

    async def compensate(
        self,
        input: dict[str, Any],
        output: dict[str, Any],
        context: RunContext,
    ) -> None:
        """
        补偿操作：恢复原始文件

        验证：补偿逻辑应该如何实现？
        注意：需要在执行前保存原始内容（由框架处理？）
        """
        # 如果是新创建的文件，删除它
        if output.get("created"):
            Path(output["path"]).unlink(missing_ok=True)
        # 如果是覆盖，需要恢复原内容（需要框架支持）
        else:
            # original_content = context.get_snapshot(output["path"])
            # Path(output["path"]).write_text(original_content)
            pass

    def _resolve_path(self, path: str) -> Path:
        resolved = (self._workspace / path).resolve()
        if not resolved.is_relative_to(self._workspace):
            raise ToolError(code="PATH_TRAVERSAL", message=f"Path traversal attempt: {path}")
        return resolved
