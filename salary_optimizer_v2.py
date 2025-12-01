import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import io
from collections import deque

# 设置页面配置
st.set_page_config(
    page_title="薪资结构优化分析系统 v2.0",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------- 核心计算函数 ----------------------
def calculate_tax_salary(taxable_income):
    """计算综合所得个税"""
    if taxable_income <= 36000:
        return taxable_income * 0.03
    elif taxable_income <= 144000:
        return taxable_income * 0.10 - 2520
    elif taxable_income <= 300000:
        return taxable_income * 0.20 - 16920
    elif taxable_income <= 420000:
        return taxable_income * 0.25 - 31920
    elif taxable_income <= 660000:
        return taxable_income * 0.30 - 52920
    elif taxable_income <= 960000:
        return taxable_income * 0.35 - 85920
    else:
        return taxable_income * 0.45 - 181920

def calculate_tax_bonus(bonus):
    """计算年终奖个税 (单独计税)"""
    avg_monthly = bonus / 12
    if avg_monthly <= 3000:
        return bonus * 0.03
    elif avg_monthly <= 12000:
        return bonus * 0.10 - 210
    elif avg_monthly <= 25000:
        return bonus * 0.20 - 1410
    elif avg_monthly <= 35000:
        return bonus * 0.25 - 2660
    elif avg_monthly <= 55000:
        return bonus * 0.30 - 4410
    elif avg_monthly <= 80000:
        return bonus * 0.35 - 7160
    else:
        return bonus * 0.45 - 15160

def calculate_social_security(monthly_salary, ss_base, hf_base):
    """计算社保公积金 (养老保险8%，医疗保险2%，失业保险0.2%，公积金5%)"""
    pension = min(ss_base, monthly_salary) * 0.08
    medical = min(ss_base, monthly_salary) * 0.02
    unemployment = min(ss_base, monthly_salary) * 0.002
    housing_fund = min(hf_base, monthly_salary) * 0.05
    
    monthly_ss = pension + medical + unemployment + housing_fund
    annual_ss = monthly_ss * 12
    
    return monthly_ss, annual_ss, {
        '养老保险': pension,
        '医疗保险': medical,
        '失业保险': unemployment,
        '公积金': housing_fund
    }

def calculate_one_scenario(base_salary, performance_salary, bonus_base_months, 
                          performance_multiplier, ss_base, hf_base, 
                          additional_deductions=0, include_performance_in_bonus=True):
    """计算单一薪资方案的结果"""
    # 1. 计算月度和年度薪资
    monthly_salary = base_salary + performance_salary
    annual_salary = monthly_salary * 12
    
    # 2. 计算年终奖基数（根据选择决定是否包含绩效工资）
    if include_performance_in_bonus:
        bonus_base = base_salary + performance_salary  # 包含绩效工资
        bonus_calculation_method = "基本工资 + 绩效工资"
    else:
        bonus_base = base_salary  # 只包含基本工资
        bonus_calculation_method = "仅基本工资"
    
    # 计算年终奖 (基本月数 × 绩效系数 × 年终奖基数)
    bonus = bonus_base * bonus_base_months * performance_multiplier
    
    # 3. 计算社保公积金
    monthly_ss, annual_ss, ss_breakdown = calculate_social_security(monthly_salary, ss_base, hf_base)
    
    # 4. 计算年收入和应纳税所得额
    total_income = annual_salary + bonus
    taxable_income = max(0, annual_salary - 60000 - annual_ss - additional_deductions*12)
    
    # 5. 计算个税
    salary_tax = calculate_tax_salary(taxable_income)
    bonus_tax = calculate_tax_bonus(bonus) if bonus > 0 else 0
    total_tax = salary_tax + bonus_tax
    
    # 6. 计算税后收入及关键指标
    after_tax_income = total_income - annual_ss - total_tax
    conversion_rate = after_tax_income / total_income if total_income > 0 else 0
    
    # 7. 确定边际税率
    marginal_rate = 0.03
    if taxable_income > 960000:
        marginal_rate = 0.45
    elif taxable_income > 660000:
        marginal_rate = 0.35
    elif taxable_income > 420000:
        marginal_rate = 0.30
    elif taxable_income > 300000:
        marginal_rate = 0.25
    elif taxable_income > 144000:
        marginal_rate = 0.20
    elif taxable_income > 36000:
        marginal_rate = 0.10
    
    # 8. 计算不同口径的月均收入
    monthly_without_bonus = (annual_salary - annual_ss - salary_tax) / 12
    monthly_with_bonus = after_tax_income / 12
    
    return {
        '基本工资': base_salary,
        '绩效工资': performance_salary,
        '月度总工资': monthly_salary,
        '年终奖月数': bonus_base_months,
        '绩效系数': performance_multiplier,
        '年终奖基数': bonus_base,
        '年终奖金额': bonus,
        '税前年收入': total_income,
        '社保公积金(年)': annual_ss,
        '社保公积金详情': ss_breakdown,
        '个人所得税': total_tax,
        '税后年收入': after_tax_income,
        '收入转化率': conversion_rate,
        '边际税率': marginal_rate,
        '月均到手(不含年终奖)': monthly_without_bonus,
        '月均到手(含年终奖)': monthly_with_bonus,
        '年度社保公积金': annual_ss,
        '年度个税': total_tax,
        '年终奖计算方式': bonus_calculation_method,
        '年终奖包含绩效工资': include_performance_in_bonus
    }

def generate_comprehensive_data(base_salary, performance_salary, bonus_base_months, 
                               performance_multiplier, ss_base, hf_base, 
                               additional_deductions=0, include_performance_in_bonus=True):
    """生成综合对比数据"""
    salary_range = np.arange(5000, 100001, 500)
    
    data = {
        '月薪': [],
        '税后年收入': [],
        '收入转化率': [],
        '边际税率': [],
        '月度个税': [],
        '月度社保公积金': [],
        '税前月收入': []
    }
    
    for s in salary_range:
        # 保持绩效工资比例不变，调整基本工资
        current_base = base_salary * (s / (base_salary + performance_salary)) if (base_salary + performance_salary) > 0 else s/2
        current_perf = performance_salary * (s / (base_salary + performance_salary)) if (base_salary + performance_salary) > 0 else s/2
        
        result = calculate_one_scenario(
            current_base, current_perf, bonus_base_months, 
            performance_multiplier, ss_base, hf_base, additional_deductions,
            include_performance_in_bonus
        )
        
        data['月薪'].append(s)
        data['税后年收入'].append(result['税后年收入'])
        data['收入转化率'].append(result['收入转化率'])
        data['边际税率'].append(result['边际税率'])
        data['月度个税'].append(result['个人所得税'] / 12)
        data['月度社保公积金'].append(result['社保公积金(年)'] / 12)
        data['税前月收入'].append(s)
    
    return pd.DataFrame(data)

# ---------------------- 图表主题配置 ----------------------
def get_chart_theme(theme_name):
    """获取图表主题配置"""
    themes = {
        "自动跟随系统": {
            "template": None,  # 使用默认，跟随系统
            "colors": {
                "primary": "#4CAF50",
                "secondary": "#2196F3",
                "tertiary": "#FF9800",
                "quaternary": "#9C27B0",
                "success": "#4CAF50",
                "warning": "#FF9800",
                "danger": "#F44336",
                "info": "#2196F3",
                "text": None,  # 自动
                "background": None  # 自动
            }
        },
        "深色模式": {
            "template": "plotly_dark",
            "colors": {
                "primary": "#4CAF50",
                "secondary": "#2196F3",
                "tertiary": "#FF9800",
                "quaternary": "#9C27B0",
                "success": "#4CAF50",
                "warning": "#FF9800",
                "danger": "#F44336",
                "info": "#2196F3",
                "text": "#FFFFFF",
                "background": "#1E1E1E"
            }
        },
        "浅色模式": {
            "template": "plotly_white",
            "colors": {
                "primary": "#4CAF50",
                "secondary": "#2196F3",
                "tertiary": "#FF9800",
                "quaternary": "#9C27B0",
                "success": "#4CAF50",
                "warning": "#FF9800",
                "danger": "#F44336",
                "info": "#2196F3",
                "text": "#000000",
                "background": "#FFFFFF"
            }
        },
        "蓝色调方案": {
            "template": None,
            "colors": {
                "primary": "#2196F3",
                "secondary": "#03A9F4",
                "tertiary": "#00BCD4",
                "quaternary": "#0097A7",
                "success": "#4CAF50",
                "warning": "#FF9800",
                "danger": "#F44336",
                "info": "#2196F3",
                "text": "#000000",
                "background": "#FFFFFF"
            }
        },
        "暖色调方案": {
            "template": None,
            "colors": {
                "primary": "#FF9800",
                "secondary": "#FF5722",
                "tertiary": "#FFC107",
                "quaternary": "#FF7043",
                "success": "#4CAF50",
                "warning": "#FF9800",
                "danger": "#F44336",
                "info": "#2196F3",
                "text": "#000000",
                "background": "#FFFFFF"
            }
        }
    }
    
    return themes.get(theme_name, themes["自动跟随系统"])

# 获取当前系统主题
def get_system_theme():
    """获取系统主题（简化的检测方法）"""
    try:
        # 尝试检测系统主题（注意：Streamlit本身不直接支持，这里使用简化的方法）
        # 在实际使用中，可能需要通过JavaScript检测
        return "深色模式"  # 默认返回深色，用户可以在侧边栏手动调整
    except:
        return "浅色模式"

# ---------------------- 初始化session state ----------------------
if 'salary_history' not in st.session_state:
    st.session_state.salary_history = []
if 'history_count' not in st.session_state:
    st.session_state.history_count = 0
if 'current_theme' not in st.session_state:
    st.session_state.current_theme = "自动跟随系统"

def add_to_history(current_result, params):
    """添加当前方案到历史记录"""
    history_item = {
        'id': st.session_state.history_count + 1,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'params': params.copy(),
        'results': current_result.copy()
    }
    
    # 添加到历史记录，最多保留10条
    st.session_state.salary_history.append(history_item)
    if len(st.session_state.salary_history) > 10:
        st.session_state.salary_history.pop(0)
    
    st.session_state.history_count += 1
    st.success(f"✅ 已记录第 {history_item['id']} 次调整方案")

def calculate_change_rate(current_value, previous_value):
    """计算变化率"""
    if previous_value == 0:
        return 0
    return ((current_value - previous_value) / previous_value) * 100

# ---------------------- 页面标题和说明 ----------------------
st.title("💰 薪资结构优化分析系统 v2.0")
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .stButton > button {
        width: 100%;
    }
    /* 深色模式适配 */
    @media (prefers-color-scheme: dark) {
        .stApp {
            background-color: #0E1117;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------- 侧边栏：参数设置 ----------------------
with st.sidebar:
    st.header("🎛️ 参数设置")
    
    # 工资结构设置
    st.subheader("工资结构设置")
    
    col1, col2 = st.columns(2)
    with col1:
        base_salary = st.number_input(
            "基本工资 (元)", 
            min_value=0, 
            max_value=100000, 
            value=15000, 
            step=500,
            help="固定的基本工资部分"
        )
    with col2:
        performance_salary = st.number_input(
            "绩效工资 (元)", 
            min_value=0, 
            max_value=100000, 
            value=8000, 
            step=500,
            help="浮动的绩效工资部分"
        )
    
    # 年终奖设置
    st.subheader("年终奖设置")
    
    # 新增：年终奖计算方式选择
    include_performance_in_bonus = st.checkbox(
        "年终奖包含绩效工资",
        value=True,
        help="勾选：年终奖基数 = 基本工资 + 绩效工资\n不勾选：年终奖基数 = 基本工资"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        bonus_base_months = st.slider(
            "基本月数", 
            0.0, 12.0, 1.0, 0.5,
            help="年终奖基数（月数）"
        )
    with col2:
        performance_multiplier = st.slider(
            "绩效系数", 
            0.0, 5.0, 1.5, 0.1,
            help="绩效系数（1.0为标准）"
        )
    
    # 社保公积金设置
    st.subheader("社保公积金设置")
    
    city_preset = st.selectbox(
        "选择城市预设",
        ["自定义", "深圳", "北京", "上海", "广州", "杭州", "成都"]
    )
    
    if city_preset == "深圳":
        ss_base, hf_base = 4775, 2520
    elif city_preset == "北京":
        ss_base, hf_base = 6326, 2770
    elif city_preset == "上海":
        ss_base, hf_base = 5975, 2590
    elif city_preset == "广州":
        ss_base, hf_base = 4588, 2300
    elif city_preset == "杭州":
        ss_base, hf_base = 3957, 2010
    elif city_preset == "成都":
        ss_base, hf_base = 3726, 1780
    else:
        col1, col2 = st.columns(2)
        with col1:
            ss_base = st.number_input("社保基数 (元)", min_value=2000, max_value=50000, value=4775, step=100)
        with col2:
            hf_base = st.number_input("公积金基数 (元)", min_value=2000, max_value=50000, value=2520, step=100)
    
    # 专项附加扣除
    st.subheader("专项附加扣除")
    
    additional_deductions = st.number_input(
        "月度专项附加扣除 (元)",
        min_value=0,
        max_value=5000,
        value=0,
        step=100,
        help="如子女教育、住房贷款利息、赡养老人等"
    )
    
    # 薪资调整历史记录功能
    st.subheader("📝 薪资调整历史")
    
    # 记录当前方案按钮
    if st.button("💾 记录当前方案", use_container_width=True):
        # 收集当前参数
        current_params = {
            'base_salary': base_salary,
            'performance_salary': performance_salary,
            'bonus_base_months': bonus_base_months,
            'performance_multiplier': performance_multiplier,
            'ss_base': ss_base,
            'hf_base': hf_base,
            'additional_deductions': additional_deductions,
            'include_performance_in_bonus': include_performance_in_bonus,
            'city_preset': city_preset
        }
        
        # 计算当前方案结果
        current_result = calculate_one_scenario(
            base_salary, performance_salary, bonus_base_months,
            performance_multiplier, ss_base, hf_base, additional_deductions,
            include_performance_in_bonus
        )
        
        # 添加到历史记录
        add_to_history(current_result, current_params)
    
    # 显示历史记录信息
    if st.session_state.salary_history:
        st.info(f"📚 已记录 {len(st.session_state.salary_history)} 次调整方案")
        if st.button("🗑️ 清空历史记录", use_container_width=True):
            st.session_state.salary_history = []
            st.session_state.history_count = 0
            st.rerun()
    
    # 图表外观设置 - 优化版
    st.subheader("🎨 图表外观设置")
    
    # 检测当前系统主题
    system_theme = get_system_theme()
    
    # 主题选择
    chart_theme_option = st.selectbox(
        "图表主题",
        ["自动跟随系统", "深色模式", "浅色模式", "蓝色调方案", "暖色调方案"],
        help="选择图表颜色主题"
    )
    
    # 更新当前主题
    st.session_state.current_theme = chart_theme_option
    
    # 获取主题配置
    theme_config = get_chart_theme(chart_theme_option)
    
    chart_height = st.slider("图表高度", 300, 800, 500, 50)
    
    # 对比方案设置
    st.subheader("🔁 对比方案设置")
    
    enable_comparison = st.checkbox("启用对比分析", value=False)
    
    if enable_comparison:
        st.markdown("**原工作参数**")
        col1, col2 = st.columns(2)
        with col1:
            old_base_salary = st.number_input("原基本工资 (元)", min_value=0, max_value=100000, value=10000, step=500)
            old_bonus_months = st.slider("原年终奖月数", 0.0, 12.0, 1.0, 0.5)
        with col2:
            old_performance_salary = st.number_input("原绩效工资 (元)", min_value=0, max_value=100000, value=5000, step=500)
            old_performance_multiplier = st.slider("原绩效系数", 0.0, 5.0, 1.0, 0.1)
        
        # 原工作年终奖计算方式（默认也使用当前设置）
        old_include_performance_in_bonus = st.checkbox(
            "原工作年终奖包含绩效工资",
            value=include_performance_in_bonus,
            help="原工作的年终奖计算方式"
        )

# 获取当前主题配置
theme_config = get_chart_theme(st.session_state.current_theme)
chart_template = theme_config["template"]
theme_colors = theme_config["colors"]

# ---------------------- 主显示区域 ----------------------
# 计算当前方案结果
current_result = calculate_one_scenario(
    base_salary, performance_salary, bonus_base_months,
    performance_multiplier, ss_base, hf_base, additional_deductions,
    include_performance_in_bonus
)

# 生成综合数据
comprehensive_data = generate_comprehensive_data(
    base_salary, performance_salary, bonus_base_months,
    performance_multiplier, ss_base, hf_base, additional_deductions,
    include_performance_in_bonus
)

# 关键指标显示
st.header("📊 关键指标概览")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        "月度总工资", 
        f"{current_result['月度总工资']:,.0f}元",
        f"基本{current_result['基本工资']:,.0f}+绩效{current_result['绩效工资']:,.0f}"
    )
with col2:
    # 显示年终奖计算方式
    bonus_base_desc = f"基数: {current_result['年终奖基数']:,.0f}元"
    st.metric(
        "年终奖", 
        f"{current_result['年终奖金额']:,.0f}元",
        f"{current_result['年终奖月数']}月×{current_result['绩效系数']}倍 ({current_result['年终奖计算方式']})"
    )
with col3:
    st.metric(
        "税后年收入", 
        f"{current_result['税后年收入']:,.0f}元",
        f"{current_result['收入转化率']*100:.1f}%转化率"
    )
with col4:
    st.metric(
        "边际税率", 
        f"{current_result['边际税率']*100:.1f}%",
        "综合所得税率"
    )

# 月均收入对比
st.subheader("📅 月均收入分析")

col1, col2 = st.columns(2)
with col1:
    st.info(f"""
    **不含年终奖月均到手**  
    🏦 **{current_result['月均到手(不含年终奖)']:,.0f}元**  
    _(仅包含月度工资税后)_
    """)
with col2:
    st.success(f"""
    **含年终奖月均到手**  
    💰 **{current_result['月均到手(含年终奖)']:,.0f}元**  
    _(包含月度工资+年终奖平摊)_
    """)

# 年终奖计算方式说明
st.info(f"📝 **年终奖计算方式**: {current_result['年终奖计算方式']} | 年终奖基数: {current_result['年终奖基数']:,.0f}元")

# ---------------------- 图表区域 ----------------------
st.header("📈 可视化分析")

# 创建标签页 - 新增历史趋势分析标签
tab1, tab2, tab3, tab4, tab5 = st.tabs(["综合曲线图", "收入构成", "边际税率分析", "工资结构分解", "历史趋势分析"])

with tab1:
    # 综合曲线图 - 优化版本
    st.subheader("薪资分析曲线图 (月薪范围: 5,000-100,000元)")
    
    # 获取当前月薪对应的数据点索引
    current_monthly = current_result['月度总工资']
    
    # 找到最接近当前月薪的数据点
    salary_range = comprehensive_data['月薪'].values
    idx = np.argmin(np.abs(salary_range - current_monthly))
    current_conversion_rate = comprehensive_data['收入转化率'].iloc[idx] * 100
    current_after_tax = comprehensive_data['税后年收入'].iloc[idx]
    
    fig_comprehensive = go.Figure()
    
    # 1. 添加收入转化率曲线 - 使用面积图
    fig_comprehensive.add_trace(go.Scatter(
        x=comprehensive_data['月薪'],
        y=comprehensive_data['收入转化率'] * 100,
        mode='lines',
        name='收入转化率',
        line=dict(color=theme_colors['primary'], width=4),
        fill='tozeroy',
        fillcolor=f'rgba({int(theme_colors["primary"][1:3], 16)}, {int(theme_colors["primary"][3:5], 16)}, {int(theme_colors["primary"][5:7], 16)}, 0.2)',
        hovertemplate='<b>收入转化率</b><br>月薪: %{x:,.0f}元<br>转化率: %{y:.1f}%<extra></extra>'
    ))
    
    # 2. 添加税后年收入曲线（使用次坐标轴）
    fig_comprehensive.add_trace(go.Scatter(
        x=comprehensive_data['月薪'],
        y=comprehensive_data['税后年收入'] / 10000,  # 转换为万元
        mode='lines',
        name='税后年收入(万元)',
        line=dict(color=theme_colors['secondary'], width=3, dash='dash'),
        yaxis='y2',
        hovertemplate='<b>税后年收入</b><br>月薪: %{x:,.0f}元<br>年收入: %{y:.1f}万元<extra></extra>'
    ))
    
    # 3. 添加边际税率曲线（使用次坐标轴）
    fig_comprehensive.add_trace(go.Scatter(
        x=comprehensive_data['月薪'],
        y=comprehensive_data['边际税率'] * 100,
        mode='lines',
        name='边际税率(%)',
        line=dict(color=theme_colors['tertiary'], width=3, dash='dot'),
        yaxis='y3',
        hovertemplate='<b>边际税率</b><br>月薪: %{x:,.0f}元<br>税率: %{y:.1f}%<extra></extra>'
    ))
    
    # 4. 添加当前月薪的强化标记点
    fig_comprehensive.add_trace(go.Scatter(
        x=[current_monthly],
        y=[current_conversion_rate],
        mode='markers+text',
        name='当前薪资点',
        marker=dict(
            size=16,
            color=theme_colors['danger'],
            symbol='star',
            line=dict(width=2, color='white')
        ),
        text=[f'{current_conversion_rate:.1f}%'],
        textposition='top center',
        textfont=dict(size=14, color=theme_colors['danger'], family="Arial Black"),
        hovertemplate='<b>当前薪资点</b><br>月薪: %{x:,.0f}元<br>转化率: %{y:.1f}%<br>税后年收入: %{text}<extra></extra>'
    ))
    
    # 5. 添加当前月薪的垂直线
    fig_comprehensive.add_vline(
        x=current_monthly, 
        line_dash="solid", 
        line_color=f"rgba({int(theme_colors['danger'][1:3], 16)}, {int(theme_colors['danger'][3:5], 16)}, {int(theme_colors['danger'][5:7], 16)}, 0.7)",
        line_width=2,
        annotation_text=f"当前月薪: {current_monthly:,.0f}元",
        annotation_position="top right",
        annotation_font=dict(color=theme_colors['danger'], size=12),
        annotation_bgcolor="rgba(255, 255, 255, 0.8)"
    )
    
    # 6. 添加收入转化率参考线（70%, 80%, 90%）
    for rate, name in [(70, '70%参考线'), (80, '80%参考线'), (90, '90%参考线')]:
        fig_comprehensive.add_hline(
            y=rate,
            line_dash="dash",
            line_color="rgba(128, 128, 128, 0.3)",
            line_width=1,
            annotation_text=f"{name}",
            annotation_position="right",
            annotation_font=dict(size=10)
        )
    
    # 获取文本颜色
    text_color = theme_colors.get('text', '#000000')
    if text_color is None:
        # 根据主题模板自动选择
        if chart_template == "plotly_dark":
            text_color = "#FFFFFF"
        else:
            text_color = "#000000"
    
    # 更新布局
    fig_comprehensive.update_layout(
        title=dict(
            text='薪资综合分析曲线 - 以收入转化率为核心指标 (月薪范围: 5,000-100,000元)',
            font=dict(size=20, color=text_color),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title=dict(
                text="月度总工资 (元)",
                font=dict(size=14, color=text_color)
            ),
            gridcolor='rgba(128, 128, 128, 0.1)',
            showgrid=True,
            tickformat=',.0f',
            range=[5000, 100000],  # 设置x轴显示范围
            tickfont=dict(color=text_color)
        ),
        yaxis=dict(
            title=dict(
                text="收入转化率 (%)",
                font=dict(size=14, color=theme_colors['primary'])
            ),
            gridcolor='rgba(128, 128, 128, 0.1)',
            showgrid=True,
            range=[50, 100],  # 调整y轴范围以更好地显示数据
            tickfont=dict(color=text_color)
        ),
        yaxis2=dict(
            title=dict(
                text="税后年收入 (万元)",
                font=dict(size=14, color=theme_colors['secondary'])
            ),
            anchor="x",
            overlaying="y",
            side="right",
            gridcolor='rgba(128, 128, 128, 0.05)',
            showgrid=False,
            tickfont=dict(color=text_color)
        ),
        yaxis3=dict(
            title=dict(
                text="边际税率 (%)",
                font=dict(size=14, color=theme_colors['tertiary'])
            ),
            anchor="free",
            overlaying="y",
            side="right",
            position=0.85,
            gridcolor='rgba(128, 128, 128, 0.05)',
            showgrid=False,
            tickfont=dict(color=text_color)
        ),
        hovermode="x unified",
        template=chart_template,
        height=chart_height,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor=f"rgba({int(text_color[1:3], 16) if text_color.startswith('#') else 0}, "
                   f"{int(text_color[3:5], 16) if text_color.startswith('#') and len(text_color) >= 7 else 0}, "
                   f"{int(text_color[5:7], 16) if text_color.startswith('#') and len(text_color) >= 7 else 0}, 0.1)",
            bordercolor="rgba(128, 128, 128, 0.3)",
            borderwidth=1,
            font=dict(color=text_color)
        ),
        plot_bgcolor=theme_colors.get('background', 'white'),
        paper_bgcolor=theme_colors.get('background', 'white'),
        margin=dict(t=80, b=80, l=80, r=100)
    )
    
    # 添加图例说明
    fig_comprehensive.add_annotation(
        x=0.02,
        y=1.05,
        xref="paper",
        yref="paper",
        text="💡 收入转化率 = 税后收入 / 税前收入",
        showarrow=False,
        font=dict(size=12, color=text_color),
        bgcolor=f"rgba({int(text_color[1:3], 16) if text_color.startswith('#') else 0}, "
               f"{int(text_color[3:5], 16) if text_color.startswith('#') and len(text_color) >= 7 else 0}, "
               f"{int(text_color[5:7], 16) if text_color.startswith('#') and len(text_color) >= 7 else 0}, 0.1)",
        bordercolor="#DDD",
        borderwidth=1,
        borderpad=4
    )
    
    st.plotly_chart(fig_comprehensive, use_container_width=True)
    
    # 添加当前点的详细数据
    st.info(f"""
    **当前薪资点详细分析**：
    - 📊 **月薪**: {current_monthly:,.0f}元
    - 💰 **收入转化率**: {current_conversion_rate:.1f}% 
    - 🏦 **税后年收入**: {current_after_tax:,.0f}元 ({current_after_tax/10000:.1f}万元)
    - 📈 **边际税率**: {current_result['边际税率']*100:.1f}%
    """)

with tab2:
    # 收入构成分析
    st.subheader("收入构成分析")
    
    # 收入构成饼图
    income_components = pd.DataFrame({
        '项目': ['税后收入', '个人所得税', '社保公积金'],
        '金额': [
            current_result['税后年收入'],
            current_result['个人所得税'],
            current_result['社保公积金(年)']
        ],
        '颜色': [theme_colors['primary'], theme_colors['danger'], theme_colors['secondary']]
    })
    
    fig_pie = px.pie(
        income_components, 
        values='金额', 
        names='项目',
        title='年收入构成',
        color='项目',
        color_discrete_map=dict(zip(income_components['项目'], income_components['颜色']))
    )
    
    # 更新文本颜色
    text_color = theme_colors.get('text', '#000000')
    if text_color is None and chart_template == "plotly_dark":
        text_color = "#FFFFFF"
    
    fig_pie.update_traces(
        textposition='inside', 
        textinfo='percent+label',
        hovertemplate="<b>%{label}</b><br>金额: %{value:,.0f}元<br>占比: %{percent}",
        textfont=dict(color=text_color)
    )
    
    fig_pie.update_layout(
        template=chart_template,
        height=chart_height,
        paper_bgcolor=theme_colors.get('background', 'white'),
        font=dict(color=text_color),
        title_font=dict(color=text_color)
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

with tab3:
    # 边际税率分析
    st.subheader("边际税率阶梯分析 (月薪范围: 5,000-100,000元)")
    
    fig_marginal = px.area(
        comprehensive_data, 
        x='月薪', 
        y='边际税率',
        title='边际税率变化曲线',
        labels={'边际税率': '边际税率', '月薪': '月度总工资 (元)'}
    )
    
    # 获取文本颜色
    text_color = theme_colors.get('text', '#000000')
    if text_color is None and chart_template == "plotly_dark":
        text_color = "#FFFFFF"
    
    # 添加税率区间标注
    tax_thresholds = [36000/12, 144000/12, 300000/12, 420000/12, 660000/12, 960000/12]
    tax_rates = ['3%', '10%', '20%', '25%', '30%', '35%', '45%']
    
    for i, threshold in enumerate(tax_thresholds):
        fig_marginal.add_vline(
            x=threshold,
            line_dash="dot",
            line_color="rgba(128, 128, 128, 0.5)",
            opacity=0.5,
            annotation_text=f"{tax_rates[i]}→{tax_rates[i+1]}",
            annotation_position="top",
            annotation_font=dict(color=text_color)
        )
    
    # 添加当前月薪标记
    fig_marginal.add_vline(
        x=current_monthly,
        line_dash="dash",
        line_color=theme_colors['danger'],
        annotation_text=f"当前: {current_result['边际税率']*100:.1f}%",
        annotation_position="bottom",
        annotation_font=dict(color=text_color)
    )
    
    fig_marginal.update_layout(
        template=chart_template,
        height=chart_height,
        xaxis=dict(
            range=[5000, 100000],  # 设置x轴显示范围
            tickformat=',.0f',
            tickfont=dict(color=text_color),
            title_font=dict(color=text_color)
        ),
        yaxis=dict(
            tickformat=".0%",
            title="边际税率",
            tickfont=dict(color=text_color),
            title_font=dict(color=text_color)
        ),
        paper_bgcolor=theme_colors.get('background', 'white'),
        font=dict(color=text_color),
        title_font=dict(color=text_color)
    )
    
    st.plotly_chart(fig_marginal, use_container_width=True)

with tab4:
    # 工资结构分解
    st.subheader("工资结构分解")
    
    # 月度工资分解
    monthly_breakdown = pd.DataFrame({
        '项目': ['基本工资', '绩效工资', '社保公积金', '月度个税', '月度税后收入'],
        '金额': [
            current_result['基本工资'],
            current_result['绩效工资'],
            current_result['社保公积金(年)'] / 12,
            current_result['个人所得税'] / 12,
            current_result['月均到手(不含年终奖)']
        ],
        '类型': ['收入', '收入', '扣除', '扣除', '净收入']
    })
    
    color_map = {
        '收入': theme_colors['primary'],
        '扣除': theme_colors['danger'],
        '净收入': theme_colors['secondary']
    }
    
    # 获取文本颜色
    text_color = theme_colors.get('text', '#000000')
    if text_color is None and chart_template == "plotly_dark":
        text_color = "#FFFFFF"
    
    fig_monthly = px.bar(
        monthly_breakdown,
        x='项目',
        y='金额',
        color='类型',
        title='月度工资结构分解',
        text='金额',
        color_discrete_map=color_map
    )
    
    fig_monthly.update_traces(
        texttemplate='%{y:,.0f}元',
        textposition='outside',
        textfont=dict(color=text_color)
    )
    
    fig_monthly.update_layout(
        template=chart_template,
        height=chart_height,
        xaxis_title="",
        yaxis_title="金额 (元)",
        showlegend=True,
        paper_bgcolor=theme_colors.get('background', 'white'),
        font=dict(color=text_color),
        title_font=dict(color=text_color),
        xaxis=dict(tickfont=dict(color=text_color)),
        yaxis=dict(tickfont=dict(color=text_color))
    )
    
    st.plotly_chart(fig_monthly, use_container_width=True)

with tab5:
    # 新增：薪资调整历史趋势分析
    st.subheader("📈 薪资调整历史趋势分析")
    
    if not st.session_state.salary_history:
        st.info("📝 尚未记录任何薪资调整方案。请在左侧边栏点击'记录当前方案'按钮开始记录。")
    else:
        # 显示历史记录概览
        st.success(f"📊 已记录 {len(st.session_state.salary_history)} 次薪资调整方案")
        
        # 准备历史数据
        history_df = pd.DataFrame([
            {
                '调整序号': f"第{item['id']}次",
                '记录时间': item['timestamp'],
                '月度总工资(元)': item['results']['月度总工资'],
                '年度总工资(元)': item['results']['税前年收入'],
                '税前月均工资(元)': item['results']['月度总工资'],
                '税后月均工资(元)': item['results']['月均到手(含年终奖)'],
                '收入转化率(%)': item['results']['收入转化率'] * 100,
                '年终奖计算方式': item['results']['年终奖计算方式'],
                '年终奖包含绩效工资': item['results']['年终奖包含绩效工资']
            }
            for item in st.session_state.salary_history
        ])
        
        # 计算变化率
        if len(history_df) > 1:
            change_rates = []
            for i in range(len(history_df)):
                if i == 0:
                    change_rates.append({
                        '调整序号': f"第{i+1}次",
                        '月度总工资变化率(%)': 0,
                        '年度总工资变化率(%)': 0,
                        '税前月均变化率(%)': 0,
                        '税后月均变化率(%)': 0,
                        '收入转化率变化(百分点)': 0
                    })
                else:
                    prev_row = history_df.iloc[i-1]
                    curr_row = history_df.iloc[i]
                    
                    change_rates.append({
                        '调整序号': f"第{i+1}次",
                        '月度总工资变化率(%)': calculate_change_rate(curr_row['月度总工资(元)'], prev_row['月度总工资(元)']),
                        '年度总工资变化率(%)': calculate_change_rate(curr_row['年度总工资(元)'], prev_row['年度总工资(元)']),
                        '税前月均变化率(%)': calculate_change_rate(curr_row['税前月均工资(元)'], prev_row['税前月均工资(元)']),
                        '税后月均变化率(%)': calculate_change_rate(curr_row['税后月均工资(元)'], prev_row['税后月均工资(元)']),
                        '收入转化率变化(百分点)': curr_row['收入转化率(%)'] - prev_row['收入转化率(%)']
                    })
            
            change_df = pd.DataFrame(change_rates)
        
        # 创建多图表显示
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 历史记录数据表")
            display_df = history_df.copy()
            display_df = display_df[['调整序号', '记录时间', '月度总工资(元)', '年度总工资(元)', 
                                    '税前月均工资(元)', '税后月均工资(元)', '收入转化率(%)', '年终奖计算方式']]
            
            # 格式化显示
            formatted_df = display_df.copy()
            for col in ['月度总工资(元)', '年度总工资(元)', '税前月均工资(元)', '税后月均工资(元)']:
                formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,.0f}")
            formatted_df['收入转化率(%)'] = formatted_df['收入转化率(%)'].apply(lambda x: f"{x:.1f}%")
            
            st.dataframe(formatted_df, use_container_width=True, hide_index=True)
        
        with col2:
            if len(history_df) > 1:
                st.subheader("📊 变化率分析")
                # 格式化变化率数据
                change_display_df = change_df.copy()
                for col in ['月度总工资变化率(%)', '年度总工资变化率(%)', 
                          '税前月均变化率(%)', '税后月均变化率(%)']:
                    change_display_df[col] = change_display_df[col].apply(
                        lambda x: f"{x:+.1f}%" if x != 0 else "0.0%"
                    )
                change_display_df['收入转化率变化(百分点)'] = change_display_df['收入转化率变化(百分点)'].apply(
                    lambda x: f"{x:+.2f}pp" if x != 0 else "0.00pp"
                )
                
                st.dataframe(change_display_df, use_container_width=True, hide_index=True)
            else:
                st.info("📈 记录至少2次调整方案后，将显示变化率分析")
        
        # 绘制历史趋势图 - 优化版本
        st.subheader("📈 薪资调整历史趋势图")
        
        # 计算数据范围，用于统一格线
        min_monthly = history_df['月度总工资(元)'].min()
        max_monthly = history_df['月度总工资(元)'].max()
        min_annual = history_df['年度总工资(元)'].min()
        max_annual = history_df['年度总工资(元)'].max()
        min_monthly_after_tax = history_df['税后月均工资(元)'].min()
        max_monthly_after_tax = history_df['税后月均工资(元)'].max()
        min_conversion = history_df['收入转化率(%)'].min()
        max_conversion = history_df['收入转化率(%)'].max()
        
        # 标准化格线：使用5个均匀分布的刻度
        tick_count = 5
        
        # 为每个指标计算均匀分布的刻度
        monthly_ticks = np.linspace(min_monthly, max_monthly, tick_count)
        annual_ticks = np.linspace(min_annual, max_annual, tick_count)
        after_tax_ticks = np.linspace(min_monthly_after_tax, max_monthly_after_tax, tick_count)
        conversion_ticks = np.linspace(min_conversion, max_conversion, tick_count)
        
        fig_history = go.Figure()
        
        # 定义曲线颜色（与主题一致）
        trace_colors = [
            theme_colors['primary'],   # 月度总工资
            theme_colors['secondary'], # 年度总工资
            theme_colors['tertiary'],  # 税后月均工资
            theme_colors['quaternary'] # 收入转化率
        ]
        
        # 添加多条曲线 - 优化图例文字颜色
        traces_data = [
            ('月度总工资', '月度总工资(元)', 'y', None),
            ('年度总工资', '年度总工资(元)', 'y2', 'dash'),
            ('税后月均工资', '税后月均工资(元)', 'y3', 'dot'),
            ('收入转化率', '收入转化率(%)', 'y4', 'dashdot')
        ]
        
        for i, (name, col, yaxis, dash) in enumerate(traces_data):
            fig_history.add_trace(go.Scatter(
                x=history_df['调整序号'],
                y=history_df[col],
                mode='lines+markers',
                name=name,
                line=dict(color=trace_colors[i], width=3, dash=dash),
                marker=dict(size=8, color=trace_colors[i]),
                yaxis=yaxis,
                hovertemplate=f'<b>{name}</b><br>调整: %{{x}}<br>数值: %{{y:,.0f}}元' if '工资' in name else f'<b>{name}</b><br>调整: %{{x}}<br>数值: %{{y:.1f}}%<extra></extra>'
            ))
        
        # 获取文本颜色
        text_color = theme_colors.get('text', '#000000')
        if text_color is None and chart_template == "plotly_dark":
            text_color = "#FFFFFF"
        
        # 更新布局 - 优化格线显示
        fig_history.update_layout(
            title=dict(
                text='薪资调整历史趋势分析',
                font=dict(size=20, color=text_color),
                x=0.5,
                xanchor='center'
            ),
            xaxis=dict(
                title="调整序号",
                tickmode='array',
                tickvals=history_df['调整序号'],
                ticktext=history_df['调整序号'],
                gridcolor='rgba(128, 128, 128, 0.1)',
                showgrid=True,
                gridwidth=1,
                tickfont=dict(color=text_color),
                title_font=dict(color=text_color)
            ),
            yaxis=dict(
                title="月度总工资 (元)",
                title_font=dict(color=trace_colors[0], size=12),
                tickfont=dict(color=text_color, size=10),
                tickmode='array',
                tickvals=monthly_ticks,
                ticktext=[f'{tick:,.0f}' for tick in monthly_ticks],
                gridcolor='rgba(128, 128, 128, 0.1)',
                showgrid=True,
                gridwidth=1,
                zeroline=False
            ),
            yaxis2=dict(
                title="年度总工资 (元)",
                title_font=dict(color=trace_colors[1], size=12),
                tickfont=dict(color=text_color, size=10),
                anchor="x",
                overlaying="y",
                side="right",
                position=0.15,
                tickmode='array',
                tickvals=annual_ticks,
                ticktext=[f'{tick:,.0f}' for tick in annual_ticks],
                gridcolor='rgba(128, 128, 128, 0.05)',
                showgrid=True,
                gridwidth=0.5,
                zeroline=False
            ),
            yaxis3=dict(
                title="税后月均工资 (元)",
                title_font=dict(color=trace_colors[2], size=12),
                tickfont=dict(color=text_color, size=10),
                anchor="free",
                overlaying="y",
                side="right",
                position=0.35,
                tickmode='array',
                tickvals=after_tax_ticks,
                ticktext=[f'{tick:,.0f}' for tick in after_tax_ticks],
                gridcolor='rgba(128, 128, 128, 0.05)',
                showgrid=True,
                gridwidth=0.5,
                zeroline=False
            ),
            yaxis4=dict(
                title="收入转化率 (%)",
                title_font=dict(color=trace_colors[3], size=12),
                tickfont=dict(color=text_color, size=10),
                anchor="free",
                overlaying="y",
                side="right",
                position=0.55,
                tickmode='array',
                tickvals=conversion_ticks,
                ticktext=[f'{tick:.1f}' for tick in conversion_ticks],
                gridcolor='rgba(128, 128, 128, 0.05)',
                showgrid=True,
                gridwidth=0.5,
                zeroline=False
            ),
            hovermode="x unified",
            template=chart_template,
            height=chart_height,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor=f"rgba({int(text_color[1:3], 16) if text_color.startswith('#') else 0}, "
                       f"{int(text_color[3:5], 16) if text_color.startswith('#') and len(text_color) >= 7 else 0}, "
                       f"{int(text_color[5:7], 16) if text_color.startswith('#') and len(text_color) >= 7 else 0}, 0.1)",
                bordercolor="rgba(128, 128, 128, 0.3)",
                borderwidth=1,
                font=dict(color=text_color)
            ),
            plot_bgcolor=theme_colors.get('background', 'white'),
            paper_bgcolor=theme_colors.get('background', 'white'),
            margin=dict(t=80, b=80, l=80, r=100)
        )
        
        # 添加水平参考线（主要网格线）
        for i, tick in enumerate(monthly_ticks):
            if i > 0:  # 跳过第一个，避免与x轴重叠
                fig_history.add_hline(
                    y=tick,
                    line_dash="solid",
                    line_color="rgba(128, 128, 128, 0.1)",
                    line_width=1,
                    opacity=0.3
                )
        
        st.plotly_chart(fig_history, use_container_width=True)
        
        # 绘制变化率图表 - 优化版本
        if len(history_df) > 1:
            st.subheader("📈 变化率趋势图")
            
            # 只从第二次开始有变化率
            change_indicators = ['月度总工资变化率(%)', '年度总工资变化率(%)', 
                               '税前月均变化率(%)', '税后月均变化率(%)']
            
            colors = [
                theme_colors['primary'],
                theme_colors['secondary'],
                theme_colors['tertiary'],
                theme_colors['quaternary']
            ]
            
            # 计算变化率数据的范围
            change_min = float('inf')
            change_max = float('-inf')
            
            for indicator in change_indicators:
                values = change_df[indicator].iloc[1:].values
                change_min = min(change_min, np.min(values))
                change_max = max(change_max, np.max(values))
            
            # 计算收入转化率变化范围
            conversion_values = change_df['收入转化率变化(百分点)'].iloc[1:].values
            conversion_min = np.min(conversion_values)
            conversion_max = np.max(conversion_values)
            
            # 统一两个y轴的范围，使格线对齐
            overall_min = min(change_min, conversion_min)
            overall_max = max(change_max, conversion_max)
            
            # 扩展范围，确保包含0点（如果有正负变化）
            if overall_min > 0:
                overall_min = -overall_max * 0.1  # 向下扩展10%
            if overall_max < 0:
                overall_max = -overall_min * 0.1  # 向上扩展10%
            
            # 确保对称性，使图表更美观
            abs_max = max(abs(overall_min), abs(overall_max))
            overall_min = -abs_max * 1.1  # 扩展10%
            overall_max = abs_max * 1.1    # 扩展10%
            
            # 创建均匀分布的刻度
            tick_count_change = 7  # 使用7个刻度，包括0点
            change_ticks = np.linspace(overall_min, overall_max, tick_count_change)
            
            # 获取文本颜色
            text_color = theme_colors.get('text', '#000000')
            if text_color is None and chart_template == "plotly_dark":
                text_color = "#FFFFFF"
            
            # 创建柱状图
            fig_change = go.Figure()
            
            # 获取x轴值（跳过第一次）
            x_values = change_df['调整序号'].iloc[1:]
            
            # 添加柱状图（变化率）
            for i, indicator in enumerate(change_indicators):
                y_values = change_df[indicator].iloc[1:].values
                
                # 为正值和负值设置不同颜色
                positive_mask = y_values >= 0
                negative_mask = y_values < 0
                
                if np.any(positive_mask):
                    fig_change.add_trace(go.Bar(
                        x=x_values[positive_mask],
                        y=y_values[positive_mask],
                        name=indicator.replace('变化率(%)', '') + '(+)',
                        marker_color=colors[i],
                        text=[f"{y:+.1f}%" for y in y_values[positive_mask]],
                        textposition='outside',
                        textfont=dict(color=text_color),
                        hovertemplate=f'<b>{indicator.replace("变化率(%)", "")}</b><br>调整: %{{x}}<br>变化率: %{{y:+.1f}}%<extra></extra>',
                        showlegend=False  # 不在图例中显示正负分开的条目
                    ))
                
                if np.any(negative_mask):
                    fig_change.add_trace(go.Bar(
                        x=x_values[negative_mask],
                        y=y_values[negative_mask],
                        name=indicator.replace('变化率(%)', '') + '(-)',
                        marker_color=colors[i],
                        marker_pattern_shape="/",  # 添加斜线图案区分负值
                        text=[f"{y:+.1f}%" for y in y_values[negative_mask]],
                        textposition='outside',
                        textfont=dict(color=text_color),
                        hovertemplate=f'<b>{indicator.replace("变化率(%)", "")}</b><br>调整: %{{x}}<br>变化率: %{{y:+.1f}}%<extra></extra>',
                        showlegend=False  # 不在图例中显示正负分开的条目
                    ))
            
            # 添加线图（收入转化率变化）
            y_values_conversion = change_df['收入转化率变化(百分点)'].iloc[1:].values
            
            fig_change.add_trace(go.Scatter(
                x=x_values,
                y=y_values_conversion,
                mode='lines+markers',
                name='收入转化率变化',
                line=dict(color=theme_colors['danger'], width=3),
                marker=dict(size=8, color=theme_colors['danger']),
                yaxis='y2',
                text=[f"{y:+.2f}pp" for y in y_values_conversion],
                textposition='top center',
                textfont=dict(color=text_color),
                hovertemplate='<b>收入转化率变化</b><br>调整: %{x}<br>变化: %{y:+.2f}pp<extra></extra>'
            ))
            
            # 更新布局 - 优化格线显示
            fig_change.update_layout(
                title=dict(
                    text='各指标变化率趋势',
                    font=dict(size=18, color=text_color),
                    x=0.5,
                    xanchor='center'
                ),
                xaxis=dict(
                    title="调整序号",
                    tickmode='array',
                    tickvals=x_values,
                    ticktext=x_values,
                    gridcolor='rgba(128, 128, 128, 0.1)',
                    showgrid=True,
                    gridwidth=1,
                    tickfont=dict(color=text_color),
                    title_font=dict(color=text_color)
                ),
                yaxis=dict(
                    title="变化率 (%)",
                    tickmode='array',
                    tickvals=change_ticks,
                    ticktext=[f'{tick:+.1f}' for tick in change_ticks],
                    range=[overall_min, overall_max],
                    gridcolor='rgba(128, 128, 128, 0.1)',
                    showgrid=True,
                    gridwidth=1,
                    zeroline=True,
                    zerolinecolor='rgba(128, 128, 128, 0.3)',
                    zerolinewidth=1,
                    tickfont=dict(color=text_color),
                    title_font=dict(color=text_color)
                ),
                yaxis2=dict(
                    title="收入转化率变化 (百分点)",
                    overlaying="y",
                    side="right",
                    tickmode='array',
                    tickvals=change_ticks,
                    ticktext=[f'{tick:+.2f}' for tick in change_ticks],
                    range=[overall_min, overall_max],
                    gridcolor='rgba(128, 128, 128, 0.05)',
                    showgrid=True,
                    gridwidth=0.5,
                    zeroline=True,
                    zerolinecolor='rgba(128, 128, 128, 0.3)',
                    zerolinewidth=1,
                    tickfont=dict(color=text_color),
                    title_font=dict(color=text_color)
                ),
                barmode='group',
                template=chart_template,
                height=400,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor=f"rgba({int(text_color[1:3], 16) if text_color.startswith('#') else 0}, "
                           f"{int(text_color[3:5], 16) if text_color.startswith('#') and len(text_color) >= 7 else 0}, "
                           f"{int(text_color[5:7], 16) if text_color.startswith('#') and len(text_color) >= 7 else 0}, 0.1)",
                    bordercolor="rgba(128, 128, 128, 0.3)",
                    borderwidth=1,
                    font=dict(color=text_color)
                ),
                plot_bgcolor=theme_colors.get('background', 'white'),
                paper_bgcolor=theme_colors.get('background', 'white')
            )
            
            # 添加水平网格线（均匀分布）
            for tick in change_ticks:
                fig_change.add_hline(
                    y=tick,
                    line_dash="solid",
                    line_color="rgba(128, 128, 128, 0.1)",
                    line_width=1,
                    opacity=0.3
                )
            
            # 添加0线强调
            fig_change.add_hline(
                y=0,
                line_dash="solid",
                line_color="rgba(128, 128, 128, 0.5)",
                line_width=1.5,
                opacity=0.5
            )
            
            # 添加图例说明
            fig_change.add_annotation(
                x=0.02,
                y=1.05,
                xref="paper",
                yref="paper",
                text="💡 柱状图: 各指标变化率 | 线图: 收入转化率变化",
                showarrow=False,
                font=dict(size=10, color=text_color),
                bgcolor=f"rgba({int(text_color[1:3], 16) if text_color.startswith('#') else 0}, "
                       f"{int(text_color[3:5], 16) if text_color.startswith('#') and len(text_color) >= 7 else 0}, "
                       f"{int(text_color[5:7], 16) if text_color.startswith('#') and len(text_color) >= 7 else 0}, 0.1)",
                bordercolor="#DDD",
                borderwidth=1,
                borderpad=4
            )
            
            st.plotly_chart(fig_change, use_container_width=True)
        
        # 显示最佳方案
        if len(history_df) > 1:
            st.subheader("🏆 最佳方案分析")
            
            # 找出税后月均工资最高的方案
            best_monthly_idx = history_df['税后月均工资(元)'].idxmax()
            best_monthly = history_df.iloc[best_monthly_idx]
            
            # 找出收入转化率最高的方案
            best_conversion_idx = history_df['收入转化率(%)'].idxmax()
            best_conversion = history_df.iloc[best_conversion_idx]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.success(f"""
                **最佳税后收入方案**：
                - 🥇 **第{best_monthly_idx+1}次调整**
                - 💰 **税后月均工资**: {best_monthly['税后月均工资(元)']:,.0f}元
                - 📊 **月度总工资**: {best_monthly['月度总工资(元)']:,.0f}元
                - 🏦 **年度总工资**: {best_monthly['年度总工资(元)']:,.0f}元
                - 📈 **收入转化率**: {best_monthly['收入转化率(%)']:.1f}%
                - ⏰ **记录时间**: {best_monthly['记录时间']}
                """)
            
            with col2:
                st.info(f"""
                **最佳转化率方案**：
                - 🥈 **第{best_conversion_idx+1}次调整**
                - 📈 **收入转化率**: {best_conversion['收入转化率(%)']:.1f}%
                - 💰 **税后月均工资**: {best_conversion['税后月均工资(元)']:,.0f}元
                - 📊 **月度总工资**: {best_conversion['月度总工资(元)']:,.0f}元
                - 🏦 **年度总工资**: {best_conversion['年度总工资(元)']:,.0f}元
                - ⏰ **记录时间**: {best_conversion['记录时间']}
                """)

# ---------------------- 详细数据表格 ----------------------
st.header("📋 详细数据表格")

col1, col2 = st.columns(2)

with col1:
    # 社保公积金详情
    st.subheader("社保公积金明细")
    
    ss_details = pd.DataFrame({
        '项目': list(current_result['社保公积金详情'].keys()),
        '月度金额(元)': list(current_result['社保公积金详情'].values()),
        '年度金额(元)': [v * 12 for v in current_result['社保公积金详情'].values()]
    })
    
    st.dataframe(
        ss_details.style.format({
            '月度金额(元)': '{:,.0f}',
            '年度金额(元)': '{:,.0f}'
        }),
        use_container_width=True
    )

with col2:
    # 年终奖计算明细
    st.subheader("年终奖计算明细")
    
    # 根据计算方式显示不同的基数
    if include_performance_in_bonus:
        bonus_base = current_result['基本工资'] + current_result['绩效工资']
        bonus_base_desc = f"基本工资({current_result['基本工资']:,.0f}) + 绩效工资({current_result['绩效工资']:,.0f})"
    else:
        bonus_base = current_result['基本工资']
        bonus_base_desc = f"基本工资({current_result['基本工资']:,.0f})"
    
    bonus_details = pd.DataFrame({
        '项目': ['计算方式', '基本月数', '绩效系数', '年终奖基数', '年终奖税前', '年终奖个税', '年终奖税后'],
        '数值': [
            current_result['年终奖计算方式'],
            f"{current_result['年终奖月数']}个月",
            f"{current_result['绩效系数']}倍",
            f"{bonus_base:,.0f}元 ({bonus_base_desc})",
            f"{current_result['年终奖金额']:,.0f}元",
            f"{calculate_tax_bonus(current_result['年终奖金额']):,.0f}元",
            f"{current_result['年终奖金额'] - calculate_tax_bonus(current_result['年终奖金额']):,.0f}元"
        ]
    })
    
    st.dataframe(bonus_details, use_container_width=True)

# ---------------------- 对比分析 ----------------------
if enable_comparison:
    st.header("🔄 新旧工作对比分析")
    
    # 计算旧工作结果
    old_result = calculate_one_scenario(
        old_base_salary, old_performance_salary, old_bonus_months,
        old_performance_multiplier, ss_base, hf_base, additional_deductions,
        old_include_performance_in_bonus
    )
    
    # 创建对比表格
    comparison_data = {
        '项目': ['月度总工资', '基本工资', '绩效工资', '年终奖计算方式', '年终奖金额', '税前年收入', 
                '税后年收入', '收入转化率', '边际税率', '月均到手(含年终奖)'],
        '原工作': [
            f"{old_result['月度总工资']:,.0f}元",
            f"{old_result['基本工资']:,.0f}元",
            f"{old_result['绩效工资']:,.0f}元",
            f"{old_result['年终奖计算方式']}",
            f"{old_result['年终奖金额']:,.0f}元",
            f"{old_result['税前年收入']:,.0f}元",
            f"{old_result['税后年收入']:,.0f}元",
            f"{old_result['收入转化率']*100:.1f}%",
            f"{old_result['边际税率']*100:.1f}%",
            f"{old_result['月均到手(含年终奖)']:,.0f}元"
        ],
        '现工作': [
            f"{current_result['月度总工资']:,.0f}元",
            f"{current_result['基本工资']:,.0f}元",
            f"{current_result['绩效工资']:,.0f}元",
            f"{current_result['年终奖计算方式']}",
            f"{current_result['年终奖金额']:,.0f}元",
            f"{current_result['税前年收入']:,.0f}元",
            f"{current_result['税后年收入']:,.0f}元",
            f"{current_result['收入转化率']*100:.1f}%",
            f"{current_result['边际税率']*100:.1f}%",
            f"{current_result['月均到手(含年终奖)']:,.0f}元"
        ],
        '变化': [
            f"{current_result['月度总工资'] - old_result['月度总工资']:+,.0f}元",
            f"{current_result['基本工资'] - old_result['基本工资']:+,.0f}元",
            f"{current_result['绩效工资'] - old_result['绩效工资']:+,.0f}元",
            "-",
            f"{current_result['年终奖金额'] - old_result['年终奖金额']:+,.0f}元",
            f"{current_result['税前年收入'] - old_result['税前年收入']:+,.0f}元",
            f"{current_result['税后年收入'] - old_result['税后年收入']:+,.0f}元",
            f"{(current_result['收入转化率'] - old_result['收入转化率'])*100:+.1f}%",
            f"{(current_result['边际税率'] - old_result['边际税率'])*100:+.1f}%",
            f"{current_result['月均到手(含年终奖)'] - old_result['月均到手(含年终奖)']:+,.0f}元"
        ]
    }
    
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    
    # 收入变化可视化
    fig_comparison = go.Figure()
    
    categories = ['税前年收入', '税后年收入', '月均到手(含年终奖)']
    old_values = [
        old_result['税前年收入'], 
        old_result['税后年收入'], 
        old_result['月均到手(含年终奖)']
    ]
    new_values = [
        current_result['税前年收入'], 
        current_result['税后年收入'], 
        current_result['月均到手(含年终奖)']
    ]
    
    # 获取文本颜色
    text_color = theme_colors.get('text', '#000000')
    if text_color is None and chart_template == "plotly_dark":
        text_color = "#FFFFFF"
    
    fig_comparison.add_trace(go.Bar(
        name='原工作',
        x=categories,
        y=old_values,
        marker_color=theme_colors['warning'],
        text=[f'{v:,.0f}' for v in old_values],
        textposition='outside',
        textfont=dict(color=text_color)
    ))
    
    fig_comparison.add_trace(go.Bar(
        name='现工作',
        x=categories,
        y=new_values,
        marker_color=theme_colors['primary'],
        text=[f'{v:,.0f}' for v in new_values],
        textposition='outside',
        textfont=dict(color=text_color)
    ))
    
    fig_comparison.update_layout(
        title='收入对比',
        barmode='group',
        template=chart_template,
        height=400,
        paper_bgcolor=theme_colors.get('background', 'white'),
        font=dict(color=text_color),
        title_font=dict(color=text_color),
        xaxis=dict(tickfont=dict(color=text_color)),
        yaxis=dict(tickfont=dict(color=text_color))
    )
    
    st.plotly_chart(fig_comparison, use_container_width=True)

# ---------------------- 导出功能 ----------------------
st.header("💾 数据导出")

col1, col2 = st.columns(2)

with col1:
    # 导出当前方案数据
    if st.button("📥 导出当前方案数据"):
        export_data = {
            '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '参数设置': {
                '基本工资': base_salary,
                '绩效工资': performance_salary,
                '年终奖月数': bonus_base_months,
                '绩效系数': performance_multiplier,
                '社保基数': ss_base,
                '公积金基数': hf_base,
                '专项附加扣除': additional_deductions,
                '城市预设': city_preset,
                '年终奖包含绩效工资': include_performance_in_bonus
            },
            '计算结果': {
                k: v for k, v in current_result.items() 
                if k not in ['社保公积金详情']
            },
            '社保公积金详情': current_result['社保公积金详情']
        }
        
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="下载JSON文件",
            data=json_str,
            file_name=f"薪资分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    # 导出历史记录数据
    if st.session_state.salary_history:
        if st.button("📊 导出历史记录数据"):
            history_export = {
                '导出时间': datetime.now().strftime('%Y-%m-d %H:%M:%S'),
                '历史记录数量': len(st.session_state.salary_history),
                '薪资调整历史': st.session_state.salary_history
            }
            
            history_json = json.dumps(history_export, ensure_ascii=False, indent=2)
            st.download_button(
                label="下载历史记录JSON",
                data=history_json,
                file_name=f"薪资调整历史_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

with col2:
    # 导出图表数据
    if st.button("📈 导出图表数据"):
        csv_data = comprehensive_data.to_csv(index=False)
        st.download_button(
            label="下载CSV文件",
            data=csv_data,
            file_name=f"薪资分析数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# ---------------------- 页脚 ----------------------
st.divider()
st.caption("""
    💡 **使用说明**：
    1. 在左侧边栏调整所有参数，图表会实时更新
    2. 工资结构已细分为基本工资和绩效工资
    3. 年终奖计算方式可通过复选框选择：
       - 勾选：年终奖基数 = 基本工资 + 绩效工资
       - 不勾选：年终奖基数 = 基本工资
    4. 年终奖金额 = 年终奖基数 × 基本月数 × 绩效系数
    5. 月均收入分别显示包含和不包含年终奖的情况
    6. 图表显示范围：月薪5,000-100,000元（个税起征点至10万月薪）
    7. 薪资调整历史功能：
       - 点击"记录当前方案"保存当前参数和结果
       - 最多保存最近10次调整记录
       - 在"历史趋势分析"标签页查看趋势和变化率
    8. 图表主题设置：
       - 自动跟随系统：尝试跟随系统深色/浅色模式
       - 深色模式：适合暗光环境使用
       - 浅色模式：传统明亮风格
       - 蓝色调/暖色调：特色配色方案
    9. 数据仅供参考，实际纳税以税务机关规定为准
""")
