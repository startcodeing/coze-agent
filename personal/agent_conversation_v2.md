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

 新增文件（14个）

 数据模型（3个）

 - app/models/agent_conversation.py - 会话表模型
 - app/models/agent_message.py - 消息表模型
 - app/models/agent_conversation_resource.py - 会话-资源关联表模型

 服务层（统一放在 agent 目录下，参考 workflow 分层架构）

 - app/services/agent/__init__.py - 服务层初始化
 - app/services/agent/executor.py - Coze API 调用执行器
 - app/services/agent/conversation_service.py - 会话管理服务
 - app/services/agent/message_service.py - 消息管理服务
 - app/services/agent/resource_service.py - 资源关联服务
 - app/services/agent/orchestrator.py - 统一编排器（整合Coze+持久化）

 Schema

 - app/schemas/agent_conversation.py - 会话相关Schema（请求/响应模型）

 API路由

 - app/api/agent_conversation.py - 会话管理API

 数据库迁移

 - migrations/add_agent_conversation_tables.sql - SQL建表脚本

 修改文件（3个，仅新增导入，不修改现有逻辑）

 - app/api/__init__.py - 注册新路由（仅添加一行 import）
 - app/models/__init__.py - 导入新模型（仅添加3行 import）

 不修改的文件

 - app/api/coze_agent.py - 保持现有接口不变
 - app/services/coze_agent.py - 保持现有服务不变
 - app/schemas/coze_agent.py - 保持现有 Schema 不变

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
 六、服务层架构设计（参考 workflow 分层模式）

 6.1 分层架构

 app/services/agent/
 ├── __init__.py              # 导出所有服务
 ├── executor.py              # Coze API 调用执行器（底层）
 ├── conversation_service.py  # 会话管理服务（中间层）
 ├── message_service.py       # 消息管理服务（中间层）
 ├── resource_service.py      # 资源关联服务（中间层）
 └── orchestrator.py          # 统一编排器（上层）

 6.2 各层职责

 Executor（执行器层）

 - 职责: 封装 Coze API 调用，处理流式/非流式响应
 - 关键方法:
   - send_message() - 发送非流式消息
   - send_message_stream() - 发送流式消息（异步生成器）
 - 特点:
   - 纯粹的 API 调用封装
   - 不涉及数据库操作
   - 可被其他服务复用

 ConversationService（会话服务层）

 - 职责: 管理会话的 CRUD 操作
 - 关键方法:
   - create_conversation() - 创建会话
   - get_conversation_by_id() - 获取会话（含权限验证）
   - get_conversation_by_coze_id() - 根据 Coze ID 查询
   - list_conversations() - 获取会话列表（分页、筛选）
   - update_conversation_title() - 更新标题
   - delete_conversation() - 软删除
   - archive_conversation() - 归档/取消归档
 - 特点:
   - 所有操作都验证用户权限（user_id 匹配）
   - 软删除机制（查询时过滤 is_deleted）
   - 统一的错误处理

 MessageService（消息服务层）

 - 职责: 管理消息的 CRUD 和流式处理
 - 关键方法:
   - create_message() - 创建消息
   - create_user_message() - 创建用户消息
   - create_assistant_message() - 创建助手消息
   - get_messages_by_conversation() - 获取会话消息列表
   - build_chat_history() - 构建对话历史（用于继续对话）
   - append_stream_content() - 追加流式内容
   - finalize_stream_message() - 完成流式消息
 - 特点:
   - 支持流式消息的增量保存
   - 自动提取和关联资源
   - 统计 token 消耗

 ResourceService（资源关联服务层）

 - 职责: 管理会话与资源的关联关系
 - 关键方法:
   - link_resource() - 关联资源到会话
   - unlink_resource() - 取消关联
   - get_conversation_resources() - 获取会话所有资源（含详情）
   - get_resources_by_message() - 获取消息关联的资源
   - extract_resources_from_content() - 从内容中提取资源ID
 - 特点:
   - 支持多种资源类型（video/image）
   - 唯一约束防止重复关联
   - JOIN 查询获取资源详情

 Orchestrator（编排器层）

 - 职责: 整合所有服务，提供统一的业务接口
 - 关键方法:
   - create_conversation_with_message() - 创建会话并发送首条消息
   - send_message_to_conversation() - 向会话发送消息（非流式）
   - send_message_to_conversation_stream() - 向会话发送消息（流式）
 - 特点:
   - 协调多个服务完成复杂业务
   - 事务管理（确保数据一致性）
   - 统一的日志记录
   - 异常处理和回滚

 6.3 服务层调用关系

 Orchestrator（编排器）
     ├── ConversationService（会话服务）
     ├── MessageService（消息服务）
     ├── ResourceService（资源服务）
     └── Executor（执行器）
          └── Coze API

 6.4 关键实现模式

 模式1: 创建会话并发送消息（非流式）

 async def create_conversation_with_message(
     db: Session,
     query: str,
     user_id: int,
     bot_id: Optional[str] = None
 ) -> Tuple[bool, Optional[Dict], Optional[str]]:
     """
     创建会话并发送首条消息

     流程：
     1. 生成标题（截取前50字符）
     2. 创建会话记录
     3. 调用 Executor 发送消息到 Coze
     4. 保存用户消息
     5. 保存助手消息
     6. 提取并关联资源
     7. 更新会话统计
     """
     try:
         # 1. 创建会话
         conversation = conversation_service.create_conversation(...)

         # 2. 调用 Coze API
         success, response_data, error = await executor.send_message(...)

         if not success:
             # 回滚会话创建
             conversation_service.delete_conversation(db, conversation.id, user_id)
             return False, None, error

         # 3. 保存消息
         user_message = message_service.create_user_message(...)
         assistant_message = message_service.create_assistant_message(...)

         # 4. 关联资源
         resource_service.link_resources_from_response(...)

         # 5. 更新统计
         conversation_service.increment_message_count(db, conversation.id)
         conversation_service.update_last_message_time(db, conversation.id)

         return True, {...}, None
     except Exception as e:
         # 事务回滚
         db.rollback()
         return False, None, str(e)

 模式2: 流式发送消息

 async def send_message_to_conversation_stream(
     db: Session,
     conversation_id: int,
     query: str,
     user_id: int
 ) -> AsyncGenerator[Dict, None]:
     """
     流式发送消息到会话

     流程：
     1. 验证会话权限
     2. 保存用户消息
     3. 创建空的助手消息
     4. 流式调用 Coze API
     5. 逐块返回给前端
     6. 流式完成后更新完整内容
     7. 提取并关联资源
     8. 更新会话统计
     """
     # 1. 验证权限
     conversation = conversation_service.get_conversation_by_id(...)

     # 2. 保存用户消息
     user_message = message_service.create_user_message(...)

     # 3. 创建空的助手消息
     assistant_message = message_service.create_assistant_message(
         db=db,
         conversation_id=conversation_id,
         content="",  # 初始为空
         ...
     )

     # 4. 流式调用
     content_buffer = []
     async for chunk in executor.send_message_stream(...):
         yield chunk  # 返回给前端
         content_buffer.append(chunk)

     # 5. 更新完整内容
     final_content = "".join(content_buffer)
     message_service.finalize_stream_message(
         db=db,
         message_id=assistant_message.id,
         content=final_content
     )

     # 6. 关联资源
     resource_service.link_resources_from_content(...)

     # 7. 更新统计
     conversation_service.increment_message_count(...)
     conversation_service.update_last_message_time(...)

 模式3: 权限验证

 def get_conversation_by_id(
     db: Session,
     conversation_id: int,
     user_id: int
 ) -> Optional[AgentConversation]:
     """
     获取会话（含权限验证）

     验证逻辑：
     1. 查询会话
     2. 检查 is_deleted
     3. 检查 user_id 匹配（用户隔离）
     """
     conversation = db.query(AgentConversation).filter(
         AgentConversation.id == conversation_id,
         AgentConversation.is_deleted == False
     ).first()

     if not conversation:
         return None

     # 用户隔离验证
     if conversation.user_id != user_id:
         raise ValueError("无权访问该会话")

     return conversation

 ---
 七、关键文件实现要点

 7.1 模型文件实现（3个）

 app/models/agent_conversation.py

 from sqlalchemy import Column, String, BigInteger, DateTime, Text, Integer, Index
 from sqlalchemy.sql import text
 from app.models.base import BaseModel

 class AgentConversation(BaseModel):
     __tablename__ = "agent_conversations"
     __table_args__ = (
         Index('idx_user_id', 'user_id'),
         Index('idx_coze_conversation_id', 'coze_conversation_id'),
         Index('idx_user_create_time', 'user_id', 'create_time'),
     )

     title = Column(String(200), nullable=False, comment="会话标题")
     bot_id = Column(String(100), nullable=False, comment="Coze智能体ID")
     coze_conversation_id = Column(String(100), index=True, comment="Coze conversation_id")
     user_id = Column(BigInteger, index=True, nullable=False, comment="用户ID")
     status = Column(String(20), default="active", comment="状态：active/archived")
     message_count = Column(Integer, default=0, comment="消息数量")
     last_message_at = Column(DateTime, index=True, comment="最后消息时间")
     metadata = Column(Text, comment="扩展字段JSON")

 app/models/agent_message.py

 from sqlalchemy import Column, String, BigInteger, DateTime, Text, Integer, ForeignKey, Index
 from app.models.base import BaseModel

 class AgentMessage(BaseModel):
     __tablename__ = "agent_messages"
     __table_args__ = (
         Index('idx_conversation_id', 'conversation_id'),
         Index('idx_conversation_create_time', 'conversation_id', 'create_time'),
     )

     conversation_id = Column(BigInteger, ForeignKey("agent_conversations.id", ondelete="CASCADE"), index=True, nullable=False)
     coze_chat_id = Column(String(100), comment="Coze chat_id")
     role = Column(String(20), nullable=False, comment="角色：user/assistant/system")
     message_type = Column(String(20), default="text", comment="消息类型：text/image/video/tool")
     content = Column(Text, nullable=False, comment="消息内容")
     stream_chunks = Column(Integer, default=0, comment="流式消息块数量")
     tokens_used = Column(Integer, comment="Token消耗")
     metadata = Column(Text, comment="扩展字段JSON")

 app/models/agent_conversation_resource.py

 from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Index, UniqueConstraint
 from app.models.base import BaseModel

 class AgentConversationResource(BaseModel):
     __tablename__ = "agent_conversation_resources"
     __table_args__ = (
         UniqueConstraint('conversation_id', 'resource_type', 'resource_id', name='uk_conv_resource'),
         Index('idx_conversation_id', 'conversation_id'),
         Index('idx_resource', 'resource_type', 'resource_id'),
         Index('idx_message_id', 'message_id'),
     )

     conversation_id = Column(BigInteger, ForeignKey("agent_conversations.id", ondelete="CASCADE"), index=True, nullable=False)
     message_id = Column(BigInteger, ForeignKey("agent_messages.id", ondelete="SET NULL"), index=True)
     resource_type = Column(String(20), nullable=False, comment="资源类型：video/image")
     resource_id = Column(BigInteger, nullable=False, index=True, comment="资源ID")
     created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), comment="创建时间")

 7.2 Executor 实现（参考 coze_agent.py）

 # app/services/agent/executor.py
 import httpx
 import json
 from typing import Dict, Any, Optional, AsyncGenerator
 from app.core.config import settings

 class CozeAgentExecutor:
     """Coze Agent API 调用执行器"""

     def __init__(self):
         self.api_base = getattr(settings, "COZE_API_BASE", "https://api.coze.cn/v1")
         self.api_token = getattr(settings, "COZE_API_TOKEN", "")
         self.timeout = 120.0

     async def send_message(
         self,
         bot_id: str,
         user_id: str,
         query: str,
         conversation_id: Optional[str] = None,
         additional_messages: Optional[list] = None
     ) -> tuple[bool, Dict[str, Any] | None, str | None]:
         """发送非流式消息"""
         # 实现参考 coze_agent.py 的 CozeAgentService.send_message()
         pass

     async def send_message_stream(
         self,
         bot_id: str,
         user_id: str,
         query: str,
         conversation_id: Optional[str] = None,
         additional_messages: Optional[list] = None
     ) -> AsyncGenerator[Dict[str, Any], None]:
         """发送流式消息"""
         # 实现参考 coze_agent.py 的 CozeAgentService.send_message_stream()
         pass

 7.3 API 层实现模式

 # app/api/agent_conversation.py
 from fastapi import APIRouter, Depends, HTTPException, status
 from sqlalchemy.orm import Session
 from app.core.database import get_db
 from app.api.auth import oauth2_scheme, get_current_user_from_token
 from app.schemas.common import ResponseModel
 from app.schemas.agent_conversation import *
 from app.services.agent.orchestrator import agent_orchestrator

 router = APIRouter(prefix="/agent/conversations", tags=["Agent会话管理"])

 def _id_to_int(id_str: str) -> int:
     """字符串ID转整数"""
     if id_str is None:
         raise HTTPException(status_code=422, detail="ID不能为空")
     s = str(id_str).strip()
     if not s or not s.isdigit():
         raise HTTPException(status_code=422, detail="ID必须是数字字符串")
     return int(s)

 def get_current_user_id(token: str, db: Session) -> int:
     """获取当前用户ID"""
     user = get_current_user_from_token(token, db)
     return user.id

 @router.post("/", response_model=ResponseModel[ConversationDetailOut], summary="创建会话")
 async def create_conversation(
     request: ConversationCreate,
     current_user_id: int = Depends(get_current_user_id),
     db: Session = Depends(get_db)
 ):
     """创建会话并发送首条消息"""
     success, result, error = await agent_orchestrator.create_conversation_with_message(
         db=db,
         query=request.query,
         user_id=current_user_id,
         stream=request.stream
     )

     if not success:
         raise HTTPException(status_code=500, detail=error)

     return ResponseModel(data=result, message="会话创建成功")

 @router.post("/{id}/messages/stream", summary="发送消息（流式）")
 async def send_message_stream(
     id: str,
     request: MessageSend,
     current_user_id: int = Depends(get_current_user_id),
     db: Session = Depends(get_db)
 ):
     """流式发送消息"""
     conversation_id = _id_to_int(id)
     from fastapi.responses import StreamingResponse

     async def generate():
         async for chunk in agent_orchestrator.send_message_to_conversation_stream(
             db=db,
             conversation_id=conversation_id,
             query=request.query,
             user_id=current_user_id
         ):
             yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

     return StreamingResponse(generate(), media_type="text/event-stream")

 ---
 八、数据库迁移脚本

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

 ---
 十二、实施优先级

 P0（必须实现）- 核心功能

 1. 数据库层
   - 3 个数据库模型文件
   - SQL 迁移脚本
 2. 服务层
   - Executor（Coze API 调用封装）
   - ConversationService（基础 CRUD）
   - MessageService（基础 CRUD）
   - Orchestrator（统一编排器）
 3. API 层
   - POST /agent/conversations（创建会话）
   - POST /agent/conversations/{id}/messages/stream（流式发送消息）
   - GET /agent/conversations（会话列表）

 P1（重要功能）- 增强功能

 1. GET /agent/conversations/{id}（会话详情）
 2. PUT /agent/conversations/{id}（更新标题）
 3. DELETE /agent/conversations/{id}（删除会话）
 4. ResourceService（资源关联）

 P2（扩展功能）- 优化功能

 1. 非流式发送消息接口
 2. 归档/取消归档功能
 3. 资源关联/取消关联接口
 4. 会话搜索和高级筛选

 ---
 十三、关键注意事项

 13.1 用户隔离

 - 所有会话查询必须验证 user_id 匹配
 - 防止用户访问其他用户的会话
 - 使用 create_by 字段记录创建者

 13.2 软删除机制

 - 所有查询默认过滤 is_deleted == False
 - 删除操作只更新标记，不物理删除
 - 级联删除：会话删除 → 消息删除，资源关联保留

 13.3 ID 处理

 - 数据库使用 BigInteger 雪花算法 ID
 - API 层统一使用字符串传递 ID
 - 序列化时 ID 转为字符串（避免 JS 精度丢失）

 13.4 事务管理

 - 创建会话 + 发送消息使用事务
 - 失败时回滚所有操作
 - 使用 try-except-rollback 模式

 13.5 流式消息处理

 - 先创建空消息记录
 - 流式过程中缓冲内容
 - 流式结束后一次性更新完整内容
 - 注意数据库连接超时问题

 13.6 资源关联

 - 唯一约束防止重复关联
 - 支持多种资源类型（video/image）
 - 使用 JOIN 查询获取资源详情
 - 自动从 Coze 响应中提取资源 ID

 ---
 十四、文件结构总览

 app/
 ├── models/
 │   ├── agent_conversation.py           # 新增：会话表模型
 │   ├── agent_message.py                # 新增：消息表模型
 │   └── agent_conversation_resource.py  # 新增：资源关联表模型
 │
 ├── services/
 │   └── agent/                          # 新增目录：服务层
 │       ├── __init__.py                  # 导出所有服务
 │       ├── executor.py                  # Coze API 调用执行器
 │       ├── conversation_service.py       # 会话管理服务
 │       ├── message_service.py            # 消息管理服务
 │       ├── resource_service.py           # 资源关联服务
 │       └── orchestrator.py              # 统一编排器
 │
 ├── schemas/
 │   └── agent_conversation.py            # 新增：Schema 定义
 │
 └── api/
     ├── __init__.py                      # 修改：注册新路由（仅添加一行 import）
     ├── coze_agent.py                    # 不修改：保持现有接口不变
     └── agent_conversation.py            # 新增：会话管理 API

 migrations/
 └── add_agent_conversation_tables.sql    # 新增：建表脚本

 说明：
 - 所有新增文件都有明确标注
 - 修改的文件仅限于添加导入，不修改现有逻辑
 - 服务层统一放在 agent/ 目录下，遵循项目分层架构
 - 参考了 workflow/ 的分层模式（executor → services → orchestrator）

 ---
 十五、不兼容的变更说明

 与现有代码的关系

 1. app/api/coze_agent.py
   - 保持不变：现有的 3 个接口（/chat, /chat/stream, /chat/stream/proxy）不受影响
   - 新增接口：/agent/conversations/* 为新的会话管理接口
   - 两者并存：旧接口继续使用，新接口提供持久化功能
 2. app/services/coze_agent.py
   - 保持不变：CozeAgentService 继续提供基础功能
   - 复用逻辑：Executor 参考其实现，但不在原文件修改
 3. app/schemas/coze_agent.py
   - 保持不变：现有的 Schema 继续使用
   - 新增 Schema：agent_conversation.py 定义新的数据模型

 ---
 十六、后续扩展方向

 1. 会话导出：支持导出对话历史为 PDF/Markdown
 2. 会话分享：生成分享链接，允许他人查看
 3. 会话分支：支持从某个消息点创建新分支
 4. 会话模板：保存常用对话为模板
 5. 消息搜索：全文搜索会话内容
 6. 智能摘要：自动生成长对话的摘要
 7. 多模态支持：图片、视频、文件消息
 8. 实时同步：WebSocket 实时推送消息

 ---
 十七、总结

 核心目标

 为 Agent 模块实现完整的会话管理系统，支持：
 - 多会话管理
 - 消息持久化
 - 资源关联展示
 - 用户隔离和权限控制

 技术方案

 - 分层架构：Executor → Services → Orchestrator → API
 - 数据库设计：3 个表（会话、消息、资源关联）
 - 不修改现有代码：所有功能都是新增，与现有代码并存
 - 遵循项目规范：参考 workflow 分层模式，保持代码风格一致

 实施路径

 按照 P0 → P1 → P2 的优先级顺序实施，确保核心功能优先可用。

 预期收益

 - 用户体验提升：可查看历史对话记录
 - 功能增强：支持资源关联展示
 - 易于扩展：清晰的分层架构便于后续功能添加
