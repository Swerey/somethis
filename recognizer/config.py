"""共享配置"""

import os

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据路径（相对 recognizer 目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "datasets", "processed_v2")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# BERT 模型
MODEL_NAME = "bert-base-chinese"
MAX_LEN = 128
NUM_CLASSES = 6

LABEL_MAP = {
    0: "正常",
    1: "色情低俗",
    2: "辱骂暴力",
    3: "广告引流",
    4: "敏感言论",
    5: "歧视煽动",
}

# TextCNN / BiLSTM 参数
VOCAB_SIZE = 20000
EMBED_DIM = 300

CNN_BATCH_SIZE = 32
CNN_EPOCHS = 10
CNN_LR = 1e-3

LSTM_BATCH_SIZE = 32
LSTM_EPOCHS = 10
LSTM_LR = 1e-3
LSTM_HIDDEN = 256
LSTM_NUM_LAYERS = 2
LSTM_DROPOUT = 0.3

# BERT 训练参数
BERT_BATCH_SIZE = 16
BERT_EPOCHS = 5
BERT_LR = 2e-5

# Focal Loss
FOCAL_GAMMA = 2.0

# FGM 对抗训练
FGM_EPSILON = 1.0

# 设备
import torch

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
