# Mission Control (任务中控台) - 功能总结

## 📋 执行概要

本文档详细规划了SplitMind v3.0的核心功能**Mission Control**，这是一个从"波次任务管理"向"空间化任务编排系统"的革命性升级。

---

## 🎯 核心设计理念

### 从线性到空间

**v2.0 (当前)**:
- 扁平的任务列表
- 简单的依赖数组
- 5个状态流转
- 全局project_overview

**v3.0 (Mission Control)**:
- 树形任务结构，支持无限嵌套
- DAG依赖图，可视化关系
- 6个状态 + 严格状态机
- 分层上下文(Global + Local + Snapshot)

---

## 🏗️ 核心功能模块

### 1. Mission (使命/项目)

**扩展Project模型，新增**:
- `GlobalContext`: 全局不可变约束
- `root_task_ids`: 支持多个根任务
- `snapshots`: 项目快照，支持时间旅行
- `MissionStats`: 完整的统计信息

### 2. TaskNode (任务节点)

**扩展Task模型，新增**:
- **树形结构**: parent_id, children_ids, depth, path
- **增强依赖**: Dependency对象（类型、状态要求、工件引用）
- **上下文管理**: LocalContext, input/output artifacts
- **AI配置**: PromptSpec, AIExecutionConfig
- **执行结果**: ExecutionResult with logs and commits
- **评审信息**: ReviewInfo with auto-review

### 3. 严格状态机

**6个状态**:
```
Draft → Ready → Running → Review → Completed
                    ↓
                  Failed
```

**关键特性**:
- 状态转换约束矩阵
- 状态转换事件日志
- 副作用处理器（on_draft_to_ready等）
- WebSocket实时广播

### 4. 分层上下文管理

**三层架构**:
1. **Global Context**: 对所有节点可见的技术约束、设计规范
2. **Parent Context**: 从父节点继承的决策和输出
3. **Local Context**: 节点专属信息和用户补充

**关键算法**:
- 上下文组装: 只加载必需信息
- Token控制: 压缩策略确保不超限
- 指针引用: 不复制完整历史

### 5. 快照与时间旅行

**功能**:
- 创建项目快照（手动/自动）
- 恢复到任意历史状态
- 快照对比（显示差异）
- 自动备份机制

### 6. AI协作 (Co-Pilot)

**能力**:
- **任务拆解**: AI自动分解复杂任务为子任务
- **Prompt优化**: 建议改进任务指令
- **Token预估**: 准确预测消耗
- **Hot-Swap**: 全局上下文变更时重新规划

### 7. Review流程

**流程**:
```
AI执行完成 → Review状态
    ↓
自动评审（可选）
    ↓
人工决策: 批准/驳回/请求修改
    ↓
Completed or 回到Running
```

**自动评审标准**:
- 代码规范检查
- 单元测试覆盖
- 文档完整性
- 成功标准匹配

---

## 🎨 用户界面

### 双视图系统

#### 1. Kanban视图（增强版）
- 6列对应6个状态
- 增强的TaskNodeCard:
  - 显示父子关系
  - 依赖状态指示
  - Token预估和消耗
  - 实时进度（Running状态）
- 拖拽状态转换

#### 2. Node Graph视图（全新）
- 使用React Flow库
- 可视化依赖DAG图
- 节点根据状态着色
- 依赖边支持动画
- 支持递归展开子任务

### Co-Pilot侧边栏

**始终可见的AI助手**:
- 聊天界面
- 快捷操作:
  - 拆解任务
  - 优化Prompt
  - 预估Token
- 结构化响应展示

### 其他关键界面

- **NodeDetailsPanel**: 节点详情编辑
- **GlobalContextEditor**: 全局上下文管理
- **SnapshotManager**: 快照管理和对比
- **ReviewPanel**: 评审界面

---

## 💾 技术架构

### 后端

**数据库**:
- PostgreSQL + SQLAlchemy ORM
- 表: missions, task_nodes, artifacts, mission_snapshots, state_transitions
- JSON/JSONB字段存储复杂结构
- 索引优化查询性能

**API**:
- `/api/v3/*` 新版API
- 向后兼容 `/api/*`
- RESTful设计
- WebSocket实时通信

**核心类**:
- `StateTransitionHandler`: 状态机管理
- `ContextBuilder`: 上下文组装
- `SnapshotManager`: 快照管理
- `DependencyValidator`: 依赖验证

### 前端

**技术栈**:
- React 18 + TypeScript
- React Flow (节点图)
- TanStack Query (状态管理)
- Framer Motion (动画)

**组件结构**:
```
MissionControl/
├── MissionView
│   ├── KanbanView
│   └── NodeGraphView
├── CoPilotSidebar
├── NodeDetailsPanel
├── ReviewPanel
└── GlobalContextEditor
```

---

## 🚀 迁移计划

### 10周迁移路径

| 阶段 | 周数 | 核心任务 | 交付物 |
|------|------|----------|--------|
| **Phase 1** | Week 1-2 | 数据层扩展 | 新数据模型, 迁移脚本, API v3 |
| **Phase 2** | Week 3 | 状态机实现 | StateTransitionHandler, 日志系统 |
| **Phase 3** | Week 4 | 上下文管理 | ContextBuilder, SnapshotManager |
| **Phase 4** | Week 5-6 | 前端基础 | 核心UI组件, 双视图 |
| **Phase 5** | Week 7 | AI协作 | Co-Pilot, 任务拆解API |
| **Phase 6** | Week 8 | Review流程 | ReviewPanel, 自动评审 |
| **Phase 7** | Week 9-10 | 集成测试 | 端到端测试, 性能优化 |

### 向后兼容策略

- API v2和v3并存
- 自动迁移脚本
- 数据库备份机制
- 分阶段灰度发布

---

## 🛡️ 风险控制

### 主要风险

1. **循环依赖**: DAG验证算法
2. **上下文爆炸**: Token压缩策略
3. **状态不一致**: ACID事务保证
4. **性能退化**: 索引优化、缓存
5. **数据迁移失败**: 回滚机制

### 压力测试场景

- 1000+节点的深度树
- 复杂的依赖网络
- 并发状态转换
- 频繁快照创建
- 大规模上下文组装

---

## 📊 成功指标

### 性能目标

- 状态转换响应 < 200ms
- 上下文组装 < 500ms
- 快照创建 < 2s
- 节点图渲染(100节点) < 1s
- Token预估误差 < 10%

### 用户体验

- 学习曲线 < 30分钟
- 任务拆解准确率 > 80%
- 自动评审准确率 > 70%
- UI响应流畅 (60fps)

### 业务价值

- 项目管理效率提升 50%
- 减少任务冲突 80%
- 上下文遗忘问题解决 90%
- 支持更复杂的项目结构

---

## 🎓 与现有系统深度适配

### 复用现有组件

**保留并增强**:
- `OrchestratorManager`: 扩展支持TaskNode
- `WebSocketManager`: 新增node_*事件类型
- `ProjectManager`: 升级为MissionManager
- `claude_integration`: 用于AI拆解和优化
- A2AMCP协议: 增强节点间协调

**新增模块**:
- `StateTransitionHandler`
- `ContextBuilder`
- `SnapshotManager`
- `DependencyValidator`

### 数据模型映射

```python
# v2 → v3 迁移
Project → Mission (扩展)
Task → TaskNode (扩展)
TaskStatus → TaskNodeStatus (重新设计)
dependencies: List[str] → dependencies: List[Dependency] (结构化)
```

### API路由兼容

```
/api/projects → /api/v3/missions (向后兼容)
/api/projects/{id}/tasks → /api/v3/missions/{id}/nodes
新增: /api/v3/missions/{id}/co-pilot/*
新增: /api/v3/missions/{id}/snapshots/*
```

---

## 🔮 未来扩展

### v3.1 计划

- Timeline视图（甘特图）
- 资源池管理（Agent资源调度）
- 批量操作（批量状态转换）
- 模板系统（项目模板、任务模板）

### v3.2 计划

- 多人协作（实时协同编辑）
- 权限管理（节点级别权限）
- 审批流程（多级审批）
- 数据分析（项目效率分析）

### v4.0 愿景

- 可视化编程（拖拽生成代码）
- 自适应调度（AI自动优化执行顺序）
- 跨项目依赖（Mission间依赖）
- 分布式执行（多机器并行）

---

## 📚 参考资源

### 设计灵感

- Linear (项目管理)
- Mermaid (依赖图可视化)
- GitHub Projects (看板+图视图)
- Figma (实时协作)

### 技术参考

- DAG调度算法
- Git快照机制
- 上下文窗口管理（LangChain）
- 状态机设计模式

---

## ✅ 总结

Mission Control是SplitMind从"任务执行工具"升级为"智能项目编排平台"的关键功能。它解决了现有系统的核心痛点:

1. ✅ **长时程遗忘** → 分层上下文管理
2. ✅ **线性思维局限** → 树形结构+图视图
3. ✅ **状态模糊** → 严格状态机
4. ✅ **缺乏回滚** → 快照系统
5. ✅ **AI参与不足** → Co-Pilot协作
6. ✅ **质量控制弱** → Review流程

通过10周的迁移计划，我们将构建一个企业级的、可扩展的、用户友好的任务编排系统，为SplitMind的未来发展奠定坚实基础。

---

**文档版本**: v1.0  
**创建日期**: 2025-12-04  
**作者**: SplitMind Team  
**状态**: ✅ 已完成规划，待实施
