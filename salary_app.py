import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime

# 设置中文字体，防止图表乱码
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# ---------------------- 核心计算函数 (复用之前已验证的逻辑) ----------------------
# 为简洁起见，这里定义了最核心的几个函数。完整的类定义可以参考我们之前的对话。
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

def calculate_one_scenario(monthly_salary, bonus_months, ss_base, hf_base, additional_deductions=0):
    """计算单一薪资方案的结果"""
    # 1. 计算社保公积金 (简化模型：按固定基数计算，与实际可能略有差异)
    # 养老保险8%，医疗保险2%，失业保险0.2%，公积金5%
    pension = min(ss_base, monthly_salary) * 0.08
    medical = min(ss_base, monthly_salary) * 0.02
    unemployment = min(ss_base, monthly_salary) * 0.002
    housing_fund = min(hf_base, monthly_salary) * 0.05
    monthly_ss = pension + medical + unemployment + housing_fund
    annual_ss = monthly_ss * 12

    # 2. 计算年收入和应纳税所得额
    annual_salary = monthly_salary * 12
    bonus = monthly_salary * bonus_months
    total_income = annual_salary + bonus
    taxable_income = max(0, annual_salary - 60000 - annual_ss - additional_deductions*12)

    # 3. 计算个税
    salary_tax = calculate_tax_salary(taxable_income)
    bonus_tax = calculate_tax_bonus(bonus) if bonus > 0 else 0
    total_tax = salary_tax + bonus_tax

    # 4. 计算税后收入及关键指标
    after_tax_income = total_income - annual_ss - total_tax
    conversion_rate = after_tax_income / total_income if total_income > 0 else 0

    # 确定边际税率
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

    return {
        '税前年收入': total_income,
        '社保公积金(年)': annual_ss,
        '个人所得税': total_tax,
        '税后年收入': after_tax_income,
        '收入转化率': conversion_rate,
        '边际税率': marginal_rate,
        '月均到手': after_tax_income / 12,
        '参数': {
            '月薪': monthly_salary,
            '年终奖月数': bonus_months,
            '社保基数': ss_base,
            '公积金基数': hf_base,
            '专项附加扣除(月)': additional_deductions
        }
    }

# ---------------------- Streamlit 网页应用界面 ----------------------
st.set_page_config(page_title="薪资结构优化分析器", layout="wide")
st.title("💰 薪资结构与个税优化分析器")
st.markdown("通过调整下方参数，实时分析您的税后收入、税率临界点及优化空间。")

# 使用侧边栏放置输入控件，使主界面更整洁[citation:5]
with st.sidebar:
    st.header("参数设置")
    
    # 收入参数
    monthly_salary = st.slider("月度税前工资 (元)", 5000, 100000, 23000, step=500)
    bonus_months = st.slider("年终奖 (月数)", 0.0, 12.0, 1.0, step=0.5)
    
    # 城市预设（快速设置社保公积金基数）
    city_preset = st.selectbox("选择城市 (快速设置基数)", ["自定义", "深圳", "北京", "上海", "广州"])
    if city_preset == "深圳":
        ss_base, hf_base = 4775, 2520
    elif city_preset == "北京":
        ss_base, hf_base = 6326, 2770
    elif city_preset == "上海":
        ss_base, hf_base = 5975, 2590
    elif city_preset == "广州":
        ss_base, hf_base = 4588, 2300
    else:
        ss_base = st.number_input("社保缴纳基数 (元)", min_value=2000, max_value=50000, value=4775, step=100)
        hf_base = st.number_input("公积金缴纳基数 (元)", min_value=2000, max_value=50000, value=2520, step=100)
    
    # 专项附加扣除
    additional_deductions = st.number_input("月度专项附加扣除 (元)", min_value=0, max_value=5000, value=0, step=100,
                                             help="例如子女教育、住房贷款利息、赡养老人等")
    
    # 添加上一份工作的参数用于对比
    st.divider()
    st.subheader("添加上一份工作用于对比")
    compare_mode = st.checkbox("启用对比分析")
    if compare_mode:
        old_monthly_salary = st.slider("上一份工作月薪 (元)", 5000, 100000, 15000, step=500)
        old_bonus_months = st.slider("上一份工作年终奖 (月数)", 0.0, 12.0, 1.0, step=0.5)

# 主显示区域
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📈 收入分析图表")
    
    # 生成不同月薪下的数据用于绘制曲线
    salary_range = np.arange(5000, 50001, 1000)
    after_tax_list = []
    conversion_list = []
    marginal_rate_list = []
    
    for s in salary_range:
        result = calculate_one_scenario(s, bonus_months, ss_base, hf_base, additional_deductions)
        after_tax_list.append(result['税后年收入'])
        conversion_list.append(result['收入转化率'])
        marginal_rate_list.append(result['边际税率'])
    
    # 创建图表
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. 税后收入曲线
    ax = axes[0, 0]
    ax.plot(salary_range, after_tax_list, 'b-', linewidth=2.5)
    ax.axvline(x=monthly_salary, color='r', linestyle='--', alpha=0.7, label='当前月薪')
    ax.set_xlabel('月薪 (元)', fontsize=12)
    ax.set_ylabel('税后年收入 (元)', fontsize=12)
    ax.set_title('税后收入 vs 月薪', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # 2. 收入转化率曲线
    ax = axes[0, 1]
    ax.plot(salary_range, conversion_list, 'g-', linewidth=2.5)
    ax.axvline(x=monthly_salary, color='r', linestyle='--', alpha=0.7)
    ax.set_xlabel('月薪 (元)', fontsize=12)
    ax.set_ylabel('收入转化率 (税后/税前)', fontsize=12)
    ax.set_title('收入转化率 vs 月薪', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0.7, 1.0)
    
    # 3. 边际税率阶梯图
    ax = axes[1, 0]
    # 使用阶梯图展示税率跳变
    ax.step(salary_range, marginal_rate_list, where='post', linewidth=2.5)
    ax.axvline(x=monthly_salary, color='r', linestyle='--', alpha=0.7)
    ax.set_xlabel('月薪 (元)', fontsize=12)
    ax.set_ylabel('边际税率', fontsize=12)
    ax.set_title('边际税率阶梯变化', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 0.5)
    
    # 4. 收入构成饼图（当前方案）
    ax = axes[1, 1]
    current_result = calculate_one_scenario(monthly_salary, bonus_months, ss_base, hf_base, additional_deductions)
    labels = ['税后收入', '个人所得税', '社保公积金']
    sizes = [
        current_result['税后年收入'],
        current_result['个人所得税'],
        current_result['社保公积金(年)']
    ]
    # 只显示正值的部分
    if sum(sizes) > 0:
        colors = ['#4CAF50', '#F44336', '#2196F3']
        ax.pie([s for s in sizes if s > 0], 
               labels=[labels[i] for i, s in enumerate(sizes) if s > 0],
               colors=colors[:sum(1 for s in sizes if s > 0)], 
               autopct='%1.1f%%', startangle=90)
        ax.set_title('年收入构成分析', fontsize=14, fontweight='bold')
    else:
        ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=16)
        ax.set_title('年收入构成分析', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    st.pyplot(fig)

with col2:
    st.subheader("📊 当前方案详细结果")
    current_result = calculate_one_scenario(monthly_salary, bonus_months, ss_base, hf_base, additional_deductions)
    
    # 显示关键指标
    st.metric("税前年收入", f"{current_result['税前年收入']:,.0f} 元")
    st.metric("税后年收入", f"{current_result['税后年收入']:,.0f} 元", 
              delta=f"{current_result['收入转化率']*100:.1f}% 转化率")
    st.metric("月均到手收入", f"{current_result['月均到手']:,.0f} 元")
    
    # 显示详细构成
    st.divider()
    st.write("**详细构成：**")
    detail_df = pd.DataFrame({
        '项目': ['税前总收入', '社保公积金扣除', '个人所得税扣除', '税后总收入'],
        '金额(元)': [
            current_result['税前年收入'],
            -current_result['社保公积金(年)'],
            -current_result['个人所得税'],
            current_result['税后年收入']
        ],
        '占比': [
            '100.0%',
            f"{current_result['社保公积金(年)']/current_result['税前年收入']*100:.1f}%",
            f"{current_result['个人所得税']/current_result['税前年收入']*100:.1f}%",
            f"{current_result['收入转化率']*100:.1f}%"
        ]
    })
    st.dataframe(detail_df, hide_index=True, use_container_width=True)
    
    # 税率信息
    st.divider()
    st.write("**税率信息：**")
    st.write(f"边际税率：**{current_result['边际税率']*100:.1f}%**")
    
    # 临界点分析
    # 找出下一个税率跳档点 (简化示例)
    if current_result['边际税率'] < 0.45:
        next_thresholds = {0.03: 36000, 0.10: 144000, 0.20: 300000, 0.25: 420000, 0.30: 660000, 0.35: 960000}
        current_taxable = max(0, monthly_salary*12 - 60000 - current_result['社保公积金(年)'] - additional_deductions*12)
        for rate, threshold in next_thresholds.items():
            if current_result['边际税率'] < rate:
                gap = threshold - current_taxable
                if gap > 0:
                    extra_monthly = gap / 12
                    st.info(f"距离下一税率档位(**{rate*100:.0f}%**)还差约 **{gap:,.0f}** 元应纳税所得额，相当于月薪增加约 **{extra_monthly:,.0f}** 元。")
                break

# ---------------------- 对比分析功能 ----------------------
if compare_mode and 'old_monthly_salary' in locals():
    st.divider()
    st.subheader("🔄 新旧工作对比分析")
    
    col_a, col_b, col_c = st.columns(3)
    
    # 计算旧工作的结果
    old_result = calculate_one_scenario(old_monthly_salary, old_bonus_months, ss_base, hf_base, additional_deductions)
    
    with col_a:
        st.write("**上一份工作**")
        st.write(f"月薪: {old_monthly_salary:,.0f} 元")
        st.write(f"年终奖: {old_monthly_salary * old_bonus_months:,.0f} 元")
        st.write(f"税后年收入: {old_result['税后年收入']:,.0f} 元")
        st.write(f"收入转化率: {old_result['收入转化率']*100:.1f}%")
    
    with col_b:
        st.write("**当前工作**")
        st.write(f"月薪: {monthly_salary:,.0f} 元")
        st.write(f"年终奖: {monthly_salary * bonus_months:,.0f} 元")
        st.write(f"税后年收入: {current_result['税后年收入']:,.0f} 元")
        st.write(f"收入转化率: {current_result['收入转化率']*100:.1f}%")
    
    with col_c:
        st.write("**变化对比**")
        income_change = current_result['税后年收入'] - old_result['税后年收入']
        change_percent = (income_change / old_result['税后年收入']) * 100 if old_result['税后年收入'] > 0 else 0
        
        st.metric("税后年收入增长", f"{income_change:+,.0f} 元", delta=f"{change_percent:+.1f}%")
        
        # 计算边际税率变化
        if current_result['边际税率'] > old_result['边际税率']:
            st.warning(f"边际税率从 {old_result['边际税率']*100:.1f}% 升至 {current_result['边际税率']*100:.1f}%")
        elif current_result['边际税率'] < old_result['边际税率']:
            st.success(f"边际税率从 {old_result['边际税率']*100:.1f}% 降至 {current_result['边际税率']*100:.1f}%")
        else:
            st.info(f"边际税率保持在 {current_result['边际税率']*100:.1f}%")

# ---------------------- 数据导出功能 ----------------------
st.divider()
st.subheader("💾 导出分析结果")

# 生成报告摘要
if st.button("生成详细报告摘要"):
    report = f"""
# 薪资结构分析报告
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 当前方案参数
- 月薪：{monthly_salary:,.0f} 元
- 年终奖：{bonus_months:.1f} 个月工资
- 社保基数：{ss_base:,.0f} 元
- 公积金基数：{hf_base:,.0f} 元
- 专项附加扣除：{additional_deductions:,.0f} 元/月

## 核心计算结果
- 税前年收入：{current_result['税前年收入']:,.2f} 元
- 社保公积金(年)：{current_result['社保公积金(年)']:,.2f} 元
- 个人所得税：{current_result['个人所得税']:,.2f} 元
- 税后年收入：{current_result['税后年收入']:,.2f} 元
- 收入转化率：{current_result['收入转化率']*100:.2f}%
- 边际税率：{current_result['边际税率']*100:.1f}%
- 月均到手收入：{current_result['月均到手']:,.2f} 元
"""
    st.text_area("报告内容", report, height=300)
    
    # 提供下载（在真实部署中需要更完善的实现）
    st.download_button(
        label="下载报告为文本文件",
        data=report,
        file_name=f"薪资分析报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain"
    )

# 页脚
st.divider()
st.caption("数据说明：本工具计算结果仅供参考，实际纳税请以税务机关规定为准。计算模型基于中国现行个税法及常见社保政策，具体参数可能因地区和时间有所调整。")