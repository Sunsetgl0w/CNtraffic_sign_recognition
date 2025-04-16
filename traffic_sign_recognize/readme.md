智能交通标志识别系统

# 项目简介
智能交通标志识别系统是一个基于深度学习(YOLO模型)和FastAPI框架的Web应用，能够实时检测图片和视频中的交通标志，并提供相关交通知识的问答功能。系统具有以下特点：

实时检测图片和视频中的交通标志

提供交通标志的详细解释和驾驶员建议行动

内置交通知识问答功能

数据看板展示检测统计信息

历史记录查询和搜索功能

语音播报功能(支持中文)

# 技术栈
前端：HTML5, CSS3, JavaScript

后端：Python, FastAPI, WebSocket

深度学习：YOLOv8 (Ultralytics)

语言模型：Ollama (LLaMA 3)

计算机视觉：OpenCV

# 项目结构
final /
├── data/        
│   └── stats.json   # 数据看板文件
├── models/       
│   └── best.pt   # YOLO模型文件
├── routers/        
│   ├── __init__.py   
│   └── router.py   # 路由文件
├── services   
│   ├── __init__.py 
│   ├── connection_service.py    # 连接状态服务
│   └── model_service.py    # 模型服务
├── static/
│   ├── css/
│   │   └── styles.css   # 样式文件
│   ├── js/
│   │   └── index.js # JavaScript
│   └── index.html  # 页面
├── main.py    # FastAPI 初始化
└── signs.txt   # 交通标志映射表

# 功能特性
1. 交通标志检测
支持图片上传检测

支持视频上传逐帧检测

实时显示检测结果和置信度

检测结果可视化(边界框和标签)

2. 交通知识问答
自然语言提问交通相关问题

基于LLaMA模型的智能回答

问答历史记录

3. 数据统计
总检测数统计

当日检测数统计

总问答数统计

最后更新时间显示

4. 历史记录
检测记录保存和查询

关键词搜索功能

分页加载

图片预览功能

5. 语音功能
检测结果语音播报

可开关语音提示

支持中文语音合成

# 安装与运行
前置要求
Python 3.8+

Ollama服务运行中(用于问答功能)

YOLO模型文件(best.pt)

# 安装步骤
克隆仓库

git clone <仓库地址>
cd final

安装Python依赖

pip install fastapi uvicorn opencv-python numpy httpx ultralytics

确保Ollama服务运行

ollama serve

启动应用

python main.py

访问应用

打开浏览器访问 http://localhost:8000

# 配置说明
模型配置：修改 model_service.py 中的 MODEL_NAME 使用不同的LLM模型

语音设置：在 index.js 中调整 utterance 参数修改语音速度和音调

历史记录限制：在 ModelManager 类中修改 max_records 属性调整最大保存记录数

# 使用说明
图片检测：

点击"选择图片"按钮上传图片

点击"检测标志"按钮开始检测

查看检测结果和标志详细信息

视频检测：

点击"选择视频"按钮上传视频

点击"处理视频"按钮开始逐帧检测

使用"停止处理"按钮可随时停止

交通咨询：

在输入框中输入交通相关问题

按Enter或点击"提问"按钮获取答案

历史记录：

在搜索框中输入关键词搜索历史记录

点击"刷新"按钮重新加载最新记录

点击图片可放大查看

# 注意事项
首次使用前请确保已下载YOLO模型文件(best.pt)并放置在models目录下

视频处理功能会消耗较多计算资源，建议处理短时长视频

语音功能需要浏览器支持Web Speech API

问答功能需要本地运行Ollama服务

未来改进
增加更多交通标志的支持

优化视频处理性能

添加用户账户系统


增加多语言支持
