# API服务集成

<cite>
**本文档引用的文件**
- [api.ts](file://dashboard/frontend/src/services/api.ts)
- [websocket.ts](file://dashboard/frontend/src/services/websocket.ts)
- [useWebSocket.ts](file://dashboard/frontend/src/hooks/useWebSocket.ts)
- [index.ts](file://dashboard/frontend/src/types/index.ts)
- [websocket_manager.py](file://dashboard/backend/websocket_manager.py)
- [api.py](file://dashboard/backend/api.py)
- [main.py](file://dashboard/backend/main.py)
- [models.py](file://dashboard/backend/models.py)
- [vite.config.ts](file://dashboard/frontend/vite.config.ts)
</cite>

## 目录
1. [简介](#简介)
2. [项目架构概览](#项目架构概览)
3. [RESTful API服务](#restful-api服务)
4. [WebSocket通信机制](#websocket通信机制)
5. [数据模型与类型安全](#数据模型与类型安全)
6. [通信时序与流程](#通信时序与流程)
7. [错误处理与重连机制](#错误处理与重连机制)
8. [最佳实践与优化建议](#最佳实践与优化建议)
9. [总结](#总结)

## 简介

TaskTree项目采用现代化的前后端分离架构，通过RESTful API和WebSocket两种通信机制实现高效的数据交换。前端使用TypeScript构建，后端基于Python FastAPI框架，提供了完整的任务管理、项目协调和实时通信功能。

本文档详细分析了API服务的集成方式，包括请求封装、错误处理、WebSocket连接管理以及实时数据推送等核心功能。

## 项目架构概览

系统采用分层架构设计，清晰分离前端服务层、业务逻辑层和数据访问层：

```mermaid
graph TB
subgraph "前端层"
UI[用户界面组件]
API[API服务层]
WS[WebSocket服务层]
Hooks[React Hooks]
end
subgraph "后端层"
FastAPI[FastAPI应用]
APILayer[API路由层]
WSLayer[WebSocket层]
BL[业务逻辑层]
DAL[数据访问层]
end
subgraph "通信层"
REST[RESTful API]
WS[WebSocket连接]
Proxy[代理服务器]
end
UI --> API
UI --> WS
API --> REST
WS --> WS
REST --> FastAPI
WS --> FastAPI
FastAPI --> APILayer
FastAPI --> WSLayer
APILayer --> BL
WSLayer --> BL
BL --> DAL
```

**图表来源**
- [main.py](file://dashboard/backend/main.py#L34-L56)
- [api.ts](file://dashboard/frontend/src/services/api.ts#L1-L248)
- [websocket.ts](file://dashboard/frontend/src/services/websocket.ts#L1-L98)

**章节来源**
- [main.py](file://dashboard/backend/main.py#L1-L56)
- [api.ts](file://dashboard/frontend/src/services/api.ts#L1-L248)
- [websocket.ts](file://dashboard/frontend/src/services/websocket.ts#L1-L98)

## RESTful API服务

### API客户端架构

前端API服务采用类封装模式，提供统一的请求管理和错误处理机制：

```mermaid
classDiagram
class ApiService {
-API_BASE : string
+request~T~(url, options) Promise~T~
+getProjects() Promise~Project[]~
+getProject(id) Promise~Project~
+createProject(project) Promise~Project~
+updateProject(id, updates) Promise~Project~
+deleteProject(id) Promise~void~
+getTasks(projectId) Promise~Task[]~
+createTask(projectId, title, description) Promise~Task~
+updateTask(projectId, taskId, updates) Promise~Task~
+deleteTask(projectId, taskId) Promise~void~
+getAgents(projectId) Promise~Agent[]~
+launchAgentMonitor(projectId) Promise~Object~
+getOrchestratorConfig() Promise~OrchestratorConfig~
+updateOrchestratorConfig(config) Promise~OrchestratorConfig~
+startOrchestrator(projectId) Promise~void~
+stopOrchestrator() Promise~void~
+generatePlan(projectId, data) Promise~Object~
+generateTaskBreakdown(projectId, data) Promise~Object~
}
class Project {
+id : string
+name : string
+path : string
+description? : string
+max_agents : number
+active : boolean
+created_at : string
+updated_at : string
}
class Task {
+id : string
+title : string
+description? : string
+status : TaskStatus
+branch : string
+dependencies? : string[]
+priority? : number
+created_at : string
+updated_at : string
}
ApiService --> Project : "管理"
ApiService --> Task : "管理"
```

**图表来源**
- [api.ts](file://dashboard/frontend/src/services/api.ts#L5-L248)
- [index.ts](file://dashboard/frontend/src/types/index.ts#L1-L84)

### 请求封装与错误处理

API服务实现了统一的请求封装机制，包含以下特性：

1. **自动JSON解析**：自动处理响应数据的JSON解析
2. **错误处理**：统一的HTTP错误和解析错误处理
3. **日志记录**：关键操作的日志输出
4. **类型安全**：TypeScript类型约束确保数据完整性

### 核心API方法

系统提供了完整的CRUD操作和业务特定接口：

| 功能分类 | 方法名称 | HTTP方法 | 描述 |
|---------|---------|---------|------|
| 项目管理 | getProjects | GET | 获取所有项目列表 |
| 项目管理 | getProject | GET | 获取单个项目详情 |
| 项目管理 | createProject | POST | 创建新项目 |
| 项目管理 | updateProject | PUT | 更新项目信息 |
| 项目管理 | deleteProject | DELETE | 删除项目 |
| 项目统计 | getProjectStats | GET | 获取项目统计数据 |
| 任务管理 | getTasks | GET | 获取项目任务列表 |
| 任务管理 | createTask | POST | 创建新任务 |
| 任务管理 | updateTask | PUT | 更新任务状态 |
| 任务管理 | deleteTask | DELETE | 删除任务 |
| 任务管理 | mergeTask | POST | 合并完成的任务 |
| 代理管理 | getAgents | GET | 获取项目代理列表 |
| 代理管理 | launchITerm | POST | 启动iTerm会话 |
| 代理管理 | launchAgentMonitor | POST | 启动代理监控 |
| 代理管理 | resetAgentTasks | POST | 重置代理任务 |
| 协调器 | getOrchestratorConfig | GET | 获取配置 |
| 协调器 | updateOrchestratorConfig | PUT | 更新配置 |
| 协调器 | startOrchestrator | POST | 启动协调器 |
| 协调器 | stopOrchestrator | POST | 停止协调器 |
| 计划生成 | generatePlan | POST | 生成项目计划 |
| 计划生成 | generateTaskBreakdown | POST | 生成任务分解 |

**章节来源**
- [api.ts](file://dashboard/frontend/src/services/api.ts#L29-L248)

## WebSocket通信机制

### WebSocket连接管理

后端WebSocket服务采用连接池管理模式，支持多客户端实时通信：

```mermaid
classDiagram
class WebSocketService {
-ws : WebSocket | null
-handlers : Set~MessageHandler~
-reconnectTimer : ReturnType~setTimeout~
-reconnectAttempts : number
-maxReconnectAttempts : number
-reconnectDelay : number
+connect() void
+disconnect() void
+subscribe(handler) Function
+send(message) void
-scheduleReconnect() void
}
class WebSocketManager {
+active_connections : WebSocket[]
+connect(websocket) Promise~void~
+disconnect(websocket) void
+send_personal_message(message, websocket) Promise~void~
+broadcast(message) Promise~void~
+broadcast_to_project(project_id, message) Promise~void~
}
class MessageHandler {
<<interface>>
+(message) void
}
WebSocketService --> MessageHandler : "管理"
WebSocketManager --> WebSocketService : "使用"
```

**图表来源**
- [websocket.ts](file://dashboard/frontend/src/services/websocket.ts#L5-L98)
- [websocket_manager.py](file://dashboard/backend/websocket_manager.py#L10-L55)

### WebSocket Hook抽象

前端提供了`useWebSocket` Hook来简化WebSocket事件处理：

```mermaid
sequenceDiagram
participant Component as React组件
participant Hook as useWebSocket Hook
participant Service as WebSocketService
participant Backend as WebSocket后端
Component->>Hook : 调用useWebSocket(handler)
Hook->>Service : connect()
Service->>Backend : 建立WebSocket连接
Backend-->>Service : 连接确认
Service-->>Hook : 连接成功
Hook->>Service : subscribe(handler)
Service-->>Hook : 返回取消订阅函数
Note over Backend,Service : 实时消息推送
Backend->>Service : 广播消息
Service->>Service : 解析消息
Service->>Hook : 触发消息处理器
Hook->>Component : 更新组件状态
Component->>Hook : 组件卸载
Hook->>Service : 取消订阅
Hook->>Service : disconnect()
```

**图表来源**
- [useWebSocket.ts](file://dashboard/frontend/src/hooks/useWebSocket.ts#L5-L24)
- [websocket.ts](file://dashboard/frontend/src/services/websocket.ts#L13-L98)

### 消息协议格式

WebSocket消息采用标准化的JSON格式：

| 字段名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| type | string | 是 | 消息类型标识符 |
| project_id | string | 否 | 关联的项目ID |
| data | any | 是 | 消息负载数据 |
| timestamp | string | 是 | UTC时间戳 |

**章节来源**
- [websocket.ts](file://dashboard/frontend/src/services/websocket.ts#L1-L98)
- [useWebSocket.ts](file://dashboard/frontend/src/hooks/useWebSocket.ts#L1-L24)
- [websocket_manager.py](file://dashboard/backend/websocket_manager.py#L1-L55)

## 数据模型与类型安全

### 前端类型定义

系统采用强类型设计，确保前后端数据一致性：

```mermaid
classDiagram
class Project {
+id : string
+name : string
+path : string
+description? : string
+project_overview? : string
+initial_prompt? : string
+plan? : string
+max_agents : number
+active : boolean
+created_at : string
+updated_at : string
+git_remote? : string
+is_git_repo? : boolean
}
class Task {
+id : string
+task_id? : number
+title : string
+description? : string
+prompt? : string
+status : TaskStatus
+branch : string
+session? : string
+dependencies? : string[]
+priority? : number
+created_at : string
+updated_at : string
+completed_at? : string
+merged_at? : string
}
class Agent {
+id : string
+session_name : string
+task_id : string
+task_title : string
+branch : string
+status : string
+progress : number
+started_at : string
+logs : string[]
}
class ProjectStats {
+total_tasks : number
+unclaimed_tasks : number
+up_next_tasks : number
+in_progress_tasks : number
+completed_tasks : number
+merged_tasks : number
+active_agents : number
+total_agents_run : number
}
class OrchestratorConfig {
+max_concurrent_agents : number
+auto_merge : boolean
+merge_strategy : string
+auto_spawn_interval : number
+enabled : boolean
+api_provider : string
+api_key? : string
+api_model : string
+api_base_url? : string
+api_version? : string
}
class WebSocketMessage {
+type : string
+project_id? : string
+data : any
+timestamp : string
}
Project --> Task : "包含"
Project --> Agent : "管理"
Project --> ProjectStats : "统计"
Project --> OrchestratorConfig : "配置"
WebSocketMessage --> Project : "关联"
WebSocketMessage --> Task : "关联"
WebSocketMessage --> Agent : "关联"
```

**图表来源**
- [index.ts](file://dashboard/frontend/src/types/index.ts#L1-L84)

### 后端数据模型

后端使用Pydantic模型确保数据验证和序列化：

| 模型名称 | 用途 | 主要字段 |
|---------|------|---------|
| Project | 项目实体 | id, name, path, max_agents, active |
| Task | 任务实体 | id, title, status, branch, dependencies |
| Agent | 代理实体 | id, session_name, task_id, status, progress |
| ProjectStats | 项目统计 | 各状态任务数量、活跃代理数 |
| OrchestratorConfig | 协调器配置 | 并发限制、合并策略、API设置 |
| WebSocketMessage | WebSocket消息 | type, project_id, data, timestamp |

**章节来源**
- [index.ts](file://dashboard/frontend/src/types/index.ts#L1-L84)
- [models.py](file://dashboard/backend/models.py#L99-L135)

## 通信时序与流程

### 前端请求到后端响应流程

```mermaid
sequenceDiagram
participant UI as 用户界面
participant API as API服务
participant Backend as FastAPI后端
participant Manager as 业务管理器
participant WS as WebSocket管理器
UI->>API : 发起API请求
API->>API : 构建请求参数
API->>Backend : HTTP请求
Backend->>Backend : 路由匹配
Backend->>Manager : 调用业务逻辑
Manager->>Manager : 执行数据库操作
Manager-->>Backend : 返回结果
Backend-->>API : HTTP响应
API->>API : 解析响应数据
API-->>UI : 返回结果
Note over UI,WS : 实时推送通知
Manager->>WS : 广播更新消息
WS->>WS : 推送给所有连接客户端
WS-->>UI : WebSocket消息
UI->>UI : 更新界面状态
```

**图表来源**
- [api.ts](file://dashboard/frontend/src/services/api.ts#L6-L27)
- [api.py](file://dashboard/backend/api.py#L94-L136)

### 实时推送流程

```mermaid
sequenceDiagram
participant Client as 客户端
participant WS as WebSocket服务
participant Backend as 后端业务
participant Manager as WebSocket管理器
Client->>WS : 建立WebSocket连接
WS->>Manager : 注册连接
Manager-->>WS : 连接确认
Backend->>Manager : 业务状态变更
Manager->>Manager : 构造WebSocket消息
Manager->>Manager : 广播消息给相关客户端
Manager-->>WS : 推送消息
WS-->>Client : 实时更新
Note over Client,Manager : 连接保持和心跳检测
Client->>WS : 心跳包
WS-->>Client : 确认响应
```

**图表来源**
- [websocket.ts](file://dashboard/frontend/src/services/websocket.ts#L13-L47)
- [websocket_manager.py](file://dashboard/backend/websocket_manager.py#L16-L55)

### 项目生命周期管理流程

```mermaid
flowchart TD
Start([开始项目]) --> CreateProject[创建项目]
CreateProject --> InitGit[初始化Git仓库]
InitGit --> ConfigOrchestrator[配置协调器]
ConfigOrchestrator --> StartOrchestrator[启动协调器]
StartOrchestrator --> MonitorTasks[监控任务状态]
MonitorTasks --> TaskUpdate{任务状态更新?}
TaskUpdate --> |是| BroadcastUpdate[广播更新消息]
TaskUpdate --> |否| MonitorTasks
BroadcastUpdate --> UpdateUI[更新前端界面]
UpdateUI --> MonitorTasks
MonitorTasks --> CheckCompletion{项目完成?}
CheckCompletion --> |是| StopOrchestrator[停止协调器]
CheckCompletion --> |否| MonitorTasks
StopOrchestrator --> CleanupResources[清理资源]
CleanupResources --> End([结束])
```

**图表来源**
- [api.py](file://dashboard/backend/api.py#L94-L136)
- [websocket_manager.py](file://dashboard/backend/websocket_manager.py#L32-L55)

## 错误处理与重连机制

### 前端错误处理策略

API服务实现了多层次的错误处理机制：

```mermaid
flowchart TD
Request[API请求] --> TryCatch{Try-Catch块}
TryCatch --> |网络错误| NetworkError[网络错误处理]
TryCatch --> |HTTP错误| HTTPError[HTTP状态码处理]
TryCatch --> |解析错误| ParseError[JSON解析错误]
TryCatch --> |成功| Success[返回数据]
NetworkError --> RetryLogic[重试逻辑]
HTTPError --> ErrorMsg[提取错误信息]
ParseError --> LogError[记录错误日志]
RetryLogic --> MaxRetry{达到最大重试次数?}
MaxRetry --> |否| DelayRetry[延迟重试]
MaxRetry --> |是| FinalError[最终错误]
DelayRetry --> Request
ErrorMsg --> UserNotification[用户通知]
LogError --> DebugInfo[调试信息]
Success --> TypeValidation[类型验证]
TypeValidation --> ReturnData[返回数据]
```

**图表来源**
- [api.ts](file://dashboard/frontend/src/services/api.ts#L6-L27)

### WebSocket重连机制

WebSocket服务实现了指数退避重连算法：

```mermaid
stateDiagram-v2
[*] --> Connected : 初始连接
Connected --> Disconnected : 连接断开
Disconnected --> CheckingReconnect : 检查重连条件
CheckingReconnect --> Reconnecting : 需要重连
CheckingReconnect --> Failed : 达到最大重试次数
Reconnecting --> BackoffDelay : 指数退避延迟
BackoffDelay --> Connecting : 尝试重新连接
Connecting --> Connected : 连接成功
Connecting --> Reconnecting : 连接失败
Failed --> [*] : 放弃重连
```

**图表来源**
- [websocket.ts](file://dashboard/frontend/src/services/websocket.ts#L50-L67)

### 错误恢复策略

| 错误类型 | 处理策略 | 恢复机制 |
|---------|---------|---------|
| 网络超时 | 自动重试3次 | 指数退避延迟 |
| HTTP 4xx错误 | 显示用户友好提示 | 不自动重试 |
| HTTP 5xx错误 | 自动重试3次 | 固定延迟重试 |
| WebSocket断开 | 指数退避重连 | 最大5次重试 |
| JSON解析错误 | 记录日志并降级处理 | 使用默认值 |
| 认证失败 | 清除缓存并要求重新登录 | 引导用户重新认证 |

**章节来源**
- [api.ts](file://dashboard/frontend/src/services/api.ts#L15-L27)
- [websocket.ts](file://dashboard/frontend/src/services/websocket.ts#L50-L67)

## 最佳实践与优化建议

### 性能优化建议

1. **请求批处理**：对于频繁的API调用，考虑使用批处理减少网络开销
2. **缓存策略**：对静态数据实施客户端缓存机制
3. **连接池管理**：合理配置WebSocket连接池大小
4. **消息压缩**：对大数据量的消息启用压缩传输

### 安全最佳实践

1. **输入验证**：前后端双重验证确保数据安全性
2. **CORS配置**：严格控制跨域请求来源
3. **认证授权**：实施适当的访问控制机制
4. **数据加密**：敏感数据传输使用HTTPS/WSS

### 监控与调试

1. **日志记录**：关键操作添加详细日志
2. **性能监控**：跟踪API响应时间和WebSocket连接状态
3. **错误追踪**：集成错误监控服务
4. **用户行为分析**：收集使用模式优化体验

### 扩展性考虑

1. **微服务架构**：为大型项目考虑服务拆分
2. **消息队列**：引入异步处理机制
3. **CDN加速**：静态资源使用内容分发网络
4. **负载均衡**：多实例部署支持水平扩展

## 总结

TaskTree项目通过精心设计的API服务集成方案，实现了高效的前后端通信。RESTful API提供了完整的CRUD操作和业务逻辑处理，而WebSocket机制则确保了实时数据推送和状态同步。

系统的主要优势包括：

1. **类型安全**：完整的TypeScript类型定义确保数据一致性
2. **错误处理**：多层次的错误处理和恢复机制
3. **实时通信**：可靠的WebSocket连接和消息广播
4. **可扩展性**：模块化的架构设计支持功能扩展
5. **开发体验**：良好的开发工具链和调试支持

通过遵循本文档中的最佳实践和优化建议，可以进一步提升系统的性能、可靠性和用户体验。这种混合通信模式为现代Web应用提供了坚实的技术基础，能够满足复杂业务场景的需求。