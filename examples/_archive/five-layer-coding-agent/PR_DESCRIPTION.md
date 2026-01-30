# Pull Request: Add Five-Layer Coding Agent with Evidence-Based Planning

## 🎯 Overview

This PR adds a complete five-layer coding agent example demonstrating the DARE framework's core architecture with an evidence-based planning system.

## ✨ Features

### Core Components
- **Evidence-based planning** - Plans define verification criteria (what to achieve), not execution steps (how to do it)
- **Interactive CLI** - Command system with plan approval workflow (`/mode`, `/help`, `/quit`)
- **Enhanced Execute Loop** - System message instructs model to use tools, with capability ID mapping
- **Milestone Loop retry** - Automatic retry on verification failure (Verify → Remediate → Retry, up to 3 attempts)
- **Evidence extraction** - Extracts and displays evidence from event log with ✓/✗ marks

### Components Added
- `enhanced_agent.py` - Fixed tool calling with system message + capability ID mapping
- `cli_commands.py` - Command parser and session state management
- `cli_display.py` - Display formatters for plans and evidence
- `evidence_tracker.py` - Extract evidence from event log
- `planners/llm_planner.py` - LLM-based evidence planner
- `validators/simple_validator.py` - Fixed validator (no longer always returns True)

## 🔧 Fixes

1. **Execute Loop tool calling** - Added system message instructing model to use tools
2. **Capability ID mapping** - Maps function names to capability IDs (`write_file` → `tool:write_file`)
3. **Validator behavior** - Now properly checks outputs and triggers retry on failure
4. **File organization** - Organized `tests/` and `docs/` directories

## 📚 Documentation

- `STATUS.md` - Implementation status and known issues
- `HANDOFF.md` - Handoff documentation for future maintenance
- `README.md` - Updated with new features and structure
- `docs/` - Organized all design docs and fix summaries

## ⚠️ Known Issues

**Free OpenRouter models inconsistently support function calling**
- Even with strong system messages, free models often return text instead of calling tools
- **Workaround**: Use paid models (`gemini-flash-1.5`, `claude-sonnet`, `gpt-4o`) or local Ollama

## 🧪 Testing

```bash
# Test tool calling
PYTHONPATH=../.. python tests/test_tool_use.py

# Test retry mechanism
PYTHONPATH=../.. python tests/test_milestone_retry.py

# Interactive CLI
PYTHONPATH=../.. python interactive_cli.py --openrouter
```

## 📊 File Changes

- 33 files changed, 5184 insertions(+), 126 deletions(-)
- New files: `enhanced_agent.py`, `cli_*.py`, `evidence_tracker.py`, `STATUS.md`, `HANDOFF.md`
- Organized: `tests/` (12 test files), `docs/` (10 doc files)

## 🎯 Design Decisions

1. **Evidence-based planning** - Aligns with user journey (right pane = evidence slots, left pane = execution)
2. **EnhancedFiveLayerAgent** - Subclass instead of modifying framework core (easier to maintain)
3. **System message for tools** - Prompt engineering fix, not framework change
4. **Validator fix** - No longer always returns `success=True`, enables proper retry mechanism

## 🔍 Framework Compatibility

Designed to be compatible with future framework updates. See `HANDOFF.md` for:
- Framework change detection guide
- Adaptation strategy for interface changes
- Testing checklist for compatibility

## 📋 Review Checklist

- [ ] Code follows framework architecture patterns
- [ ] Tests pass (`python tests/test_*.py`)
- [ ] Documentation is complete and clear
- [ ] Known issues are documented in STATUS.md
- [ ] Framework compatibility considerations documented

---

**Ready for review!** All core features implemented, tests passing, documentation complete. Main limitation is free model capability (documented in STATUS.md).

## 🔗 Quick Links

- **Main PR branch**: `feature/add-five-layer-example`
- **Base branch**: `main`
- **Commits**: 2 commits (feat + docs)
  - `a95a844` - Main features
  - `82f94dc` - Handoff docs
