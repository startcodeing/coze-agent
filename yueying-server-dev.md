 本地启动指南

  1️⃣ 环境准备

  Python版本: Python 3.10+

  # 检查Python版本
  python --version

  2️⃣ 激活虚拟环境

  # Windows
  .venv\Scripts\activate

  # Linux/Mac
  source .venv/bin/activate

  3️⃣ 安装依赖（如果需要）

  pip install -r requirements.txt

  4️⃣ 配置数据库

  项目使用 MySQL 8.0，配置在 app/core/config.py 中：

  # 当前配置（远程数据库）
  SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:yingyue666888@115.190.248.65:3306/YingyueAI_db?charset=utf8mb4"

  如果使用现有远程数据库：
  - 无需修改，直接使用即可

  如果需要本地MySQL：
  1. 安装 MySQL 8.0
  2. 创建数据库：
  CREATE DATABASE YingyueAI_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  3. 导入初始数据（可选）：
  mysql -u root -p YingyueAI_db < seed_system_config.sql
  4. 修改 .env 文件或 config.py 中的数据库连接：
  SQLALCHEMY_DATABASE_URL=mysql+pymysql://root:你的密码@localhost:3306/YingyueAI_db?charset=utf8mb4

  5️⃣ 启动开发服务器

  # 方式1：使用uvicorn启动（推荐）
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # 方式2：指定日志级别
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --log-level debug

  启动成功后：
  - API服务: http://127.0.0.1:8000
  - Swagger文档: http://127.0.0.1:8000/docs
  - ReDoc文档: http://127.0.0.1:8000/redoc

  6️⃣ 验证服务

  测试API健康状态：
  curl http://127.0.0.1:8000/docs

  在浏览器访问 Swagger UI：
  http://127.0.0.1:8000/docs

  7️⃣ 调试Coze工作流接口

  在Swagger文档中测试新添加的Coze工作流接口：

  触发工作流：
  POST /api/v1/coze-workflow/trigger
  {
    "topic": "测试视频生成",
    "radio": "16:9",
    "resolution": "720p"
  }

  查询执行结果：
  GET /api/v1/coze-workflow/result/{execute_id}

  🔧 IDE调试配置

  VSCode 调试配置

  创建 .vscode/launch.json：

  {
    "version": "0.2.0",
    "configurations": [
      {
        "name": "FastAPI Debug",
        "type": "python",
        "request": "launch",
        "module": "uvicorn",
        "args": [
          "app.main:app",
          "--host",
          "0.0.0.0",
          "--port",
          "8000",
          "--reload"
        ],
        "console": "integratedTerminal",
        "justMyCode": false
      }
    ]
  }

  PyCharm 调试配置

  1. Run → Edit Configurations
  2. 添加 Python 配置：
    - Module name: uvicorn
    - Parameters: app.main:app --host 0.0.0.0 --port 8000 --reload
    - Working directory: 项目根目录
    - Environment: 激活虚拟环境

  📝 常见问题

  Q1: 依赖安装失败

  # 升级pip
  pip install --upgrade pip

  # 使用国内镜像
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

  Q2: 数据库连接失败

  - 检查MySQL服务是否启动
  - 检查用户名密码是否正确
  - 检查数据库是否已创建

  Q3: 端口被占用

  # Windows: 查找占用8000端口的进程
  netstat -ano | findstr :8000
  taskkill /PID <进程ID> /F

  # Linux/Mac:
  lsof -ti:8000 | xargs kill -9

  Q4: CORS跨域问题

  项目已配置CORS中间件（app/main.py），允许所有来源。如果遇到跨域问题，检查：
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )

  📊 日志查看

  启动后日志格式：
  2026-01-23 10:22:45 - app.main - INFO - Application startup complete
  2026-01-23 10:22:50 - app.services.coze_workflow - INFO - 触发Coze工作流...

  🧪 运行测试

  # 运行所有测试
  pytest

  # 运行特定测试文件
  pytest tests/test_coze_workflow.py -v

  # 运行测试并显示详细输出
  pytest -v --tb=short

  🎯 快速开始

  如果你已经有虚拟环境（看到 .venv 目录），直接：

  # 1. 激活虚拟环境
  .venv\Scripts\activate

  # 2. 启动服务
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # 3. 浏览器访问
  # http://127.0.0.1:8000/docs

  启动成功后，你就可以在Swagger UI中测试Coze工作流接口了！