"""LLM-based planner that uses real model to generate plans."""
from __future__ import annotations

import json
from pathlib import Path

from dare_framework.context.kernel import IContext
from dare_framework.context import Message
from dare_framework.infra.component import ComponentType
from dare_framework.model import IModelAdapter, Prompt
from dare_framework.plan.types import ProposedPlan, ProposedStep


class LLMPlanner:
    """Planner that uses LLM to generate plans based on user tasks.

    This planner calls the actual model to understand the task and generate
    appropriate execution steps.
    """

    def __init__(self, model: IModelAdapter, workspace: Path, verbose: bool = True):
        """Initialize with a model adapter.

        Args:
            model: Model adapter for LLM calls.
            workspace: Workspace directory path.
            verbose: Whether to print verbose output.
        """
        self._model = model
        self._workspace = workspace
        self._verbose = verbose

    @property
    def component_type(self) -> ComponentType:
        """Component type for planner."""
        return ComponentType.PLANNER

    @property
    def name(self) -> str:
        return "llm-planner"

    async def plan(self, ctx: IContext) -> ProposedPlan:
        """Generate a plan using LLM.

        Args:
            ctx: Context containing task information.

        Returns:
            Generated plan.
        """
        # Get task description from context STM
        messages = ctx.stm_get()
        task_description = messages[-1].content if messages else "Unknown task"

        # Get available tools
        available_tools = self._get_available_tools()

        # Create prompt for LLM
        system_prompt = self._create_system_prompt(available_tools)
        user_prompt = f"""Task: {task_description}

Workspace: {self._workspace}

Please analyze this task and generate an execution plan using the available tools.
Output ONLY a valid JSON object with this structure:
{{
    "plan_description": "brief description of what the plan will do",
    "steps": [
        {{
            "step_id": "step1",
            "capability_id": "tool_name",
            "params": {{"param1": "value1"}},
            "description": "what this step does"
        }}
    ]
}}

Important:
- Use ONLY the tools listed in the available tools
- Provide concrete parameter values (actual paths, patterns, etc.)
- Keep the plan minimal but effective
- workspace path is: {self._workspace}
"""

        if self._verbose:
            print(f"\n💭 Asking LLM to plan for: {task_description[:50]}...")

        # Call model
        try:
            prompt = Prompt(messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt),
            ])

            response = await self._model.generate(prompt)
            response_text = response.content.strip()

            if self._verbose:
                print(f"📝 LLM response received ({len(response_text)} chars)")

        except Exception as e:
            if self._verbose:
                print(f"⚠️  LLM call failed: {type(e).__name__}: {str(e)[:100]}")
                print(f"⚙️  Using fallback plan...")

            return self._create_fallback_plan(task_description)

        # Parse response
        try:
            plan_data = self._parse_plan_response(response_text)
            steps = [
                ProposedStep(
                    step_id=step["step_id"],
                    capability_id=step["capability_id"],
                    params=step["params"],
                    description=step.get("description", ""),
                )
                for step in plan_data["steps"]
            ]

            # Validate: check if LLM used tool names instead of evidence types
            forbidden_ids = ["read_file", "write_file", "search_code", "run_python", "run_python_file", "open_file", "open_folder"]
            has_tool_calls = any(
                step.capability_id in forbidden_ids
                for step in steps
            )

            if has_tool_calls:
                if self._verbose:
                    print(f"⚠️  LLM returned TOOL CALLS instead of evidence types!")
                    print(f"   Detected tool names: {[s.capability_id for s in steps if s.capability_id in forbidden_ids]}")
                    print(f"   Using fallback plan with correct evidence types...")

                # Reject and use fallback
                return self._create_fallback_plan(task_description)

            plan = ProposedPlan(
                plan_description=plan_data["plan_description"],
                steps=steps,
            )

            if self._verbose:
                print(f"✓ Generated plan with {len(steps)} steps")
                print(f"📋 Plan: {plan_data['plan_description']}")
                for i, step in enumerate(steps, 1):
                    print(f"   {i}. [{step.capability_id}] {step.description}")
                    print(f"      Params: {step.params}")

            return plan

        except Exception as e:
            if self._verbose:
                print(f"⚠️  Failed to parse LLM response, using fallback: {e}")

            # Fallback to simple plan
            return self._create_fallback_plan(task_description)

    def _create_system_prompt(self, available_tools: dict) -> str:
        """Create system prompt for evidence-based planning."""
        return f"""⚠️⚠️⚠️ ABSOLUTELY CRITICAL - READ THIS FIRST ⚠️⚠️⚠️

You are a PLANNING AGENT, NOT an execution agent!

🚫 STRICTLY FORBIDDEN - DO NOT DO THESE:
1. DO NOT output code directly (no Python, JS, HTML, etc.)
2. DO NOT use tool names in capability_id (NEVER use: read_file, write_file, search_code, run_python, open_file)
3. DO NOT plan execution steps - you only define WHAT to achieve, not HOW

✅ YOUR ONLY JOB:
Define EVIDENCE REQUIREMENTS - what proof is needed to show the task is complete.

---

🎯 YOUR ROLE:
- You are NOT an execution agent - you do NOT answer questions directly
- You are NOT planning tool calls - the Execute Loop will decide that (ReAct mode)
- You are defining ACCEPTANCE CRITERIA and EVIDENCE REQUIREMENTS
- Think of yourself as defining "what needs to be proven" to complete the task

⚠️ CRITICAL UNDERSTANDING:
The Plan you generate is a CONTRACT with the user:
- RIGHT PANE (Plan): Acceptance criteria - "What to achieve" ✅
- LEFT PANE (Execute): Task list - "How to do it" (decided by LLM during execution)

Your job: Define the RIGHT PANE (acceptance criteria), NOT the left pane (execution steps)

🎯 OUTPUT FORMAT:
You MUST output ONLY valid JSON with this EXACT structure:
{{
    "plan_description": "Brief description of WHAT needs to be achieved (the goal)",
    "steps": [  // NOTE: "steps" here means "evidence requirements", not "execution steps"
        {{
            "step_id": "evidence_1",
            "capability_id": "evidence_type",  // MUST be one of: file_evidence, search_evidence, summary_evidence, code_creation_evidence, functionality_evidence
            "params": {{"expected_content": "description of what evidence is needed"}},
            "description": "What evidence must be collected to prove this requirement"
        }}
    ]
}}

🚫 ABSOLUTELY FORBIDDEN capability_id values:
- read_file (use file_evidence instead)
- write_file (use code_creation_evidence instead)
- search_code (use search_evidence instead)
- run_python, run_python_file (use functionality_evidence instead)
- open_file, open_folder (never use these)

📋 EVIDENCE TYPES:

Use these capability_id values (NOT tool names):

**For READING/EXPLORING tasks:**

1. "file_evidence" - Proof that relevant files were read and understood
   - params: {{"expected_files": "at least 1 source file", "min_count": 1}}
   - Example: "证据：已读取并理解至少 1 个源文件"

2. "search_evidence" - Proof that code search was performed
   - params: {{"search_target": "what to search for", "min_results": 1}}
   - Example: "证据：搜索到 TODO 注释并提供摘要"

3. "summary_evidence" - Proof that analysis/summary was generated
   - params: {{"required_content": ["项目类型", "主要功能"]}}
   - Example: "证据：生成项目概览（类型、功能、技术栈）"

**For WRITING/CREATING tasks:**

4. "code_creation_evidence" - Proof that code files were created
   - params: {{"expected_files": ["file1.py", "file2.js"], "file_type": "Python/JS/etc"}}
   - Example: "证据：创建了 snake.py 游戏文件"

5. "functionality_evidence" - Proof that code works (runnable/testable)
   - params: {{"test_method": "run/test/demo", "expected_behavior": "what should work"}}
   - Example: "证据：贪吃蛇游戏可以运行并可玩"

⚠️ CRITICAL FOR CODE WRITING TASKS:
- When user asks to "写代码" or "创建程序", DO NOT output code directly!
- Instead, define evidence requirements: "code_creation_evidence" + "functionality_evidence"
- The Execute Loop will write the actual code using write_file tool

🚫 WRONG WAY (Execution steps - DO NOT DO THIS):
{{
    "steps": [
        {{"capability_id": "read_file", "params": {{"path": "sample.py"}}}}  // ❌ This is a tool call!
    ]
}}

✅ CORRECT WAY (Evidence requirements):
{{
    "steps": [
        {{
            "capability_id": "file_evidence",  // ✓ This is evidence type
            "params": {{"expected_files": "至少 1 个源文件"}},
            "description": "证据：已读取并理解源文件内容"
        }}
    ]
}}

📝 EXAMPLES:

User: "这是一个什么项目？"
WRONG (tool calls): {{
    "steps": [
        {{"capability_id": "read_file", "params": {{"path": "sample.py"}}}}  // ❌ Tool call
    ]
}}
CORRECT (evidence requirements): {{
    "plan_description": "理解项目的类型、功能和结构",
    "steps": [
        {{
            "step_id": "evidence_1",
            "capability_id": "file_evidence",
            "params": {{"expected_files": "至少 2 个项目文件（源码或文档）", "min_count": 2}},
            "description": "证据：已读取并理解项目文件内容"
        }},
        {{
            "step_id": "evidence_2",
            "capability_id": "summary_evidence",
            "params": {{"required_content": ["项目类型", "主要功能", "技术栈"]}},
            "description": "证据：生成项目概览总结"
        }}
    ]
}}

User: "Find all TODO comments"
CORRECT: {{
    "plan_description": "查找并汇总代码中的 TODO 注释",
    "steps": [
        {{
            "step_id": "evidence_1",
            "capability_id": "search_evidence",
            "params": {{"search_target": "TODO 注释", "min_results": 0}},
            "description": "证据：搜索到的 TODO 注释列表（可能为空）"
        }}
    ]
}}

User: "探索这个项目的代码结构"
CORRECT: {{
    "plan_description": "理解项目的代码组织和主要模块",
    "steps": [
        {{
            "step_id": "evidence_1",
            "capability_id": "file_evidence",
            "params": {{"expected_files": "多个源文件", "min_count": 3}},
            "description": "证据：已读取多个源文件"
        }},
        {{
            "step_id": "evidence_2",
            "capability_id": "search_evidence",
            "params": {{"search_target": "函数和类定义"}},
            "description": "证据：找到的主要函数和类结构"
        }},
        {{
            "step_id": "evidence_3",
            "capability_id": "summary_evidence",
            "params": {{"required_content": ["模块划分", "主要组件"]}},
            "description": "证据：代码结构总结"
        }}
    ]
}}

User: "写一个可以玩的贪吃蛇游戏"
WRONG (直接写代码): {{
    "plan_description": "创建贪吃蛇游戏",
    "steps": [
        {{
            "step_id": "step1",
            "capability_id": "write_file",  // ❌ Tool name!
            "params": {{"path": "snake.py", "content": "import pygame..."}},  // ❌ Code!
            "description": "Write snake game code"
        }}
    ]
}}
CORRECT (证据要求): {{
    "plan_description": "创建可玩的贪吃蛇游戏",
    "steps": [
        {{
            "step_id": "evidence_1",
            "capability_id": "code_creation_evidence",  // ✓ Evidence type
            "params": {{"expected_files": ["snake.py"], "file_type": "Python游戏"}},
            "description": "证据：创建了贪吃蛇游戏文件 snake.py"
        }},
        {{
            "step_id": "evidence_2",
            "capability_id": "functionality_evidence",
            "params": {{"test_method": "运行测试", "expected_behavior": "游戏可启动并响应键盘操作"}},
            "description": "证据：游戏可以运行并可玩"
        }}
    ]
}}

User: "帮我实现一个计算器程序"
CORRECT: {{
    "plan_description": "创建计算器程序",
    "steps": [
        {{
            "step_id": "evidence_1",
            "capability_id": "code_creation_evidence",
            "params": {{"expected_files": ["calculator.py"], "file_type": "Python"}},
            "description": "证据：创建了 calculator.py 文件"
        }},
        {{
            "step_id": "evidence_2",
            "capability_id": "functionality_evidence",
            "params": {{"test_method": "运行基本计算", "expected_behavior": "能进行加减乘除运算"}},
            "description": "证据：计算器功能正常"
        }}
    ]
}}

🚨 CRITICAL REMINDERS:
1. capability_id MUST be one of:
   - file_evidence, search_evidence, summary_evidence (reading tasks)
   - code_creation_evidence, functionality_evidence (writing tasks)
2. Do NOT use tool names (read_file, write_file, search_code, etc.)
3. Do NOT output code directly - define evidence requirements instead!
4. Think: "What evidence do I need to prove the task is done?"
5. The Execute Loop will decide HOW to collect this evidence (using tools in ReAct mode)
6. Keep it simple: 1-3 evidence requirements usually sufficient
7. For "写XX" tasks: use code_creation_evidence + functionality_evidence"""

    def _get_available_tools(self) -> dict:
        """Get available tools and their descriptions."""
        return {
            "read_file": {
                "description": "Read contents of a file",
                "params": {
                    "path": "absolute file path"
                }
            },
            "search_code": {
                "description": "Search for code patterns using regex",
                "params": {
                    "pattern": "search pattern (regex)",
                    "file_pattern": "file glob pattern (e.g., *.py)"
                }
            },
            "write_file": {
                "description": "Write content to a file",
                "params": {
                    "path": "absolute file path",
                    "content": "file content"
                }
            }
        }

    def _parse_plan_response(self, response: str) -> dict:
        """Parse LLM response to extract plan JSON."""
        # Try to find JSON in response
        response = response.strip()

        # Remove markdown code blocks if present
        if response.startswith("```"):
            lines = response.split("\n")
            # Remove first and last line (code block markers)
            response = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        # Try to parse as JSON
        return json.loads(response)

    def _create_fallback_plan(self, task_description: str) -> ProposedPlan:
        """Create a fallback plan when LLM parsing fails.

        Uses evidence types, not tool names.
        """
        # Simple keyword-based fallback
        task_lower = task_description.lower()

        # Check if it's a writing/creation task
        if any(word in task_lower for word in ["写", "创建", "实现", "开发", "做", "build", "create", "implement"]):
            # Writing task fallback
            return ProposedPlan(
                plan_description=f"创建代码以完成: {task_description}",
                steps=[
                    ProposedStep(
                        step_id="evidence_1",
                        capability_id="code_creation_evidence",
                        params={"expected_files": "代码文件", "file_type": "代码"},
                        description="证据：创建了必要的代码文件",
                    ),
                    ProposedStep(
                        step_id="evidence_2",
                        capability_id="functionality_evidence",
                        params={"test_method": "运行测试", "expected_behavior": "功能正常"},
                        description="证据：代码功能正常",
                    ),
                ],
            )
        elif "read" in task_lower or any(word in task_lower for word in ["什么", "介绍", "about", "探索"]):
            # Task is about reading/understanding the project
            return ProposedPlan(
                plan_description=f"理解项目以回答: {task_description}",
                steps=[
                    ProposedStep(
                        step_id="evidence_1",
                        capability_id="file_evidence",
                        params={"expected_files": "项目文件", "min_count": 1},
                        description="证据：已读取项目文件",
                    ),
                    ProposedStep(
                        step_id="evidence_2",
                        capability_id="summary_evidence",
                        params={"required_content": ["项目信息"]},
                        description="证据：生成项目总结",
                    ),
                ],
            )
        elif "todo" in task_lower or "search" in task_lower or "find" in task_lower:
            return ProposedPlan(
                plan_description=f"搜索以回答: {task_description}",
                steps=[
                    ProposedStep(
                        step_id="evidence_1",
                        capability_id="search_evidence",
                        params={"search_target": "搜索目标", "min_results": 0},
                        description="证据：搜索结果",
                    ),
                ],
            )
        else:
            # Default fallback
            return ProposedPlan(
                plan_description=f"探索项目以回答: {task_description}",
                steps=[
                    ProposedStep(
                        step_id="evidence_1",
                        capability_id="file_evidence",
                        params={"expected_files": "项目文件", "min_count": 1},
                        description="证据：已读取文件",
                    ),
                ],
            )
