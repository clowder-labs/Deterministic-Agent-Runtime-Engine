"""
Run Tests Tool

验证点：
1. 产出证据的工具如何定义 produces_assertions？
2. 长时间运行的工具如何处理超时？
"""

from typing import Any
import asyncio

from dare_framework.components.base_component import BaseComponent
from dare_framework.contracts.evidence import Evidence
from dare_framework.contracts.ids import generator_id
from dare_framework.contracts.risk import RiskLevel
from dare_framework.contracts.run_context import RunContext
from dare_framework.contracts.tool import ToolResult, ToolType


class RunTestsTool(BaseComponent):
    """
    运行测试工具

    功能：运行项目的测试套件
    风险级别：READ_ONLY（不修改代码，只运行测试）
    """

    @property
    def name(self) -> str:
        return "run_tests"

    @property
    def description(self) -> str:
        return """Run the project's test suite.

Use this tool when you need to:
- Verify code changes work correctly
- Check for regressions
- Validate bug fixes
"""

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Test file or directory to run",
                },
                "pattern": {
                    "type": "string",
                    "description": "Test name pattern to match",
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Enable verbose output",
                    "default": False,
                },
            },
        }

    @property
    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "passed": {"type": "integer"},
                "failed": {"type": "integer"},
                "skipped": {"type": "integer"},
                "output": {"type": "string"},
                "failures": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "test": {"type": "string"},
                            "error": {"type": "string"},
                        },
                    },
                },
            },
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.READ_ONLY

    @property
    def tool_type(self) -> ToolType:
        return ToolType.WORKUNIT

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 300

    @property
    def produces_assertions(self) -> list:
        return [
            {"type": "test_pass", "produces": {"suite": "unit"}},
            {"type": "evidence_type", "produces": {"types": ["TEST_REPORT"]}},
        ]

    @property
    def is_work_unit(self) -> bool:
        return True

    async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult:
        cmd = ["pytest", "--tb=short", "-q"]

        if input.get("path"):
            cmd.append(input["path"])
        if input.get("pattern"):
            cmd.extend(["-k", input["pattern"]])
        if input.get("verbose"):
            cmd.append("-v")

        try:
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                ),
                timeout=self.timeout_seconds,
            )
            stdout, _ = await process.communicate()
            output = stdout.decode("utf-8", errors="replace")

            parsed = self._parse_pytest_output(output)
            success = process.returncode == 0
            return ToolResult(
                success=success,
                output={
                    "success": success,
                    "passed": parsed["passed"],
                    "failed": parsed["failed"],
                    "skipped": parsed["skipped"],
                    "output": output,
                    "failures": parsed["failures"],
                },
                evidence=[
                    Evidence(
                        evidence_id=generator_id("evidence"),
                        kind="test_report",
                        payload={"success": success},
                    )
                ],
            )
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output={
                    "success": False,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "output": "Test execution timed out",
                    "failures": [],
                },
                error="timeout",
                evidence=[],
            )
        except OSError as exc:
            return ToolResult(success=False, output={"success": False, "output": str(exc)}, error=str(exc), evidence=[])

    def _parse_pytest_output(self, output: str) -> dict:
        return {
            "passed": output.count(" passed"),
            "failed": output.count(" failed"),
            "skipped": output.count(" skipped"),
            "failures": [],
        }
