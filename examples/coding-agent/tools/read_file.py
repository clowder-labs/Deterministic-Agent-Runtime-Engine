"""
Read File Tool

验证点：
1. ITool 接口是否足够表达工具能力？
2. input_schema / output_schema 格式是否合理？
3. risk_level 分类是否准确？
4. 错误处理如何表达？
"""

from typing import Any
from pathlib import Path

from dare_framework.errors import ToolError
from dare_framework.models import Evidence, RunContext, ToolResult, ToolRiskLevel, ToolType, new_id


class ReadFileTool:  # (ITool)
    """
    读取文件工具

    功能：读取指定路径的文件内容
    风险级别：READ_ONLY（只读，无副作用）
    """

    def __init__(self, workspace: str = "."):
        """
        Args:
            workspace: 工作目录，限制文件访问范围
        """
        self._workspace = Path(workspace).resolve()

    # === 基本属性 ===

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return """Read the contents of a file.

Use this tool when you need to:
- View source code
- Read configuration files
- Examine documentation

The file path should be relative to the workspace root.
"""

    # === Schema 定义 ===
    # 验证：这种格式是否对 LLM 友好？

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read (relative to workspace)"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding",
                    "default": "utf-8"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Start reading from this line (1-indexed, optional)"
                },
                "end_line": {
                    "type": "integer",
                    "description": "Stop reading at this line (1-indexed, optional)"
                }
            },
            "required": ["path"]
        }

    @property
    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "File content"
                },
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file"
                },
                "size_bytes": {
                    "type": "integer",
                    "description": "File size in bytes"
                },
                "line_count": {
                    "type": "integer",
                    "description": "Number of lines in the file"
                },
                "truncated": {
                    "type": "boolean",
                    "description": "Whether the content was truncated"
                }
            }
        }

    # === 风险与权限 ===
    # 验证：这些属性是否足够？

    @property
    def risk_level(self):  # -> ToolRiskLevel
        return ToolRiskLevel.READ_ONLY

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def requires_approval(self) -> bool:
        return False  # 只读操作不需要审批

    @property
    def timeout_seconds(self) -> int:
        return 10  # 读文件应该很快

    # === 产出断言 ===
    # 验证：断言格式是否合理？用于确定性覆盖计算

    @property
    def produces_assertions(self) -> list:
        return [
            # Assertion(type="file_content", produces={"path": "*"})
            {"type": "file_content", "produces": {"path": "*"}}
        ]

    @property
    def is_work_unit(self) -> bool:
        return False

    # === 执行逻辑 ===

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext,
    ) -> ToolResult:
        """
        执行读取文件

        验证：
        1. 输入已经过框架消毒，这里是否还需要验证？
        2. 错误应该 raise 还是返回错误对象？
        3. 执行上下文应该包含什么？
        """
        path = input["path"]
        encoding = input.get("encoding", "utf-8")
        start_line = input.get("start_line")
        end_line = input.get("end_line")

        # 路径安全检查（框架应该已经做过，这里是防御性编程）
        abs_path = self._resolve_path(path)

        # 读取文件
        try:
            content = abs_path.read_text(encoding=encoding)
        except FileNotFoundError:
            # 验证：错误如何表达？
            raise ToolError(
                code="FILE_NOT_FOUND",
                message=f"File not found: {path}",
                retryable=False,
            )
        except PermissionError:
            raise ToolError(
                code="PERMISSION_DENIED",
                message=f"Permission denied: {path}",
                retryable=False,
            )

        # 处理行范围
        lines = content.splitlines(keepends=True)
        if start_line or end_line:
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else len(lines)
            lines = lines[start_idx:end_idx]
            content = "".join(lines)

        # 截断过长内容（验证：截断策略应该在哪里定义？）
        max_chars = 100000
        truncated = len(content) > max_chars
        if truncated:
            content = content[:max_chars] + "\n... [truncated]"

        return ToolResult(
            success=True,
            output={
                "content": content,
                "path": str(abs_path),
                "size_bytes": abs_path.stat().st_size,
                "line_count": len(lines),
                "truncated": truncated,
            },
            evidence=[
                Evidence(
                    evidence_id=new_id("evidence"),
                    kind="file_read",
                    payload={"path": str(abs_path)},
                )
            ],
        )

    def _resolve_path(self, path: str) -> Path:
        """解析并验证路径"""
        # 防止路径遍历攻击
        resolved = (self._workspace / path).resolve()
        if not resolved.is_relative_to(self._workspace):
            raise ToolError(
                code="PATH_TRAVERSAL",
                message=f"Path traversal attempt: {path}",
                retryable=False,
            )
        return resolved
