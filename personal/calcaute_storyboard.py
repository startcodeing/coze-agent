async def main(args: Args) -> Output:
    # Coze Python 代码节点示例：计算分镜数量
    
    # 输入变量，确保在 Coze 流程里有传入
    # maxDuration: 视频总时长，单位秒
    # min_storyboard_video: 每个分镜最短时长，单位秒
    params = args.params
    max_duration = float(params.get("maxDuration"))  # 默认5秒
    min_storyboard_time = float(params.get("min_storyboard_video"))  # 默认5秒

    
    # 计算最大分镜数量
    if min_storyboard_time > 0:
        max_storyboard_count = int(max_duration // min_storyboard_time)  # 向下取整
    else:
        max_storyboard_count = 1  # 避免除以0
    
    # 确保至少生成1个分镜
    if max_storyboard_count < 1:
        max_storyboard_count = 1
    
    # 输出结果给后续节点
    ret = {
        "maxStoryboardCount": max_storyboard_count,
        "message": f"最大分镜数量为 {max_storyboard_count} 个"
    }

    return ret