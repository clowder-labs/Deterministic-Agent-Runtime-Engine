## 1. Implementation
- [x] 1.1 Add default model adapter manager in `dare_framework/model/_internal/` and a public factory in `dare_framework/model/factories.py`.
- [x] 1.2 Map `Config.llm` into adapter construction (model/api_key/endpoint/proxy/extra) and raise a clear error for unsupported adapters.
- [x] 1.3 Add a public factory for the default prompt store and update builders to use the factory (no `_internal` imports from other domains).
- [x] 1.4 Move OpenRouter model adapter into the model domain, update it to `IModelAdapter` + `ModelInput`, and re-export from `dare_framework.model`.
- [x] 1.5 Update five-layer coding agent examples to import the OpenRouter adapter from `dare_framework.model`.
- [x] 1.6 Update architecture/docs to reflect factory entry points and `_internal` access boundaries.
- [x] 1.7 Add/adjust unit tests for default manager selection and unsupported adapter errors.

## 2. Validation
- [x] 2.1 Run unit tests covering manager selection and prompt store factory usage.
- [ ] 2.2 Run or document a manual OpenRouter example smoke test (if API key available).
