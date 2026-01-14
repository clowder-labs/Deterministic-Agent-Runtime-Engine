from __future__ import annotations

import re

from dare_framework.core.models.context import MilestoneContext
from dare_framework.core.models.plan import (
    DonePredicate,
    Envelope,
    EnvelopeBudget,
    EvidenceCondition,
    ProposedStep,
)
from dare_framework.core.models.runtime import new_id

FIX_HINTS = ("fix", "bug", "修复", "修正")
SEARCH_HINTS = ("search", "grep", "搜索")
READ_HINTS = ("read", "查看", "读取")
WRITE_HINTS = ("write", "update", "写", "写入", "更新")
TEST_HINTS = ("test", "pytest", "测试")
EDIT_INSERT_HINTS = ("insert", "add", "增加", "插入")
EDIT_DELETE_HINTS = ("delete", "remove", "删除", "移除")
DEFAULT_EDIT_TEXT = "TEMPORARY LINE: plan test"


def build_demo_steps(
    description: str,
    raw_description: str,
    default_read_path: str,
) -> list[ProposedStep]:
    steps: list[ProposedStep] = []
    if contains_any(description, SEARCH_HINTS):
        steps.append(
            ProposedStep(
                step_id=new_id("step"),
                tool_name="search_code",
                tool_input={"pattern": extract_pattern(description)},
            )
        )
    if contains_any(description, READ_HINTS) or not steps:
        steps.append(
            ProposedStep(
                step_id=new_id("step"),
                tool_name="read_file",
                tool_input={"path": default_read_path},
                envelope=read_envelope(),
            )
        )
    if contains_any(description, EDIT_INSERT_HINTS):
        steps.append(
            ProposedStep(
                step_id=new_id("step"),
                tool_name="edit_line",
                tool_input={
                    "path": default_read_path,
                    "line_number": extract_line_number(description),
                    "text": DEFAULT_EDIT_TEXT,
                    "mode": "insert",
                },
            )
        )
    if contains_any(description, EDIT_DELETE_HINTS):
        steps.append(
            ProposedStep(
                step_id=new_id("step"),
                tool_name="edit_line",
                tool_input={
                    "path": default_read_path,
                    "line_number": extract_line_number(description),
                    "text": DEFAULT_EDIT_TEXT,
                    "mode": "delete",
                    "strict_match": True,
                },
            )
        )
    if contains_any(description, WRITE_HINTS):
        steps.append(
            ProposedStep(
                step_id=new_id("step"),
                tool_name="write_file",
                tool_input={
                    "path": "notes.txt",
                    "content": f"Task notes: {raw_description}",
                },
            )
        )
    if contains_any(description, TEST_HINTS):
        steps.append(
            ProposedStep(
                step_id=new_id("step"),
                tool_name="run_tests",
                tool_input={},
                envelope=test_envelope(),
            )
        )
    return steps


def read_envelope() -> Envelope:
    return Envelope(
        allowed_tools=["read_file"],
        budget=EnvelopeBudget(max_tool_calls=2),
        done_predicate=DonePredicate(
            evidence_conditions=[
                EvidenceCondition(condition_type="evidence_kind", params={"kind": "file_read"})
            ],
            description="Require file_read evidence to finish the step.",
        ),
    )


def test_envelope() -> Envelope:
    return Envelope(
        allowed_tools=["run_tests"],
        budget=EnvelopeBudget(max_tool_calls=1),
        done_predicate=DonePredicate(
            evidence_conditions=[
                EvidenceCondition(condition_type="evidence_kind", params={"kind": "test_report"})
            ],
            description="Require test_report evidence to finish the step.",
        ),
    )


def extract_pattern(description: str) -> str:
    for token in ("todo", "fixme"):
        if token in description:
            return token.upper()
    return "TODO"


def contains_any(description: str, tokens: tuple[str, ...]) -> bool:
    return any(token in description for token in tokens)


def seen_plan_tool(milestone_ctx: MilestoneContext, tool_name: str) -> bool:
    marker = f"plan tool encountered: {tool_name}"
    return any(marker in reflection for reflection in milestone_ctx.reflections)


def extract_line_number(description: str, default: int = 2) -> int:
    match = re.search(r"line\s+(\d+)", description)
    if match:
        return int(match.group(1))
    match = re.search(r"第\s*(\d+)\s*行", description)
    if match:
        return int(match.group(1))
    return default
