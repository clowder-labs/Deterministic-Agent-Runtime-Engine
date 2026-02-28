# 设计文档重建 SOP（Rebuild from Docs）

> 目标：在代码缺失或需要大规模重构时，仅基于 `docs/` 资产重建核心能力并可验证。

## 1. 适用触发

1. 代码主干发生不可逆损坏，需要按文档重建。
2. 进行大规模重构，需要验证“文档描述 -> 实现行为”一致性。
3. 新成员 onboarding，需要以文档为唯一输入快速复现核心链路。

## 2. 输入资产（最小集合）

- `docs/design/Architecture.md`
- `docs/design/Interfaces.md`
- `docs/design/Design_Reconstructability_Traceability_Matrix.md`
- `docs/design/modules/*/README.md`
- `docs/guides/Documentation_First_Development_SOP.md`
- 当轮 gap/todo 文档（`docs/todos/*reconstructability*`）

## 3. 标准重建顺序（不可打乱）

1. **核心契约层**：先重建 `types/kernel/interfaces`（不写 `_internal` 实现）。
2. **运行骨架层**：重建 Agent 五层循环与关键边界（plan/tool/security/context/event）。
3. **默认实现层**：补 `_internal` 默认实现并对齐追踪矩阵锚点。
4. **治理与观测层**：补 Hook/Observability/Transport 边界与错误语义。
5. **回归验证层**：运行矩阵绑定测试并更新 evidence。

## 4. 最小验收门禁（必须全部通过）

1. 接口契约检查通过（签名、字段、错误语义）。
2. 关键测试最小集通过（以追踪矩阵 `Test Anchor` 为准）。
3. 文档漂移检查通过（`scripts/ci/check_design_doc_drift.sh`）。
4. 当轮 TODO 全量回写（状态 + 证据 + 更新时间）。

## 5. 失败回滚策略

1. 若 P0 能力任一项验证失败，禁止继续推进到下一层。
2. 回滚到上一步稳定状态，记录失败原因到 gap 分析。
3. 形成最小修复变更后再进入下一轮重建尝试。

## 6. 证据归档规范

1. 每轮重建必须产出：
   - gap 分析文档
   - TODO 清单
   - OpenSpec change artifacts
   - 验证命令与结果摘要
2. 完成后按 `openspec archive` + `docs/todos/archive/` 归档。
3. 归档条目必须包含日期前缀与可追溯链接。
