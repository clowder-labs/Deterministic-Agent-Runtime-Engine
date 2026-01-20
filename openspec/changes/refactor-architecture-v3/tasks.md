## 1. Spec and design alignment
- [x] 1.1 Update OpenSpec deltas for v3 package layout, interfaces, and security/context ownership.
- [x] 1.2 Finalize v3 design decisions (domain facades, runtime removal, type ownership).

## 2. Refactor v1 and v2 frameworks
- [x] 2.1 Refactor `dare_framework2/` to the v3.2 domain layout (context/memory merge, security domain split, kernel/component split).
- [x] 2.2 Refactor `dare_framework/` to align with v3.2 layout and ownership rules (domain layout, kernel/component separation, security/context fixes).
- [x] 2.3 Update composition wiring and imports to use the new interface locations.

## 3. Create dare_framework3 scaffold
- [x] 3.1 Scaffold `dare_framework3/` with v3.2 domain packages, facades, and types.
- [x] 3.2 Add placeholder implementations/stubs for new components (event/hook/resource/execution control).
- [x] 3.3 Update default agent wiring for v3.2 composition.

## 4. Validation and docs
- [x] 4.1 Update architecture docs to reflect v3.2 structure and migration path.
- [x] 4.2 Update examples to reflect v3.2 usage.

## 5. v3.2 alignment
- [x] 5.1 Sync OpenSpec change docs to v3.2 layout (remove runtime, add event/hook, rename component).
- [x] 5.2 Update `dare_framework3/` to v3.2 type ownership and exports.
