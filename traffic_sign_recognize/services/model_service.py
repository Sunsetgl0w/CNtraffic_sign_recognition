import cv2
import numpy as np
import base64
import httpx
import json
from fastapi import HTTPException
from ultralytics import YOLO
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime, date
from pathlib import Path

#映射
SIGN_MAPPING = {
    # 警告标志 (w)
    "w13": "十字交叉", "w21": "T形交叉", "w22": "T形交叉", "w30": "慢行",
    "w32": "施工", "w55": "注意儿童", "w57": "注意行人", "w58": "注意合流",
    "w59": "注意合流", "w63": "注意安全",

    # 禁止标志 (p)
    "p1": "禁止超车", "p3": "禁止大型客车驶入", "p5": "禁止掉头",
    "p6": "禁止非机动车进入", "p9": "禁止行人进入", "p10": "禁止机动车驶入",
    "p11": "禁止鸣喇叭", "p12": "禁止二轮摩托车驶入", "p13": "禁止某两种车驶入",
    "p18": "禁止拖拉机驶入", "p19": "禁止向右转弯", "p23": "禁止向左转弯",
    "p26": "禁止载货汽车驶入", "p27": "装载危险品车辆禁止通行", "pb": "禁止通行",
    "pbm": "禁止非机动车和二轮摩托驶入", "pbp": "禁止行人和非机动车进入",
    "pcl": "禁止机动车左转", "pg": "减速让行", "pn": "禁止车辆临时或长时停放",
    "pne": "禁止驶入", "ps": "停车让行", "pa14": "限制轴承",
    "ph4": "限制高度", "ph4.5": "限制高度", "ph5": "限制高度",
    "pl5": "限制速度", "pl15": "限制速度", "pl20": "限制速度",
    "pl30": "限制速度", "pl40": "限制速度", "pl50": "限制速度",
    "pl60": "限制速度", "pl70": "限制速度", "pl80": "限制速度",
    "pl90": "限制速度", "pl100": "限制速度", "pl120": "限制速度",
    "pm10": "限制吨数", "pm20": "限制吨数", "pm30": "限制吨数",
    "pm55": "限制吨数", "pr40": "解除限制速度", "pr60": "解除限制速度",

    # 指示标志 (i)
    "i2": "非机动车道行驶", "i4": "机动车车道", "i5": "靠右侧道路行驶",
    "i10": "向右转弯", "im": "摩托车车道", "ip": "人行横道",
    "i4l": "左侧机动车车道", "i2r": "右侧非机动车车道",
    "il60": "最低限速", "il80": "最低限速", "il90": "最低限速",
    "il100": "最低限速"
}


def load_sign_mapping():
    """从signs.txt加载标志代号到中文名称的映射"""
    try:
        with open("signs.txt", "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:  # 确保行包含分隔符
                    code, name = line.strip().split(":", 1)  # 只分割第一个冒号
                    SIGN_MAPPING[code.strip()] = name.strip()
        print(f"成功加载 {len(SIGN_MAPPING)} 个标志映射")
    except Exception as e:
        print(f"加载标志映射失败: {str(e)}")
        # 设置默认值避免崩溃
        SIGN_MAPPING.update({
            "w13": "十字交叉",
            "p1": "禁止超车",
            "i2": "非机动车道行驶"
        })


# 在应用启动时加载映射
load_sign_mapping()

# 本地模型配置
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1:8b"


class OllamaRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = False


class ModelManager:
    def __init__(self):
        self.yolo_model = YOLO("models/best.pt")
        self.detection_history = []
        self.video_processing = False
        # 统计属性
        self.total_detections = 0
        self.daily_detections = {"date": str(date.today()), "count": 0}
        self.total_questions = 0
        self.daily_questions = {"date": str(date.today()), "count": 0}
        # 历史记录
        self.detection_records = []  # 存储历史记录
        self.max_records = 1000  # 最大保存数
        # 添加停止标志
        self.should_stop_processing = False
        # 记录已存在的检测结果哈希
        self.detection_hashes = set()
        # 统计数据保存路径
        self.stats_file = Path("data/stats.json")
        self._load_stats()  # 初始化时加载统计数据

    def stop_processing(self):
        """设置停止处理标志"""
        self.should_stop_processing = True

    def get_sign_name(self, class_code: str) -> str:
        return SIGN_MAPPING.get(class_code, f"未知标志({class_code})")

    def increment_detections(self):
        """增加检测计数"""
        self.total_detections += 1
        today = str(date.today())
        if self.daily_detections["date"] != today:
            self.daily_detections = {"date": today, "count": 1}
        else:
            self.daily_detections["count"] += 1
        self._save_stats()  # 每次更新后自动保存

    def increment_questions(self):
        """增加问题计数"""
        self.total_questions += 1
        today = str(date.today())
        if self.daily_questions["date"] != today:
            self.daily_questions = {"date": today, "count": 1}
        else:
            self.daily_questions["count"] += 1
        self._save_stats()  # 每次更新后自动保存

    def get_stats(self):
        """获取统计数据"""
        return {
            "total_detections": self.total_detections,
            "daily_detections": self.daily_detections["count"],
            "total_questions": self.total_questions,
            "daily_questions": self.daily_questions["count"],
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_detection_records(self, limit: int = 10, offset: int = 0):
        """获取检测记录"""
        end_idx = offset + limit
        return self.detection_records[offset:end_idx]

    def search_detection_records(self, keyword: str, limit: int = 10):
        """搜索检测记录"""
        results = []
        for record in reversed(self.detection_records):  # 从新到旧搜索
            for det in record["detections"]:
                if keyword.lower() in det["class"].lower() or keyword.lower() in det["class_code"].lower():
                    results.append(record)
                    if len(results) >= limit:
                        return results
                    break  # 一个记录中找到一个匹配就够
        return results

    def _generate_detection_hash(self, detections: List[Dict]) -> str:
        """生成检测结果的唯一哈希"""
        detection_keys = sorted([(d["class_code"], d["class"]) for d in detections])
        return str(hash(frozenset(detection_keys)))

    def add_detection_record(self, detections: List[Dict], image_data: str = None) -> Optional[Dict]:
        """添加检测记录，自动去重"""
        if not detections:
            return None

        record_hash = self._generate_detection_hash(detections)
        if record_hash in self.detection_hashes:
            return None  # 重复记录不保存

        self.detection_hashes.add(record_hash)

        if len(self.detection_records) >= self.max_records:
            oldest_record = self.detection_records.pop(0)
            old_hash = self._generate_detection_hash(oldest_record["detections"])
            self.detection_hashes.discard(old_hash)

        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "detections": detections,
            "image_data": image_data,
            "hash": record_hash
        }
        self.detection_records.append(record)
        return record

    def _load_stats(self):
        """从文件加载统计数据"""
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.total_detections = data.get('total_detections', 0)
                    self.total_questions = data.get('total_questions', 0)

                    # 处理每日数据（如果日期变化则重置）
                    today = str(date.today())
                    if data.get('daily_date') != today:
                        self.daily_detections = {"date": today, "count": 0}
                        self.daily_questions = {"date": today, "count": 0}
                    else:
                        self.daily_detections = data.get('daily_detections', {"date": today, "count": 0})
                        self.daily_questions = data.get('daily_questions', {"date": today, "count": 0})
        except Exception as e:
            print(f"加载统计数据失败: {e}")
            # 初始化默认值
            today = str(date.today())
            self.total_detections = 0
            self.total_questions = 0
            self.daily_detections = {"date": today, "count": 0}
            self.daily_questions = {"date": today, "count": 0}

    def _save_stats(self):
        """保存统计数据到文件"""
        try:
            self.stats_file.parent.mkdir(exist_ok=True)  # 确保目录存在
            data = {
                "total_detections": self.total_detections,
                "total_questions": self.total_questions,
                "daily_detections": self.daily_detections,
                "daily_questions": self.daily_questions,
                "daily_date": self.daily_detections["date"],
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存统计数据失败: {e}")

    async def query_ollama(self, prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            data = {
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            }
            response = await client.post(
                OLLAMA_API_URL,
                json=data,
                timeout=60.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Ollama请求失败")
            return response.json().get("response", "")

    async def get_traffic_info(self, sign_name: str) -> Dict:
        prompt = f"请详细介绍交通标志'{sign_name}'的含义。用中文回答，分点说明，简明扼要。"
        response = await self.query_ollama(prompt)
        return {
            "sign": sign_name,
            "description": response.strip(),
            "actions": await self.get_recommended_actions(sign_name)
        }

    async def get_recommended_actions(self, sign_name: str) -> str:
        prompt = f"驾驶员看到交通标志'{sign_name}'时应该采取什么具体行动？用中文回答，分步骤说明，简明扼要。"
        return (await self.query_ollama(prompt)).strip()

    async def ask_traffic_question(self, question: str) -> str:
        self.increment_questions() #计数
        prompt = f"你是一名交通专家，请直接回答问题，不要重复问题。问题：{question}"
        response = await self.query_ollama(prompt)
        return response.split("回答:")[-1].strip()

    async def process_video_frame(self, frame: np.ndarray) -> Dict:
        """处理视频帧"""
        if self.should_stop_processing:  # 检查停止标志
            self.should_stop_processing = False
            raise HTTPException(status_code=499, detail="客户端关闭请求")

        try:
            results = self.yolo_model.predict(frame, conf=0.3)  # 提高置信度阈值

            detections = []
            sign_details = []

            for result in results:
                boxes = result.boxes.xyxy.cpu().numpy()
                classes = result.boxes.cls.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()

                for box, cls, conf in zip(boxes, classes, confs):
                    x1, y1, x2, y2 = map(int, box)
                    class_code = self.yolo_model.names[int(cls)]
                    class_name = self.get_sign_name(class_code)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"{class_code} {conf:.2f}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                    detections.append({
                        "class_code": class_code,
                        "class": class_name,
                        "confidence": float(conf)
                    })

            # 处理所有置信度大于阈值的标志
            if detections:
                # 获取所有置信度大于0.3的标志
                valid_detections = [d for d in detections if d["confidence"] > 0.3]

                # 为每个有效检测获取详细信息
                for detection in valid_detections:
                    detail = await self.get_traffic_info(detection["class"])
                    sign_details.append(detail)

            _, img_encoded = cv2.imencode('.jpg', frame)
            img_base64 = base64.b64encode(img_encoded).decode()

            # 构建返回结果
            result = {
                "image": f"data:image/jpeg;base64,{img_base64}",
                "detections": detections,
                "sign_details": sign_details
            }

            # 在处理完成后添加记录
            if detections:
                self.increment_detections()
                self.add_detection_record(detections, result["image"])

            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"处理帧时出错: {str(e)}")

model_manager = ModelManager()