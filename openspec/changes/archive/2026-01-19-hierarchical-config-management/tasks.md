## 1. Interface and Model Updates
- [x] 1.1 Define the Config model with llm/mcp/tools/allow_tools/allow_mcps fields and doc comments
- [x] 1.2 Update SessionContext to carry the effective Config
- [x] 1.3 Extend IConfigProvider with reload() -> Config semantics and doc comments

## 2. Runtime Integration
- [x] 2.1 Update component loading flow to accept the effective Config object
- [x] 2.2 Ensure all runtime components read from the effective Config

## 3. Validation and Tests
- [x] 3.1 Add unit tests for layer override semantics and Config parsing helpers
- [x] 3.2 Add integration test for ConfigProvider reload returning a new effective Config
- [x] 3.3 Run test suite for affected areas
