# Five-Layer Coding Agent - Implementation Status

**Last Updated**: 2025-01-29

## 📊 Current Status

### ✅ Completed Features

#### 1. Evidence-Based Planning System
- **Status**: ✅ Fully implemented
- **Components**:
  - `planners/llm_planner.py` - Generates evidence requirements (not execution steps)
  - `evidence_tracker.py` - Extracts evidence from event log
  - `cli_display.py` - Displays evidence with ✓/✗ marks

**Design**: Plans define verification criteria (what to achieve), Execute Loop uses ReAct mode (model decides how).

#### 2. Enhanced Execute Loop
- **Status**: ✅ Fixed with workarounds
- **File**: `enhanced_agent.py`
- **Fixes**:
  1. Added system message instructing model to use tools
  2. Maps function names to capability IDs (`write_file` → `tool:write_file`)
  3. Handles ReAct mode (when `_session_state` is None)

#### 3. Interactive CLI
- **Status**: ✅ Working
- **Files**: `interactive_cli.py`, `cli_commands.py`, `cli_display.py`
- **Features**:
  - Command system (`/mode`, `/help`, `/quit`)
  - Plan and Execute modes
  - Evidence display after execution

#### 4. Milestone Loop Retry Mechanism
- **Status**: ✅ Framework correct, Validator fixed
- **Framework**: `dare_framework/agent/_internal/five_layer.py:435-493`
- **Fix**: `validators/simple_validator.py` - No longer always returns `success=True`

**Behavior**: When verification fails → Remediate → Retry (up to 3 attempts)

### 🐛 Known Issues

#### Issue #1: Free Models Don't Reliably Call Tools

**Severity**: 🔴 Critical
**Status**: ⚠️ Workaround (use paid models)

**Symptoms**:
```
[DEBUG] Model returned NO tool calls (finish_reason: stop)
✓ Task completed successfully!  ← But no files created!
```

**Root Cause**: Free OpenRouter models (e.g., `arcee-ai/trinity-large-preview:free`, `google/gemini-flash-1.5:free`) have inconsistent function calling support.

**What We Tried**:
1. ✅ Added strong system message ("YOU MUST USE TOOLS")
2. ✅ Provided tools correctly in API call
3. ✅ Verified tools are sent to model
4. ❌ Model still returns text instead of calling tools

**Workarounds**:
- Use paid models: `google/gemini-flash-1.5`, `claude-sonnet-3.5`, `gpt-4o`
- Use local models with Ollama (e.g., `llama3.1`)
- Accept that free models are unreliable for this use case

**Decision**: This is a model capability issue, not a framework bug. Document it and recommend better models.

#### Issue #2: Workspace Configuration

**Severity**: ⚠️ Medium
**Status**: 🔍 Under investigation

**Symptom**: Tool invocation succeeds but file not found at expected path.

**Possible Causes**:
- Envelope not configured with workspace_roots
- Tool writes to different directory
- Path resolution issue

**TODO**: Add debug logging to show actual file paths created.

### 🚧 MVP Limitations

#### 1. No Remediator Implementation

**Status**: ⚠️ MVP - Left empty
**Framework Support**: ✅ Exists (called in Milestone Loop)
**Example Implementation**: ❌ Not implemented

**Current Behavior**: When verification fails, retry with no additional context.

**Future Enhancement**: Implement `LLMRemediator` to generate structured reflections.

#### 2. Simplified Evidence Matching

**Status**: ⚠️ MVP - Heuristic matching
**File**: `evidence_tracker.py`

**Current**: Matches evidence by capability_id using simple string matching.

**Future**:
- Semantic evidence matching
- Richer event log queries
- Evidence provenance tracking

#### 3. No Event Log Persistence

**Status**: ⚠️ MVP - In-memory only
**Framework Support**: ✅ IEventLog interface exists

**Impact**: Evidence extraction only works within single session.

**Future**: Persist event log to enable cross-session evidence tracking.

## 🗂️ File Organization

### Core Components (Root)

```
interactive_cli.py          - Main CLI application
enhanced_agent.py           - Enhanced agent with tool calling fixes
cli_commands.py             - Command parser and session state
cli_display.py              - Display formatters
evidence_tracker.py         - Evidence extraction logic
scenarios.py                - Example scenarios
```

### Supporting Modules

```
planners/
  ├── __init__.py
  ├── llm_planner.py         - Evidence-based LLM planner
  └── deterministic_planner.py

validators/
  ├── __init__.py
  └── simple_validator.py    - Fixed validator (checks outputs)

model_adapters/
  ├── __init__.py
  └── openrouter.py          - OpenRouter adapter with tool calling
```

### Tests & Documentation

```
tests/                       - All test files (organized)
  ├── test_milestone_retry.py
  ├── test_tool_use.py
  ├── test_assembled_tools.py
  └── ...

docs/                        - Documentation (organized)
  ├── FIXES_SUMMARY.md
  ├── MILESTONE_LOOP_DIAGNOSIS.md
  ├── EVIDENCE_SYSTEM_UPDATE.md
  └── ...
```

## 🔄 Framework Compatibility

### Current Framework Version

**Assumption**: As of 2025-01-29, based on `/Users/lysander/projects/dare-framework`

**Key Dependencies**:
- `dare_framework.agent.FiveLayerAgent` - Five-layer loop implementation
- `dare_framework.tool.*` - Tool system (ReadFile, WriteFile, SearchCode)
- `dare_framework.plan.types` - Plan types (ProposedPlan, ValidatedPlan, etc.)
- `dare_framework.context` - Context management

### Known Framework Changes to Watch

⚠️ **User Note**: "我估计别人可能提交了新的代码，我们可能后面还得适配"

**Potential Breaking Changes**:
1. **Five-layer loop changes** - If `_run_milestone_loop` or `_run_execute_loop` signatures change
2. **Tool interface changes** - If tool registration or invocation API changes
3. **Context assembly** - If `context.assemble()` behavior changes
4. **Event log interface** - If event log query API changes

**Migration Strategy**:
1. Check `dare_framework/agent/_internal/five_layer.py` for changes
2. Update `enhanced_agent.py` to match new signatures
3. Verify tool invocation still works
4. Update tests if needed

## 🎯 Key Design Decisions

### 1. Evidence-Based Planning

**Decision**: Plans define "what to achieve" (verification criteria), not "how to do it" (execution steps).

**Rationale**:
- Aligns with user journey (right pane = evidence slots, left pane = execution)
- Enables dynamic execution (model decides tool calls)
- Supports verification and retry

**Files**: `planners/llm_planner.py`, `evidence_tracker.py`

### 2. System Message for Tool Calling

**Decision**: Add strong system message in Execute Loop instructing model to use tools.

**Rationale**:
- Framework's Execute Loop doesn't add system message
- Models don't know they should use tools without instruction
- This is a presentation/prompt engineering concern, not a framework concern

**File**: `enhanced_agent.py:EXECUTE_SYSTEM_PROMPT`

### 3. Capability ID Mapping

**Decision**: Map model's function names to gateway's capability IDs in Execute Loop.

**Rationale**:
- Model returns function names (e.g., `write_file`)
- ToolGateway expects capability IDs (e.g., `tool:write_file`)
- This is an impedance mismatch that needs bridging

**File**: `enhanced_agent.py:_run_execute_loop` (line ~100)

### 4. EnhancedFiveLayerAgent vs Framework Modification

**Decision**: Create `EnhancedFiveLayerAgent` subclass instead of modifying framework.

**Rationale**:
- Example should not modify framework core
- Keeps changes isolated and easy to understand
- Framework may get updated by others
- Easier to maintain and adapt

**Trade-off**: Some code duplication (override methods).

## 🧪 Test Coverage

### Unit Tests

```
tests/test_tool_use.py              - Verify model supports function calling
tests/test_assembled_tools.py       - Verify context.assemble() returns tools
tests/test_capability_id.py         - Verify capability ID mapping
tests/test_system_message.py        - Verify system message works
```

### Integration Tests

```
tests/test_execute_loop_debug.py    - Debug Execute Loop behavior
tests/test_milestone_retry.py       - Test Milestone Loop retry mechanism
tests/test_snake_end_to_end.py      - End-to-end snake game scenario
```

### Manual Tests

```
interactive_cli.py --openrouter     - Manual testing with real model
scenarios.py all                    - Run all scenarios
```

## 📋 TODO / Future Enhancements

### High Priority

- [ ] **Fix free model compatibility** - Find free models that reliably support function calling
- [ ] **Debug workspace path issue** - Why files aren't created at expected paths
- [ ] **Add event log persistence** - Enable cross-session evidence tracking

### Medium Priority

- [ ] **Implement LLMRemediator** - Generate structured reflections on failure
- [ ] **Improve evidence matching** - Semantic matching instead of string matching
- [ ] **Add more test coverage** - Edge cases, error handling

### Low Priority

- [ ] **Add HITL integration** - Real human-in-the-loop for plan approval
- [ ] **Add security boundary** - Implement ISecurityBoundary for tool execution
- [ ] **Optimize system message** - Avoid repeating on every iteration

## 🔧 Development Workflow

### Making Changes

1. **Understand current state** - Read this STATUS.md
2. **Check framework changes** - `git log dare_framework/agent/`
3. **Update code** - Modify example files
4. **Run tests** - `python tests/test_*.py`
5. **Update STATUS.md** - Document changes
6. **Commit** - Clear commit message

### Testing Checklist

- [ ] Run `tests/test_milestone_retry.py` - Verify retry mechanism
- [ ] Run `tests/test_tool_use.py` - Verify tool calling works
- [ ] Run `interactive_cli.py` - Manual smoke test
- [ ] Check file creation in `workspace/`

### Documentation Checklist

- [ ] Update STATUS.md with changes
- [ ] Update README.md if user-facing changes
- [ ] Add docs/*.md for major design decisions
- [ ] Keep commit messages clear and descriptive

## 🚀 Quick Reference

### Running the Example

```bash
# Interactive CLI (recommended for demos)
PYTHONPATH=../.. python interactive_cli.py --openrouter

# Test retry mechanism
PYTHONPATH=../.. python tests/test_milestone_retry.py

# Run all scenarios
PYTHONPATH=../.. python scenarios.py all
```

### Common Issues

**"Model doesn't call tools"** → Use paid model or Ollama
**"File not found after execution"** → Check workspace_roots configuration
**"Milestone fails immediately"** → Check validator logic in validators/simple_validator.py

### Key Files to Check When Framework Updates

1. `dare_framework/agent/_internal/five_layer.py` - Core loop logic
2. `dare_framework/tool/_internal/gateway/` - Tool invocation
3. `dare_framework/context/_internal/context.py` - Context assembly
4. `dare_framework/plan/types.py` - Plan types

## 📝 Summary

**What Works**:
- ✅ Five-layer loop architecture (Session → Milestone → Plan → Execute → Tool)
- ✅ Evidence-based planning (define verification criteria, not execution steps)
- ✅ Milestone Loop retry mechanism (Verify fails → Remediate → Retry)
- ✅ Interactive CLI with command system
- ✅ Evidence extraction and display

**What Doesn't Work (Yet)**:
- ❌ Free models unreliably call tools (workaround: use paid models)
- ⚠️ Workspace path configuration needs debugging
- ⚠️ Remediator not implemented (MVP limitation)

**Overall Assessment**: Core architecture is solid and correct. Main blocker is model capability (free models don't reliably support function calling). With a better model, the system should work end-to-end.
