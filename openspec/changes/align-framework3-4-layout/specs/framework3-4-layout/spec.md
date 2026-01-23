## ADDED Requirements

### Requirement: v3.4 provides v4-style domain layout scaffolding
The system SHALL provide v4.0 doc-aligned domain scaffolding under `dare_framework3_4/` so that each existing domain exposes `types.py`, `kernel.py`, and (when applicable) `interfaces.py`, with default implementations (when present) placed under `_internal/` or clearly documented as legacy.

#### Scenario: Contributor inspects a domain package
- **WHEN** a contributor opens `dare_framework3_4/context/` or `dare_framework3_4/tool/`
- **THEN** they can find `types.py` and `kernel.py` (and `interfaces.py` where the domain defines pluggable contracts)

### Requirement: v3.4 internal implementations live under `_internal/`
The system SHALL place v3.4 default implementations under `_internal/` directories (not `internal/`) in order to match the v4.0 domain convention.

#### Scenario: Locating a default implementation
- **WHEN** a contributor searches for a default implementation such as `InMemorySTM`
- **THEN** it is located under a domain `_internal/` package (e.g., `dare_framework3_4/memory/_internal/`)

### Requirement: v3.4 includes placeholder v4 domains
The system SHALL provide importable placeholder domains for `plan`, `security`, `event`, `hook`, and `config` under `dare_framework3_4/` with minimal type and Protocol declarations aligned to `doc/design/Interfaces_v4.0.md`.

#### Scenario: Importing placeholder domains
- **WHEN** a developer imports `dare_framework3_4.plan` or `dare_framework3_4.security`
- **THEN** the import succeeds and exposes the documented types/interfaces

### Requirement: v3.4 tool internal package must not contain broken imports
The system SHALL ensure that importing `dare_framework3_4.tool._internal` does not raise `ImportError` due to missing modules.

#### Scenario: Importing tool internal package
- **WHEN** a developer runs `import dare_framework3_4.tool._internal`
- **THEN** the import succeeds without missing-module errors
