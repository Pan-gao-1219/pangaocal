# ============ 导入库 ============
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import subprocess
import hashlib
import os
import tempfile
import zipfile
from io import BytesIO
# 机器学习相关库
import matplotlib
matplotlib.use('Agg')  # 必须在导入 pyplot 之前设置
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
# 忽略警告
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="中国海洋大学学生成绩测算系统",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


from app.config.major_config import MajorConfig
from app.core.calculator import StudentGradeCalculator
from app.core.tongshi import load_tongshi_db



def show_signature():
    """显示醒目的作者签名"""
    try:
        st.image("签名.png", width=200)  # 把你的签名图片放在同级目录
    except:
        pass

    st.markdown("""
    <div style='text-align: center; padding: 30px; background: linear-gradient(135deg, #FF6B6B 0%, #4ECDC4 100%); border-radius: 20px; margin: 30px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.3); border: 3px solid #FFE66D;'>
        <h1 style='color: white; font-size: 56px; margin-bottom: 10px; text-shadow: 4px 4px 8px rgba(0,0,0,0.4); font-weight: 900;'>
            👨‍🎓 潘 高 👨‍🎓
        </h1>
        <h2 style='color: #FFE66D; font-size: 36px; margin-bottom: 15px; text-shadow: 2px 2px 4px rgba(0,0,0,0.4); font-weight: bold;'>
            2023级勘查技术与工程专业
        </h2>
        <p style='color: white; font-size: 24px; opacity: 0.95; font-weight: 500; letter-spacing: 2px;'>
            ⚓ 中国海洋大学 · 海洋地球科学学院 ⚓
        </p>
        <div style='margin-top: 15px; font-size: 28px;'>
            🎯 📊 ✨ 🎓 📚 ⚡
        </div>
    </div>
    """, unsafe_allow_html=True)



def main():
    # ============ 初始化session_state ============
    if 'calc' not in st.session_state:
        st.session_state.calc = None
    if 'major_code' not in st.session_state:
        st.session_state.major_code = None
    if 'major_name' not in st.session_state:
        st.session_state.major_name = None
    if 'major_school' not in st.session_state:
        st.session_state.major_school = ''
    if 'major_year' not in st.session_state:
        st.session_state.major_year = ''
    if 'tongshi_rule' not in st.session_state:
        st.session_state.tongshi_rule = '不设限'
    if 'tongshi_rule_label' not in st.session_state:
        st.session_state.tongshi_rule_label = '不设限（全部计入）'
    if 'tongshi_credit_limit' not in st.session_state:
        st.session_state.tongshi_credit_limit = 9
    if 'has_excellent_class' not in st.session_state:
        st.session_state.has_excellent_class = False
    if 'excellent_students' not in st.session_state:
        st.session_state.excellent_students = {}
    if 'current_major' not in st.session_state:  # 新增：保存当前专业配置
        st.session_state.current_major = None
    if 'semester_filter' not in st.session_state:
        st.session_state.semester_filter = None
    if 'calc_mode' not in st.session_state:
        st.session_state.calc_mode = '保研'
    if 'generate_details' not in st.session_state:
        st.session_state.generate_details = False
    if 'result_df' not in st.session_state:
        st.session_state.result_df = None

    # ============ 恢复calc对象的属性 ============
    if st.session_state.calc is not None:
        calc = st.session_state.calc
        # 从session_state恢复属性
        if st.session_state.current_major is not None:
            calc.current_major = st.session_state.current_major
        if st.session_state.major_name is not None:
            calc.major_name = st.session_state.major_name
        if st.session_state.has_excellent_class:
            calc.has_excellent_class = st.session_state.has_excellent_class
        if st.session_state.excellent_students:
            calc.excellent_students = st.session_state.excellent_students
    else:
        calc = StudentGradeCalculator()
        st.session_state.calc = calc
    # ============ 侧边栏：系统特色（对应原print） ============
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center;'>
            <h1 style='color: #2c3e50;'>🎓 中国海洋大学</h1>
            <h3 style='color: #3498db;'>成绩测算系统</h3>
            <p style='color: #7f8c8d; font-size: 14px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #ecf0f1;'>
                海洋地球科学学院<br>2023级勘查技术与工程<br>潘高 制 <br>邮箱1534827320@qq.com 
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ============ 系统简介 ============
        with st.expander("📖 系统简介", expanded=False):
            st.markdown("""
            **🎯 系统功能**
            - 自动检测Excel表头，智能识别列名
            - 支持保研/综测两种计算模式
            - 选修课学分择优折算
            - 补考成绩特殊处理

            **🧠 智能分析**
            - 学习状态分类（6+种类型）
            - 成绩趋势分析
            - K-Means聚类分析
            - 学业警示检测
            - 随机森林成绩预警

            **📊 数据可视化**
            - 单学生成绩趋势图
            - 特征重要性分析
            - 状态分布统计
            """)

        st.markdown("---")

        # 对应原控制台打印的特色列表
        st.markdown("### ✨ 系统特色")

        # 创建一个两列的网格来显示特色
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                <span style='font-size: 20px;'>✅</span> 自动检测表头
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                <span style='font-size: 20px;'>✅</span> 自动识别列名
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                <span style='font-size: 20px;'>✅</span> 适配任意Excel
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                <span style='font-size: 20px;'>✅</span> 补考处理
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                <span style='font-size: 20px;'>✅</span> 5位有效数字
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                <span style='font-size: 20px;'>✅</span> 独立计算明细
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                <span style='font-size: 20px;'>✅</span> 学习状态分析
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                <span style='font-size: 20px;'>✅</span> 学业预警
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                <span style='font-size: 20px;'>🔐</span> 加密评审细则
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")

        # ============ 支持的专业 ============
        with st.expander("📚 支持的专业", expanded=False):
            major_list = MajorConfig().get_all_majors()
            for major in major_list:
                st.markdown(f"- {major['emoji']} {major['name']}")

        st.markdown("---")

        # ============ 使用流程 ============
        with st.expander("📋 使用流程", expanded=False):
            st.markdown("""
            **Step 1** 上传Excel文件
            **Step 2** 选择专业
            **Step 3** 选择学期（可选）
            **Step 4** 选择计算模式
            **Step 5** 生成明细（可选）
            **Step 6** 查看分析结果
            **Step 7** 下载报告
            """)

        st.markdown("---")

        # ============ 联系与反馈 ============
        st.markdown("""
        <div style='background-color: #e8f4f8; padding: 15px; border-radius: 10px;'>
            <h4 style='color: #2c3e50; margin: 0;'>📞 联系作者</h4>
            <p style='color: #34495e; margin: 5px 0;'>潘高</p>
            <p style='color: #34495e; margin: 5px 0;'>邮箱: 1534827320@qq.com</p>
            <p style='color: #7f8c8d; font-size: 12px; margin: 10px 0 0 0;'>
            如果遇到问题或有建议，欢迎联系！
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ============ 主界面标题（对应原print） ============
    st.title("🎓 中国海洋大学学生成绩测算系统")

    st.markdown("""
    <div style='background-color: #f0f8ff; padding: 20px; border-radius: 10px; border-left: 5px solid #3498db; margin-bottom: 20px;'>
        <strong>中国海洋大学 海洋地球科学学院</strong>
    </div>
    """, unsafe_allow_html=True)

    # ============ 欢迎信息和快速引导 ============
    if 'result_df' not in st.session_state or st.session_state.result_df is None:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.info("""
            📤 **第一步**
            上传Excel成绩表
            """)

        with col2:
            st.info("""
            ⚙️ **第二步**
            选择专业和计算模式
            """)

        with col3:
            st.info("""
            📊 **第三步**
            查看分析结果
            """)

        st.markdown("""
        <div style='background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; margin: 20px 0;'>
            <h3 style='color: white; margin: 0;'>✨ 欢迎使用成绩测算系统</h3>
            <p style='color: white; opacity: 0.9; margin: 10px 0 0 0;'>
            本系统可以自动分析学生成绩，提供学习状态分类、学业警示检测和成绩预警等功能。
            请按照左侧流程逐步操作。
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ============ 初始化session_state ============
    if 'calc' not in st.session_state:
        st.session_state.calc = None
    if 'major_code' not in st.session_state:
        st.session_state.major_code = None
    if 'semester_filter' not in st.session_state:
        st.session_state.semester_filter = None
    if 'calc_mode' not in st.session_state:
        st.session_state.calc_mode = '保研'
    if 'generate_details' not in st.session_state:
        st.session_state.generate_details = False
    if 'result_df' not in st.session_state:
        st.session_state.result_df = None

    # ============ 1. 文件选择对话框（对应filedialog.askopenfilename） ============
    st.header("📂 第一步：选择成绩表文件")

    # 创建两列布局：左侧上传文件，右侧下载示例
    col1, col2 = st.columns([3, 1])

    with col2:
        # 下载示例表格按钮
        try:
            # 尝试从GitHub仓库中读取示例文件
            example_file_path = "表格使用示意.xlsx"
            if os.path.exists(example_file_path):
                with open(example_file_path, "rb") as f:
                    example_data = f.read()
                st.download_button(
                    label="📥 下载示例表格",
                    data=example_data,
                    file_name="表格使用示意.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="secondary",
                    help="下载示例Excel文件，查看正确的格式要求"
                )
            else:
                st.info("📋 示例表格：请确保文件格式包含：学号、姓名、课程名称、学分、总成绩等字段")
        except Exception as e:
            st.info("📋 示例表格：请确保文件格式包含：学号、姓名、课程名称、学分、总成绩等字段")

    with col1:
        uploaded_file = st.file_uploader(
            "请选择Excel成绩表文件",
            type=['xlsx', 'xls'],
            help="支持 .xlsx .xls 格式。如果不确定格式，可以点击右侧按钮下载示例表格参考"
        )

    if uploaded_file is None:
        # 添加示例表格的说明
        st.info("""
        👆 **请上传Excel文件开始使用**

        **表格格式要求：**
        - 必须包含列：学号、姓名、学分、总成绩
        - 可选列：取得方式、成绩标志、学年学期、课程名称等
        - 支持任意表头位置，系统会自动识别

        如果不确定格式，可以下载右侧的示例表格参考！
        """)
        st.stop()
    # ============ 初始化计算器 ============
    calc = StudentGradeCalculator()
    st.session_state.calc = calc

    # ============ 2. 加载数据（对应calc.load_data()） ============
    with st.spinner("正在加载数据..."):
        try:
            # 读取原始数据用于检测表头
            calc.raw_data = pd.read_excel(uploaded_file, header=None, nrows=20)
            # 检测表头行
            calc.detect_header_row()
            # 使用检测到的表头行重新读取
            calc.df = pd.read_excel(uploaded_file, header=calc.header_row)
            # 识别列名
            success, missing = calc.auto_detect_columns()

            if not success:
                st.error(f"❌ 错误: 缺少必要字段: {missing}")
                st.stop()

            st.success(f"✅ 加载数据成功，共 {len(calc.df)} 条成绩记录")

            # 上传文件会重建计算器对象，因此必须把已选择的专业重新应用到新对象上。
            # 否则卓越班名单会丢失，导致所有学生都被显示为普通班。
            if st.session_state.major_code:
                success_major, major_name = calc.set_major(st.session_state.major_code)
                if success_major:
                    st.session_state.major_name = major_name
                    st.session_state.has_excellent_class = calc.has_excellent_class
                    st.session_state.excellent_students = calc.excellent_students
                    st.session_state.current_major = calc.current_major
                    st.session_state.calc = calc

            # 数据预览（对应原preview_data）
            with st.expander("👁️ 数据预览（前3行）", expanded=True):
                preview_cols = ['学号', '姓名', '课程名称', '学分', '总成绩', '取得方式']
                available_cols = []
                for field in preview_cols:
                    if field in calc.column_mapping:
                        available_cols.append(calc.column_mapping[field])
                if available_cols:
                    preview_df = calc.df[available_cols].head(3)
                    st.dataframe(preview_df, use_container_width=True)

        except Exception as e:
            st.error(f"❌ 无法加载文件，请检查文件格式: {str(e)}")
            st.stop()

    st.markdown("---")

    # ============ 3. 专业选择对话框 ============
    st.header("🎓 第二步：选择专业")

    # 获取所有专业列表
    major_list = calc.major_config.get_all_majors()

    # ---- 按年级 → 学院 分组展示 ----
    from collections import defaultdict

    # 分离特殊专业
    SPECIAL_CODES = {'other', 'custom', 'custom_manual'}
    normal_majors = [m for m in major_list if m['code'] not in SPECIAL_CODES]
    special_majors = [m for m in major_list if m['code'] in SPECIAL_CODES]

    # 按年级分组，再按学院分组
    by_year = defaultdict(lambda: defaultdict(list))
    for m in normal_majors:
        year = m.get('year', '2024')
        school = m.get('school', '其他')
        by_year[year][school].append(m)

    years_sorted = sorted(by_year.keys())  # ['2023', '2024']
    year_tab_labels = [f"📅 {y}级" for y in years_sorted]
    year_tabs = st.tabs(year_tab_labels)

    def _render_major_buttons(majors_in_school, tab_key):
        ROW_SIZE = 4
        for row_start in range(0, len(majors_in_school), ROW_SIZE):
            row = majors_in_school[row_start:row_start + ROW_SIZE]
            cols = st.columns(ROW_SIZE)
            for j, major in enumerate(row):
                with cols[j]:
                    btn_key = f"btn_{tab_key}_{major['code']}"
                    if st.button(
                        f"{major['emoji']} {major['name']}",
                        key=btn_key,
                        use_container_width=True,
                        type="primary" if st.session_state.major_code == major['code'] else "secondary"
                    ):
                        st.session_state.major_code = major['code']
                        st.session_state.major_school = major.get('school', '')
                        st.session_state.major_year = major.get('year', '')
                        success, major_name = calc.set_major(major['code'])
                        if success:
                            st.session_state.major_name = major_name
                            st.session_state.has_excellent_class = calc.has_excellent_class
                            st.session_state.excellent_students = calc.excellent_students
                            st.session_state.current_major = calc.current_major
                            st.session_state.calc = calc
                            st.session_state.result_df = None
                            st.session_state.excel_buffer = None
                            st.session_state.just_selected_major = True
                        st.rerun()

    for year, tab in zip(years_sorted, year_tabs):
        with tab:
            schools_in_year = by_year[year]
            for school_name in sorted(schools_in_year.keys()):
                majors_in_school = schools_in_year[school_name]
                with st.expander(f"🏫 {school_name}（{len(majors_in_school)} 个专业）", expanded=False):
                    _render_major_buttons(majors_in_school, f"{year}_{school_name}")

    # 其他/自定义专业单独一行
    if special_majors:
        st.markdown("---")
        cols = st.columns(len(special_majors))
        for i, major in enumerate(special_majors):
            with cols[i]:
                btn_key = f"btn_special_{major['code']}"
                if st.button(
                    f"{major['emoji']} {major['name']}",
                    key=btn_key,
                    use_container_width=True,
                    type="primary" if st.session_state.major_code == major['code'] else "secondary"
                ):
                    st.session_state.major_code = major['code']
                    st.session_state.major_school = major.get('school', '')
                    st.session_state.major_year = major.get('year', '')
                    success, major_name = calc.set_major(major['code'])
                    if success:
                        st.session_state.major_name = major_name
                        st.session_state.has_excellent_class = calc.has_excellent_class
                        st.session_state.excellent_students = calc.excellent_students
                        st.session_state.current_major = calc.current_major
                        st.session_state.calc = calc
                        st.session_state.result_df = None
                        st.session_state.excel_buffer = None
                        st.session_state.just_selected_major = True
                    st.rerun()

    if st.session_state.major_code is not None:
        # ===== 显示成功选择专业的提示 =====
        if st.session_state.get('just_selected_major', False):
            major_name = st.session_state.get('major_name', '未知专业')
            major_school = st.session_state.get('major_school', '')
            major_year = st.session_state.get('major_year', '')
            year_str = f"{major_year}级" if major_year else ''
            info_parts = [p for p in [major_school, major_name, year_str] if p]
            st.success(f"✅ 已选择：{'  |  '.join(info_parts)}")
            if st.session_state.get('has_excellent_class', False):
                excellent_count = len(st.session_state.get('excellent_students', {}))
                st.success(f"   📋 卓越班学生: {excellent_count} 人")
            # 重置标志，避免重复显示
            st.session_state.just_selected_major = False

        # 显示学分要求与选修课清单（默认展开）
        with st.expander("📖 查看学分要求与选修课清单", expanded=True):
            current_major = st.session_state.get('current_major', None)
            if current_major is not None:
                if '学分要求' not in current_major:
                    st.warning("该专业未配置学分要求")
                else:
                    courses_dict = current_major.get('选修课列表', {})
                    has_exc = st.session_state.get('has_excellent_class', False)

                    # ---- 学分要求表 ----
                    if has_exc and '卓越' in current_major['学分要求']:
                        tab1, tab2 = st.tabs(["🎓 卓越班学分要求", "📚 普通班学分要求"])
                        with tab1:
                            req = current_major['学分要求'].get('卓越', {})
                            rows = [{'课程类别': k, '要求学分': v,
                                     '培养方案选修课数': len(courses_dict.get(k, []))} for k, v in req.items()]
                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                        with tab2:
                            req = current_major['学分要求'].get('普通', {})
                            rows = [{'课程类别': k, '要求学分': v,
                                     '培养方案选修课数': len(courses_dict.get(k, []))} for k, v in req.items()]
                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                    else:
                        req = current_major['学分要求']
                        rows = [{'课程类别': k, '要求学分': v,
                                 '培养方案选修课数': len(courses_dict.get(k, []))} for k, v in req.items()]
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    # ---- 选修课清单 ----
                    has_any_courses = any(len(v) > 0 for v in courses_dict.values())
                    if has_any_courses:
                        st.markdown("---")
                        st.markdown("**📋 培养方案选修课程清单**")
                        st.caption("保研测算时，系统将优先在以下课程中匹配您的成绩单，符合类别的课程方可计入对应类别学分")
                        for cat, courses in courses_dict.items():
                            if courses:
                                st.markdown(f"**{cat}**（共 {len(courses)} 门）")
                                # Display in 3 columns
                                n = len(courses)
                                cols = st.columns(min(3, n))
                                for i, c in enumerate(courses):
                                    cols[i % len(cols)].markdown(f"- {c}")
                    else:
                        st.caption("该专业培养方案中无预设选修课程清单，所有符合类别的修读课程均可计入")
            else:
                st.info("请先选择专业")

    # 如果专业未选择，阻止后续步骤
    if st.session_state.major_code is None:
        st.stop()

    # ============ 新增：自定义专业培养方案录入模块（仅在自定义专业且保研模式时显示） ============
    if st.session_state.major_code in ['custom', 'custom_manual'] and st.session_state.calc_mode == '保研':
        st.header("📝 自定义专业培养方案")

        # 提示用户当前状态
        st.info("当前为自定义专业 + 保研模式，请设置您的专业培养方案")

        # 创建标签页
        tab1, tab2 = st.tabs(["📤 上传培养方案文件", "✏️ 手动录入"])

        with tab1:
            st.subheader("上传专业培养方案文件")

            # 在这里添加下载参考文件的按钮
            col_ref1, col_ref2 = st.columns(2)
            with col_ref1:
                # 下载选修学分要求示例
                try:
                    if os.path.exists("选修学分要求.xlsx"):
                        with open("选修学分要求.xlsx", "rb") as f:
                            req_data = f.read()
                        st.download_button(
                            label="📊 下载学分要求示例",
                            data=req_data,
                            file_name="选修学分要求.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            type="secondary",
                            help="下载选修学分要求示例文件，查看格式"
                        )
                except Exception as e:
                    st.warning("学分要求示例文件不存在")

            with col_ref2:
                # 下载选修课程汇总示例
                try:
                    if os.path.exists("选修课程汇总.xlsx"):
                        with open("选修课程汇总.xlsx", "rb") as f:
                            course_data = f.read()
                        st.download_button(
                            label="📚 下载课程汇总示例",
                            data=course_data,
                            file_name="选修课程汇总.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            type="secondary",
                            help="下载选修课程汇总示例文件，查看格式"
                        )
                except Exception as e:
                    st.warning("课程汇总示例文件不存在")

            st.markdown("---")
            st.markdown("""
            **文件格式要求：**
            - `选修学分要求.xlsx`：包含课程类型和最低要求学分
            - `选修课程汇总.xlsx`：包含具体的选修课程清单

            可以上传单个文件或两个文件一起上传。
            """)

            col1, col2 = st.columns(2)

            with col1:
                req_file = st.file_uploader(
                    "上传选修学分要求文件",
                    type=['xlsx', 'xls'],
                    key="req_file",
                    help="包含课程类型和最低要求学分的Excel文件"
                )

            with col2:
                course_file = st.file_uploader(
                    "上传选修课程汇总文件",
                    type=['xlsx', 'xls'],
                    key="course_file",
                    help="包含具体选修课程清单的Excel文件"
                )

            if req_file is not None or course_file is not None:
                if st.button("应用上传的培养方案", key="apply_upload"):
                    try:
                        custom_major = {
                            '专业名称': '自定义专业（上传）',
                            '专业代码': 'custom',
                            '有卓越班': False,
                            '学分要求': {},
                            '选修课列表': {
                                '学科基础课程': [],
                                '专业知识课程': [],
                                '工作技能课程': []
                            }
                        }

                        # 处理选修学分要求文件
                        if req_file is not None:
                            req_df = pd.read_excel(req_file)
                            # 假设文件有两列：课程类型 和 选修最低要求学分
                            for _, row in req_df.iterrows():
                                course_type = row.iloc[0]  # 第一列是课程类型
                                credit = float(row.iloc[1])  # 第二列是学分要求
                                if pd.notna(course_type) and pd.notna(credit):
                                    custom_major['学分要求'][course_type] = credit

                            st.success(f"✅ 已加载 {len(custom_major['学分要求'])} 个类别的学分要求")

                        # 处理选修课程汇总文件
                        if course_file is not None:
                            course_df = pd.read_excel(course_file)
                            # 假设文件包含：课程模块、课程名称、学分等列
                            for _, row in course_df.iterrows():
                                module = row.iloc[0]  # 第一列是课程模块
                                course_name = row.iloc[3] if len(row) > 3 else row.iloc[1]  # 课程名称所在列

                                if pd.notna(module) and pd.notna(course_name):
                                    if module in custom_major['选修课列表']:
                                        if course_name not in custom_major['选修课列表'][module]:
                                            custom_major['选修课列表'][module].append(course_name)

                            st.success(f"✅ 已加载选修课程："
                                       f"基础课{len(custom_major['选修课列表']['学科基础课程'])}门，"
                                       f"专业课{len(custom_major['选修课列表']['专业知识课程'])}门，"
                                       f"技能课{len(custom_major['选修课列表']['工作技能课程'])}门")

                        # 将自定义专业添加到专业配置中
                        st.session_state.calc.major_config.majors['custom'] = custom_major

                        # 更新当前专业的配置
                        st.session_state.calc.current_major = custom_major
                        st.session_state.calc.major_name = custom_major['专业名称']

                        st.success("✅ 自定义培养方案已应用！")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ 处理文件时出错：{str(e)}")
        with tab2:
            st.subheader("手动录入培养方案")

            with st.form("manual_input_form"):
                st.markdown("**学分要求设置**")

                col1, col2, col3 = st.columns(3)
                with col1:
                    basic_credit = st.number_input("学科基础课程要求学分", min_value=0.0, max_value=20.0, value=6.0,
                                                   step=0.5)
                with col2:
                    major_credit = st.number_input("专业知识课程要求学分", min_value=0.0, max_value=20.0, value=6.0,
                                                   step=0.5)
                with col3:
                    skill_credit = st.number_input("工作技能课程要求学分", min_value=0.0, max_value=20.0, value=0.0,
                                                   step=0.5)

                st.markdown("---")
                st.markdown("**选修课程列表设置**")
                st.markdown("请输入课程名称，每行一个课程")

                col1, col2, col3 = st.columns(3)

                with col1:
                    basic_courses = st.text_area(
                        "学科基础课程",
                        value="Matlab语言与应用\nPython程序设计与实践\n信号分析与处理",
                        height=150,
                        help="每行输入一个课程名称"
                    )

                with col2:
                    major_courses = st.text_area(
                        "专业知识课程",
                        value="GNSS测量与应用\n海洋工程地质\n海洋遥感概论",
                        height=150,
                        help="每行输入一个课程名称"
                    )

                with col3:
                    skill_courses = st.text_area(
                        "工作技能课程",
                        value="地质旅行I\n地质旅行II",
                        height=150,
                        help="每行输入一个课程名称"
                    )

                submitted = st.form_submit_button("✅ 应用手动录入的培养方案")

                if submitted:
                    # 处理课程列表
                    basic_list = [c.strip() for c in basic_courses.split('\n') if c.strip()]
                    major_list = [c.strip() for c in major_courses.split('\n') if c.strip()]
                    skill_list = [c.strip() for c in skill_courses.split('\n') if c.strip()]

                    custom_major = {
                        '专业名称': '自定义专业（手动录入）',
                        '专业代码': 'custom_manual',
                        '有卓越班': False,
                        '学分要求': {
                            '学科基础课程': basic_credit,
                            '专业知识课程': major_credit,
                            '工作技能课程': skill_credit
                        },
                        '选修课列表': {
                            '学科基础课程': basic_list,
                            '专业知识课程': major_list,
                            '工作技能课程': skill_list
                        }
                    }

                    # 将自定义专业添加到专业配置中
                    st.session_state.calc.major_config.majors['custom_manual'] = custom_major

                    # 更新当前专业的配置
                    st.session_state.calc.current_major = custom_major
                    st.session_state.calc.major_name = custom_major['专业名称']

                    st.success("✅ 手动录入的培养方案已应用！")
                    st.rerun()

        # 如果当前是自定义专业，显示当前配置
        if st.session_state.major_code in ['custom', 'custom_manual']:
            with st.expander("📋 当前自定义专业配置", expanded=True):
                if st.session_state.calc and st.session_state.calc.current_major:
                    # 显示学分要求
                    st.subheader("📊 学分要求")
                    req_df = pd.DataFrame(
                        list(st.session_state.calc.current_major.get('学分要求', {}).items()),
                        columns=['课程类别', '要求学分']
                    )
                    st.dataframe(req_df, use_container_width=True)

                    # 显示选修课程列表
                    st.subheader("📚 选修课程列表")
                    tabs = st.tabs(["学科基础课程", "专业知识课程", "工作技能课程"])

                    with tabs[0]:
                        basic_courses = st.session_state.calc.current_major.get('选修课列表', {}).get(
                            '学科基础课程', [])
                        if basic_courses:
                            for i, course in enumerate(basic_courses, 1):
                                st.write(f"{i}. {course}")
                        else:
                            st.info("暂无学科基础课程")

                    with tabs[1]:
                        major_courses = st.session_state.calc.current_major.get('选修课列表', {}).get(
                            '专业知识课程', [])
                        if major_courses:
                            for i, course in enumerate(major_courses, 1):
                                st.write(f"{i}. {course}")
                        else:
                            st.info("暂无专业知识课程")

                    with tabs[2]:
                        skill_courses = st.session_state.calc.current_major.get('选修课列表', {}).get(
                            '工作技能课程', [])
                        if skill_courses:
                            for i, course in enumerate(skill_courses, 1):
                                st.write(f"{i}. {course}")
                        else:
                            st.info("暂无工作技能课程")
                else:
                    st.warning("请先设置培养方案")

    st.markdown("---")

    # ============ 通识教育选修课查询 ============
    tongshi_db = load_tongshi_db()
    if tongshi_db is not None and st.session_state.major_code is not None:
        major_year = st.session_state.get('major_year', '')

        if major_year in ('2023', '2024'):
            st.header("📖 通识教育选修课完成情况")

            # 按年级选择模块列
            module_col = '2024级模块' if major_year == '2024' else '2023级模块'

            # 提取学生所有课程名
            course_name_col = calc.column_mapping.get('课程名称')
            if course_name_col and course_name_col in calc.df.columns:
                student_courses = set(calc.df[course_name_col].dropna().astype(str).str.strip().unique())

                # 在数据库中匹配（完整课程名匹配）
                db_year = tongshi_db[tongshi_db[module_col].notna() & (tongshi_db[module_col].str.strip() != '')].copy()
                matched = db_year[db_year['课程名'].isin(student_courses)].copy()

                # 按模块汇总
                modules = sorted(db_year[module_col].str.strip().unique())
                module_stats = []
                for mod in modules:
                    mod_courses = matched[matched[module_col].str.strip() == mod]
                    module_stats.append({
                        '模块': mod,
                        '已修课程数': len(mod_courses),
                        '已修学分': mod_courses['学分'].sum(),
                        '已修课程': '、'.join(mod_courses['课程名'].tolist()) if len(mod_courses) > 0 else '—'
                    })

                total_credits = matched['学分'].sum()
                modules_covered = sum(1 for s in module_stats if s['已修课程数'] > 0)

                # 达标规则因年级不同：
                # 2024级：3个模块每个至少1门（全覆盖），总学分=9
                # 2023级：至少2个模块，总学分≥9
                req_credits = 9
                if major_year == '2024':
                    req_modules = len(modules)   # 必须全部3个模块
                    module_rule_str = f"3个模块全部覆盖（每模块≥1门）"
                else:
                    req_modules = 2              # 至少2个模块
                    module_rule_str = f"5个模块中至少覆盖2个"

                credits_ok = total_credits >= req_credits
                modules_ok = modules_covered >= req_modules

                # 显示总结指标
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("通识选修总学分", f"{total_credits:.1f} 分", help="已修通识课程学分合计")
                with col_b:
                    if total_credits > req_credits:
                        delta = f"超出 +{total_credits - req_credits:.1f} 分"
                    elif credits_ok:
                        delta = "恰好达标 ✓"
                    else:
                        delta = f"差 {req_credits - total_credits:.1f} 分"
                    st.metric("要求学分", f"{req_credits} 分", delta=delta,
                              delta_color="normal" if credits_ok else "inverse")
                with col_c:
                    delta_mod = "达标 ✓" if modules_ok else f"还差 {req_modules - modules_covered} 个模块"
                    st.metric("已覆盖模块数", f"{modules_covered} / {len(modules)}",
                              delta=delta_mod,
                              delta_color="normal" if modules_ok else "inverse",
                              help=module_rule_str)

                # 模块明细表
                with st.expander("📋 各模块完成详情", expanded=True):
                    stats_df = pd.DataFrame(module_stats)
                    stats_df['状态'] = stats_df['已修课程数'].apply(lambda x: '✅ 已修' if x > 0 else '❌ 未修')
                    st.dataframe(stats_df[['模块', '状态', '已修学分', '已修课程数', '已修课程']],
                                 use_container_width=True, hide_index=True)

                # 整体达标判断
                if credits_ok and modules_ok:
                    st.success(f"✅ 通识教育选修课达标：共 {total_credits:.1f} 学分，已覆盖 {modules_covered} 个模块")
                else:
                    warns = []
                    if not credits_ok:
                        warns.append(f"学分不足（已修 {total_credits:.1f} 分，需 {req_credits} 分）")
                    if not modules_ok:
                        if major_year == '2024':
                            uncovered = [s['模块'] for s in module_stats if s['已修课程数'] == 0]
                            warns.append(f"未覆盖模块：{'、'.join(uncovered)}")
                        else:
                            warns.append(f"仅覆盖 {modules_covered} 个模块（需至少 {req_modules} 个）")
                    st.warning("⚠️ 通识教育选修课未达标：" + "；".join(warns))

                # 美育类提示（培养方案要求≥2学分美育类课程，需人工核对）
                st.caption("⚠️ 注意：培养方案另要求其中至少 2 学分须修读美育类课程，请自行核对。")
            else:
                st.info("未检测到课程名称列，无法匹配通识课程。")

    st.markdown("---")

    # ============ 4. 学期选择（对应原学期选择对话框） ============
    st.header("📅 第三步：学期选择（可选）")

    semester_filter = None
    if '学年学期' in calc.column_mapping:
        sem_col = calc.column_mapping['学年学期']
        semesters = calc.df[sem_col].dropna().unique()
        semesters = sorted([str(s) for s in semesters if pd.notna(s)])

        st.write(f"📌 检测到 {len(semesters)} 个学期")

        choice = st.radio(
            "是否只计算特定学期？",
            options=['全部学期', '指定学期'],
            horizontal=True
        )

        if choice == '指定学期':
            selected_semesters = st.multiselect(
                "请选择要计算的学期（可多选）",
                options=semesters
            )
            semester_filter = selected_semesters if selected_semesters else None
            if semester_filter:
                st.success(f"✅ 已选择 {len(semester_filter)} 个学期")

    st.session_state.semester_filter = semester_filter

    st.markdown("---")

    # ============ 5. 计算模式选择（对应原messagebox.askyesno） ============
    # ============ 5. 计算模式选择（对应原messagebox.askyesno） ============
    st.header("⚙️ 第四步：选择计算模式")

    mode_choice = st.radio(
        "请选择计算模式",
        options=['保研模式', '综测模式'],
        horizontal=True,
        help="保研模式：按选修课学分要求择优折算；综测模式：所有课程全部计入"
    )

    calc_mode = '保研' if mode_choice == '保研模式' else '综测'

    # 如果计算模式改变，更新session_state并重新运行
    if st.session_state.calc_mode != calc_mode:
        st.session_state.calc_mode = calc_mode
        st.session_state.result_df = None
        st.session_state.excel_buffer = None
        st.rerun()  # 添加这一行，确保自定义模块的显示状态更新

    st.info(f"✅ 已选择: {calc_mode}模式")

    # 海洋地球科学学院可按本院细则选择是否启用课程加分和低学分扣分。
    is_earth_sciences = (
        st.session_state.get('major_school') == '海洋地球科学学院'
    )
    apply_low_credit_penalty = False
    apply_course_credit_bonus = False
    if calc_mode == '综测' and is_earth_sciences:
        st.subheader("➕➖ 综测加扣分项（均可选）")
        previous_bonus_setting = st.session_state.get('apply_course_credit_bonus', False)
        previous_penalty_setting = st.session_state.get('apply_low_credit_penalty', False)

        apply_course_credit_bonus = st.checkbox(
            "启用“满足12学分后，必修课与限选课每学分加0.2分”规则",
            value=st.session_state.get('apply_course_credit_bonus', False),
            help=(
                "仅适用于海洋地球科学学院；按学期判断，通过学分（不含任选课）"
                "达到12分后，该学期必修及限选课程每学分加0.2分。"
            )
        )
        apply_low_credit_penalty = st.checkbox(
            "启用“每学期不足12学分，每缺1学分扣5分”规则",
            value=st.session_state.get('apply_low_credit_penalty', False),
            help="仅适用于海洋地球科学学院；未勾选时不进行此项扣分。"
        )
        if apply_low_credit_penalty:
            st.warning(
                "已启用低学分扣分：按每学期通过学分（不含任选课）计算，"
                "不足12学分的部分每学分扣5分。"
            )
        if apply_course_credit_bonus:
            st.success(
                "已启用课程学分加分：每学期达到12学分后，"
                "该学期必修课与限选课按每学分0.2分加分。"
            )
        if (
            apply_course_credit_bonus != previous_bonus_setting
            or apply_low_credit_penalty != previous_penalty_setting
        ):
            st.session_state.result_df = None
            st.session_state.excel_buffer = None
    st.session_state.apply_course_credit_bonus = apply_course_credit_bonus
    st.session_state.apply_low_credit_penalty = apply_low_credit_penalty

    # ============ 通识课保研规则（仅保研模式显示） ============
    if calc_mode == '保研':
        st.subheader("📚 通识教育选修课计入规则（保研模式）")
        tongshi_rule = st.radio(
            "通识课如何计入保研成绩",
            options=['不设限（全部计入）', '折算（上限N学分，择优，可拆分）', '不折算（上限N学分，整门选取）'],
            index=['不设限（全部计入）', '折算（上限N学分，择优，可拆分）', '不折算（上限N学分，整门选取）'].index(
                st.session_state.get('tongshi_rule_label', '不设限（全部计入）')),
            horizontal=False,
            help="折算：同专业选修课逻辑，超出部分按比例拆分；不折算：成绩高的整门选入直到满额"
        )
        st.session_state.tongshi_rule_label = tongshi_rule

        tongshi_credit_limit = 9
        if tongshi_rule != '不设限（全部计入）':
            tongshi_credit_limit = st.number_input(
                "通识课学分上限",
                min_value=1, max_value=20, value=st.session_state.get('tongshi_credit_limit', 9), step=1,
                help="超过此学分的通识课不计入保研计算"
            )
            st.session_state.tongshi_credit_limit = tongshi_credit_limit

        # 映射到内部规则码
        _rule_map = {'不设限（全部计入）': '不设限', '折算（上限N学分，择优，可拆分）': '折算',
                     '不折算（上限N学分，整门选取）': '不折算'}
        st.session_state.tongshi_rule = _rule_map[tongshi_rule]
    else:
        st.session_state.tongshi_rule = '不设限'
        tongshi_credit_limit = 9

    st.markdown("---")

    # ============ 6. 是否生成明细（对应原messagebox.askyesno） ============
    st.header("📋 第五步：明细生成设置")

    generate_details = st.checkbox(
        "✅ 生成每位学生的独立计算明细",
        value=True,
        help="每位学生一个Excel文件，包含成绩换算、重复课程处理、选修课折算等完整逻辑"
    )
    st.session_state.generate_details = generate_details

    st.markdown("---")

    # ============ 7. 开始计算（对应原计算流程） ============
    st.header("🚀 第六步：开始计算")

    if st.button("🎯 开始计算", type="primary", use_container_width=True):

        with st.spinner("正在计算成绩，请稍候..."):

            # 计算前再次同步专业配置，避免页面刷新/上传文件后calc对象丢失卓越班名单。
            if st.session_state.major_code:
                success_major, major_name = calc.set_major(st.session_state.major_code)
                if success_major:
                    st.session_state.major_name = major_name
                    st.session_state.has_excellent_class = calc.has_excellent_class
                    st.session_state.excellent_students = calc.excellent_students
                    st.session_state.current_major = calc.current_major
                    st.session_state.calc = calc

            # 注入通识课规则
            calc.tongshi_rule = st.session_state.get('tongshi_rule', '不设限')
            calc.tongshi_credit_limit = st.session_state.get('tongshi_credit_limit', 9)
            _tongshi_db = load_tongshi_db()
            if _tongshi_db is not None:
                calc.tongshi_course_names = set(_tongshi_db['课程名'].dropna().str.strip().tolist())
            else:
                calc.tongshi_course_names = set()

            # 导出汇总结果到BytesIO
            output_buffer = BytesIO()
            result_df, excellent_count, normal_count = calc.export_to_excel(
                output_buffer,
                st.session_state.semester_filter,
                st.session_state.calc_mode,
                st.session_state.get('apply_low_credit_penalty', False),
                st.session_state.get('apply_course_credit_bonus', False),
            )

            st.session_state.result_df = result_df
            st.session_state.excel_buffer = output_buffer
            st.session_state.excellent_count = excellent_count
            st.session_state.normal_count = normal_count

            # 生成学生计算明细
            if generate_details and not result_df.empty:
                with st.spinner("正在生成学生计算明细..."):
                    # 创建临时目录
                    temp_dir = tempfile.mkdtemp()
                    student_count, error_count, detail_files = calc.export_student_calculation_details(temp_dir)

                    # 打包成ZIP
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for file_path in detail_files:
                            file_name = os.path.basename(file_path)
                            with open(file_path, 'rb') as f:
                                zf.writestr(file_name, f.read())

                    st.session_state.detail_zip = zip_buffer
                    st.session_state.student_count = student_count

            st.balloons()
            st.success("✅ 成绩计算完成！")
            show_signature()

            st.markdown("---")

    # ============ 8. 显示结果（对应原print结果） ============
    if st.session_state.result_df is not None:
        result_df = st.session_state.result_df

        st.header("📊 计算结果")

        score_column = (
            '综测成绩'
            if st.session_state.get('calc_mode') == '综测' and '综测成绩' in result_df.columns
            else '平均成绩'
        )
        score_label = '平均综测成绩' if score_column == '综测成绩' else '平均分'

        # 统计信息
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("总人数", len(result_df))
        with col2:
            avg_score = result_df[score_column].mean()
            st.metric(score_label, f"{avg_score:.2f}")
        with col3:
            max_score = result_df[score_column].max()
            st.metric("最高分", f"{max_score:.2f}")
        with col4:
            min_score = result_df[score_column].min()
            st.metric("最低分", f"{min_score:.2f}")

        # 班级统计
        if '班级类型' in result_df.columns:
            st.subheader("📊 班级统计")
            class_stats = result_df.groupby('班级类型').agg({
                '学号': 'count',
                score_column: ['mean', 'max', 'min'],
                '总学分': 'mean'
            }).round(2)
            class_stats.columns = ['人数', '平均分', '最高分', '最低分', '平均学分']
            st.dataframe(class_stats, use_container_width=True)

        # 前10名（对应原print前10名）
        st.subheader("🏆 前10名学生")

        top10_columns = ['排名', '姓名', '班级类型', score_column]
        if st.session_state.get('apply_course_credit_bonus') and '课程学分加分' in result_df.columns:
            top10_columns.append('课程学分加分')
        if st.session_state.get('apply_low_credit_penalty') and '低学分扣分' in result_df.columns:
            top10_columns.append('低学分扣分')
        top10_columns.append('总学分')
        top10 = result_df.head(10)[top10_columns].copy()
        top10[score_column] = top10[score_column].apply(lambda x: f"{x:.2f}")
        if '课程学分加分' in top10.columns:
            top10['课程学分加分'] = top10['课程学分加分'].apply(lambda x: f"{x:.2f}")
        if '低学分扣分' in top10.columns:
            top10['低学分扣分'] = top10['低学分扣分'].apply(lambda x: f"{x:.2f}")
        top10['总学分'] = top10['总学分'].apply(lambda x: f"{x:.1f}")

        # 添加奖牌emoji
        def add_medal(rank):
            if rank == 1:
                return "🥇 第1名"
            elif rank == 2:
                return "🥈 第2名"
            elif rank == 3:
                return "🥉 第3名"
            else:
                return f"第{rank}名"

        top10['名次'] = top10['排名'].apply(add_medal)
        display_columns = ['名次', '姓名', '班级类型', score_column]
        if '课程学分加分' in top10.columns:
            display_columns.append('课程学分加分')
        if '低学分扣分' in top10.columns:
            display_columns.append('低学分扣分')
        display_columns.append('总学分')
        top10 = top10[display_columns]

        st.dataframe(top10, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ============ 新增：学习状态智能分析 ============
        st.header("🧠 学习状态智能分析（基于机器学习）")

        with st.expander("📊 查看学生学习状态分析", expanded=False):

            if st.button("🔍 开始分析学习状态", key="analyze_status", use_container_width=True):
                with st.spinner("正在分析学生学习状态，请稍候..."):

                    # 调用学习状态分析函数
                    status_df = calc.analyze_learning_status()

                    if status_df is not None and not status_df.empty:
                        st.session_state.status_df = status_df

                        # 显示统计信息
                        st.subheader("📈 状态分布统计")

                        # 获取所有唯一的状态值（动态获取，不硬编码）
                        all_statuses = status_df['学习状态'].value_counts()
                        total_students = len(status_df)

                        # 创建好看的卡片式布局
                        cols = st.columns(3)  # 改为3列，每行显示3个状态

                        # 定义状态对应的颜色
                        status_colors = {
                            '🌟 进步稳定型': '#90EE90',  # 浅绿色
                            '🌟 进步稳定型（高分段）': '#90EE90',
                            '🌟 进步稳定型（中分段）': '#90EE90',
                            '🟢 稳定优秀型': '#98FB98',  # 淡绿色
                            '🟡 稳定中等型': '#FFE4B5',  # 浅橙色
                            '🟠 波动进步型': '#FFA07A',  # 浅鲑鱼色
                            '🟠 波动型': '#FFA07A',
                            '🔴 波动下滑型': '#FFB6C1',  # 浅粉色
                            '🔴 退步型（需关注）': '#FFB6C1',
                            '⚫ 稳定低分型': '#D3D3D3',  # 浅灰色
                            '⚫ 稳定待提升型': '#D3D3D3',
                            '📈 进步型': '#87CEEB',  # 天蓝色
                            '📈 进步型（高分段）': '#87CEEB',
                            '📈 进步型（低分段）': '#87CEEB',
                            '📉 退步预警（高分段）': '#FFA07A',
                            '📉 退步型': '#FFA07A',
                            '✨ 优秀型': '#98FB98',
                            '🔸 待提升型': '#E6E6FA',  # 淡紫色
                            '数据不足': '#D3D3D3',
                        }

                        # 创建状态卡片
                        for i, (status, count) in enumerate(all_statuses.items()):
                            col_idx = i % 3
                            if col_idx == 0:
                                cols = st.columns(3)

                            percentage = (count / total_students) * 100
                            color = status_colors.get(status, '#F0F0F0')  # 默认浅灰色

                            with cols[col_idx]:
                                # 创建美观的卡片
                                st.markdown(f"""
                                <div style="
                                    background-color: {color};
                                    padding: 15px;
                                    border-radius: 10px;
                                    margin: 5px 0;
                                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                                    border-left: 5px solid #2c3e50;
                                ">
                                    <h4 style="margin: 0; color: #2c3e50;">{status}</h4>
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                                        <span style="font-size: 28px; font-weight: bold; color: #2c3e50;">{count}</span>
                                        <span style="font-size: 16px; color: #34495e;">{percentage:.1f}%</span>
                                    </div>
                                    <div style="width: 100%; background-color: #ecf0f1; height: 8px; border-radius: 4px; margin-top: 10px;">
                                        <div style="width: {percentage}%; background-color: #3498db; height: 8px; border-radius: 4px;"></div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                        # 添加总计卡片
                        st.markdown("---")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("📊 总人数", total_students)
                        with col2:
                            avg_score = status_df['平均成绩'].mean() if '平均成绩' in status_df.columns else 0
                            st.metric("📈 平均分", f"{avg_score:.2f}")
                        with col3:
                            status_types = len(all_statuses)
                            st.metric("🎯 状态类型", status_types)
                        with col4:
                            top_status = all_statuses.index[0] if len(all_statuses) > 0 else "无"
                            st.metric("🏆 主要状态", top_status[:10] + "..." if len(top_status) > 10 else top_status)
                        # 显示详细分析表格
                        st.subheader("📋 详细分析结果")

                        display_cols = ['学号', '姓名', '班级类型', '平均成绩', '最高成绩',
                                        '最低成绩', '标准差', '学习状态', '建议']
                        available_cols = [col for col in display_cols if col in status_df.columns]

                        # 添加颜色标记
                        def color_status(val):
                            if '进步稳定' in str(val):
                                return 'background-color: #90EE90'
                            elif '稳定优秀' in str(val):
                                return 'background-color: #98FB98'
                            elif '稳定中等' in str(val):
                                return 'background-color: #FFE4B5'
                            elif '波动进步' in str(val):
                                return 'background-color: #FFA07A'
                            elif '波动下滑' in str(val):
                                return 'background-color: #FFB6C1'
                            elif '稳定低分' in str(val):
                                return 'background-color: #D3D3D3'
                            return ''

                        styled_df = status_df[available_cols].style.applymap(
                            color_status, subset=['学习状态']
                        )

                        st.dataframe(styled_df, use_container_width=True, hide_index=True)

                        # 聚类结果
                        if '聚类簇' in status_df.columns and status_df['聚类簇'].iloc[0] != -1:
                            st.subheader("🔬 K-Means 聚类分析结果")

                            cluster_view = status_df.groupby('聚类簇').agg({
                                '学号': 'count',
                                '平均成绩': 'mean',
                                '标准差': 'mean',
                                '斜率': 'mean',
                                '聚类说明': 'first'
                            }).round(2)

                            cluster_view.columns = ['人数', '平均成绩', '平均标准差', '平均斜率', '聚类特征']
                            st.dataframe(cluster_view, use_container_width=True)

                        # 导出报告
                        status_buffer = BytesIO()
                        calc.export_learning_status_report(status_buffer)

                        st.download_button(
                            label="📥 下载学习状态分析报告",
                            data=status_buffer.getvalue(),
                            file_name=f"{calc.major_name}_学习状态分析_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            type="primary"
                        )

                    else:
                        st.warning("⚠️ 无法生成学习状态分析，可能是数据不足")

            # 单个学生查询
            st.subheader("🔎 查询单个学生学习状态")

            if st.session_state.result_df is not None and not st.session_state.result_df.empty:
                student_options = [f"{row['学号']} - {row['姓名']}"
                                   for _, row in st.session_state.result_df.head(20).iterrows()]

                selected = st.selectbox("选择学生（仅显示前20名）", options=student_options, key="student_select")

                if selected and st.button("📈 查看该生详细趋势", key="view_student", use_container_width=True):
                    student_id = selected.split(' - ')[0]

                    # 获取该生状态
                    status_df = calc.analyze_learning_status(student_id)

                    if status_df is not None and not status_df.empty:
                        st.success(f"**{selected}** 的学习状态：**{status_df.iloc[0]['学习状态']}**")

                        col1, col2 = st.columns(2)
                        with col1:
                            st.info(f"📌 状态说明：{status_df.iloc[0]['状态说明']}")
                        with col2:
                            st.info(f"💡 学习建议：{status_df.iloc[0]['建议']}")

                        # 生成趋势图
                        try:
                            fig = calc.plot_student_trend(student_id)
                            if fig:
                                st.pyplot(fig)
                            else:
                                st.warning("数据不足，无法生成趋势图")
                        except Exception as e:
                            st.warning(f"无法生成趋势图: {str(e)}")
                    else:
                        st.warning("该学生数据不足，无法分析")

        st.markdown("---")
        # ============ 新增：学业警示与预警分析 ============
        st.header("⚠️ 学业警示与成绩预警分析（随机森林）")

        with st.expander("📊 查看学业警示分析", expanded=False):

            # 添加学业警示说明
            st.markdown("""
            <div style='background-color: #fff3cd; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
                <h4 style='color: #856404; margin: 0;'>⚠️ 学业警示说明</h4>
                <p style='color: #856404; margin: 10px 0 0 0;'>
                <strong>学业警示</strong>：某学期通过学分（≥60分）不足12分<br>
                <strong>成绩预警</strong>：基于随机森林模型预测下一学期成绩<br>
                <strong>预警等级</strong>：🔴 严重预警 (&lt;60) | 🟠 中等预警 (60-70) | 🟡 关注 (70-75) | 🟢 安全 (&gt;75)
                </p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔍 开始学业警示分析", key="analyze_warning", use_container_width=True):
                with st.spinner("正在分析学业警示和构建预警模型..."):

                    warning_summary, feature_importance, prediction_df, rf_model, mse, r2 = calc.analyze_academic_warning()

                    if warning_summary is not None:
                        st.session_state.warning_summary = warning_summary
                        st.session_state.prediction_df = prediction_df

                        # 显示学业警示统计
                        st.subheader("📋 学业警示统计")

                        col1, col2, col3, col4 = st.columns(4)
                        total_students = len(warning_summary)
                        warning_students = len(warning_summary[warning_summary['学业警示次数'] > 0])
                        total_warnings = warning_summary['学业警示次数'].sum()
                        recent_warnings = len(warning_summary[warning_summary['最近有学业警示'] == True])

                        with col1:
                            st.metric("👥 总人数", total_students)
                        with col2:
                            st.metric("⚠️ 有警示史", warning_students,
                                      delta=f"{warning_students / total_students * 100:.1f}%")
                        with col3:
                            st.metric("📊 总警示次数", total_warnings)
                        with col4:
                            st.metric("🆕 最近有警示", recent_warnings)

                        # 显示详细警示记录
                        st.subheader("📝 学期通过学分警示记录")

                        # 展开详细记录
                        warning_detail = []
                        for _, row in warning_summary.iterrows():
                            for i, (sem, credit, warning) in enumerate(
                                    zip(row['学期'], row['通过学分'], row['学业警示'])):
                                if warning:  # 只显示有警示的学期
                                    warning_detail.append({
                                        '学号': row['学号'],
                                        '姓名': row['姓名'],
                                        '学期': sem,
                                        '通过学分': credit,
                                        '状态': '⚠️ 通过学分未满12分'
                                    })

                        if warning_detail:
                            warning_df = pd.DataFrame(warning_detail)
                            st.dataframe(warning_df, use_container_width=True, hide_index=True)
                        else:
                            st.success("✅ 所有学生每学期通过学分均达到12学分以上！")
                        # 显示特征重要性
                        if feature_importance is not None:
                            st.subheader("🎯 随机森林特征重要性分析")

                            col1, col2 = st.columns([1, 1])

                            with col1:
                                # 显示特征重要性表格
                                st.dataframe(feature_importance, use_container_width=True, hide_index=True)

                            with col2:
                                # 绘制特征重要性图
                                fig = calc.plot_feature_importance(feature_importance)
                                st.pyplot(fig)
                                # 模型性能
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("📈 R² 分数", f"{r2:.3f}", help="越接近1表示模型预测越准确")
                                with col2:
                                    st.metric("📉 MSE 均方误差", f"{mse:.2f}", help="值越小表示预测误差越小")

                            # 模型解释
                            st.info("""
                            **特征解释：**
                            - **历史平均成绩**：过往所有学期的平均成绩，反映整体水平
                            - **成绩波动**：成绩的标准差，反映稳定性
                            - **最近成绩**：最近一个学期的成绩，反映当前状态
                            - **平均学分**：每学期平均修读学分，反映学习负荷
                            - **学期数**：已修读学期数量，反映年级
                            - **成绩趋势**：成绩变化斜率，反映进步/退步趋势
                            """)

                        # 显示成绩预警
                        if prediction_df is not None and not prediction_df.empty:
                            st.subheader("🔮 下一学期成绩预警")

                            # 按预警等级排序
                            warning_order = {'🔴 严重预警': 0, '🟠 中等预警': 1, '🟡 关注': 2, '🟢 安全': 3}
                            prediction_df['预警等级排序'] = prediction_df['预警等级'].map(warning_order)
                            prediction_df = prediction_df.sort_values('预警等级排序').drop('预警等级排序', axis=1)

                            # 显示统计
                            col1, col2, col3, col4 = st.columns(4)
                            severe = len(prediction_df[prediction_df['预警等级'] == '🔴 严重预警'])
                            medium = len(prediction_df[prediction_df['预警等级'] == '🟠 中等预警'])
                            attention = len(prediction_df[prediction_df['预警等级'] == '🟡 关注'])
                            safe = len(prediction_df[prediction_df['预警等级'] == '🟢 安全'])

                            with col1:
                                st.metric("🔴 严重预警", severe, delta_color="inverse")
                            with col2:
                                st.metric("🟠 中等预警", medium)
                            with col3:
                                st.metric("🟡 关注", attention)
                            with col4:
                                st.metric("🟢 安全", safe)

                            # 显示详细预警表格
                            st.dataframe(
                                prediction_df[
                                    ['学号', '姓名', '当前平均分', '预测下一学期成绩', '预警等级', '趋势斜率']],
                                use_container_width=True,
                                hide_index=True
                            )

                            # 添加颜色标记
                            def color_warning(val):
                                if '严重预警' in str(val):
                                    return 'background-color: #ffcccc'
                                elif '中等预警' in str(val):
                                    return 'background-color: #ffe5cc'
                                elif '关注' in str(val):
                                    return 'background-color: #ffffcc'
                                return ''

                            styled_df = prediction_df.style.applymap(color_warning, subset=['预警等级'])
                            st.dataframe(styled_df, use_container_width=True, hide_index=True)

                            # 导出预警报告
                            warning_buffer = BytesIO()
                            with pd.ExcelWriter(warning_buffer, engine='openpyxl') as writer:
                                warning_summary.to_excel(writer, sheet_name='学业警示记录', index=False)
                                if feature_importance is not None:
                                    feature_importance.to_excel(writer, sheet_name='特征重要性', index=False)
                                prediction_df.to_excel(writer, sheet_name='成绩预警', index=False)

                            st.download_button(
                                label="📥 下载学业警示分析报告",
                                data=warning_buffer.getvalue(),
                                file_name=f"{calc.major_name}_学业警示分析_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                type="primary"
                            )

                    else:
                        st.warning("⚠️ 无法进行学业警示分析，请检查数据是否包含学期字段")
        # ============ 10. 下载结果（对应原文件保存对话框） ============
        st.header("📥 第七步：下载结果")
        st.markdown("""
        <div style='background-color: #d4edda; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
            <h4 style='color: #155724; margin: 0;'>📋 可下载文件说明</h4>
            <p style='color: #155724; margin: 10px 0 0 0;'>
            <strong>成绩汇总Excel</strong>：包含全校排名、班级统计等信息<br>
            <strong>学生明细压缩包</strong>：每位学生的详细计算过程（无加密）<br>
            <strong>学习状态分析报告</strong>：学习状态分类和聚类分析结果<br>
            <strong>学业警示分析报告</strong>：学业警示记录和成绩预警结果<br>
            <strong>🔐 评审细则</strong>：为每位学生的明细文件添加密码保护（需上传密码表）
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            # 下载汇总结果
            if st.session_state.excel_buffer:
                st.download_button(
                    label="📊 下载成绩汇总Excel",
                    data=st.session_state.excel_buffer.getvalue(),
                    file_name=f"{calc.major_name}_成绩计算结果_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary",
                    help="包含全校成绩排名、班级统计、计算配置等信息"
                )

        with col2:
            # 下载明细压缩包（无加密）
            if st.session_state.generate_details and hasattr(st.session_state, 'detail_zip'):
                st.download_button(
                    label="📁 下载学生明细压缩包",
                    data=st.session_state.detail_zip.getvalue(),
                    file_name=f"{calc.major_name}_计算明细_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    help="包含每位学生的详细成绩计算过程（无加密）"
                )

                if hasattr(st.session_state, 'student_count'):
                    st.info(f"📋 共生成 {st.session_state.student_count} 位学生的计算明细文件")

        # ============ 加密下载模块 ============
        st.markdown("---")
        st.subheader("🔐 加密下载（可选）")

        with st.expander("📦 为学生明细文件添加密码保护（让学生自己核对计算逻辑是否正确，进行校验并保护同学隐私）", expanded=False):
            st.markdown("""
            <div style='background-color: #fff3cd; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
                <h4 style='color: #856404; margin: 0;'>📌 说明</h4>
                <p style='color: #856404; margin: 10px 0 0 0;'>
                上传包含学生姓名和密码的Excel文件，系统会为每位学生的计算明细文件创建加密的评审细则压缩包。<br>
                <strong>文件格式要求：</strong>Excel文件应包含两列：第一列为学生姓名，第二列为密码。
                </p>
                <p style='color: #856404; margin: 10px 0 0 0;'>
                <strong>🔔 提示：</strong>请先下载普通明细压缩包并确认内容无误后，再使用此加密功能。
                </p>
            </div>
            """, unsafe_allow_html=True)

            # 检查是否已有明细文件
            if not (st.session_state.generate_details and hasattr(st.session_state, 'detail_zip')):
                st.warning("⚠️ 请先在上方生成学生明细压缩包，然后再使用加密功能")
            else:
                col1, col2 = st.columns([3, 1])

                with col1:
                    password_file = st.file_uploader(
                        "上传姓名-密码对应表 (Excel格式)",
                        type=['xlsx', 'xls'],
                        key="password_file",
                        help="Excel文件应包含两列：姓名、密码"
                    )

                with col2:
                    # 下载示例密码文件
                    if st.button("📥 下载示例", key="download_example_password"):
                        # 创建示例密码文件
                        example_df = pd.DataFrame({
                            '姓名': ['张三', '李四', '王五'],
                            '密码': ['123456', 'abcdef', '888888']
                        })
                        example_buffer = BytesIO()
                        example_df.to_excel(example_buffer, index=False)
                        st.download_button(
                            label="点击下载",
                            data=example_buffer.getvalue(),
                            file_name="姓名密码示例.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                if password_file is not None:
                    if st.button("🔐 生成加密压缩包", type="primary", use_container_width=True):
                        with st.spinner("正在创建加密压缩包，这可能需要一些时间..."):
                            try:
                                # 先解压原有的明细文件到临时目录
                                temp_extract_dir = tempfile.mkdtemp()
                                with zipfile.ZipFile(st.session_state.detail_zip, 'r') as zf:
                                    zf.extractall(temp_extract_dir)

                                # 创建加密压缩包
                                encrypted_buffer, success, failed = calc.create_encrypted_zip(
                                    temp_extract_dir,
                                    password_file
                                )

                                # 清理临时目录
                                import shutil
                                shutil.rmtree(temp_extract_dir)

                                if encrypted_buffer:
                                    st.session_state.encrypted_zip = encrypted_buffer
                                    st.session_state.encrypt_success = success
                                    st.session_state.encrypt_failed = failed

                                    st.success(f"✅ 加密完成！成功：{success} 个，失败：{len(failed)} 个")

                                    if failed:
                                        with st.expander("📋 查看失败文件详情"):
                                            for f in failed:
                                                st.write(f"- {f}")

                                    # 显示7-Zip检测提示
                                    if calc._find_7zip_executable():
                                        st.info("✅ 使用7-Zip AES-256加密，安全性高")
                                    else:
                                        st.warning("⚠️ 未检测到7-Zip，使用基础加密，建议安装7-Zip获得更好的加密效果")

                            except Exception as e:
                                st.error(f"❌ 加密过程出错：{str(e)}")

                # 显示下载按钮
                if hasattr(st.session_state, 'encrypted_zip'):
                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    with col2:
                        st.download_button(
                            label="📥 下载评审细则包",
                            data=st.session_state.encrypted_zip.getvalue(),
                            file_name=f"{calc.major_name}_评审细则_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                            mime="application/zip",
                            use_container_width=True,
                            type="primary"
                        )

                    # 显示统计信息
                    if hasattr(st.session_state, 'encrypt_success'):
                        st.success(f"✅ 加密包包含 {st.session_state.encrypt_success} 个加密文件")

        # ============ 学习状态分析报告下载 ============
        if hasattr(st.session_state, 'status_df'):
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                status_buffer = BytesIO()
                calc.export_learning_status_report(status_buffer)
                st.download_button(
                    label="📊 下载学习状态分析报告",
                    data=status_buffer.getvalue(),
                    file_name=f"{calc.major_name}_学习状态分析_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="secondary"
                )

        # ============ 学业警示分析报告下载 ============
        if hasattr(st.session_state, 'warning_summary'):
            with col2:
                warning_buffer = BytesIO()
                with pd.ExcelWriter(warning_buffer, engine='openpyxl') as writer:
                    st.session_state.warning_summary.to_excel(writer, sheet_name='学业警示记录', index=False)
                    if hasattr(st.session_state, 'prediction_df'):
                        st.session_state.prediction_df.to_excel(writer, sheet_name='成绩预警', index=False)
                st.download_button(
                    label="⚠️ 下载学业警示分析报告",
                    data=warning_buffer.getvalue(),
                    file_name=f"{calc.major_name}_学业警示分析_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="secondary"
                )

        # ============ 页脚 ============
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #7f8c8d; padding: 20px;'>
            <p>© 2024 中国海洋大学 海洋地球科学学院 潘高 | 版本 2.0</p>
            <p style='font-size: 12px;'>本系统仅供中国海洋大学使用，数据仅供参考</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == '__main__':
    main()
