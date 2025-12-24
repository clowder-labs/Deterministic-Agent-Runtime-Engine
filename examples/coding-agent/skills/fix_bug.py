"""
Fix Bug Skill

验证点：
1. Skill 与 Tool 的边界是否清晰？
2. Skill 内部的决策逻辑如何表达？
3. DonePredicate 如何定义？
4. Skill 如何调用多个 Tool？
"""

from dare_framework.models import Evidence, RunContext, ToolResult, new_id


class FixBugSkill:
    """
    修复 Bug 技能

    这是一个复合技能的占位实现。当前版本仅用于验证
    Plan Tool 的注册与识别，不直接执行具体逻辑。
    """

    @property
    def name(self) -> str:
        return "fix_bug"

    @property
    def description(self) -> str:
        return """Analyze and fix a bug in the codebase.

This skill will:
1. Analyze the bug description
2. Search for relevant code
3. Identify the root cause
4. Generate a fix
5. Verify the fix passes tests
"""

    async def execute(self, input: dict, context: RunContext) -> ToolResult:
        return ToolResult(
            success=False,
            output={"message": "Skill execution is not implemented in MVP."},
            error="not_implemented",
            evidence=[
                Evidence(
                    evidence_id=new_id("evidence"),
                    kind="skill_stub",
                    payload={"name": "fix_bug"},
                )
            ],
        )
