## ADDED Requirements
### Requirement: Canonical Framework Package and Legacy Archive
The repository SHALL expose a single active framework package at `dare_framework/`. Historical framework versions SHALL be archived under `archive/frameworks/` and MUST NOT remain as top-level importable packages.

#### Scenario: Locating the active framework
- **WHEN** a contributor searches for the active framework package
- **THEN** they find `dare_framework/` at the repository root and legacy versions only under `archive/frameworks/`.

#### Scenario: Example and test imports
- **WHEN** examples or tests import framework modules
- **THEN** they import from `dare_framework` and not from archived legacy package names.
