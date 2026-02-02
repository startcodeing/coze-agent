Agent 会话管理系统实现方案

     概述

     为 Agent 模块增加会话持久化功能，支持用户多会话管理、历史消息查看、以及会话与生成资源（视频/图片）的关联展示。

     用户需求确认

     - 关联方式: 使用中间关联表（agent_conversation_resources）
     - 会话标题: 使用用户首条消息自动生成（截取前50个字符）
     - 展示内容: 对话消息 + 生成结果（视频/图片）
     - 流式保存: 流式完成后一次性保存完整消息

     ---
     一、数据库表设计

     1.1 会话表 (agent_conversations)
     ┌──────────────────────┬──────────────┬───────────────────────────────┬───────┐
     │         字段         │     类型     │             说明              │ 索引  │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ id                   │ BIGINT       │ 主键ID（雪花算法）            │ PK    │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ title                │ VARCHAR(200) │ 会话标题（首条消息前50字符）  │ -     │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ bot_id               │ VARCHAR(100) │ Coze智能体ID                  │ -     │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ coze_conversation_id │ VARCHAR(100) │ Coze API返回的conversation_id │ INDEX │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ user_id              │ BIGINT       │ 用户ID（create_by）           │ INDEX │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ status               │ VARCHAR(20)  │ 状态：active/archived         │ -     │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ message_count        │ INT          │ 消息数量                      │ -     │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ last_message_at      │ DATETIME     │ 最后消息时间（排序用）        │ INDEX │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ metadata             │ TEXT         │ 扩展字段JSON                  │ -     │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ create_time          │ DATETIME     │ 创建时间                      │ INDEX │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ update_time          │ DATETIME     │ 更新时间                      │ -     │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ is_deleted           │ TINYINT(1)   │ 软删除标记                    │ -     │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ create_by            │ BIGINT       │ 创建人ID                      │ -     │
     ├──────────────────────┼──────────────┼───────────────────────────────┼───────┤
     │ update_by            │ BIGINT       │ 修改人ID                      │ -     │
     └──────────────────────┴──────────────┴───────────────────────────────┴───────┘
     复合索引: (user_id, create_time), 唯一索引: (user_id, coze_conversation_id)

     1.2 消息表 (agent_messages)
     ┌─────────────────┬──────────────┬─────────────────────────────┬───────┐
     │      字段       │     类型     │            说明             │ 索引  │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ id              │ BIGINT       │ 主键ID                      │ PK    │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ conversation_id │ BIGINT       │ 会话ID（外键）              │ INDEX │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ coze_chat_id    │ VARCHAR(100) │ Coze API返回的chat_id       │ -     │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ role            │ VARCHAR(20)  │ 角色：user/assistant/system │ -     │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ message_type    │ VARCHAR(20)  │ 类型：text/image/video/tool │ -     │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ content         │ TEXT         │ 消息内容                    │ -     │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ stream_chunks   │ INT          │ 流式消息块数量              │ -     │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ tokens_used     │ INT          │ Token消耗                   │ -     │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ metadata        │ TEXT         │ 扩展字段JSON                │ -     │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ create_time     │ DATETIME     │ 创建时间                    │ INDEX │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ is_deleted      │ TINYINT(1)   │ 软删除标记                  │ -     │
     ├─────────────────┼──────────────┼─────────────────────────────┼───────┤
     │ create_by       │ BIGINT       │ 创建人ID                    │ -     │
     └─────────────────┴──────────────┴─────────────────────────────┴───────┘
     复合索引: (conversation_id, create_time), 外键: conversation_id → agent_conversations(id)

     1.3 会话-资源关联表 (agent_conversation_resources)
     ┌─────────────────┬─────────────┬───────────────────────┬───────┐
     │      字段       │    类型     │         说明          │ 索引  │
     ├─────────────────┼─────────────┼───────────────────────┼───────┤
     │ id              │ BIGINT      │ 主键ID                │ PK    │
     ├─────────────────┼─────────────┼───────────────────────┼───────┤
     │ conversation_id │ BIGINT      │ 会话ID（外键）        │ INDEX │
     ├─────────────────┼─────────────┼───────────────────────┼───────┤
     │ message_id      │ BIGINT      │ 消息ID（外键，可选）  │ INDEX │
     ├─────────────────┼─────────────┼───────────────────────┼───────┤
     │ resource_type   │ VARCHAR(20) │ 资源类型：video/image │ -     │
     ├─────────────────┼─────────────┼───────────────────────┼───────┤
     │ resource_id     │ BIGINT      │ 资源表主键ID          │ INDEX │
     ├─────────────────┼─────────────┼───────────────────────┼───────┤
     │ created_at      │ DATETIME    │ 创建时间              │ -     │
     ├─────────────────┼─────────────┼───────────────────────┼───────┤
     │ create_by       │ BIGINT      │ 创建人ID              │ -     │
     └─────────────────┴─────────────┴───────────────────────┴───────┘
     唯一约束: (conversation_id, resource_type, resource_id), 外键: conversation_id → agent_conversations(id)

     ---
     二、API 接口设计

     2.1 会话管理接口
     ┌────────┬──────────────────────────────────────────────────┬──────────────────────────────┐
     │  方法  │                       路径                       │             功能             │
     ├────────┼──────────────────────────────────────────────────┼──────────────────────────────┤
     │ POST   │ /api/v1/agent/conversations                      │ 创建会话（发送首条消息）     │
     ├────────┼──────────────────────────────────────────────────┼──────────────────────────────┤
     │ GET    │ /api/v1/agent/conversations                      │ 获取用户会话列表（分页）     │
     ├────────┼──────────────────────────────────────────────────┼──────────────────────────────┤
     │ GET    │ /api/v1/agent/conversations/{id}                 │ 获取会话详情（含消息和资源） │
     ├────────┼──────────────────────────────────────────────────┼──────────────────────────────┤
     │ POST   │ /api/v1/agent/conversations/{id}/messages        │ 发送消息（非流式）           │
     ├────────┼──────────────────────────────────────────────────┼──────────────────────────────┤
     │ POST   │ /api/v1/agent/conversations/{id}/messages/stream │ 发送消息（流式SSE）          │
     ├────────┼──────────────────────────────────────────────────┼──────────────────────────────┤
     │ PUT    │ /api/v1/agent/conversations/{id}                 │ 更新会话标题                 │
     ├────────┼──────────────────────────────────────────────────┼──────────────────────────────┤
     │ DELETE │ /api/v1/agent/conversations/{id}                 │ 删除会话（软删除）           │
     ├────────┼──────────────────────────────────────────────────┼──────────────────────────────┤
     │ PATCH  │ /api/v1/agent/conversations/{id}/status          │ 归档/取消归档                │
     └────────┴──────────────────────────────────────────────────┴──────────────────────────────┘
     2.2 资源关联接口
     ┌────────┬──────────────────────────────────────────────────────────┬────────────────┐
     │  方法  │                           路径                           │      功能      │
     ├────────┼──────────────────────────────────────────────────────────┼────────────────┤
     │ POST   │ /api/v1/agent/conversations/{id}/resources               │ 关联资源到会话 │
     ├────────┼──────────────────────────────────────────────────────────┼────────────────┤
     │ DELETE │ /api/v1/agent/conversations/{id}/resources/{resource_id} │ 取消资源关联   │
     └────────┴──────────────────────────────────────────────────────────┴────────────────┘
     ---
     三、文件清单及路径

     新增文件（13个）

     数据模型

     - app/models/agent_conversation.py - 会话表模型
     - app/models/agent_message.py - 消息表模型
     - app/models/agent_conversation_resource.py - 会话-资源关联表模型

     服务层

     - app/services/agent_conversation.py - 会话管理服务
     - app/services/agent_message.py - 消息管理服务
     - app/services/agent_conversation_resource.py - 资源关联服务
     - app/services/agent_service.py - Agent统一服务（整合Coze+持久化）

     Schema

     - app/schemas/agent_conversation.py - 会话相关Schema（请求/响应模型）

     API路由

     - app/api/agent_conversation.py - 会话管理API

     数据库迁移

     - migrations/add_agent_conversation_tables.sql - SQL建表脚本

     测试

     - tests/test_agent_conversation.py - 单元测试

     修改文件（3个）

     - app/api/__init__.py - 注册新路由
     - app/models/__init__.py - 导入新模型
     - app/core/config.py - 添加Agent相关配置（可选）

     ---
     四、核心业务逻辑流程

     4.1 创建会话流程（首条消息）

     1. 接收用户query → 生成标题（截取前50字符）
     2. 调用 Coze API 发送消息
     3. 创建会话记录（agent_conversations）
     4. 保存用户消息（role=user）
     5. 保存助手消息（role=assistant）
     6. 提取响应中的资源信息
     7. 关联资源到会话（agent_conversation_resources）
     8. 更新会话统计（message_count, last_message_at）

     4.2 流式发送消息流程

     1. 获取会话记录
     2. 保存用户消息
     3. 创建空的助手消息记录（content=""）
     4. 流式调用 Coze API
     5. 接收每个chunk → 追加到content → SSE返回前端
     6. 流式结束 → 一次性更新完整content到数据库
     7. 提取并关联资源
     8. 更新会话统计

     4.3 获取会话详情流程

     1. 查询会话记录
     2. 查询会话的所有消息（按create_time排序）
     3. 查询会话关联的所有资源
     4. 根据resource_id JOIN查询资源详情（video_homepage/image_homepage）
     5. 组装返回数据（messages + resources）

     ---
     五、Schema 定义要点

     请求模型

     class ConversationCreate(BaseModel):
         query: str = Field(..., min_length=1, max_length=10000)
         stream: Optional[bool] = Field(False)
         auto_save: Optional[bool] = Field(True)

     class MessageSend(BaseModel):
         query: str = Field(..., min_length=1, max_length=10000)
         stream: Optional[bool] = Field(False)

     class ConversationUpdate(BaseModel):
         title: str = Field(..., min_length=1, max_length=200)

     class ResourceLink(BaseModel):
         resource_type: Literal["video", "image"]
         resource_id: int
         message_id: Optional[int] = None

     响应模型

     class MessageOut(BaseModel):
         id: int  # 序列化为字符串
         role: str
         content: str
         message_type: str
         create_time: datetime

     class ResourceOut(BaseModel):
         id: int
         resource_type: str
         resource_id: int
         message_id: Optional[int]
         resource_data: Optional[Dict]  # 包含video/image详情

     class ConversationDetailOut(BaseModel):
         id: int
         title: str
         bot_id: str
         status: str
         message_count: int
         messages: List[MessageOut]
         resources: List[ResourceOut]

     ---
     六、服务层设计要点

     ConversationService 关键方法

     - create_conversation() - 创建会话
     - get_conversation_by_id() - 获取会话详情（含权限验证）
     - get_conversation_by_coze_id() - 根据Coze conversation_id查询本地会话
     - list_conversations() - 获取用户会话列表（分页、筛选）
     - update_conversation_title() - 更新标题
     - delete_conversation() - 软删除
     - increment_message_count() - 增加消息计数
     - update_last_message_time() - 更新最后消息时间

     MessageService 关键方法

     - create_message() - 创建消息
     - get_messages_by_conversation() - 获取会话消息列表
     - build_chat_history() - 构建对话历史（用于继续对话）
     - append_stream_content() - 追加流式内容
     - finalize_stream_message() - 完成流式消息

     ConversationResourceService 关键方法

     - link_resource() - 关联资源到会话
     - unlink_resource() - 取消关联
     - get_conversation_resources() - 获取会话所有资源（含详情）
     - get_resources_by_message() - 获取消息关联的资源

     ---
     七、数据库迁移脚本

     -- 1. 创建会话表
     CREATE TABLE agent_conversations (
         id BIGINT NOT NULL COMMENT '主键ID',
         title VARCHAR(200) NOT NULL COMMENT '会话标题',
         bot_id VARCHAR(100) NOT NULL COMMENT 'Coze智能体ID',
         coze_conversation_id VARCHAR(100) COMMENT 'Coze conversation_id',
         user_id BIGINT NOT NULL COMMENT '用户ID',
         status VARCHAR(20) DEFAULT 'active' COMMENT '状态',
         message_count INT DEFAULT 0 COMMENT '消息数量',
         last_message_at DATETIME COMMENT '最后消息时间',
         metadata TEXT COMMENT '扩展字段',
         create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
         update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
         is_deleted TINYINT(1) DEFAULT 0,
         create_by BIGINT DEFAULT 0,
         update_by BIGINT DEFAULT 0,
         PRIMARY KEY (id),
         INDEX idx_user_id (user_id),
         INDEX idx_coze_conversation_id (coze_conversation_id),
         INDEX idx_user_create_time (user_id, create_time),
         UNIQUE KEY uk_user_coze_conv (user_id, coze_conversation_id)
     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent会话表';

     -- 2. 创建消息表
     CREATE TABLE agent_messages (
         id BIGINT NOT NULL COMMENT '主键ID',
         conversation_id BIGINT NOT NULL COMMENT '会话ID',
         coze_chat_id VARCHAR(100) COMMENT 'Coze chat_id',
         role VARCHAR(20) NOT NULL COMMENT '角色',
         message_type VARCHAR(20) DEFAULT 'text' COMMENT '消息类型',
         content TEXT NOT NULL COMMENT '内容',
         stream_chunks INT DEFAULT 0 COMMENT '流式块数',
         tokens_used INT COMMENT 'token数',
         metadata TEXT COMMENT '扩展字段',
         create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
         update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
         is_deleted TINYINT(1) DEFAULT 0,
         create_by BIGINT DEFAULT 0,
         update_by BIGINT DEFAULT 0,
         PRIMARY KEY (id),
         INDEX idx_conversation_id (conversation_id),
         INDEX idx_conversation_create_time (conversation_id, create_time),
         FOREIGN KEY (conversation_id) REFERENCES agent_conversations(id) ON DELETE CASCADE
     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent消息表';

     -- 3. 创建会话-资源关联表
     CREATE TABLE agent_conversation_resources (
         id BIGINT NOT NULL COMMENT '主键ID',
         conversation_id BIGINT NOT NULL COMMENT '会话ID',
         message_id BIGINT COMMENT '消息ID',
         resource_type VARCHAR(20) NOT NULL COMMENT '资源类型',
         resource_id BIGINT NOT NULL COMMENT '资源ID',
         created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
         create_by BIGINT DEFAULT 0,
         PRIMARY KEY (id),
         INDEX idx_conversation_id (conversation_id),
         INDEX idx_resource (resource_type, resource_id),
         INDEX idx_message_id (message_id),
         UNIQUE KEY uk_conv_resource (conversation_id, resource_type, resource_id),
         FOREIGN KEY (conversation_id) REFERENCES agent_conversations(id) ON DELETE CASCADE
     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent会话-资源关联表';

     ---
     八、关键实现文件

     最关键的5个文件

     1. app/models/agent_conversation.py - 会话表ORM模型，定义数据结构
     2. app/services/agent_conversation.py - 会话管理服务，核心业务逻辑
     3. app/services/agent_service.py - Agent统一服务，整合Coze调用+持久化
     4. app/api/agent_conversation.py - RESTful API接口，前端调用入口
     5. app/schemas/agent_conversation.py - Schema定义，请求/响应数据模型

     ---
     九、实现步骤建议

     Phase 1: 数据库层（优先级最高）

     1. 创建3个数据模型文件（models/）
     2. 编写SQL迁移脚本
     3. 执行数据库迁移

     Phase 2: 服务层

     1. 实现ConversationService
     2. 实现MessageService
     3. 实现ConversationResourceService
     4. 修改CozeAgentService集成持久化逻辑

     Phase 3: Schema和API层

     1. 定义Schema模型
     2. 实现API路由
     3. 注册路由到主应用

     Phase 4: 测试验证

     1. 编写单元测试
     2. 手动测试所有接口
     3. 测试流式消息保存
     4. 测试资源关联功能

     ---
     十、扩展性考虑

     多模态消息支持

     - message_type: text/image/video/audio/file
     - content存储不同格式的JSON

     Metadata扩展字段

     - 会话: {"tags": ["创作", "动画"], "model_version": "v1.0"}
     - 消息: {"tool_calls": [...], "references": [...], "rating": 5}

     未来功能预留

     - 会话导出（exported_at字段）
     - 会话分享（share_token字段）
     - 会话分支（parent_conversation_id字段）

     ---
     十一、验证测试

     手动测试流程

     1. 创建会话
       - 调用 POST /api/v1/agent/conversations
       - 验证会话创建成功，标题为首条消息前50字符
       - 验证消息保存（user + assistant）
     2. 流式发送消息
       - 调用 POST /api/v1/agent/conversations/{id}/messages/stream
       - 验证SSE流式返回
       - 验证消息在流式完成后保存到数据库
     3. 获取会话列表
       - 调用 GET /api/v1/agent/conversations
       - 验证分页、排序、筛选功能
     4. 获取会话详情
       - 调用 GET /api/v1/agent/conversations/{id}
       - 验证返回完整消息列表
       - 验证返回关联的资源详情
     5. 资源关联
       - 调用 POST /api/v1/agent/conversations/{id}/resources
       - 验证资源关联成功
       - 验证会话详情中包含资源数据
     6. 删除会话
       - 调用 DELETE /api/v1/agent/conversations/{id}
       - 验证软删除（is_deleted=1）
       - 验证关联消息级联删除