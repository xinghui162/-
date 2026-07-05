"""
工具模块 — 导出、数据处理等辅助功能
"""
import io
import base64
from datetime import datetime

import pandas as pd


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "测试用例") -> bytes:
    """将 DataFrame 导出为 Excel 文件的字节流"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

        # 获取工作表，调整列宽
        worksheet = writer.sheets[sheet_name]
        for i, col in enumerate(df.columns, 1):
            # 根据列内容计算合适的列宽
            max_len = max(
                df[col].astype(str).str.len().max(),
                len(str(col)),
            )
            # 限制最大 50、最小 10
            col_width = min(max(max_len * 1.8, 10), 50)
            worksheet.column_dimensions[chr(64 + i) if i <= 26 else "A"].width = col_width

        # 冻结首行
        worksheet.freeze_panes = "A2"

    return output.getvalue()


def get_excel_download_link(df: pd.DataFrame, filename: str = "test_cases") -> str:
    """生成 Excel 下载链接（base64 编码，用于 Streamlit）"""
    excel_bytes = dataframe_to_excel_bytes(df)
    b64 = base64.b64encode(excel_bytes).decode()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    href = f"""
    <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}"
       download="{filename}_{timestamp}.xlsx"
       style="text-decoration:none;">
       📥 下载 Excel 文件
    </a>
    """
    return href


def get_csv_download_link(df: pd.DataFrame, filename: str = "test_cases") -> str:
    """生成 CSV 下载链接"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode("utf-8")).decode()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    href = f"""
    <a href="data:text/csv;charset=utf-8;base64,{b64}"
       download="{filename}_{timestamp}.csv"
       style="text-decoration:none;">
       📥 下载 CSV 文件
    </a>
    """
    return href


def compute_coverage_score(df: pd.DataFrame) -> dict:
    """
    计算测试覆盖度评分（0-100）
    综合考虑：模块数、类型数、方法数、优先级分布合理性
    """
    scores = {}

    # 1. 模块覆盖（满分 25）
    module_count = df["module"].nunique()
    scores["模块覆盖"] = min(module_count * 8, 25)

    # 2. 类型覆盖（满分 25）
    type_count = df["type"].nunique()
    scores["类型覆盖"] = min(type_count * 8, 25)

    # 3. 方法覆盖（满分 25）
    method_count = df["design_method"].nunique()
    scores["方法覆盖"] = min(method_count * 8, 25)

    # 4. 优先级分布合理性（满分 25）
    total = len(df)
    if total > 0:
        p0_pct = len(df[df["priority"] == "P0-阻塞"]) / total
        p1_pct = len(df[df["priority"] == "P1-高"]) / total
        # P0 10-20% 且 P1 25-40% 得满分
        p0_ok = 0.10 <= p0_pct <= 0.25
        p1_ok = 0.25 <= p1_pct <= 0.45
        scores["优先级分布"] = 10 * p0_ok + 10 * p1_ok + 5
    else:
        scores["优先级分布"] = 0

    scores["总分"] = sum(scores.values())
    return scores
