"""
AI 智能测试用例生成平台 — 主应用入口

基于大语言模型（DeepSeek/通义千问）的测试用例自动生成工具。
输入需求描述，自动生成结构化测试用例，并提供可视化分析。

技术栈: Python + Streamlit + DeepSeek API + Plotly + Pandas
"""

import streamlit as st
import pandas as pd
import time

from config import TEST_DESIGN_METHODS, PRIORITY_LEVELS, PRIORITY_COLORS
from testcase_generator import TestCaseGenerator
from visualization import create_dashboard
from utils import (
    get_excel_download_link,
    get_csv_download_link,
    compute_coverage_score,
)

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="AI 智能测试用例生成平台",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 自定义 CSS 样式
# ============================================================
st.markdown("""
<style>
    /* 主标题样式 */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #5470C6, #3BA272);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .sub-title {
        color: #888;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    /* KPI 卡片 */
    .kpi-container { display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }
    .kpi-card {
        flex: 1; min-width: 120px;
        background: linear-gradient(135deg, #f5f7fa, #e8ecf1);
        border-radius: 12px; padding: 1rem 1.2rem; text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .kpi-value { font-size: 2rem; font-weight: 700; color: #5470C6; }
    .kpi-label { font-size: 0.8rem; color: #888; margin-top: 0.2rem; }
    /* 用例表格中的优先级标签 */
    .priority-tag {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 0.78rem; font-weight: 600; color: white;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 初始化 Session State
# ============================================================
if "generated_df" not in st.session_state:
    st.session_state.generated_df = None
if "history" not in st.session_state:
    st.session_state.history: list[dict] = []
if "generator" not in st.session_state:
    st.session_state.generator = TestCaseGenerator(provider="deepseek")

# ============================================================
# 侧边栏 — 配置区
# ============================================================
with st.sidebar:
    st.markdown("### ⚙️ 配置面板")

    # API Key 配置
    with st.expander("🔑 API 设置", expanded=False):
        provider = st.selectbox("LLM 提供商", ["deepseek", "qwen"], index=0)
        api_key = st.text_input(
            "API Key",
            type="password",
            placeholder="输入你的 API Key（留空则使用环境变量）",
        )
        st.caption("💡 [获取 DeepSeek API Key](https://platform.deepseek.com/api_keys)")

    # 生成参数
    st.markdown("### 🎯 生成参数")

    module_count = st.slider("拆分模块数", 2, 8, 3, help="将需求拆分为几个测试模块")

    st.markdown("**测试设计方法**（至少选 3 种）")
    selected_methods = []
    cols = st.columns(2)
    for i, method in enumerate(TEST_DESIGN_METHODS):
        with cols[i % 2]:
            if st.checkbox(method, value=(i < 4)):
                selected_methods.append(method)

    extra_context = st.text_area(
        "补充说明（可选）",
        placeholder="例如：重点测试登录安全、兼容微信小程序、数据库为 MySQL...",
        height=80,
    )

    st.markdown("---")

    # 历史记录
    if st.session_state.history:
        st.markdown("### 📜 生成历史")
        for h in st.session_state.history[-5:]:
            st.caption(f"🕐 {h['timestamp']} — {h['case_count']}条用例")
            st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;_{h['requirement'][:40]}..._")

# ============================================================
# 主区域
# ============================================================

# 标题
st.markdown('<p class="main-title">🧪 AI 智能测试用例生成平台</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">基于大语言模型 · 一键生成结构化测试用例 · 可视化覆盖度分析 · 支持 Excel 导出</p>',
    unsafe_allow_html=True,
)

# 两栏布局：左侧输入，右侧预览
col_input, col_preview = st.columns([1, 1], gap="medium")

with col_input:
    st.markdown("### 📝 需求输入")

    input_mode = st.radio(
        "输入方式",
        ["📄 文本输入", "📁 文件上传", "🔖 示例模板"],
        horizontal=True,
        label_visibility="collapsed",
    )

    requirement_text = ""

    if input_mode == "📄 文本输入":
        requirement_text = st.text_area(
            "请输入需求描述",
            placeholder="示例：\n某电商平台用户登录功能：\n1. 支持手机号+验证码和邮箱+密码两种登录方式\n2. 连续输错5次密码锁定账号30分钟\n3. 支持记住密码功能\n4. 支持微信/支付宝第三方登录\n5. 密码需包含大小写字母+数字，长度8-20位",
            height=220,
        )

    elif input_mode == "📁 文件上传":
        uploaded_file = st.file_uploader(
            "上传需求文档",
            type=["txt", "md", "docx"],
            help="支持 TXT、Markdown、Word 格式",
        )
        if uploaded_file:
            if uploaded_file.name.endswith(".docx"):
                st.warning("Word 解析需要 python-docx 库，请先用 TXT 格式")
            requirement_text = uploaded_file.read().decode("utf-8", errors="ignore")
            st.success(f"已读取文件: {uploaded_file.name}")
            with st.expander("📄 预览内容"):
                st.text(requirement_text[:500])

    elif input_mode == "🔖 示例模板":
        templates = {
            "电商-用户注册登录": "用户注册功能：支持手机号注册（需短信验证码），邮箱注册（需邮箱验证），注册需同意用户协议。用户名2-20字符，密码8-20位需包含大小写字母+数字+特殊字符。一个手机号/邮箱只能注册一个账号。",
            "后台管理-权限系统": "后台管理系统的角色权限功能：系统预置超级管理员、普通管理员、编辑员、只读用户四种角色。超级管理员可创建/删除角色并分配权限；权限粒度包括菜单权限、按钮权限、数据权限；角色支持继承。",
            "金融-转账功能": "银行转账功能：支持行内转账和跨行转账。单笔限额50000元，日累计限额200000元。转账需输入交易密码+短信验证码双因子认证。支持预约转账（定时/周期）。转账成功后短信通知双方。",
            "社交-消息推送": "社交APP消息推送功能：支持系统通知、私信、群聊消息三种类型。用户可设置免打扰时段（22:00-8:00），可屏蔽指定用户消息。消息支持文字、图片、语音三种格式，图片自动压缩到500KB以内。",
        }
        template_name = st.selectbox("选择示例", list(templates.keys()))
        requirement_text = st.text_area(
            "需求描述（可编辑）",
            value=templates[template_name],
            height=200,
        )
        st.caption(f"✅ 已加载「{template_name}」模板，可修改后生成")

    # 生成按钮
    st.markdown("")
    gen_btn = st.button(
        "🚀 生成测试用例",
        type="primary",
        width="stretch",
        disabled=(not requirement_text.strip() or len(selected_methods) < 1),
    )

    if not requirement_text.strip():
        st.caption("⚠️ 请输入需求描述或选择示例模板")
    if len(selected_methods) < 1:
        st.caption("⚠️ 请至少选择一种测试设计方法")

with col_preview:
    st.markdown("### 📊 生成结果预览")
    if st.session_state.generated_df is not None:
        df = st.session_state.generated_df
        st.success(f"✅ 共生成 {len(df)} 条测试用例，覆盖 {df['module'].nunique()} 个模块")

        # KPI 摘要
        kpi = {
            "总用例数": len(df),
            "P0 阻断级": len(df[df["priority"] == "P0-阻塞"]),
            "高优先级占比": f"{round((len(df[df['priority'].isin(['P0-阻塞','P1-高'])]) / len(df)) * 100)}%",
            "覆盖模块": df["module"].nunique(),
            "测试方法": df["design_method"].nunique(),
        }
        kpi_cols = st.columns(len(kpi))
        for i, (label, value) in enumerate(kpi.items()):
            with kpi_cols[i]:
                st.metric(label=label, value=value)

        # 下载按钮
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.markdown(get_excel_download_link(df, "AI测试用例"), unsafe_allow_html=True)
        with dl_col2:
            st.markdown(get_csv_download_link(df, "AI测试用例"), unsafe_allow_html=True)
    else:
        st.info("👈 在左侧输入需求并点击「生成测试用例」，结果将在这里展示")

# ============================================================
# 生成逻辑（点击按钮触发）
# ============================================================
if gen_btn and requirement_text.strip() and len(selected_methods) >= 1:
    with st.spinner("🤖 AI 正在分析需求并生成测试用例，请稍候..."):
        start_time = time.time()
        try:
            # 更新 API Key（如果用户输入了）
            if api_key:
                st.session_state.generator.llm.client.api_key = api_key

            df = st.session_state.generator.generate(
                requirement=requirement_text,
                methods=selected_methods,
                module_count=module_count,
                extra_context=extra_context,
            )
            st.session_state.generated_df = df

            # 记录历史
            elapsed = round(time.time() - start_time, 1)
            st.session_state.history.append({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "requirement": requirement_text[:100],
                "case_count": len(df),
                "elapsed": elapsed,
            })

            st.success(f"🎉 生成完成！用时 {elapsed} 秒")
            # 不使用 st.rerun()，让代码自然执行到下方的展示区域

        except RuntimeError as e:
            st.error(f"❌ API 调用失败: {e}")
            st.info("💡 请检查: 1) API Key 是否正确  2) 网络是否连通  3) 账户余额是否充足")
        except ValueError as e:
            st.error(f"❌ 数据解析失败: {e}")
        except Exception as e:
            st.error(f"❌ 未知错误: {e}")

# ============================================================
# 下半部分 — 数据展示与分析（仅在生成后显示）
# ============================================================
if st.session_state.generated_df is not None:
    df = st.session_state.generated_df

    st.markdown("---")
    st.markdown("## 📋 测试用例详情")

    # ---- 筛选栏 ----
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        filter_module = st.multiselect("📦 按模块筛选", df["module"].unique().tolist(), key="fm")
    with filter_col2:
        filter_priority = st.multiselect("🚩 按优先级筛选", PRIORITY_LEVELS, key="fp")
    with filter_col3:
        filter_type = st.multiselect("🏷️ 按类型筛选", df["type"].unique().tolist(), key="ft")
    with filter_col4:
        search_term = st.text_input("🔍 关键词搜索", placeholder="搜索用例标题/步骤...")

    # 应用筛选
    filtered_df = df.copy()
    if filter_module:
        filtered_df = filtered_df[filtered_df["module"].isin(filter_module)]
    if filter_priority:
        filtered_df = filtered_df[filtered_df["priority"].isin(filter_priority)]
    if filter_type:
        filtered_df = filtered_df[filtered_df["type"].isin(filter_type)]
    if search_term:
        mask = (
            filtered_df["title"].str.contains(search_term, case=False, na=False)
            | filtered_df["steps"].str.contains(search_term, case=False, na=False)
            | filtered_df["expected"].str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    # ---- 用例表格 ----
    def highlight_priority(val):
        """根据优先级返回样式"""
        color = PRIORITY_COLORS.get(val, "#999")
        return f"background-color: {color}; color: white; font-weight: 600; border-radius: 12px; padding: 2px 10px; text-align: center;"

    display_cols = ["id", "module", "title", "priority", "type", "design_method", "steps", "expected"]
    st.dataframe(
        filtered_df[display_cols],
        width="stretch",
        height=400,
        column_config={
            "id": st.column_config.TextColumn("编号", width="small"),
            "module": st.column_config.TextColumn("模块", width="small"),
            "title": st.column_config.TextColumn("用例标题", width="medium"),
            "priority": st.column_config.TextColumn("优先级", width="small"),
            "type": st.column_config.TextColumn("类型", width="small"),
            "design_method": st.column_config.TextColumn("设计方法", width="small"),
            "steps": st.column_config.TextColumn("测试步骤", width="large"),
            "expected": st.column_config.TextColumn("预期结果", width="medium"),
        },
        hide_index=True,
    )

    st.caption(f"显示 {len(filtered_df)} / {len(df)} 条用例")

    # ---- 用例详情展开 ----
    with st.expander("🔍 查看某条用例的详细信息"):
        if len(filtered_df) > 0:
            case_ids = filtered_df["id"].tolist()
            selected_case = st.selectbox("选择用例编号", case_ids)
            case = filtered_df[filtered_df["id"] == selected_case].iloc[0]
            detail_cols = st.columns(2)
            with detail_cols[0]:
                st.markdown(f"**编号:** {case['id']}")
                st.markdown(f"**模块:** {case['module']}")
                st.markdown(f"**标题:** {case['title']}")
                st.markdown(f"**优先级:** {case['priority']}")
                st.markdown(f"**类型:** {case['type']}")
            with detail_cols[1]:
                st.markdown(f"**设计方法:** {case['design_method']}")
                st.markdown(f"**前置条件:** {case.get('precondition', '—')}")
                st.markdown(f"**测试数据:** {case.get('test_data', '—')}")
            st.markdown("**测试步骤:**")
            for step in case["steps"].split(";"):
                st.markdown(f"- {step.strip()}")
            st.markdown(f"**预期结果:** {case['expected']}")

    st.markdown("---")
    st.markdown("## 📊 可视化分析")

    # ---- 生成仪表盘 ----
    dashboard = create_dashboard(df)
    kpi_data = dashboard["kpi"]

    # KPI 卡片行
    kpi_cols = st.columns(6)
    kpi_items = [
        ("📋 总用例数", kpi_data["total"], ""),
        ("🔴 P0 阻塞", kpi_data["p0_count"], ""),
        ("🟠 P1 高优", kpi_data["p1_count"], ""),
        ("⚠️ 高优占比", f"{kpi_data['high_ratio']}%", ""),
        ("📦 测试模块", kpi_data["module_count"], ""),
        ("🔧 设计方法", kpi_data["method_count"], ""),
    ]
    for i, (label, value, _) in enumerate(kpi_items):
        with kpi_cols[i]:
            st.metric(label=label, value=value)

    # 图表区 — 纯 HTML/CSS 渲染，零 C 扩展依赖
    st.markdown("### 🔴 用例优先级分布")
    st.markdown(dashboard["pie_html"], unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("### 📊 用例类型分布")
        st.markdown(dashboard["bar_html"], unsafe_allow_html=True)
    with chart_col2:
        st.markdown("### 🔥 模块 × 优先级")
        st.markdown(dashboard["heatmap_html"], unsafe_allow_html=True)

    st.markdown("### 🧩 设计方法 × 优先级")
    st.markdown(dashboard["method_html"], unsafe_allow_html=True)

    # ---- 覆盖度评分 ----
    st.markdown("---")
    st.markdown("## 🎯 测试覆盖度评估")
    coverage = compute_coverage_score(df)

    cov_cols = st.columns(5)
    cov_items = list(coverage.items())
    for i, (label, score) in enumerate(cov_items):
        with cov_cols[i]:
            # 进度环样式
            color = "#D32F2F" if score < 15 else "#FF8C00" if score < 20 else "#4CAF50"
            st.markdown(
                f"""
                <div style="text-align:center; padding:0.5rem;">
                    <div style="font-size:1.6rem; font-weight:700; color:{color};">{score}<span style="font-size:0.8rem;color:#999;">/25</span></div>
                    <div style="font-size:0.8rem; color:#888;">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 总分进度条
    total_score = coverage["总分"]
    st.progress(total_score / 100, text=f"📊 综合覆盖度得分: {total_score} / 100")
    if total_score >= 80:
        st.success("✨ 覆盖度优秀！用例设计全面均衡")
    elif total_score >= 60:
        st.info("👍 覆盖度良好，可适当补充边缘场景")
    else:
        st.warning("📝 建议调整生成参数，增加测试设计方法或模块拆分粒度")

# ============================================================
# 页脚
# ============================================================
st.markdown("---")
st.caption(
    "🧪 AI 智能测试用例生成平台 | Powered by DeepSeek + Streamlit + Plotly | "
    "适用于软件测试工程师提升效率、保证用例质量"
)
