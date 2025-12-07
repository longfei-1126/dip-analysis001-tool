# app.py - DIP病种及费用分析工具
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import io

# 设置页面配置（必须放在最前面）
st.set_page_config(
    page_title="DIP病种分析工具",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化session state
def init_session_state():
    """初始化所有session state变量"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        
        # DIP相关参数
        st.session_state.dip_base_score_input = 27.7173
        st.session_state.dip_base_score_slider = 27.7173
        st.session_state.dip_base_score = 27.7173
        
        # 文件处理状态
        st.session_state.file_processed = False
        st.session_state.surgery_file_processed = False
        st.session_state.diagnosis_file_processed = False
        
        # 上传的文件
        st.session_state.uploaded_file = None
        st.session_state.uploaded_surgery_file = None
        st.session_state.uploaded_diagnosis_file = None
        
        # 显示状态
        st.session_state.show_group_info = False
        
        # 选择状态
        st.session_state.selected_diagnosis = None
        st.session_state.selected_operation = None
        st.session_state.custom_operation_input = ""
        st.session_state.custom_diagnosis_input = ""
        
        # 数据库
        st.session_state.dip_database = create_default_dip_database()
        st.session_state.surgery_database = create_default_surgery_database()
        st.session_state.diagnosis_database = create_default_diagnosis_database()

# 创建默认数据库
def create_default_dip_database():
    """创建默认的DIP病种目录"""
    data = {
        '序号': [1, 2, 3, 4],
        'DIP编码': ['B11.0S001', 'C12.0T001', 'D13.0S001', 'H25.0S002'],
        'DIP名称': ['高血压病-手术组01', '糖尿病-治疗组01', '冠心病-手术组01', '老年性初期白内障-手术组02'],
        '病种类型': ['核心病种', '核心病种', '核心病种', '基层病种'],
        '诊断编码': ['I10', 'E11.9', 'I25.1', 'H25.0'],
        '诊断名称': ['特发性高血压', '2型糖尿病', '动脉粥样硬化性心脏病', '老年性初期白内障'],
        '操作编码': ['无', '无', '36.06', '13.4100x001'],
        '操作名称': ['无', '无', '冠状动脉搭桥术', '白内障超声乳化抽吸术'],
        '病例数': [1000, 800, 500, 7568],
        '入组的DIP基准分值': [15.5000, 12.3000, 45.2000, 78.0521]
    }
    return pd.DataFrame(data)

def create_default_surgery_database():
    """创建默认的手术操作分类目录"""
    data = {
        '操作编码': ['13.4100x001', '36.06', '54.11', '88.01'],
        '操作名称': ['白内障超声乳化抽吸术', '冠状动脉搭桥术', '腹腔镜胆囊切除术', '胸部X线检查'],
        '操作类别': ['手术', '手术', '手术', '诊断性操作']
    }
    return pd.DataFrame(data)

def create_default_diagnosis_database():
    """创建默认的诊断编码目录"""
    data = {
        '诊断编码': ['I10', 'I10.x00', 'I11.900', 'I20.000', 'I21.900', 
                   'J18.900', 'J44.900', 'K35.900', 'N17.900', 'R50.900',
                   'E11.9', 'I25.1', 'H25.0'],
        '诊断名称': ['特发性高血压', '特发性高血压', '高血压性心脏病', '不稳定型心绞痛',
                   '急性心肌梗死', '肺炎', '慢性阻塞性肺病', '急性阑尾炎', 
                   '急性肾衰竭', '发热', '2型糖尿病', '动脉粥样硬化性心脏病', 
                   '老年性初期白内障']
    }
    return pd.DataFrame(data)

# 辅助函数
def replace_nan_with_chinese(value):
    """将NaN值替换为中文'无'"""
    if pd.isna(value) or value is None or str(value).strip() == "":
        return "无"
    return str(value)

def calculate_dip_metrics(诊疗费用, 检查检验费用, 药品费用, 耗材费用,
                          医疗性收入成本率, 药耗成本率, 统筹基金支付金额,
                          入组的DIP基准分值, 医院等级系数, 点值):
    """计算DIP相关指标"""
    # 计算入组的DIP分值
    入组的DIP分值 = 入组的DIP基准分值 * 医院等级系数
    
    # 计算中间指标
    住院总费用 = 诊疗费用 + 检查检验费用 + 药品费用 + 耗材费用
    医疗性收入 = 诊疗费用 + 检查检验费用
    药耗收入 = 药品费用 + 耗材费用
    治疗成本 = 医疗性收入 * 医疗性收入成本率 + 药耗收入 * 药耗成本率
    病人自付金额 = 住院总费用 - 统筹基金支付金额
    DIP支付标准 = 入组的DIP分值 * 点值
    
    # 根据新的DIP付费办法，DIP核算金额为负数时计算为0
    DIP核算金额 = max(DIP支付标准 - 病人自付金额, 0)
    
    # 计算目标指标
    病例真实盈亏金额 = DIP支付标准 - 治疗成本
    DIP回款率 = DIP核算金额 / 统筹基金支付金额 if 统筹基金支付金额 != 0 else 0
    DIP盈亏金额 = DIP核算金额 - 统筹基金支付金额
    
    return {
        '病例真实盈亏金额': 病例真实盈亏金额,
        'DIP回款率': DIP回款率,
        '住院总费用': 住院总费用,
        '治疗成本': 治疗成本,
        'DIP支付标准': DIP支付标准,
        'DIP核算金额': DIP核算金额,
        'DIP盈亏金额': DIP盈亏金额,
        '入组的DIP分值': 入组的DIP分值
    }

# 主应用
def main():
    # 初始化session state
    init_session_state()
    
    # 应用标题
    st.title('🏥 DIP病种及费用分析工具')
    
    # 侧边栏配置
    st.sidebar.header('📁 数据导入')
    
    # 1. DIP目录导入
    with st.sidebar.expander("DIP目录导入", expanded=False):
        uploaded_file = st.file_uploader(
            "上传DIP目录文件 (Excel格式)",
            type=['xlsx', 'xls'],
            key="dip_uploader"
        )
        
        if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file:
            try:
                dip_data = pd.read_excel(uploaded_file)
                required_columns = ['诊断名称', '诊断编码', '操作名称', '操作编码', '入组的DIP基准分值']
                missing_columns = [col for col in required_columns if col not in dip_data.columns]
                
                if missing_columns:
                    st.error(f"缺少必要列: {', '.join(missing_columns)}")
                else:
                    for col in dip_data.columns:
                        if dip_data[col].dtype == 'object':
                            dip_data[col] = dip_data[col].apply(replace_nan_with_chinese)
                    
                    st.session_state.dip_database = dip_data
                    st.session_state.uploaded_file = uploaded_file
                    st.success(f"成功导入 {len(dip_data)} 条DIP记录")
            except Exception as e:
                st.error(f"文件读取错误: {str(e)}")
    
    # 2. 手术操作目录导入
    with st.sidebar.expander("手术操作目录导入", expanded=False):
        uploaded_surgery_file = st.file_uploader(
            "上传手术操作目录 (Excel格式)",
            type=['xlsx', 'xls'],
            key="surgery_uploader"
        )
        
        if uploaded_surgery_file is not None and uploaded_surgery_file != st.session_state.uploaded_surgery_file:
            try:
                surgery_data = pd.read_excel(uploaded_surgery_file)
                required_columns = ['操作编码', '操作名称', '操作类别']
                missing_columns = [col for col in required_columns if col not in surgery_data.columns]
                
                if missing_columns:
                    st.error(f"缺少必要列: {', '.join(missing_columns)}")
                else:
                    for col in surgery_data.columns:
                        if surgery_data[col].dtype == 'object':
                            surgery_data[col] = surgery_data[col].apply(replace_nan_with_chinese)
                    
                    st.session_state.surgery_database = surgery_data
                    st.session_state.uploaded_surgery_file = uploaded_surgery_file
                    st.success(f"成功导入 {len(surgery_data)} 条手术操作记录")
            except Exception as e:
                st.error(f"文件读取错误: {str(e)}")
    
    # 3. 诊断目录导入
    with st.sidebar.expander("诊断目录导入", expanded=False):
        uploaded_diagnosis_file = st.file_uploader(
            "上传诊断目录 (Excel格式)",
            type=['xlsx', 'xls'],
            key="diagnosis_uploader"
        )
        
        if uploaded_diagnosis_file is not None and uploaded_diagnosis_file != st.session_state.uploaded_diagnosis_file:
            try:
                diagnosis_data = pd.read_excel(uploaded_diagnosis_file)
                required_columns = ['诊断编码', '诊断名称']
                missing_columns = [col for col in required_columns if col not in diagnosis_data.columns]
                
                if missing_columns:
                    st.error(f"缺少必要列: {', '.join(missing_columns)}")
                else:
                    for col in diagnosis_data.columns:
                        if diagnosis_data[col].dtype == 'object':
                            diagnosis_data[col] = diagnosis_data[col].apply(replace_nan_with_chinese)
                    
                    st.session_state.diagnosis_database = diagnosis_data
                    st.session_state.uploaded_diagnosis_file = uploaded_diagnosis_file
                    st.success(f"成功导入 {len(diagnosis_data)} 条诊断记录")
            except Exception as e:
                st.error(f"文件读取错误: {str(e)}")
    
    # 侧边栏：计算参数
    st.sidebar.header('⚙️ 计算参数')
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        诊疗费用 = st.number_input('诊疗费用', min_value=0.0, value=3936.93, step=100.0, key="诊疗费用")
        检查检验费用 = st.number_input('检查检验费用', min_value=0.0, value=3348.15, step=100.0, key="检查检验费用")
        药品费用 = st.number_input('药品费用', min_value=0.0, value=2001.41, step=100.0, key="药品费用")
        耗材费用 = st.number_input('耗材费用', min_value=0.0, value=3115.78, step=100.0, key="耗材费用")
    
    with col2:
        医疗性收入成本率 = st.slider('医疗性收入成本率', 0.0, 1.0, 0.50, 0.01, key="医疗性收入成本率")
        药耗成本率 = st.slider('药耗成本率', 0.0, 1.5, 1.00, 0.01, key="药耗成本率")
        统筹基金支付金额 = st.number_input('统筹基金支付金额', min_value=0.0, value=7657.03, step=100.0, key="统筹基金支付金额")
        医院等级系数 = st.number_input('医院等级系数', min_value=0.5, max_value=2.0, value=1.0330, step=0.0001, format="%.4f", key="医院等级系数")
    
    # 点值设置
    点值类型 = st.sidebar.selectbox('点值类型', ['居民', '职工'], index=1, key="点值类型")
    默认点值 = 63.3253 if 点值类型 == '居民' else 73.6011
    点值 = st.sidebar.number_input('点值', min_value=0.0, max_value=200.0, value=默认点值, step=0.0001, format="%.4f", key="点值")
    
    # 病种选择
    st.sidebar.header('🏷️ 病种选择')
    
    # 从DIP数据库获取诊断列表
    dip_db = st.session_state.dip_database
    diagnosis_options = ["请选择诊断..."] + list(dip_db['诊断名称'].unique())
    
    selected_diagnosis = st.sidebar.selectbox("选择诊断", diagnosis_options, key="diagnosis_select")
    
    # 根据诊断筛选操作
    operation_options = ["请选择操作...", "无操作"]
    if selected_diagnosis and selected_diagnosis != "请选择诊断...":
        filtered_ops = dip_db[dip_db['诊断名称'] == selected_diagnosis]
        if not filtered_ops.empty:
            for _, row in filtered_ops.iterrows():
                op_name = replace_nan_with_chinese(row['操作名称'])
                if op_name != "无" and op_name not in operation_options:
                    operation_options.append(op_name)
    
    selected_operation = st.sidebar.selectbox("选择操作", operation_options, key="operation_select")
    
    # 获取DIP基准分值
    if selected_diagnosis and selected_diagnosis != "请选择诊断..." and selected_operation and selected_operation != "请选择操作...":
        filtered = dip_db[
            (dip_db['诊断名称'] == selected_diagnosis) & 
            (dip_db['操作名称'].apply(replace_nan_with_chinese) == selected_operation)
        ]
        if not filtered.empty:
            st.session_state.dip_base_score = filtered.iloc[0]['入组的DIP基准分值']
        else:
            st.session_state.dip_base_score = 27.7173
    else:
        st.session_state.dip_base_score = 27.7173
    
    # DIP基准分值输入
    st.sidebar.header('📊 DIP分值')
    入组的DIP基准分值 = st.sidebar.number_input(
        '入组的DIP基准分值',
        min_value=0.0,
        value=float(st.session_state.dip_base_score),
        step=0.0001,
        format="%.4f",
        key="dip_base_score_input"
    )
    
    # 计算DIP分值
    入组的DIP分值 = 入组的DIP基准分值 * 医院等级系数
    st.sidebar.info(f"**计算DIP分值:** {入组的DIP分值:.4f}")
    
    # 计算按钮
    if st.sidebar.button("🚀 开始计算", type="primary", use_container_width=True):
        # 执行计算
        results = calculate_dip_metrics(
            诊疗费用, 检查检验费用, 药品费用, 耗材费用,
            医疗性收入成本率, 药耗成本率, 统筹基金支付金额,
            入组的DIP基准分值, 医院等级系数, 点值
        )
        
        st.session_state.results = results
        st.session_state.calculated = True
    else:
        st.session_state.calculated = False
    
    # 主显示区域
    st.header('📈 分析结果')
    
    if st.session_state.get('calculated', False):
        results = st.session_state.results
        
        # 关键指标卡片
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="病例真实盈亏金额",
                value=f"¥{results['病例真实盈亏金额']:,.2f}",
                delta="盈利" if results['病例真实盈亏金额'] >= 0 else "亏损"
            )
        
        with col2:
            st.metric(
                label="DIP回款率",
                value=f"{results['DIP回款率']:.2%}",
                delta=f"{results['DIP回款率']*100-100:.1f}%" if results['DIP回款率'] != 0 else "0%"
            )
        
        with col3:
            st.metric(
                label="DIP盈亏金额",
                value=f"¥{results['DIP盈亏金额']:,.2f}",
                delta="盈利" if results['DIP盈亏金额'] >= 0 else "亏损"
            )
        
        # 可视化图表
        st.subheader("📊 费用结构分析")
        
        # 费用结构饼图
        费用分类 = ['诊疗费用', '检查检验费用', '药品费用', '耗材费用']
        费用数值 = [诊疗费用, 检查检验费用, 药品费用, 耗材费用]
        
        fig1 = go.Figure(data=[go.Pie(
            labels=费用分类, 
            values=费用数值,
            hole=.3,
            marker_colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        )])
        fig1.update_layout(title_text="费用结构分布")
        
        st.plotly_chart(fig1, use_container_width=True)
        
        # 盈亏对比柱状图
        st.subheader("📈 盈亏对比分析")
        
        对比数据 = pd.DataFrame({
            '指标': ['DIP支付标准', '治疗成本', 'DIP核算金额', '统筹基金支付'],
            '金额': [
                results['DIP支付标准'],
                results['治疗成本'],
                results['DIP核算金额'],
                统筹基金支付金额
            ]
        })
        
        fig2 = go.Figure(data=[
            go.Bar(
                x=对比数据['指标'],
                y=对比数据['金额'],
                marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'],
                text=[f'¥{x:,.0f}' for x in 对比数据['金额']],
                textposition='auto'
            )
        ])
        fig2.update_layout(
            title_text="费用对比分析",
            yaxis_title="金额(元)",
            xaxis_title="费用项目"
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # 详细数据表格
        st.subheader("📋 详细计算结果")
        
        详细数据 = {
            '项目': [
                '住院总费用', '医疗性收入', '药耗收入', '治疗成本',
                '病人自付金额', 'DIP支付标准', 'DIP核算金额',
                '病例真实盈亏金额', 'DIP盈亏金额', 'DIP回款率'
            ],
            '金额/比率': [
                f"¥{results['住院总费用']:,.2f}",
                f"¥{诊疗费用+检查检验费用:,.2f}",
                f"¥{药品费用+耗材费用:,.2f}",
                f"¥{results['治疗成本']:,.2f}",
                f"¥{results['住院总费用']-统筹基金支付金额:,.2f}",
                f"¥{results['DIP支付标准']:,.2f}",
                f"¥{results['DIP核算金额']:,.2f}",
                f"¥{results['病例真实盈亏金额']:,.2f}",
                f"¥{results['DIP盈亏金额']:,.2f}",
                f"{results['DIP回款率']:.2%}"
            ]
        }
        
        df_detail = pd.DataFrame(详细数据)
        st.dataframe(df_detail, use_container_width=True, hide_index=True)
        
    else:
        st.info("👈 请在侧边栏设置参数并点击'开始计算'按钮查看分析结果")
    
    # 数据库显示区域
    st.header('🗃️ 当前数据库')
    
    tab1, tab2, tab3 = st.tabs(["DIP目录", "手术操作目录", "诊断目录"])
    
    with tab1:
        st.dataframe(st.session_state.dip_database, use_container_width=True)
    
    with tab2:
        st.dataframe(st.session_state.surgery_database, use_container_width=True)
    
    with tab3:
        st.dataframe(st.session_state.diagnosis_database, use_container_width=True)
    
    # 应用信息
    st.sidebar.markdown("---")
    st.sidebar.info("""
    **应用信息**
    
    - 版本: 4.0.0
    - 最后更新: 2024年4月
    - 开发者: 医院信息科
    
    **使用说明**
    
    1. 在左侧上传或选择病种
    2. 设置费用参数
    3. 点击"开始计算"
    4. 查看分析结果
    """)

if __name__ == "__main__":
    main()