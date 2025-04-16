import os
from pathlib import Path
from ultralytics import YOLO
import yaml

import matplotlib
matplotlib.use('TkAgg')  # 使用Tkinter后端替代PyCharm内置后端
import matplotlib.pyplot as plt

def train_tt100k(
        data_yaml_path= r'E:\\project_traffic\\tt100k_2021\\data.yaml',
        model_size='n',
        epochs=100,
        imgsz=640,
        batch=16,
        device='0',
        visualize=True
):
    """
    参数:
        data_yaml_path: data.yaml配置文件路径
        model_size: 模型大小 (nano, small, medium, large, xlarge)
        epochs: 训练轮数
        imgsz: 图像尺寸
        batch: 批量大小
        device: 训练设备
        visualize: 是否可视化训练结果
    """
    # 检查数据集配置
    assert Path(data_yaml_path).exists(), f"data.yaml文件不存在: {data_yaml_path}"

    # 加载数据集配置
    with open(data_yaml_path) as f:
        data_cfg = yaml.safe_load(f)

    # 验证数据集路径
    base_path = Path(data_cfg['path'])
    print("\n数据集验证:")
    print(f"- 图像路径: {base_path / data_cfg['train']}")
    print(f"- 标签路径: {base_path / data_cfg['val']}")
    print(f"- 类别数量: {len(data_cfg['names'])}")
    print(f"- 类别列表: {data_cfg['names']}\n")

    # 初始化模型 (使用预训练的YOLOv8)
    model = YOLO(f'yolov8{model_size}.pt')

    # 训练配置
    train_args = {
        'data': data_yaml_path,
        'epochs': epochs,
        'imgsz': imgsz,
        'batch': batch,
        'device': device,
        'name': f'tt100k_yolov8{model_size}',  # 训练结果保存名称

        'optimizer': 'auto',  # 自动选择优化器
        'lr0': 0.01,  # 初始学习率
        'cos_lr': True,  # 使用余弦学习率调度
        'patience': 20,  # 早停轮数
        'save_period': 10,  # 每10个epoch保存一次
        'amp': True,  # 自动混合精度
        'hsv_h': 0.015,  # 色调增强
        'hsv_s': 0.7,  # 饱和度增强
        'hsv_v': 0.4,  # 亮度增强
        'fliplr': 0.5,  # 水平翻转概率
        'mosaic': 1.0,  # 使用mosaic增强
        'cls': 5.0,  # 分类损失权重（全局调整）
        'fraction': 1.0  # 对少数类别过采样

    }

    # 开始训练
    print("🚀 开始训练YOLOv8...")
    results = model.train(**train_args)

    # 验证最佳模型
    best_model_path = Path(results.save_dir) / 'weights' / 'best.pt'
    print(f"\n✅ 训练完成! 最佳模型保存在: {best_model_path}")

    # 可视化训练结果
    if visualize:
        visualize_training_results(results.save_dir)

    return str(best_model_path)


def visualize_training_results(save_dir):
    """可视化训练指标"""
    results_dir = Path(save_dir)

    # 读取训练日志
    metrics_file = results_dir / 'results.csv'
    if not metrics_file.exists():
        print("找不到训练指标文件")
        return

    import pandas as pd
    df = pd.read_csv(metrics_file)

    # 绘制关键指标
    plt.figure(figsize=(15, 10))

    # 损失函数曲线
    plt.subplot(2, 2, 1)
    plt.plot(df['epoch'], df['train/box_loss'], label='Train Box Loss')
    plt.plot(df['epoch'], df['val/box_loss'], label='Val Box Loss')
    plt.title('Bounding Box Loss')
    plt.legend()

    # 准确率曲线
    plt.subplot(2, 2, 2)
    plt.plot(df['epoch'], df['metrics/precision(B)'], label='Precision')
    plt.plot(df['epoch'], df['metrics/recall(B)'], label='Recall')
    plt.title('Precision & Recall')
    plt.legend()

    # mAP曲线
    plt.subplot(2, 2, 3)
    plt.plot(df['epoch'], df['metrics/mAP50(B)'], label='mAP@0.5')
    plt.plot(df['epoch'], df['metrics/mAP50-95(B)'], label='mAP@0.5:0.95')
    plt.title('mAP Metrics')
    plt.legend()

    # 学习率曲线
    plt.subplot(2, 2, 4)
    plt.plot(df['epoch'], df['lr/pg0'], label='Backbone LR')
    plt.plot(df['epoch'], df['lr/pg1'], label='Head LR')
    plt.title('Learning Rate Schedule')
    plt.legend()

    plt.tight_layout()
    plt.show()

    # 显示混淆矩阵和PR曲线
    conf_matrix = results_dir / 'confusion_matrix.png'
    pr_curve = results_dir / 'PR_curve.png'

    if conf_matrix.exists():
        img = plt.imread(conf_matrix)
        plt.figure(figsize=(10, 10))
        plt.imshow(img)
        plt.axis('off')
        plt.title('Confusion Matrix')
        plt.show()

    if pr_curve.exists():
        img = plt.imread(pr_curve)
        plt.figure(figsize=(10, 10))
        plt.imshow(img)
        plt.axis('off')
        plt.title('Precision-Recall Curve')
        plt.show()


if __name__ == '__main__':
    # 示例用法
    trained_model = train_tt100k(
        data_yaml_path= r'E:\\project_traffic\\tt100k_2021\\data.yaml',
        model_size='n',  # 使用YOLOv8n模型
        epochs=100,
        imgsz=640,
        batch=16,
        device='0'  # 使用GPU
    )

    print(f"训练完成! 最佳模型路径: {trained_model}")