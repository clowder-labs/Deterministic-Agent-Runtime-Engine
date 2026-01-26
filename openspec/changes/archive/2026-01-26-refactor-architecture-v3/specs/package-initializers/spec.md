## MODIFIED Requirements
### Requirement: Contracts are defined in dedicated modules
The framework SHALL define contract surfaces (protocols, enums, dataclasses, and domain exceptions) in dedicated modules such as `component.py`, `types.py`, or `kernel.py` and SHALL NOT define them in `__init__.py`.

#### Scenario: Finding a protocol definition
- **WHEN** a contributor needs to inspect `IExecutionControl`
- **THEN** the protocol is defined in `dare_framework/tool/kernel.py`, not in `__init__.py`.

#### Scenario: Finding a model definition
- **WHEN** a contributor needs to inspect `RunResult`
- **THEN** it is defined in `dare_framework/plan/types.py`, not in `__init__.py`.

### Requirement: Package initializers are metadata-only (no re-exports)
Domain package `__init__.py` files MAY re-export public symbols; other package initializers (including `internal/__init__.py`) SHALL contain only documentation, metadata, or re-export statements and SHALL NOT define classes or functions.

#### Scenario: Auditing an implementation package initializer
- **WHEN** auditing `dare_framework/tool/_internal/__init__.py`
- **THEN** the file contains only re-exports and no class or function definitions.

#### Scenario: Auditing a domain initializer
- **WHEN** auditing `dare_framework/tool/__init__.py`
- **THEN** it re-exports public symbols and contains no class or function definitions.

### Requirement: No pass-through re-export modules
The framework SHALL avoid modules whose sole purpose is re-exporting symbols, except for domain `__init__.py` files and `internal/__init__.py` re-export lists.

#### Scenario: Removing a non-domain re-export
- **WHEN** a module contains only re-export imports and `__all__`
- **THEN** it is removed unless it is a domain or implementation initializer.
