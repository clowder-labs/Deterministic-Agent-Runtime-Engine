# organize-layered-structure Specification

## Purpose
TBD - created by archiving change refactor-layered-structure. Update Purpose after archive.
## Requirements
### Requirement: Layered Package Organization
The framework SHALL include an `infra` package for cross-domain shared contracts (e.g., `ComponentType`, `IComponent`) that are used by multiple domains.

#### Scenario: Contributor locates shared identity types
- **WHEN** a contributor needs `ComponentType` or `IComponent`
- **THEN** they find them under `dare_framework/infra/`

### Requirement: Functional Domain Grouping
The framework SHALL locate domain-specific interfaces, types, and implementations within the owning domain package.

#### Scenario: Locating a domain module
- **WHEN** a contributor searches for the security domain
- **THEN** interfaces and implementations are located under `dare_framework3_3/security/`.

### Requirement: No Pass-through Modules
The framework SHALL avoid modules whose sole purpose is re-exporting symbols, except for domain package `__init__.py` files and `internal/__init__.py` implementation exports.

#### Scenario: Facade-only re-exports are allowed
- **WHEN** a module exists only to re-export stable API symbols
- **THEN** it MUST be a domain `__init__.py` or `internal/__init__.py`; otherwise it is removed and callers import from the module-of-definition.

### Requirement: Minimal Package Initializers
Package `__init__.py` files under implementation subpackages (e.g., `dare_framework3_3/**/internal/__init__.py`) SHALL remain minimal and SHALL NOT define new symbols.

#### Scenario: Importing an implementation package
- **WHEN** a contributor opens an `internal/__init__.py`
- **THEN** it contains only a docstring, metadata, or re-exports of implementation classes.

### Requirement: Intentional Placeholder Packages
The framework SHALL only keep empty or placeholder packages when they include a clear module-level docstring describing their intent and expected contents.

#### Scenario: Documenting a placeholder
- **WHEN** a package contains no concrete implementations yet
- **THEN** its `__init__.py` documents the planned component scope or purpose.

### Requirement: Remove Unused Default Implementations
The framework SHALL remove default implementations that are not referenced by the builder/composition layer, entry point discovery, or examples, unless they are explicitly documented as planned placeholders.

#### Scenario: Identifying unused defaults
- **WHEN** a default component is not reachable from `AgentBuilder` wiring, not exposed via entry point discovery, and not used in examples
- **THEN** it is removed or marked as an intentional placeholder with documented intent.

### Requirement: Canonical Framework Package and Legacy Archive
The repository SHALL expose a single active framework package at `dare_framework/`. Historical framework versions SHALL be archived under `archive/frameworks/` and MUST NOT remain as top-level importable packages.

#### Scenario: Locating the active framework
- **WHEN** a contributor searches for the active framework package
- **THEN** they find `dare_framework/` at the repository root and legacy versions only under `archive/frameworks/`.

#### Scenario: Example and test imports
- **WHEN** examples or tests import framework modules
- **THEN** they import from `dare_framework` and not from archived legacy package names.

### Requirement: Canonical naming without version markers
The canonical (non-archived) codebase and documentation SHALL avoid version markers in package names, file names, and descriptive labels. Archived references MAY retain historical version labels under `archive/`.

#### Scenario: Naming the active codebase
- **WHEN** a contributor inspects active code, examples, tests, or docs
- **THEN** they see canonical names without version suffixes, except within `archive/`.

### Requirement: Internal implementation boundary
Domain implementations in `_internal/` SHALL NOT be imported directly by other domains; instead, the owning domain MUST expose public factory functions or facades for default implementations.

#### Scenario: External domain uses factory
- **GIVEN** a builder in another domain needs a default implementation
- **WHEN** it accesses that implementation
- **THEN** it uses the owning domain's factory or facade rather than importing `_internal` modules

