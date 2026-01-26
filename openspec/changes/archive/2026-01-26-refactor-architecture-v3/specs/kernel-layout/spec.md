## MODIFIED Requirements
### Requirement: Kernel defaults are domain-owned
The system SHALL locate default implementations within the domain `internal/` directory that owns the corresponding contract and SHALL NOT centralize defaults under a cross-domain runtime package.

#### Scenario: Default implementations live with their contracts
- **WHEN** a developer looks for the default event log implementation
- **THEN** it is located under `dare_framework3_3/event/internal/`.

### Requirement: Layer 0 must not depend on Layer 2
Kernel interfaces in `dare_framework3_3/<domain>/kernel.py` SHALL NOT import from `dare_framework3_3/<domain>/component.py` or `dare_framework3_3/<domain>/internal/**`. Shared capability contracts required by kernel defaults SHALL live under the domain `types.py` modules.

#### Scenario: Kernel remains isolated
- **WHEN** a contributor inspects a `kernel.py`
- **THEN** it contains only stable interface definitions and avoids component or implementation imports.

## ADDED Requirements
### Requirement: Kernel and component interfaces are separated per domain
Each domain package SHALL define kernel interfaces in `kernel.py` and pluggable component interfaces in `component.py` to make Layer 0 vs Layer 2 boundaries explicit.

#### Scenario: Context domain interface split
- **WHEN** a contributor inspects `dare_framework3_3/context/`
- **THEN** kernel interfaces are defined in `kernel.py` and component interfaces are defined in `component.py`.
