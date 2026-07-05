"""
AI 测试用例生成工具 — 配置文件

优先级: 环境变量 > config_local.py > 空（用户自行配置）
"""

import os

# ============================================================
# LLM API 配置
# ============================================================
# 1. 先尝试从环境变量读取
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 2. 如果环境变量为空，尝试从本地配置文件读取（不会被提交到 Git）
if not DEEPSEEK_API_KEY:
    try:
        from config_local import DEEPSEEK_API_KEY as _local_key
        DEEPSEEK_API_KEY = _local_key
    except ImportError:
        pass
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 备用：通义千问
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

# ============================================================
# 测试用例生成配置
# ============================================================
# 测试设计方法（供用户选择）
TEST_DESIGN_METHODS = [
    "等价类划分法",
    "边界值分析法",
    "场景法",
    "判定表法",
    "因果图法",
    "正交实验法",
    "错误推测法",
    "状态迁移法",
]

# 用例优先级
PRIORITY_LEVELS = ["P0-阻塞", "P1-高", "P2-中", "P3-低"]
PRIORITY_COLORS = {
    "P0-阻塞": "#FF4444",
    "P1-高": "#FF8C00",
    "P2-中": "#4CAF50",
    "P3-低": "#2196F3",
}

# 用例类型
TEST_CASE_TYPES = ["功能测试", "接口测试", "性能测试", "安全测试", "兼容性测试", "易用性测试"]

# ============================================================
# 可视化配置
# ============================================================
CHART_THEME = "plotly_white"
CHART_COLORS = ["#5470C6", "#91CC75", "#FAC858", "#EE6666", "#73C0DE", "#3BA272"]
