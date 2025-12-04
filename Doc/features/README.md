# Mission Control (任务中控台) - 文档索引

## 📚 文档概览

本目录包含SplitMind v3.0核心功能**Mission Control**的完整规划文档。

---

## 📄 文档列表

### 1. [mission-control-spec.md](./mission-control-spec.md) - **详细规格说明**

**篇幅**: 2672行，82KB  
**内容**:
- ✅ 设计理念与现状对比
- ✅ 核心数据模型扩展（Mission, TaskNode, Dependency等）
- ✅ 状态机设计（6状态转换流程）
- ✅ 上下文管理架构（分层策略、快照系统）
- ✅ 用户交互界面（Kanban + Node Graph双视图）
- ✅ 技术实现方案（后端API、数据库Schema）
- ✅ 前端组件设计（React组件详细代码）
- ✅ 迁移方案（10周迁移计划）
- ✅ 风险控制与压力测试

**适用人群**: 
- 开发团队（实现参考）
- 架构师（系统设计）
- 产品经理（功能理解）

**阅读时长**: 约60分钟

---

### 2. [mission-control-summary.md](./mission-control-summary.md) - **执行概要**

**篇幅**: 362行，8.2KB  
**内容**:
- ✅ 核心设计理念
- ✅ 主要功能模块总结
- ✅ 用户界面概览
- ✅ 技术架构要点
- ✅ 迁移计划表
- ✅ 成功指标
- ✅ 与现有系统适配要点

**适用人群**: 
- 决策层（快速了解）
- 新团队成员（入门）
- 外部合作伙伴（沟通）

**阅读时长**: 约10分钟

---

## 🎯 快速导航

### 按角色查阅

#### 👨‍💼 产品经理 / 项目经理
**推荐阅读路径**:
1. [mission-control-summary.md](./mission-control-summary.md) - 完整阅读
2. [mission-control-spec.md](./mission-control-spec.md) - 阅读以下章节:
   - 设计理念与现状对比
   - 用户交互界面
   - 迁移方案

#### 👨‍💻 后端开发
**推荐阅读路径**:
1. [mission-control-spec.md](./mission-control-spec.md) - 重点阅读:
   - 核心数据模型扩展
   - 状态机设计
   - 技术实现方案（后端部分）
   - 数据库Schema设计
   - API接口设计

#### 🎨 前端开发
**推荐阅读路径**:
1. [mission-control-summary.md](./mission-control-summary.md) - 快速了解
2. [mission-control-spec.md](./mission-control-spec.md) - 重点阅读:
   - 用户交互界面
   - 前端组件设计
   - WebSocket事件

#### 🏗️ 架构师
**推荐阅读路径**:
1. [mission-control-spec.md](./mission-control-spec.md) - 完整阅读
2. 重点关注:
   - 数据模型设计
   - 状态机约束
   - 上下文管理算法
   - 性能优化策略
   - 风险控制

#### 🧪 测试工程师
**推荐阅读路径**:
1. [mission-control-summary.md](./mission-control-summary.md) - 了解功能
2. [mission-control-spec.md](./mission-control-spec.md) - 重点阅读:
   - 状态机设计（测试用例）
   - 迁移方案 - Phase 7（测试场景）
   - 风险控制与压力测试

---

## 📊 核心概念速查

### 关键术语

| 术语 | 定义 | 详细位置 |
|------|------|----------|
| **Mission** | 项目/使命，是Project的增强版 | spec.md - 核心数据模型 |
| **TaskNode** | 任务节点，支持树形结构和复杂依赖 | spec.md - 核心数据模型 |
| **Global Context** | 全局不可变约束（技术栈、设计规范） | spec.md - 上下文管理 |
| **Local Context** | 节点专属上下文片段 | spec.md - 上下文管理 |
| **Dependency** | 增强的依赖定义（类型、状态要求） | spec.md - 核心数据模型 |
| **Artifact** | 任务的输入/输出工件 | spec.md - 核心数据模型 |
| **Snapshot** | 项目快照，支持时间旅行 | spec.md - 上下文管理 |
| **Co-Pilot** | AI协作侧边栏 | spec.md - 用户交互界面 |
| **Hot-Swap** | 全局上下文变更时的重新规划 | spec.md - 用户交互界面 |

### 6状态流转

```
Draft → Ready → Running → Review → Completed
                    ↓
                  Failed
```

**详细说明**: spec.md - 状态机设计

### 双视图系统

1. **Kanban视图**: 传统看板，6列对应6个状态
2. **Node Graph视图**: DAG图可视化依赖关系

**详细说明**: spec.md - 用户交互界面

---

## 🔗 相关资源

### 现有文档

- [../project_detailed.md](../project_detailed.md) - SplitMind项目整体介绍
- [../../README.md](../../README.md) - 项目主文档
- [../../dashboard/frontend/project-plan.md](../../dashboard/frontend/project-plan.md) - 原始开发计划

### 参考实现

- `dashboard/backend/models.py` - 现有数据模型（v2.0）
- `dashboard/backend/orchestrator.py` - 现有编排器
- `dashboard/frontend/src/components/TaskBoard.tsx` - 现有任务看板

---

## 📝 文档维护

### 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2025-12-04 | AI Assistant | 初始版本，完整功能规划 |

### 反馈与建议

如有疑问或建议，请：
1. 提交GitHub Issue
2. 联系项目负责人
3. 在团队会议中讨论

---

## ✅ 检查清单

在开始实施前，请确保：

- [ ] 所有关键决策者已阅读summary.md
- [ ] 开发团队已阅读spec.md相关章节
- [ ] 数据库迁移策略已评审
- [ ] 性能指标已达成共识
- [ ] 测试场景已确认
- [ ] 风险应对方案已准备
- [ ] 分阶段发布计划已制定

---

**最后更新**: 2025-12-04  
**文档状态**: ✅ 完整  
**实施状态**: 🟡 待启动
