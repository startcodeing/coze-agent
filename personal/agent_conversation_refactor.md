异步工作流资源绑定与轮询实现计划

 需求概述

 将 /messages/stream
 接口中的会话消息资源保存逻辑从同步改为异步，通过工作流执行ID（execute_id）绑定资源，并提供轮询接口供前端查询工作流状态和获取最终资源地址。

 修改范围

 核心文件

 - app/models/agent_conversation_resource.py - 数据模型
 - app/services/agent/resource_service.py - 服务层
 - app/api/agent_conversation.py - API层
 - app/schemas/agent_conversation.py - 数据验证模型
 - 新建 migrations/add_workflow_fields_to_agent_conversation_resources.sql - 数据库迁移

 ---
 实施步骤

 步骤1：数据库迁移（新增字段和索引）

 文件: migrations/add_workflow_fields_to_agent_conversation_resources.sql（新建）

 在 agent_conversation_resources 表添加以下字段：

 ALTER TABLE agent_conversation_resources
 ADD COLUMN execute_id VARCHAR(100) COMMENT '工作流执行ID（Coze workflow execute_id）',
 ADD COLUMN workflow_status VARCHAR(20) DEFAULT 'pending' COMMENT '工作流状态：pending/running/success/failed',
 ADD COLUMN workflow_error TEXT COMMENT '工作流错误信息',
 ADD COLUMN completed_at DATETIME COMMENT '工作流完成时间',
 ADD COLUMN task_type VARCHAR(20) COMMENT '任务类型：video/image';

 CREATE INDEX idx_execute_id ON agent_conversation_resources(execute_id);
 CREATE INDEX idx_workflow_status ON agent_conversation_resources(workflow_status);

 ---
 步骤2：修改ORM模型

 文件: app/models/agent_conversation_resource.py

 在 AgentConversationResource 类中添加新字段：

 # 在现有字段后添加
 execute_id = Column(String(100), comment="工作流执行ID（Coze workflow execute_id）")
 workflow_status = Column(String(20), default="pending", comment="工作流状态：pending/running/success/failed")
 workflow_error = Column(Text, comment="工作流错误信息")
 task_type = Column(String(20), comment="任务类型：video/image")
 completed_at = Column(DateTime, comment="工作流完成时间")

 # 在 __table_args__ 中添加索引
 Index('idx_execute_id', 'execute_id'),
 Index('idx_workflow_status', 'workflow_status'),

 ---
 步骤3：添加Schema模型

 文件: app/schemas/agent_conversation.py（文件末尾追加）

 class WorkflowResourcePollRequest(BaseModel):
     """工作流资源轮询请求模型"""
     resource_link_id: int = Field(..., gt=0, description="资源关联ID")
     execute_id: str = Field(..., min_length=1, description="工作流执行ID")
     task_type: Literal["video", "image"] = Field(..., description="任务类型")


 class WorkflowResourcePollOut(BaseModel):
     """工作流资源轮询响应模型"""
     resource_link_id: int = Field(..., description="资源关联ID")
     workflow_status: Literal["pending", "running", "success", "failed"] = Field(..., description="工作流状态")
     resource_url: Optional[str] = Field(None, description="资源URL（成功时有值）")
     error: Optional[str] = Field(None, description="错误信息（失败时有值）")
     completed_at: Optional[datetime] = Field(None, description="完成时间")

 ---
 步骤4：扩展ResourceService

 文件: app/services/agent/resource_service.py

 添加以下三个方法：

 4.1 创建带工作流ID的资源关联

 def link_resource_with_workflow(
     self,
     db: Session,
     conversation_id: int,
     resource_type: str,
     resource_id: int,
     message_id: Optional[int] = None,
     execute_id: Optional[str] = None,
     task_type: Optional[str] = None,
     create_by: int = 0
 ) -> Optional[AgentConversationResource]:
     """
     关联资源到会话（支持工作流绑定）

     参数:
         conversation_id: 会话ID
         resource_type: 资源类型（video/image）
         resource_id: 资源ID（占位时传0）
         message_id: 消息ID（可选）
         execute_id: 工作流执行ID（可选）
         task_type: 任务类型（video/image）
         create_by: 创建人ID

     返回:
         创建的关联对象，失败则返回None
     """
     if resource_type not in self.SUPPORTED_RESOURCE_TYPES:
         logger.error(f"不支持的资源类型: {resource_type}")
         return None

     # 检查是否已存在（resource_id > 0时才检查）
     existing = None
     if resource_id > 0:
         existing = db.query(AgentConversationResource).filter(
             AgentConversationResource.conversation_id == conversation_id,
             AgentConversationResource.resource_type == resource_type,
             AgentConversationResource.resource_id == resource_id,
             AgentConversationResource.is_deleted == False
         ).first()

     if existing:
         logger.debug(f"资源关联已存在，conversation_id={conversation_id}")
         return existing

     # 创建关联记录
     from app.core.snowflake import generate_snowflake_id
     id = generate_snowflake_id()

     link = AgentConversationResource(
         id=id,
         conversation_id=conversation_id,
         message_id=message_id,
         resource_type=resource_type,
         resource_id=resource_id,
         execute_id=execute_id,
         task_type=task_type,
         workflow_status="running" if execute_id else "success",
         create_by=create_by
     )

     db.add(link)
     db.commit()
     db.refresh(link)

     logger.info(f"创建资源关联成功（含工作流信息），id={id}, execute_id={execute_id}")
     return link

 4.2 轮询并更新资源

 async def poll_and_update_workflow_resource(
     self,
     db: Session,
     resource_link_id: int,
     execute_id: str,
     task_type: str,
     user_id: int
 ) -> dict:
     """
     轮询工作流状态并更新资源

     参数:
         resource_link_id: 资源关联ID
         execute_id: 工作流执行ID
         task_type: 任务类型（video/image）
         user_id: 用户ID

     返回:
         {
             "status": "running" | "success" | "failed",
             "resource_url": "...",
             "error": None
         }
     """
     from app.services.workflow.orchestrator import workflow_orchestrator
     import httpx
     import asyncio
     from app.services.storage_service import get_storage_service
     from app.services.asset import create_asset
     from app.schemas.asset import AssetCreate
     from app.core.snowflake import generate_snowflake_id
     from datetime import datetime

     # 1. 查询资源关联记录
     resource_link = db.query(AgentConversationResource).filter(
         AgentConversationResource.id == resource_link_id,
         AgentConversationResource.is_deleted == False
     ).first()

     if not resource_link:
         logger.error(f"资源关联记录不存在，id={resource_link_id}")
         return {"status": "failed", "resource_url": None, "error": "资源关联记录不存在"}

     # 2. 查询工作流状态
     result = await workflow_orchestrator.get_workflow_result(
         task_type=task_type,
         execute_id=execute_id
     )

     workflow_status = result.get("status")  # running, success, failed

     # 3. 根据状态处理
     if workflow_status == "running":
         resource_link.workflow_status = "running"
         db.commit()
         logger.info(f"工作流运行中，execute_id={execute_id}")
         return {"status": "running", "resource_url": None, "error": None}

     elif workflow_status == "success":
         final_video_url = result.get("final_video_url")

         if not final_video_url:
             error_msg = "工作流成功但未返回资源URL"
             logger.error(f"{error_msg}，execute_id={execute_id}")
             resource_link.workflow_status = "failed"
             resource_link.workflow_error = error_msg
             resource_link.completed_at = datetime.now()
             db.commit()
             return {"status": "failed", "resource_url": None, "error": error_msg}

         try:
             # 下载视频/图片
             async def download_file():
                 async with httpx.AsyncClient(timeout=300.0) as client:
                     response = await client.get(final_video_url)
                     response.raise_for_status()
                     return response.content

             # 同步执行下载
             try:
                 loop = asyncio.get_running_loop()
                 import concurrent.futures
                 with concurrent.futures.ThreadPoolExecutor() as pool:
                     future = pool.submit(asyncio.run, download_file())
                     file_bytes = future.result()
             except RuntimeError:
                 file_bytes = asyncio.run(download_file())

             # 生成文件名并上传
             file_extension = "mp4" if task_type == "video" else "jpg"
             filename = f"agent_{task_type}_{resource_link_id}_{generate_snowflake_id()}.{file_extension}"

             storage = get_storage_service()
             upload_result = storage.upload_bytes(
                 category=task_type,
                 filename=filename,
                 content=file_bytes,
                 content_type=f"video/{file_extension}" if task_type == "video" else "image/jpeg"
             )

             logger.info(f"文件上传成功，url={upload_result.url}")

             # 创建 Asset 记录
             asset_create = AssetCreate(
                 remark=f"agent生成{task_type}",
                 is_first_image="6",
                 name=f"Agent{task_type}_{generate_snowflake_id()}",
                 type=task_type,
                 file_url=upload_result.url,
                 file_extension=file_extension,
                 description=f"会话{resource_link.conversation_id}中通过Agent工作流生成",
                 version=1,
                 tags="",
                 mode="ai_generate"
             )

             asset_record = create_asset(
                 db=db,
                 asset_in=asset_create,
                 current_user_id=user_id
             )

             # 更新资源关联记录
             resource_link.resource_id = cast(int, asset_record.id)
             resource_link.workflow_status = "success"
             resource_link.completed_at = datetime.now()
             db.commit()

             logger.info(f"工作流资源处理成功，asset_id={asset_record.id}, url={upload_result.url}")

             return {"status": "success", "resource_url": upload_result.url, "error": None}

         except Exception as e:
             error_msg = f"处理资源失败: {str(e)}"
             logger.exception(f"处理工作流资源异常，execute_id={execute_id}")
             resource_link.workflow_status = "failed"
             resource_link.workflow_error = error_msg
             resource_link.completed_at = datetime.now()
             db.commit()
             return {"status": "failed", "resource_url": None, "error": error_msg}

     elif workflow_status == "failed":
         error_msg = result.get("error") or "工作流执行失败"
         logger.error(f"工作流执行失败，execute_id={execute_id}, error={error_msg}")

         resource_link.workflow_status = "failed"
         resource_link.workflow_error = error_msg
         resource_link.completed_at = datetime.now()
         db.commit()

         return {"status": "failed", "resource_url": None, "error": error_msg}

     else:
         error_msg = f"未知的工作流状态: {workflow_status}"
         logger.error(error_msg)
         return {"status": "failed", "resource_url": None, "error": error_msg}

 4.3 获取待轮询资源列表

 def get_pending_resources(
     self,
     db: Session,
     conversation_id: Optional[int] = None,
     limit: int = 100
 ) -> List[AgentConversationResource]:
     """获取待轮询的资源列表"""
     query = db.query(AgentConversationResource).filter(
         AgentConversationResource.execute_id.isnot(None),
         AgentConversationResource.workflow_status.in_(["pending", "running"]),
         AgentConversationResource.is_deleted == False
     )

     if conversation_id:
         query = query.filter(AgentConversationResource.conversation_id == conversation_id)

     return query.order_by(AgentConversationResource.created_at.asc()).limit(limit).all()

 ---
 步骤5：修改API接口

 文件: app/api/agent_conversation.py

 5.1 修改 /messages/stream 接口

 位置: 第445-458行（_send_message_stream_internal_raw 方法中的工具响应处理）

 修改前:
 if data.get("type") == "tool_response":
     content = data.get("content", "")
     if content:
         video_id = self.resource_service.process_tool_response_video(...)

 修改后:
 import json

 if data.get("type") == "tool_response":
     content = data.get("content", "")
     if content:
         try:
             content_data = json.loads(content)
             execute_id = content_data.get("execute_id")

             # 如果包含 execute_id，说明是异步工作流，创建占位资源关联
             if execute_id:
                 resource_link = self.resource_service.link_resource_with_workflow(
                     db=db,
                     conversation_id=conversation_id,
                     resource_type="video",
                     resource_id=0,  # 占位ID
                     message_id=cast(int, assistant_message.id),
                     execute_id=execute_id,
                     task_type="video",
                     create_by=user_id
                 )
                 if resource_link:
                     logger.info(f"创建异步工作流资源关联成功，resource_link_id={resource_link.id}, execute_id={execute_id}")

                     # 在SSE事件中返回资源关联ID和execute_id
                     yield f"event: workflow.resource.created\n"
                     yield f"data: {json.dumps({'resource_link_id': resource_link.id, 'execute_id': execute_id, 'task_type': 'video'},
 ensure_ascii=False)}\n\n"
             else:
                 # 如果没有 execute_id，使用原有的同步处理逻辑
                 video_id = self.resource_service.process_tool_response_video(
                     db=db,
                     conversation_id=conversation_id,
                     message_id=cast(int, assistant_message.id),
                     content=content,
                     user_id=user_id
                 )
                 if video_id:
                     logger.info(f"工具响应视频处理成功，video_id={video_id}")
         except json.JSONDecodeError as e:
             logger.error(f"解析tool_response content失败: {e}")

 5.2 新增轮询接口

 位置: 文件末尾（在 @router.delete 接口之后）

 @router.post(
     "/resources/poll",
     response_model=ResponseModel[WorkflowResourcePollOut],
     summary="轮询工作流资源状态",
     description="查询异步工作流的执行状态并更新资源地址"
 )
 async def poll_workflow_resource(
     request: WorkflowResourcePollRequest,
     token: Annotated[str, Depends(oauth2_scheme)],
     db: Session = Depends(get_db)
 ):
     """
     轮询工作流资源状态

     参数:
         - resource_link_id: 资源关联ID
         - execute_id: 工作流执行ID
         - task_type: 任务类型（video/image）

     返回:
         - workflow_status: 工作流状态
         - resource_url: 资源URL（成功时有值）
         - error: 错误信息（失败时有值）
         - completed_at: 完成时间
     """
     user_id = get_current_user_id(token, db)

     # 验证资源关联记录
     resource_link = db.query(AgentConversationResource).filter(
         AgentConversationResource.id == request.resource_link_id,
         AgentConversationResource.is_deleted == False
     ).first()

     if not resource_link:
         raise HTTPException(
             status_code=status.HTTP_404_NOT_FOUND,
             detail="资源关联记录不存在"
         )

     # 调用service层轮询并更新
     result = await resource_service.poll_and_update_workflow_resource(
         db=db,
         resource_link_id=request.resource_link_id,
         execute_id=request.execute_id,
         task_type=request.task_type,
         user_id=user_id
     )

     # 构建响应
     response_data = WorkflowResourcePollOut(
         resource_link_id=request.resource_link_id,
         workflow_status=result["status"],
         resource_url=result.get("resource_url"),
         error=result.get("error"),
         completed_at=resource_link.completed_at
     )

     status_message = {
         "running": "工作流运行中",
         "success": "资源生成成功",
         "failed": "工作流执行失败"
     }.get(result["status"], "未知状态")

     return ResponseModel(data=response_data, message=status_message)


 @router.get(
     "/{conversation_id}/resources/pending",
     response_model=ResponseModel[List[Dict[str, Any]]],
     summary="获取会话的待轮询资源",
     description="获取会话中所有工作流未完成的资源列表"
 )
 async def get_pending_resources(
     conversation_id: str,
     token: Annotated[str, Depends(oauth2_scheme)],
     db: Session = Depends(get_db)
 ):
     """
     获取会话的待轮询资源

     参数:
         - conversation_id: 会话ID（数字字符串）

     返回:
         待轮询的资源列表
     """
     user_id = get_current_user_id(token, db)
     conversation_id_int = _id_to_int(conversation_id, "会话ID")

     # 验证会话权限
     conversation = conversation_service.get_conversation_by_id(
         db=db,
         conversation_id=conversation_id_int,
         user_id=user_id
     )

     if not conversation:
         raise HTTPException(
             status_code=status.HTTP_404_NOT_FOUND,
             detail="会话不存在或无权访问"
         )

     # 获取待轮询资源
     pending_resources = resource_service.get_pending_resources(
         db=db,
         conversation_id=conversation_id_int
     )

     # 构建响应
     items = []
     for res in pending_resources:
         items.append({
             "resource_link_id": res.id,
             "resource_type": res.resource_type,
             "execute_id": res.execute_id,
             "task_type": res.task_type,
             "workflow_status": res.workflow_status,
             "created_at": res.created_at.isoformat() if res.created_at else None
         })

     return ResponseModel(data=items, message="获取待轮询资源成功")

 5.3 添加必要的导入

 在文件顶部的导入部分添加：
 from app.schemas.agent_conversation import WorkflowResourcePollRequest, WorkflowResourcePollOut
 from typing import Dict, Any

 ---
 实施顺序

 阶段1：数据库和模型（基础层）

 1. 执行数据库迁移脚本 migrations/add_workflow_fields_to_agent_conversation_resources.sql
 2. 修改 app/models/agent_conversation_resource.py，添加新字段和索引
 3. 验证表结构：DESCRIBE agent_conversation_resources;

 阶段2：Schema和服务层（业务层）

 4. 修改 app/schemas/agent_conversation.py，添加轮询相关Schema
 5. 修改 app/services/agent/resource_service.py，添加三个新方法：
   - link_resource_with_workflow()
   - poll_and_update_workflow_resource()
   - get_pending_resources()

 阶段3：API层（接口层）

 6. 修改 app/api/agent_conversation.py：
   - 修改 /messages/stream 接口的工具响应处理逻辑
   - 添加 /resources/poll 接口
   - 添加 /{conversation_id}/resources/pending 接口

 阶段4：测试和验证

 7. 重启服务，验证接口可用性
 8. 测试轮询流程（发送消息 → 收到 workflow.resource.created → 轮询状态 → 获取资源）

 ---
 验证测试

 测试场景1：异步工作流成功

 # 1. 发送消息（带视频生成）
 curl -X POST http://localhost:8000/api/v1/agent/conversations/messages/stream \
   -H "Authorization: Bearer <token>" \
   -H "Content-Type: application/json" \
   -d '{"query": "生成一个视频", "confirmAndGenerate": true}'

 # 观察 SSE 事件：workflow.resource.created
 # 记录返回的 resource_link_id 和 execute_id

 # 2. 轮询工作流状态（每3秒调用一次）
 curl -X POST http://localhost:8000/api/v1/agent/conversations/resources/poll \
   -H "Authorization: Bearer <token>" \
   -H "Content-Type: application/json" \
   -d '{
     "resource_link_id": 1234567890,
     "execute_id": "execute_xxx",
     "task_type": "video"
   }'

 # 预期响应：
 # 第一次：{"workflow_status": "running", ...}
 # 第N次：{"workflow_status": "success", "resource_url": "https://..."}

 测试场景2：获取待轮询资源列表

 curl http://localhost:8000/api/v1/agent/conversations/{conversation_id}/resources/pending \
   -H "Authorization: Bearer <token>"

 # 预期响应：
 # {
 #   "code": 200,
 #   "data": [
 #     {"resource_link_id": 123, "execute_id": "xxx", "task_type": "video", "workflow_status": "running"}
 #   ]
 # }

 测试场景3：工作流失败

 # 使用错误的 execute_id 轮询
 curl -X POST http://localhost:8000/api/v1/agent/conversations/resources/poll \
   -H "Authorization: Bearer <token>" \
   -H "Content-Type: application/json" \
   -d '{
     "resource_link_id": 1234567890,
     "execute_id": "invalid_execute_id",
     "task_type": "video"
   }'

 # 预期响应：
 # {"workflow_status": "failed", "error": "..."}

 ---
 前端集成建议

 SSE事件监听

 const eventSource = new EventSource('/api/v1/agent/conversations/messages/stream?...');

 // 监听新增的工作流资源创建事件
 eventSource.addEventListener('workflow.resource.created', (event) => {
   const { resource_link_id, execute_id, task_type } = JSON.parse(event.data);

   // 开始轮询工作流状态
   pollWorkflowResource(resource_link_id, execute_id, task_type);
 });

 // 轮询函数
 async function pollWorkflowResource(resourceLinkId, executeId, taskType) {
   const maxAttempts = 60; // 最多轮询60次（约2分钟）
   let attempts = 0;

   const pollInterval = setInterval(async () => {
     attempts++;

     const response = await fetch('/api/v1/agent/conversations/resources/poll', {
       method: 'POST',
       headers: {
         'Content-Type': 'application/json',
         'Authorization': `Bearer ${token}`
       },
       body: JSON.stringify({
         resource_link_id: resourceLinkId,
         execute_id: executeId,
         task_type: taskType
       })
     });

     const result = await response.json();
     const { data } = result;

     if (data.workflow_status === 'success') {
       clearInterval(pollInterval);
       showResource(data.resource_url); // 显示生成的视频/图片
     } else if (data.workflow_status === 'failed') {
       clearInterval(pollInterval);
       showError(data.error); // 显示错误信息
     } else if (attempts >= maxAttempts) {
       clearInterval(pollInterval);
       showError('工作流执行超时');
     }
   }, 3000); // 每3秒轮询一次
 }

 ---
 关键文件清单
 ┌────────────────────────────────────────────────────────────────────┬──────────┬──────────────────────────────────┐
 │                              文件路径                              │ 修改类型 │               说明               │
 ├────────────────────────────────────────────────────────────────────┼──────────┼──────────────────────────────────┤
 │ migrations/add_workflow_fields_to_agent_conversation_resources.sql │ 新建     │ 数据库迁移脚本                   │
 ├────────────────────────────────────────────────────────────────────┼──────────┼──────────────────────────────────┤
 │ app/models/agent_conversation_resource.py                          │ 修改     │ 添加工作流相关字段               │
 ├────────────────────────────────────────────────────────────────────┼──────────┼──────────────────────────────────┤
 │ app/schemas/agent_conversation.py                                  │ 修改     │ 添加轮询相关Schema               │
 ├────────────────────────────────────────────────────────────────────┼──────────┼──────────────────────────────────┤
 │ app/services/agent/resource_service.py                             │ 修改     │ 添加三个新方法                   │
 ├────────────────────────────────────────────────────────────────────┼──────────┼──────────────────────────────────┤
 │ app/api/agent_conversation.py                                      │ 修改     │ 修改流式接口逻辑，添加两个新接口 │
 └────────────────────────────────────────────────────────────────────┴──────────┴──────────────────────────────────┘
 ---
 注意事项

 1. 向后兼容性：保留了原有的同步处理逻辑，只有在 tool_response.content 中包含 execute_id 时才使用新的异步处理方式
 2. 事务处理：Service层方法中使用 db.commit() 确保数据一致性
 3. 错误处理：所有方法都有完善的异常捕获和日志记录
 4. 性能考虑：轮询接口建议前端间隔至少2-3秒，避免频繁请求
 5. 超时处理：前端应设置最大轮询次数（如60次约2分钟），避免无限轮询