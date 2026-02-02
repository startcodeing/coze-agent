# 在这里，您可以通过 'args'  获取节点中的输入变量，并通过 'ret' 输出结果
# 'args' 已经被正确地注入到环境中
# 下面是一个示例，首先获取节点的全部输入参数params，其次获取其中参数名为'input'的值：
# params = args.params; 
# input = params['input'];
# 下面是一个示例，输出一个包含多种数据类型的 'ret' 对象：
# ret: Output =  { "name": '小明', "hobbies": ["看书", "旅游"] };

async def main(args: Args) -> Output:
    params = args.params

    style = params.get("style")

    # 假设 style 是上一节点的输出变量
    # Coze Python 节点直接可以使用输入变量名
    try:
        if style and style.strip():  # style 不为空或非空字符串
            final_style = style.strip()
        else:
            final_style = "写实风格"
    except NameError:
        # style 未传入，直接使用默认值
        final_style = "写实风格"
    
    # 输出给后续节点使用
    ret = {
        "finalStyle": final_style,
        "message": f"最终风格为：{final_style}"
    }

    return ret