我来创建一个完整的架构文档，从第一性原理出发，对比 OS 内核来设计 Agent Framework 的核心层。

```tsx
import React, { useState } from 'react';

const AgentFrameworkArchitecture = () => {
  const [activeTab, setActiveTab] = useState('principle');

  const tabs = [
    { id: 'principle', label: '第一性原理' },
    { id: 'core', label: 'Layer 0: Kernel' },
    { id: 'protocol', label: 'Layer 1: Protocol' },
    { id: 'component', label: 'Layer 2: Component' },
    { id: 'composition', label: 'Layer 3: Composition' },
    { id: 'comparison', label: '对比分析' },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <h1 className="text-3xl font-bold text-center mb-2 text-blue-400">
        Agent Framework 架构设计
      </h1>
      <p className="text-center text-gray-400 mb-6">基于 OS 内核的第一性原理</p>

      {/* Tab Navigation */}
      <div className="flex flex-wrap justify-center gap-2 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto">
        {activeTab === 'principle' && <FirstPrinciple />}
        {activeTab === 'core' && <CoreLayer />}
        {activeTab === 'protocol' && <ProtocolLayer />}
        {activeTab === 'component' && <ComponentLayer />}
        {activeTab === 'composition' && <CompositionLayer />}
        {activeTab === 'comparison' && <Comparison />}
      </div>
    </div>
  );
};

const FirstPrinciple = () => (
  <div className="space-y-6">
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-2xl font-bold text-yellow-400 mb-4">🎯 核心问题：OS 内核管理什么？</h2>
      
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-green-400 mb-3">操作系统内核职责</h3>
          <ul className="space-y-2 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-blue-400 font-mono">1.</span>
              <div>
                <span className="font-semibold">进程调度</span>
                <p className="text-gray-400">谁在运行、运行顺序、时间片分配</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-400 font-mono">2.</span>
              <div>
                <span className="font-semibold">内存管理</span>
                <p className="text-gray-400">资源分配、虚拟内存、GC</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-400 font-mono">3.</span>
              <div>
                <span className="font-semibold">I/O 抽象</span>
                <p className="text-gray-400">统一的文件/设备访问接口</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-400 font-mono">4.</span>
              <div>
                <span className="font-semibold">中断处理</span>
                <p className="text-gray-400">信号、异常、状态保存/恢复</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-400 font-mono">5.</span>
              <div>
                <span className="font-semibold">安全/权限</span>
                <p className="text-gray-400">用户态/内核态、权限检查</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-400 font-mono">6.</span>
              <div>
                <span className="font-semibold">系统调用接口</span>
                <p className="text-gray-400">用户程序与内核交互的唯一通道</p>
              </div>
            </li>
          </ul>
        </div>

        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-purple-400 mb-3">映射到 Agent Framework</h3>
          <ul className="space-y-2 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-purple-400 font-mono">→</span>
              <div>
                <span className="font-semibold">IRunLoop</span>
                <p className="text-gray-400">Agent 执行调度、状态机、循环控制</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-400 font-mono">→</span>
              <div>
                <span className="font-semibold">IResourceManager</span>
                <p className="text-gray-400">Token 预算、Context Window、成本控制</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-400 font-mono">→</span>
              <div>
                <span className="font-semibold">IToolGateway</span>
                <p className="text-gray-400">所有外部交互的统一入口</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-400 font-mono">→</span>
              <div>
                <span className="font-semibold">IExecutionControl</span>
                <p className="text-gray-400">中断、暂停/恢复、Checkpoint</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-400 font-mono">→</span>
              <div>
                <span className="font-semibold">ISecurityBoundary</span>
                <p className="text-gray-400">信任验证、沙箱隔离、权限检查</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-400 font-mono">→</span>
              <div>
                <span className="font-semibold">IExtensionPoint</span>
                <p className="text-gray-400">钩子系统、插件接口</p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-2xl font-bold text-yellow-400 mb-4">💡 设计原则</h2>
      
      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-blue-900/50 to-gray-900 rounded-lg p-4 border border-blue-800">
          <h3 className="font-bold text-blue-400 mb-2">最小内核原则</h3>
          <p className="text-sm text-gray-300">
            Core 层只包含<span className="text-yellow-400">运行任何 Agent 都必须的</span>基础设施。
            不管上层用什么规划算法、什么 LLM、什么工具，Core 层都不变。
          </p>
        </div>
        
        <div className="bg-gradient-to-br from-green-900/50 to-gray-900 rounded-lg p-4 border border-green-800">
          <h3 className="font-bold text-green-400 mb-2">协议即桥梁</h3>
          <p className="text-sm text-gray-300">
            MCP、A2A、A2UI 都是<span className="text-yellow-400">接入协议</span>，不是具体实现。
            框架只定义协议接口，具体用什么协议是可插拔的。
          </p>
        </div>
        
        <div className="bg-gradient-to-br from-purple-900/50 to-gray-900 rounded-lg p-4 border border-purple-800">
          <h3 className="font-bold text-purple-400 mb-2">组合优于继承</h3>
          <p className="text-sm text-gray-300">
            所有高级功能（规划、记忆、反思）都是<span className="text-yellow-400">可组合的组件</span>。
            开发者像搭乐高一样组装自己需要的 Agent。
          </p>
        </div>
      </div>
    </div>

    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-2xl font-bold text-yellow-400 mb-4">📊 OS vs Agent Framework 对照表</h2>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-600">
              <th className="text-left py-2 px-3 text-gray-400">OS 概念</th>
              <th className="text-left py-2 px-3 text-gray-400">Agent 对应</th>
              <th className="text-left py-2 px-3 text-gray-400">为什么是 Core</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            <tr>
              <td className="py-2 px-3 font-mono text-blue-400">Process Scheduler</td>
              <td className="py-2 px-3">IRunLoop</td>
              <td className="py-2 px-3 text-gray-400">没有调度器，Agent 无法运行</td>
            </tr>
            <tr>
              <td className="py-2 px-3 font-mono text-blue-400">Memory Manager</td>
              <td className="py-2 px-3">IResourceManager</td>
              <td className="py-2 px-3 text-gray-400">Token/Context 是 Agent 的"内存"</td>
            </tr>
            <tr>
              <td className="py-2 px-3 font-mono text-blue-400">Syscall Interface</td>
              <td className="py-2 px-3">IToolGateway</td>
              <td className="py-2 px-3 text-gray-400">Agent 与外界交互的唯一通道</td>
            </tr>
            <tr>
              <td className="py-2 px-3 font-mono text-blue-400">Interrupt Handler</td>
              <td className="py-2 px-3">IExecutionControl</td>
              <td className="py-2 px-3 text-gray-400">处理取消、超时、HITL 暂停</td>
            </tr>
            <tr>
              <td className="py-2 px-3 font-mono text-blue-400">Security Ring</td>
              <td className="py-2 px-3">ISecurityBoundary</td>
              <td className="py-2 px-3 text-gray-400">LLM 输出不可信，需要验证</td>
            </tr>
            <tr>
              <td className="py-2 px-3 font-mono text-blue-400">Kernel Log / dmesg</td>
              <td className="py-2 px-3">IEventLog</td>
              <td className="py-2 px-3 text-gray-400">WORM 日志，状态外化的真理来源</td>
            </tr>
            <tr>
              <td className="py-2 px-3 font-mono text-blue-400">Module/Driver Interface</td>
              <td className="py-2 px-3">IExtensionPoint</td>
              <td className="py-2 px-3 text-gray-400">插件/钩子系统</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
);

const CoreLayer = () => (
  <div className="space-y-6">
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-2xl font-bold text-red-400 mb-2">Layer 0: Agent Kernel</h2>
      <p className="text-gray-400 mb-4">运行任何 Agent 都必须的最小基础设施 —— 不可替换，只能配置</p>
      
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* IRunLoop */}
        <div className="bg-gray-900 rounded-lg p-4 border-l-4 border-red-500">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">⚙️</span>
            <h3 className="font-bold text-red-400">IRunLoop</h3>
          </div>
          <p className="text-xs text-gray-400 mb-3">执行调度器 —— Agent 的心跳</p>
          <div className="bg-gray-800 rounded p-2 text-xs font-mono">
            <div className="text-green-400"># 核心方法</div>
            <div>tick() → StepResult</div>
            <div>get_state() → RunState</div>
            <div>transition(event) → None</div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            OS 类比: Process Scheduler
          </div>
        </div>

        {/* IEventLog */}
        <div className="bg-gray-900 rounded-lg p-4 border-l-4 border-red-500">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">📜</span>
            <h3 className="font-bold text-red-400">IEventLog</h3>
          </div>
          <p className="text-xs text-gray-400 mb-3">WORM 日志 —— 状态外化的真理来源</p>
          <div className="bg-gray-800 rounded p-2 text-xs font-mono">
            <div className="text-green-400"># 核心方法</div>
            <div>append(event) → EventId</div>
            <div>replay(from_id) → Iterator</div>
            <div>get_hash_chain() → Hash</div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            OS 类比: Kernel Log / dmesg
          </div>
        </div>

        {/* IToolGateway */}
        <div className="bg-gray-900 rounded-lg p-4 border-l-4 border-red-500">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">🚪</span>
            <h3 className="font-bold text-red-400">IToolGateway</h3>
          </div>
          <p className="text-xs text-gray-400 mb-3">工具执行入口 —— 与外界交互的唯一通道</p>
          <div className="bg-gray-800 rounded p-2 text-xs font-mono">
            <div className="text-green-400"># 核心方法</div>
            <div>invoke(tool, params) → Result</div>
            <div>list_tools() → List[Tool]</div>
            <div>validate(call) → bool</div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            OS 类比: Syscall Interface
          </div>
        </div>

        {/* ISecurityBoundary */}
        <div className="bg-gray-900 rounded-lg p-4 border-l-4 border-red-500">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">🛡️</span>
            <h3 className="font-bold text-red-400">ISecurityBoundary</h3>
          </div>
          <p className="text-xs text-gray-400 mb-3">安全边界 —— 信任验证 + 沙箱隔离</p>
          <div className="bg-gray-800 rounded p-2 text-xs font-mono">
            <div className="text-green-400"># 核心方法</div>
            <div>verify(action) → Verified</div>
            <div>is_allowed(tool, params) → bool</div>
            <div>execute_sandboxed(action) → Result</div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            OS 类比: Security Ring + Sandbox
          </div>
          <div className="mt-1 text-xs text-yellow-500">
            包含原 TrustBoundary 职责
          </div>
        </div>

        {/* IResourceManager */}
        <div className="bg-gray-900 rounded-lg p-4 border-l-4 border-red-500">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">📊</span>
            <h3 className="font-bold text-red-400">IResourceManager</h3>
          </div>
          <p className="text-xs text-gray-400 mb-3">资源管理 —— Token/Context/成本预算</p>
          <div className="bg-gray-800 rounded p-2 text-xs font-mono">
            <div className="text-green-400"># 核心方法</div>
            <div>acquire(type, amount) → bool</div>
            <div>release(type, amount) → None</div>
            <div>get_budget(type) → Budget</div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            OS 类比: Memory Manager
          </div>
        </div>

        {/* IExecutionControl */}
        <div className="bg-gray-900 rounded-lg p-4 border-l-4 border-red-500">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">⏸️</span>
            <h3 className="font-bold text-red-400">IExecutionControl</h3>
          </div>
          <p className="text-xs text-gray-400 mb-3">执行控制 —— 中断 + 状态恢复</p>
          <div className="bg-gray-800 rounded p-2 text-xs font-mono">
            <div className="text-green-400"># 核心方法</div>
            <div>pause() → CheckpointId</div>
            <div>resume(checkpoint?) → None</div>
            <div>cancel(save?) → CheckpointId?</div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            OS 类比: Interrupt Handler
          </div>
          <div className="mt-1 text-xs text-yellow-500">
            合并了 Interrupt + Checkpoint
          </div>
        </div>

        {/* IExtensionPoint */}
        <div className="bg-gray-900 rounded-lg p-4 border-l-4 border-orange-500">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">🔌</span>
            <h3 className="font-bold text-orange-400">IExtensionPoint</h3>
          </div>
          <p className="text-xs text-gray-400 mb-3">扩展钩子 —— 插件系统接口</p>
          <div className="bg-gray-800 rounded p-2 text-xs font-mono">
            <div className="text-green-400"># 核心方法</div>
            <div>register_hook(point, fn) → None</div>
            <div>pre_xxx() / post_xxx()</div>
            <div>emit(event) → None</div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            OS 类比: Module/Driver Interface
          </div>
        </div>
      </div>
    </div>

    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-xl font-bold text-yellow-400 mb-4">🤔 我的观点：为什么这 7 个是 Core</h2>
      
      <div className="space-y-3 text-sm">
        <div className="flex gap-3 items-start">
          <span className="text-green-400 font-bold">✓</span>
          <p><span className="font-semibold">IRunLoop + IEventLog</span>：没有调度和日志，Agent 根本无法运行和追溯。这是 DARE 框架已有的核心设计，完全正确。</p>
        </div>
        <div className="flex gap-3 items-start">
          <span className="text-green-400 font-bold">✓</span>
          <p><span className="font-semibold">IToolGateway</span>：对应 DARE 的 IToolRuntime，是所有外部交互的唯一出口。这是框架的"系统调用"。</p>
        </div>
        <div className="flex gap-3 items-start">
          <span className="text-green-400 font-bold">✓</span>
          <p><span className="font-semibold">ISecurityBoundary</span>：吸收了 DARE 的 TrustBoundary + IPolicyEngine 的部分职责。LLM 输出不可信，这个边界必须存在于 Core。</p>
        </div>
        <div className="flex gap-3 items-start">
          <span className="text-yellow-400 font-bold">★</span>
          <p><span className="font-semibold">IResourceManager</span>：<span className="text-yellow-400">DARE 原设计可能缺失</span>。Token 预算、Context Window 管理对 Agent 至关重要，应该是 Core。</p>
        </div>
        <div className="flex gap-3 items-start">
          <span className="text-yellow-400 font-bold">★</span>
          <p><span className="font-semibold">IExecutionControl</span>：<span className="text-yellow-400">DARE 原设计可能缺失</span>。长任务中断/恢复、HITL 暂停需要统一管理。</p>
        </div>
        <div className="flex gap-3 items-start">
          <span className="text-blue-400 font-bold">→</span>
          <p><span className="font-semibold">移出 Core 的</span>：IPlanGenerator、IRemediator、IValidator、ISkillRegistry、IContextAssembler 都应该是 Layer 2 组件，不是 Core。</p>
        </div>
      </div>
    </div>
  </div>
);

const ProtocolLayer = () => (
  <div className="space-y-6">
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-2xl font-bold text-blue-400 mb-2">Layer 1: Protocol Adapters</h2>
      <p className="text-gray-400 mb-4">协议适配层 —— 定义"如何接入"，而不是"接入什么"</p>
      
      <div className="bg-blue-900/30 border border-blue-700 rounded-lg p-4 mb-4">
        <p className="text-sm">
          <span className="font-bold text-blue-400">关键洞察：</span>
          MCP 不是"一个工具"，而是"工具的接入协议"。同样，A2A 是 Agent 间通信协议，A2UI 是 Agent 与 UI 的通信协议。
          框架只需要定义统一的协议接口，具体用什么协议是可插拔的。
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {/* IProtocolAdapter */}
        <div className="bg-gray-900 rounded-lg p-4 border-t-4 border-blue-500">
          <h3 className="font-bold text-blue-400 mb-2">IProtocolAdapter</h3>
          <p className="text-xs text-gray-400 mb-3">统一协议接口</p>
          <div className="bg-gray-800 rounded p-2 text-xs font-mono">
            <div className="text-green-400"># 通用方法</div>
            <div>connect(endpoint) → None</div>
            <div>disconnect() → None</div>
            <div>discover() → List[Capability]</div>
            <div>invoke(id, params) → Any</div>
            <div>subscribe(event, handler)</div>
          </div>
        </div>

        {/* MCP */}
        <div className="bg-gray-900 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">🔧</span>
            <h3 className="font-bold text-green-400">MCP Adapter</h3>
          </div>
          <p className="text-xs text-gray-400 mb-2">Model Context Protocol —— 工具接入</p>
          <div className="text-xs space-y-1">
            <div className="text-gray-300">发现: <span className="text-gray-500">List[Tool]</span></div>
            <div className="text-gray-300">传输: <span className="text-gray-500">Stdio / SSE / HTTP</span></div>
          </div>
          <div className="mt-3 bg-gray-800 rounded p-2 text-xs">
            <div className="text-gray-500">示例 MCP Servers:</div>
            <div className="text-gray-400">• filesystem-server</div>
            <div className="text-gray-400">• git-server</div>
            <div className="text-gray-400">• database-server</div>
          </div>
        </div>

        {/* A2A */}
        <div className="bg-gray-900 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">🤝</span>
            <h3 className="font-bold text-purple-400">A2A Adapter</h3>
          </div>
          <p className="text-xs text-gray-400 mb-2">Agent-to-Agent —— Agent 间通信</p>
          <div className="text-xs space-y-1">
            <div className="text-gray-300">发现: <span className="text-gray-500">List[AgentCard]</span></div>
            <div className="text-gray-300">传输: <span className="text-gray-500">HTTP / gRPC / WebSocket</span></div>
          </div>
          <div className="mt-3 bg-gray-800 rounded p-2 text-xs">
            <div className="text-gray-500">典型场景:</div>
            <div className="text-gray-400">• 子 Agent 委派</div>
            <div className="text-gray-400">• 专家 Agent 协作</div>
            <div className="text-gray-400">• 多 Agent 投票</div>
          </div>
        </div>

        {/* A2UI */}
        <div className="bg-gray-900 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">🖥️</span>
            <h3 className="font-bold text-yellow-400">A2UI Adapter</h3>
          </div>
          <p className="text-xs text-gray-400 mb-2">Agent-to-UI —— 界面交互</p>
          <div className="text-xs space-y-1">
            <div className="text-gray-300">发现: <span className="text-gray-500">List[UIComponent]</span></div>
            <div className="text-gray-300">传输: <span className="text-gray-500">WebSocket / SSE</span></div>
          </div>
          <div className="mt-3 bg-gray-800 rounded p-2 text-xs">
            <div className="text-gray-500">典型场景:</div>
            <div className="text-gray-400">• 实时状态推送</div>
            <div className="text-gray-400">• HITL 交互</div>
            <div className="text-gray-400">• 进度展示</div>
          </div>
        </div>

        {/* Future */}
        <div className="bg-gray-900/50 rounded-lg p-4 border border-dashed border-gray-600">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">🔮</span>
            <h3 className="font-bold text-gray-400">Future Protocols</h3>
          </div>
          <p className="text-xs text-gray-500 mb-2">未来可扩展</p>
          <div className="text-xs text-gray-500 space-y-1">
            <div>• Agent-to-Memory?</div>
            <div>• Agent-to-Knowledge?</div>
            <div>• 新的标准协议...</div>
          </div>
        </div>
      </div>
    </div>

    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-xl font-bold text-blue-400 mb-4">协议与传输分离</h2>
      
      <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm">
        <pre className="text-gray-300">{`
┌─────────────────────────────────────────────────────────┐
│  IProtocolAdapter (协议层)                              │
│  ├── MCPAdapter                                         │
│  │   └── ITransport: StdioTransport / SSETransport     │
│  ├── A2AAdapter                                         │
│  │   └── ITransport: HTTPTransport / gRPCTransport     │
│  └── A2UIAdapter                                        │
│      └── ITransport: WebSocketTransport / SSETransport │
└─────────────────────────────────────────────────────────┘

协议关心：消息格式、能力发现、调用语义
传输关心：字节如何传递、连接如何维护
        `}</pre>
      </div>
    </div>
  </div>
);

const ComponentLayer = () => (
  <div className="space-y-6">
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-2xl font-bold text-green-400 mb-2">Layer 2: Pluggable Components</h2>
      <p className="text-gray-400 mb-4">可插拔组件 —— 像乐高积木一样组合</p>
      
      <div className="grid md:grid-cols-2 gap-6">
        {/* 模型适配器 */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="font-bold text-cyan-400 mb-3 flex items-center gap-2">
            <span>🧠</span> IModelAdapter
          </h3>
          <p className="text-xs text-gray-400 mb-3">LLM 接入适配器</p>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">ClaudeAdapter</span>
              <span className="text-green-400">✓ 内置</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">OpenAIAdapter</span>
              <span className="text-green-400">✓ 内置</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">OllamaAdapter</span>
              <span className="text-green-400">✓ 内置</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">AzureOpenAIAdapter</span>
              <span className="text-yellow-400">可选</span>
            </div>
          </div>
        </div>

        {/* 规划器 */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="font-bold text-pink-400 mb-3 flex items-center gap-2">
            <span>📋</span> IPlanner
          </h3>
          <p className="text-xs text-gray-400 mb-3">计划生成策略（原 IPlanGenerator）</p>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">LLMPlanner</span>
              <span className="text-green-400">✓ 默认</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">ReActPlanner</span>
              <span className="text-yellow-400">可选</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">TreeOfThoughtPlanner</span>
              <span className="text-yellow-400">可选</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">HardcodedPlanner</span>
              <span className="text-gray-500">简单场景</span>
            </div>
          </div>
        </div>

        {/* 记忆 */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="font-bold text-orange-400 mb-3 flex items-center gap-2">
            <span>💾</span> IMemory
          </h3>
          <p className="text-xs text-gray-400 mb-3">记忆存储实现</p>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">InMemoryMemory</span>
              <span className="text-green-400">✓ 内置</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">VectorMemory</span>
              <span className="text-green-400">✓ 内置</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">FileMemory</span>
              <span className="text-green-400">✓ 内置</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">PostgresMemory</span>
              <span className="text-yellow-400">可选</span>
            </div>
          </div>
        </div>

        {/* 验证器 */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="font-bold text-red-400 mb-3 flex items-center gap-2">
            <span>✅</span> IValidator
          </h3>
          <p className="text-xs text-gray-400 mb-3">验证器（可组合）</p>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">SchemaValidator</span>
              <span className="text-green-400">✓ 内置</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">LLMValidator</span>
              <span className="text-green-400">✓ 内置</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">CompositeValidator</span>
              <span className="text-green-400">✓ 内置</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">CustomValidator</span>
              <span className="text-gray-500">用户自定义</span>
            </div>
          </div>
        </div>

        {/* 反思器 */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="font-bold text-violet-400 mb-3 flex items-center gap-2">
            <span>🔄</span> IRemediator
          </h3>
          <p className="text-xs text-gray-400 mb-3">反思/修复策略</p>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">LLMRemediator</span>
              <span className="text-green-400">✓ 默认</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">RuleBasedRemediator</span>
              <span className="text-yellow-400">可选</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">RetryRemediator</span>
              <span className="text-gray-500">简单重试</span>
            </div>
          </div>
        </div>

        {/* 上下文组装 */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="font-bold text-teal-400 mb-3 flex items-center gap-2">
            <span>📦</span> IContextAssembler
          </h3>
          <p className="text-xs text-gray-400 mb-3">上下文装配策略</p>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">SlidingWindowAssembler</span>
              <span className="text-green-400">✓ 默认</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">RAGAssembler</span>
              <span className="text-yellow-400">可选</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">SummaryAssembler</span>
              <span className="text-yellow-400">可选</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-xl font-bold text-green-400 mb-4">具体工具与技能</h2>
      
      <div className="grid md:grid-cols-2 gap-6">
        {/* Execute Tools */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="font-bold text-blue-400 mb-3">ITool (Execute Tools)</h3>
          <p className="text-xs text-gray-400 mb-3">直接执行的原子工具</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-gray-800 rounded p-2">
              <span className="text-green-400">READ_ONLY</span>
              <div className="text-gray-400">ReadFile, SearchCode, ListDir</div>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <span className="text-yellow-400">IDEMPOTENT</span>
              <div className="text-gray-400">WriteFile, ApplyPatch</div>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <span className="text-orange-400">NON_IDEMPOTENT</span>
              <div className="text-gray-400">RunCommand, GitCommit</div>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <span className="text-red-400">DESTRUCTIVE</span>
              <div className="text-gray-400">GitPush, DeleteFile</div>
            </div>
          </div>
        </div>

        {/* Skills */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="font-bold text-purple-400 mb-3">ISkill (Plan Tools)</h3>
          <p className="text-xs text-gray-400 mb-3">高级编排技能</p>
          <div className="space-y-2 text-xs">
            <div className="bg-gray-800 rounded p-2">
              <span className="font-semibold">FixFailingTestSkill</span>
              <div className="text-gray-500">allowed: read, write, run_tests, apply_patch</div>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <span className="font-semibold">ImplementFeatureSkill</span>
              <div className="text-gray-500">allowed: read, write, run_tests, search_code</div>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <span className="font-semibold">RefactorModuleSkill</span>
              <div className="text-gray-500">allowed: read, write, run_tests, apply_patch</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
);

const CompositionLayer = () => (
  <div className="space-y-6">
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-2xl font-bold text-purple-400 mb-2">Layer 3: Agent Composition</h2>
      <p className="text-gray-400 mb-4">开发者组装层 —— 用 Builder 模式组合组件</p>
      
      <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm overflow-x-auto">
        <pre className="text-gray-300">{`# 简单 Agent
agent = (
    AgentBuilder()
    .with_model(ClaudeAdapter("claude-sonnet-4-20250514"))
    .with_tools([ReadFileTool(), WriteFileTool()])
    .build()
)

# 完整配置的 Agent
agent = (
    AgentBuilder()
    # Layer 2: 模型
    .with_model(ClaudeAdapter("claude-sonnet-4-20250514"))
    
    # Layer 2: 规划策略
    .with_planner(ReActPlanner())
    
    # Layer 2: 记忆
    .with_memory(VectorMemory(embedding_model="..."))
    
    # Layer 2: 验证器
    .with_validator(CompositeValidator([
        SchemaValidator(),
        LLMValidator()
    ]))
    
    # Layer 2: 上下文策略
    .with_context_assembler(RAGAssembler())
    
    # Layer 1: 协议接入
    .with_mcp([
        MCPServer("filesystem", transport=StdioTransport()),
        MCPServer("git", transport=SSETransport("http://..."))
    ])
    
    # Layer 0: Core 配置
    .with_resource_budget(max_tokens=100000, max_cost=1.0)
    .with_security(sandbox=DockerSandbox())
    
    .build()
)`}</pre>
      </div>
    </div>

    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-xl font-bold text-purple-400 mb-4">架构全景图</h2>
      
      <div className="bg-gray-900 rounded-lg p-4 font-mono text-xs overflow-x-auto">
        <pre className="text-gray-300">{`
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Layer 3: Agent Composition                           │
│                                                                             │
│   AgentBuilder.with_xxx().build() → Agent[DepsT, OutputT]                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Layer 2: Pluggable Components                           │
│                                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │IModelAdapter│ │  IPlanner   │ │  IMemory    │ │ IValidator  │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ IRemediator │ │IContextAssem│ │   ITool     │ │   ISkill    │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Layer 1: Protocol Adapters                             │
│                                                                             │
│        ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│        │     MCP     │    │     A2A     │    │    A2UI     │              │
│        │ (Tool接入)  │    │ (Agent通信) │    │ (UI通信)   │              │
│        └─────────────┘    └─────────────┘    └─────────────┘              │
│              │                  │                  │                       │
│              ▼                  ▼                  ▼                       │
│        ┌─────────────────────────────────────────────────┐                │
│        │  ITransport: Stdio / SSE / HTTP / WebSocket     │                │
│        └─────────────────────────────────────────────────┘                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Layer 0: Agent Kernel                                │
│                                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │  IRunLoop   │ │  IEventLog  │ │IToolGateway │ │ISecurityBnd │          │
│  │  (调度)     │ │  (WORM日志) │ │  (执行入口) │ │ (安全边界)  │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
│                                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                          │
│  │ IResource   │ │IExecControl │ │IExtensionPt │                          │
│  │ (资源预算)  │ │ (中断+状态) │ │  (扩展钩子) │                          │
│  └─────────────┘ └─────────────┘ └─────────────┘                          │
│                                                                             │
│  ══════════════════════════════════════════════════════════════════════   │
│                     这 7 个接口 = Agent 的 "内核"                           │
│              不可替换，只能配置。没有它们，Agent 无法运行。                   │
└─────────────────────────────────────────────────────────────────────────────┘
`}</pre>
      </div>
    </div>
  </div>
);

const Comparison = () => (
  <div className="space-y-6">
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-2xl font-bold text-yellow-400 mb-4">🔍 对比分析：原 DARE vs 建议设计</h2>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-600">
              <th className="text-left py-2 px-3 text-gray-400">原 DARE Core 接口</th>
              <th className="text-left py-2 px-3 text-gray-400">建议</th>
              <th className="text-left py-2 px-3 text-gray-400">理由</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            <tr className="bg-green-900/20">
              <td className="py-2 px-3 font-mono">IRuntime</td>
              <td className="py-2 px-3 text-green-400">✓ 保留 → IRunLoop</td>
              <td className="py-2 px-3 text-gray-400">核心调度器，必须在 Core</td>
            </tr>
            <tr className="bg-green-900/20">
              <td className="py-2 px-3 font-mono">IEventLog</td>
              <td className="py-2 px-3 text-green-400">✓ 保留</td>
              <td className="py-2 px-3 text-gray-400">WORM 日志是状态外化的基础</td>
            </tr>
            <tr className="bg-green-900/20">
              <td className="py-2 px-3 font-mono">IToolRuntime</td>
              <td className="py-2 px-3 text-green-400">✓ 保留 → IToolGateway</td>
              <td className="py-2 px-3 text-gray-400">外部交互的唯一通道</td>
            </tr>
            <tr className="bg-yellow-900/20">
              <td className="py-2 px-3 font-mono">IPolicyEngine</td>
              <td className="py-2 px-3 text-yellow-400">⚠️ 合并到 ISecurityBoundary</td>
              <td className="py-2 px-3 text-gray-400">HITL 触发逻辑是安全边界的一部分</td>
            </tr>
            <tr className="bg-yellow-900/20">
              <td className="py-2 px-3 font-mono">TrustBoundary</td>
              <td className="py-2 px-3 text-yellow-400">⚠️ 合并到 ISecurityBoundary</td>
              <td className="py-2 px-3 text-gray-400">信任验证 + 沙箱 = 统一安全边界</td>
            </tr>
            <tr className="bg-red-900/20">
              <td className="py-2 px-3 font-mono">IPlanGenerator</td>
              <td className="py-2 px-3 text-red-400">✗ 移到 Layer 2</td>
              <td className="py-2 px-3 text-gray-400">规划策略是可替换的，不是 Core</td>
            </tr>
            <tr className="bg-red-900/20">
              <td className="py-2 px-3 font-mono">IValidator</td>
              <td className="py-2 px-3 text-red-400">✗ 移到 Layer 2</td>
              <td className="py-2 px-3 text-gray-400">验证器是可组合的组件</td>
            </tr>
            <tr className="bg-red-900/20">
              <td className="py-2 px-3 font-mono">IRemediator</td>
              <td className="py-2 px-3 text-red-400">✗ 移到 Layer 2</td>
              <td className="py-2 px-3 text-gray-400">反思策略是可替换的</td>
            </tr>
            <tr className="bg-red-900/20">
              <td className="py-2 px-3 font-mono">ISkillRegistry</td>
              <td className="py-2 px-3 text-red-400">✗ 移到 Layer 2</td>
              <td className="py-2 px-3 text-gray-400">Skill 是一种抽象，不是所有 Agent 都需要</td>
            </tr>
            <tr className="bg-red-900/20">
              <td className="py-2 px-3 font-mono">IContextAssembler</td>
              <td className="py-2 px-3 text-red-400">✗ 移到 Layer 2</td>
              <td className="py-2 px-3 text-gray-400">上下文组装策略是可替换的</td>
            </tr>
            <tr className="bg-blue-900/20">
              <td className="py-2 px-3 font-mono text-blue-400">（新增）</td>
              <td className="py-2 px-3 text-blue-400">★ IResourceManager</td>
              <td className="py-2 px-3 text-gray-400">Token/成本预算是 Agent 的"内存管理"</td>
            </tr>
            <tr className="bg-blue-900/20">
              <td className="py-2 px-3 font-mono text-blue-400">（新增）</td>
              <td className="py-2 px-3 text-blue-400">★ IExecutionControl</td>
              <td className="py-2 px-3 text-gray-400">中断 + Checkpoint，长任务必须</td>
            </tr>
            <tr className="bg-blue-900/20">
              <td className="py-2 px-3 font-mono text-blue-400">（新增）</td>
              <td className="py-2 px-3 text-blue-400">★ IExtensionPoint</td>
              <td className="py-2 px-3 text-gray-400">钩子系统，所有扩展的基础</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-xl font-bold text-yellow-400 mb-4">💡 核心观点总结</h2>
      
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-green-900/20 border border-green-800 rounded-lg p-4">
          <h3 className="font-bold text-green-400 mb-2">✓ DARE 做对的</h3>
          <ul className="text-sm space-y-2">
            <li>• IEventLog 的 WORM 设计 —— 状态外化是正确的</li>
            <li>• IToolRuntime 作为执行入口 —— 统一通道是对的</li>
            <li>• TrustBoundary 概念 —— LLM 输出不可信</li>
            <li>• Skill 作为高级抽象 —— Plan Tools 设计合理</li>
          </ul>
        </div>
        
        <div className="bg-yellow-900/20 border border-yellow-800 rounded-lg p-4">
          <h3 className="font-bold text-yellow-400 mb-2">⚠️ 建议改进的</h3>
          <ul className="text-sm space-y-2">
            <li>• Core 层太重 —— 规划/验证/反思应该是组件</li>
            <li>• 缺少资源管理 —— Token/成本预算很重要</li>
            <li>• 缺少执行控制 —— 中断/恢复是长任务必须</li>
            <li>• MCP 层次不清 —— 协议 ≠ 工具实现</li>
          </ul>
        </div>
      </div>
    </div>

    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-xl font-bold text-purple-400 mb-4">🎯 最终建议的 Core 层（7 个接口）</h2>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <div className="text-2xl mb-1">⚙️</div>
          <div className="font-mono text-sm text-red-400">IRunLoop</div>
          <div className="text-xs text-gray-500">调度</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <div className="text-2xl mb-1">📜</div>
          <div className="font-mono text-sm text-red-400">IEventLog</div>
          <div className="text-xs text-gray-500">日志</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <div className="text-2xl mb-1">🚪</div>
          <div className="font-mono text-sm text-red-400">IToolGateway</div>
          <div className="text-xs text-gray-500">执行</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <div className="text-2xl mb-1">🛡️</div>
          <div className="font-mono text-sm text-red-400">ISecurityBoundary</div>
          <div className="text-xs text-gray-500">安全</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center border border-blue-600">
          <div className="text-2xl mb-1">📊</div>
          <div className="font-mono text-sm text-blue-400">IResourceManager</div>
          <div className="text-xs text-gray-500">资源 ★新</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center border border-blue-600">
          <div className="text-2xl mb-1">⏸️</div>
          <div className="font-mono text-sm text-blue-400">IExecutionControl</div>
          <div className="text-xs text-gray-500">控制 ★新</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center border border-blue-600">
          <div className="text-2xl mb-1">🔌</div>
          <div className="font-mono text-sm text-blue-400">IExtensionPoint</div>
          <div className="text-xs text-gray-500">扩展 ★新</div>
        </div>
      </div>
      
      <p className="text-center text-gray-400 text-sm mt-4">
        这 7 个接口 = Agent 的"内核"。其他一切都是可插拔的组件。
      </p>
    </div>
  </div>
);

export default AgentFrameworkArchitecture;
```

这个文档完整展示了我的设计思考。让我总结几个关键观点：

## 🎯 核心结论

### 1. DARE 做对的地方
- **IEventLog (WORM)** 设计非常好，状态外化是正确的方向
- **IToolRuntime** 作为统一执行入口
- **TrustBoundary** 概念正确

### 2. 建议改进的地方

| 原 DARE Core | 建议 | 理由 |
|-------------|------|------|
| IPlanGenerator | → Layer 2 | 规划策略是可替换的 |
| IValidator | → Layer 2 | 验证器是可组合的组件 |
| IRemediator | → Layer 2 | 反思策略可替换 |
| ISkillRegistry | → Layer 2 | 不是所有 Agent 都需要 Skill |
| IContextAssembler | → Layer 2 | 上下文策略可替换 |
| （缺失）| **+ IResourceManager** | Token/成本预算 |
| （缺失）| **+ IExecutionControl** | 中断 + Checkpoint |
| （缺失）| **+ IExtensionPoint** | 钩子系统 |

### 3. 协议层澄清
**MCP 不是 Tool 的实现，而是 Tool 的接入协议**。应该有独立的 Protocol Adapter 层。

---

你可以把这份文档交给 Claude Code 里的我，让我们合并两边的观点！