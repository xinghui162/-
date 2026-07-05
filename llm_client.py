"""
LLM 客户端 — 封装 DeepSeek / 通义千问 API 调用
"""
import json
import re
from typing import Optional
from openai import OpenAI

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    QWEN_API_KEY,
    QWEN_BASE_URL,
    QWEN_MODEL,
)


class LLMClient:
    """大模型客户端，支持 DeepSeek 和通义千问"""

    def __init__(self, provider: str = "deepseek"):
        """
        初始化客户端
        :param provider: "deepseek" 或 "qwen"
        """
        self.provider = provider
        if provider == "qwen" and QWEN_API_KEY:
            self.client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)
            self.model = QWEN_MODEL
        else:
            self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
            self.model = DEEPSEEK_MODEL

    def chat(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        """发送对话请求，返回模型回复文本"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"LLM API 调用失败: {str(e)}")

    def chat_with_json_output(self, system_prompt: str, user_message: str) -> Optional[list]:
        """
        请求 LLM 并尝试解析返回的 JSON 数组。
        多层容错：正则提取 → LLM 修正 → 兼容修复 → 逐条解析
        """
        raw = self.chat(system_prompt, user_message)

        # ---- 策略 1: 直接提取 JSON ----
        json_str = self._extract_json_array(raw)
        if json_str:
            result = self._safe_json_loads(json_str)
            if result is not None:
                return result

        # ---- 策略 2: 让 LLM 修正格式 ----
        fix_prompt = (
            "以下文本应当包含一个 JSON 数组。请提取其中所有测试用例对象，"
            "严格按 JSON 数组格式输出，不要任何额外文字：\n\n" + raw
        )
        raw2 = self.chat("你是一个 JSON 格式化工具，只输出有效的 JSON 数组。", fix_prompt)
        json_str = self._extract_json_array(raw2)
        if json_str:
            result = self._safe_json_loads(json_str)
            if result is not None:
                return result

        # ---- 策略 3: 兼容性修复后重试 ----
        if json_str:
            json_str = self._repair_json(json_str)
            result = self._safe_json_loads(json_str)
            if result is not None:
                return result

        # ---- 策略 4: 逐条提取对象 ----
        result = self._extract_objects_individually(raw)
        if result:
            return result

        return None

    @staticmethod
    def _safe_json_loads(json_str: str) -> Optional[list]:
        """安全的 JSON 解析"""
        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
        return None

    @staticmethod
    def _repair_json(json_str: str) -> str:
        """修复常见 JSON 格式问题"""
        # 移除尾部逗号（在 ] 或 } 之前）
        json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
        # 移除 BOM
        json_str = json_str.lstrip("﻿")
        # 替换中文引号为英文引号
        json_str = json_str.replace("“", '"').replace("”", '"')
        json_str = json_str.replace("‘", "'").replace("’", "'")
        return json_str

    @staticmethod
    def _extract_objects_individually(text: str) -> Optional[list]:
        """逐条从文本中提取 JSON 对象，作为最后的兜底策略"""
        # 匹配所有 {...} 对象
        pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(pattern, text, re.DOTALL)
        results = []
        for match in matches:
            try:
                obj = json.loads(match)
                if isinstance(obj, dict) and "title" in obj:
                    results.append(obj)
            except json.JSONDecodeError:
                continue
        return results if results else None

    @staticmethod
    def _extract_json_array(text: str) -> Optional[str]:
        """从文本中提取 JSON 数组"""
        # 去除 markdown 代码块标记
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        # 去除 BOM
        text = text.lstrip("﻿")
        # 尝试找到 [ ... ] 段落
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end > start:
            return text[start : end + 1]
        return None
