## 1. Anthropic adapter implementation

- [x] 1.1 Add `AnthropicModelAdapter` with Anthropic Messages API request/response normalization.
- [x] 1.2 Enforce model-name pass-through from config/env without hard-coded alias mapping.
- [x] 1.3 Add adapter-focused unit tests for serialization, parsing, and generate-path payload building.

## 2. Runtime and CLI integration

- [x] 2.1 Wire `anthropic` into `DefaultModelAdapterManager` and model facade exports.
- [x] 2.2 Extend CLI doctor diagnostics for `anthropic` adapter key/dependency checks.
- [x] 2.3 Update unit tests covering manager selection and doctor behavior.

## 3. Documentation and dependency sync

- [x] 3.1 Update model/client documentation to include Anthropic adapter usage and constraints.
- [x] 3.2 Add governance feature/evidence document for this change.
- [x] 3.3 Update dependency manifests to include Anthropic SDK.
