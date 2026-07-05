"""
数据可视化模块 — 纯 Streamlit 原生 + HTML/CSS（零 C 扩展，永不崩溃）
"""
import pandas as pd
from config import PRIORITY_COLORS


def create_kpi_cards(df: pd.DataFrame) -> dict:
    """计算关键指标卡片数据"""
    total = len(df)
    p0_count = len(df[df["priority"] == "P0-阻塞"])
    p1_count = len(df[df["priority"] == "P1-高"])
    module_count = df["module"].nunique()
    method_count = df["design_method"].nunique()
    high_priority_ratio = round((p0_count + p1_count) / total * 100, 1) if total else 0

    return {
        "total": total,
        "p0_count": p0_count,
        "p1_count": p1_count,
        "high_ratio": high_priority_ratio,
        "module_count": module_count,
        "method_count": method_count,
    }


def render_priority_pie_html(df: pd.DataFrame) -> str:
    """优先级分布 — 纯 CSS 环形图 HTML"""
    priority_order = ["P0-阻塞", "P1-高", "P2-中", "P3-低"]
    counts = df["priority"].value_counts().reindex(priority_order).fillna(0).astype(int)
    counts = counts[counts > 0]
    total = counts.sum()

    if total == 0:
        return "<p>暂无数据</p>"

    colors_map = PRIORITY_COLORS
    segments = []
    cumulative = 0
    for priority, count in counts.items():
        pct = count / total * 100
        color = colors_map.get(priority, "#999")
        segments.append({
            "priority": priority,
            "count": count,
            "pct": round(pct, 1),
            "color": color,
            "start": cumulative,
        })
        cumulative += pct

    # 构建 conic-gradient
    gradient_parts = []
    for s in segments:
        gradient_parts.append(f"{s['color']} {s['start']:.1f}% {(s['start'] + s['pct']):.1f}%")

    legend_items = ""
    for s in segments:
        legend_items += f"""
        <div style="display:flex;align-items:center;gap:6px;margin:4px 0;">
            <div style="width:12px;height:12px;border-radius:3px;background:{s['color']};flex-shrink:0;"></div>
            <span style="font-size:13px;">{s['priority']}: <b>{s['count']}</b> 条 ({s['pct']}%)</span>
        </div>"""

    html = f"""
    <div style="text-align:center;">
        <div style="display:flex;align-items:center;justify-content:center;gap:30px;flex-wrap:wrap;">
            <div style="position:relative;width:220px;height:220px;border-radius:50%;
                        background: conic-gradient({','.join(gradient_parts)});
                        box-shadow: 0 3px 12px rgba(0,0,0,0.1);">
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                            width:120px;height:120px;border-radius:50%;background:white;
                            display:flex;align-items:center;justify-content:center;
                            flex-direction:column;box-shadow:inset 0 2px 4px rgba(0,0,0,0.06);">
                    <div style="font-size:28px;font-weight:700;color:#333;">{total}</div>
                    <div style="font-size:11px;color:#999;">条用例</div>
                </div>
            </div>
            <div style="text-align:left;">{legend_items}</div>
        </div>
    </div>"""
    return html


def render_type_bar_html(df: pd.DataFrame) -> str:
    """用例类型分布 — 纯 CSS 水平柱状图"""
    type_counts = df["type"].value_counts()
    max_count = type_counts.max()
    colors = ["#5470C6", "#91CC75", "#FAC858", "#EE6666", "#73C0DE", "#3BA272"]

    bars = ""
    for i, (tp, count) in enumerate(type_counts.items()):
        pct = count / max_count * 100 if max_count > 0 else 0
        color = colors[i % len(colors)]
        bars += f"""
        <div style="display:flex;align-items:center;gap:8px;margin:8px 0;">
            <span style="width:80px;font-size:13px;text-align:right;flex-shrink:0;">{tp}</span>
            <div style="flex:1;background:#f0f0f0;border-radius:6px;height:24px;overflow:hidden;">
                <div style="width:{pct}%;height:100%;background:{color};border-radius:6px;
                            display:flex;align-items:center;justify-content:flex-end;padding-right:8px;
                            transition:width 0.5s;">
                </div>
            </div>
            <span style="font-size:14px;font-weight:600;width:30px;">{count}</span>
        </div>"""

    return f"<div style='padding:10px 20px;'>{bars}</div>"


def render_module_heatmap_html(df: pd.DataFrame) -> str:
    """模块 × 优先级 — HTML 表格热力图"""
    cross = pd.crosstab(df["module"], df["priority"])
    priority_order = ["P0-阻塞", "P1-高", "P2-中", "P3-低"]
    for p in priority_order:
        if p not in cross.columns:
            cross[p] = 0
    cross = cross[priority_order]
    max_val = cross.values.max() if cross.values.max() > 0 else 1

    # 表头
    headers = "<th style='padding:8px 16px;background:#f5f5f5;'>模块</th>"
    for p in priority_order:
        headers += f"<th style='padding:8px 14px;background:#f5f5f5;text-align:center;'>{p}</th>"

    # 表体
    rows = ""
    for module_name in cross.index:
        row = f"<td style='padding:8px 16px;font-weight:500;'>{module_name}</td>"
        for p in priority_order:
            val = cross.loc[module_name, p]
            intensity = val / max_val if max_val > 0 else 0
            # 颜色从浅绿到深红
            if intensity == 0:
                bg = "#f9f9f9"
                text_color = "#ccc"
            elif intensity < 0.25:
                bg = "#E8F5E9"
                text_color = "#333"
            elif intensity < 0.5:
                bg = "#A5D6A7"
                text_color = "#333"
            elif intensity < 0.75:
                bg = "#FF8C00"
                text_color = "white"
            else:
                bg = "#D32F2F"
                text_color = "white"
            row += f"<td style='padding:10px;text-align:center;background:{bg};color:{text_color};font-weight:600;border-radius:4px;'>{int(val)}</td>"
        rows += f"<tr>{row}</tr>"

    html = f"""
    <table style='width:100%;border-collapse:collapse;'>
        <thead><tr>{headers}</tr></thead>
        <tbody>{rows}</tbody>
    </table>"""
    return html


def render_method_bar_html(df: pd.DataFrame) -> str:
    """设计方法 × 优先级 — 分组统计表"""
    mp = df.groupby(["design_method", "priority"]).size().unstack(fill_value=0)
    priority_order = ["P0-阻塞", "P1-高", "P2-中", "P3-低"]
    for p in priority_order:
        if p not in mp.columns:
            mp[p] = 0
    mp = mp[priority_order]
    mp["合计"] = mp.sum(axis=1)

    # 表头
    headers = "<th style='padding:8px 14px;background:#f5f5f5;'>设计方法</th>"
    for p in priority_order:
        color = PRIORITY_COLORS.get(p, "#999")
        headers += f"<th style='padding:8px 12px;background:#f5f5f5;text-align:center;border-bottom:3px solid {color};'>{p}</th>"
    headers += "<th style='padding:8px 14px;background:#f5f5f5;text-align:center;'>合计</th>"

    rows = ""
    for method_name in mp.index:
        row = f"<td style='padding:8px 14px;font-weight:500;'>{method_name}</td>"
        for p in priority_order:
            val = int(mp.loc[method_name, p])
            color = "#999" if val == 0 else "#333"
            row += f"<td style='padding:8px;text-align:center;font-weight:600;color:{color};'>{val if val>0 else '-'}</td>"
        row += f"<td style='padding:8px;text-align:center;font-weight:700;background:#f0f4ff;border-radius:4px;'>{int(mp.loc[method_name,'合计'])}</td>"
        rows += f"<tr>{row}</tr>"

    html = f"""
    <table style='width:100%;border-collapse:collapse;'>
        <thead><tr>{headers}</tr></thead>
        <tbody>{rows}</tbody>
    </table>"""
    return html


def create_dashboard(df: pd.DataFrame) -> dict:
    """生成完整仪表盘数据（包含 HTML 字符串和 KPI）"""
    return {
        "kpi": create_kpi_cards(df),
        "pie_html": render_priority_pie_html(df),
        "bar_html": render_type_bar_html(df),
        "heatmap_html": render_module_heatmap_html(df),
        "method_html": render_method_bar_html(df),
    }
