text2Video_agent_optimize：AI工具，Agent模式-视频生成工具使用工作流
text2Image_agent： AI工具，Agent模式-图片生成工具使用工作流
text2Video_workflow：coze平台智能体调用的视频生成工作流
text2Video_workflow_retry：基于text2Video_workflow优化后的工作流，实现将前一个分镜的尾帧图作为下一个分镜的首帧图，获取视频生成结果时添加重试机制
obtain_storyboard_video_url：重试获取视频结果的工作流，作为text2Video_workflow_retry的子工作流使用

text_2_video_use_Runninghub：复刻的Runninghub的工作流，项目中未使用


















