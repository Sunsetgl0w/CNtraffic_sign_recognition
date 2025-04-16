from services.model_service import model_manager
from services.connection_service import manager
import cv2
import numpy as np
import base64
import time
import tempfile
import os
from fastapi import Request, WebSocket, WebSocketDisconnect, Query, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse

router = APIRouter()

templates = Jinja2Templates(directory="static")

#首页
@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

#检测
@router.websocket("/ws/detect")
async def websocket_detection(websocket: WebSocket):
    client_id = str(id(websocket))
    await manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_text()

            # 处理停止命令
            if data == "stop_processing":
                model_manager.stop_processing()
                await websocket.send_json({
                    "type": "video_status",
                    "status": "stopped",
                    "message": "视频处理已停止"
                })
                continue

            # 处理问题咨询
            if data.startswith("question:"):
                question = data[len("question:"):]
                answer = await model_manager.ask_traffic_question(question)
                await websocket.send_json({
                    "type": "knowledge_answer",
                    "question": question,
                    "answer": answer
                })
                continue

            # 处理视频处理请求
            if data.startswith("video_start:"):
                await websocket.send_json({
                    "type": "video_status",
                    "status": "processing",
                    "message": "开始处理视频"
                })
                continue

            # 处理视频结束
            if data.startswith("video_end"):
                await websocket.send_json({
                    "type": "video_status",
                    "status": "completed",
                    "message": "视频处理完成"
                })
                continue

            # 处理图片检测
            try:
                start_time = time.time()
                img_data = base64.b64decode(data.split(",")[1])
                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                result = await model_manager.process_video_frame(img)
                process_time = time.time() - start_time

                await websocket.send_json({
                    "type": "detection_result",
                    **result,
                    "process_time": process_time
                })
            except Exception as e:
                print(f"处理帧时出错: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"处理帧时出错: {str(e)}"
                })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        manager.disconnect(client_id)

#视频上传
@router.post("/upload-video")
async def upload_video(request: Request):
    form_data = await request.form()
    video_file = form_data["video"]

    # 保存临时视频文件
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, video_file.filename)
    with open(temp_path, "wb") as buffer:
        buffer.write(await video_file.read())

    return {"filename": video_file.filename, "temp_path": temp_path}

#数据统计
@router.get("/api/stats")
async def get_stats():
    return JSONResponse(content=model_manager.get_stats())

# 历史记录
@router.get("/api/history")
async def get_detection_history(
    limit: int = Query(10, description="返回的记录数量"),
    offset: int = Query(0, description="偏移量"),
    search: str = Query(None, description="搜索关键词")
):
    if search:
        # 使用模型管理器的搜索方法
        records = model_manager.search_detection_records(search, limit)
        return JSONResponse(content={
            "records": records,
            "total": len(records),
            "has_search": True,
            "search_term": search  # 返回搜索关键词
        })
    else:
        # 普通分页查询
        records = model_manager.get_detection_records(limit, offset)
        return JSONResponse(content={
            "records": records,
            "total": len(model_manager.detection_records),
            "has_search": False
        })