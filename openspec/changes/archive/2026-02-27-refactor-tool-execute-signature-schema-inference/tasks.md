## 1. Contract and Runtime
- [x] 1.1 Update `ITool.execute` kernel contract to keyword-parameter style with `run_context`.
- [x] 1.2 Make `ToolResult` generic and wire output-schema inference from `ToolResult[T]` return annotations.
- [x] 1.3 Add schema inference + docstring description extraction helpers and default `ITool` schema properties.
- [x] 1.4 Update `ToolGateway.invoke` to call `tool.execute(run_context=..., **params)`.

## 2. Tool Migration
- [x] 2.1 Migrate built-in tool implementations to explicit execute parameters and docstring comments.
- [x] 2.2 Migrate skill/knowledge tools and test doubles implementing `ITool`.

## 3. Verification
- [x] 3.1 Run targeted tool + builder + validator unit tests.
- [x] 3.2 Ensure schema generation matches execute signature fields and descriptions in tests.
