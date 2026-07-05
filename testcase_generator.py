"""
测试用例生成器 — 核心业务逻辑
负责构建 Prompt、调用 LLM、解析和结构化输出
"""
import hashlib
import time
from typing import Optional

import pandas as pd

from config import TEST_DESIGN_METHODS, PRIORITY_LEVELS
from llm_client import LLMClient


# ============================================================
# Prompt 模板
# ============================================================

SYSTEM_PROMPT = """你是一位资深的软件测试架构师，拥有 10 年以上测试经验，精通各种测试设计方法。

你的任务是根据用户提供的需求描述，生成专业、结构化、可直接执行的测试用例。

## 输出要求
1. 必须严格返回 JSON 数组格式，不要任何额外文字
2. 每条用例包含以下字段：
   - "id": 用例编号(如 TC-001)
   - "module": 所属模块
   - "title": 用例标题(简洁明确，15字以内)
   - "precondition": 前置条件
   - "steps": 测试步骤(用分号分隔的字符串)
   - "expected": 预期结果
   - "priority": 优先级(P0-阻塞/P1-高/P2-中/P3-低)
   - "type": 用例类型(功能测试/接口测试/性能测试/安全测试/兼容性测试/易用性测试)
   - "design_method": 使用的测试设计方法
   - "test_data": 测试数据(如适用)

## 优先级判定标准
- P0-阻塞: 核心主流程，失败则系统不可用
- P1-高: 重要功能，影响主要用户使用
- P2-中: 一般功能或边界场景
- P3-低: 界面美化、文案、非关键路径

## 数量要求
- 生成 15-25 条用例
- P0 占 10-15%，P1 占 30-40%，P2 占 30-40%，P3 占 10-20%
- 至少使用 3 种不同的测试设计方法
- 至少覆盖 3 种用例类型
"""


def build_user_prompt(
    requirement: str,
    methods: list[str],
    module_count: int = 3,
    extra_context: str = "",
) -> str:
    """构建用户提示词"""
    methods_str = "、".join(methods)
    prompt = f"""## 需求描述
{requirement}

## 要求
- 使用以下测试设计方法：{methods_str}
- 将需求拆分为 {module_count} 个测试模块
- 为每个模块生成对应用例

"""
    if extra_context:
        prompt += f"""## 补充说明
{extra_context}
"""
    prompt += """
请直接返回 JSON 数组，格式如下：
[
  {
    "id": "TC-001",
    "module": "登录模块",
    "title": "正确账号密码登录成功",
    "precondition": "已有注册账号 test@example.com / Pass1234",
    "steps": "1.打开登录页面; 2.输入正确邮箱和密码; 3.点击登录按钮",
    "expected": "登录成功，跳转到首页，显示用户名",
    "priority": "P0-阻塞",
    "type": "功能测试",
    "design_method": "场景法",
    "test_data": "邮箱:test@example.com,密码:Pass1234"
  }
]"""
    return prompt


# ============================================================
# 生成器核心类
# ============================================================

class TestCaseGenerator:
    """AI 测试用例生成器"""

    def __init__(self, provider: str = "deepseek"):
        self.llm = LLMClient(provider=provider)
        self.generation_history: list[dict] = []  # 生成历史

    def generate(
        self,
        requirement: str,
        methods: Optional[list[str]] = None,
        module_count: int = 3,
        extra_context: str = "",
    ) -> pd.DataFrame:
        """
        根据需求描述生成测试用例

        返回 DataFrame，包含所有用例结构化数据
        """
        if methods is None:
            methods = ["等价类划分法", "边界值分析法", "场景法"]

        user_prompt = build_user_prompt(requirement, methods, module_count, extra_context)

        # 调用 LLM
        cases = self.llm.chat_with_json_output(SYSTEM_PROMPT, user_prompt)

        if cases is None:
            raise ValueError("LLM 返回格式异常，未能解析出有效的 JSON 数组，请重试")

        # 转换为 DataFrame
        df = pd.DataFrame(cases)

        # 数据清洗与标准化
        df = self._normalize(df)

        # 记录生成历史
        self.generation_history.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "requirement": requirement[:100],
            "methods": methods,
            "case_count": len(df),
            "hash": hashlib.md5(requirement.encode()).hexdigest()[:8],
        })

        return df

    @staticmethod
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        """标准化 DataFrame 字段"""
        # 确保必要字段存在
        required_cols = [
            "id", "module", "title", "precondition", "steps",
            "expected", "priority", "type", "design_method", "test_data",
        ]
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""

        # 统一优先级格式
        valid_priorities = set(PRIORITY_LEVELS)
        df["priority"] = df["priority"].apply(
            lambda x: x if x in valid_priorities else "P2-中"
        )

        # 填充空值
        df = df.fillna("")

        return df[required_cols]
