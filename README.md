# DARE Framework

`deterministic-agent-runtime-engine` 是当前仓库的发行包名，安装后在 Python 代码里使用的导入名是 `dare_framework`。

除非特别说明，下面的命令都默认在仓库根目录、且已激活目标 Python 虚拟环境后执行。

## 本地安装

### 方式 1：可编辑安装（联调推荐）

```bash
python -m pip install -e .
```

如果你只想安装入口而暂时跳过依赖解析：

```bash
python -m pip install -e . --no-deps
```

### 方式 2：先打本地 wheel，再安装（冻结版本推荐）

```bash
python -m pip wheel . -w dist --no-deps
python -m pip install dist/deterministic_agent_runtime_engine-0.1.0-py3-none-any.whl
```

## 在另一个项目里引用当前仓库

如果下游项目和当前仓库在同一台机器上，不需要发布到公共镜像仓库。

### 直接从源码路径安装

```bash
python -m pip install -e /abs/path/to/Deterministic-Agent-Runtime-Engine
```

如果两个项目是同级目录，也可以用相对路径：

```bash
python -m pip install -e ../Deterministic-Agent-Runtime-Engine
```

### 从本地 wheel 安装

先在当前仓库构建 wheel：

```bash
python -m pip wheel . -w dist --no-deps
```

再在下游项目环境里安装：

```bash
python -m pip install /abs/path/to/Deterministic-Agent-Runtime-Engine/dist/deterministic_agent_runtime_engine-0.1.0-py3-none-any.whl
```

## 导入方式

安装成功后，下游项目直接导入 `dare_framework`：

```python
from dare_framework.agent import BaseAgent
from dare_framework.model import OpenAIModelAdapter
```

如果下游项目可以接受修改 import，推荐直接迁到 `dare_framework.*`，不要额外做 `agentscope` 兼容包。

## 相关文档

- `client/README.md`：CLI 使用方式与运行参数
- `docs/README.md`：设计、治理和模块文档导航
