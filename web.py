import streamlit as st
import pandas as pd
import numpy as np
import datetime
import os
import io
from io import BytesIO
import zipfile
import base64

# ============ 页面配置 ============
st.set_page_config(
    page_title="2023级成绩测算系统",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============ 专业配置类（完全保留您的代码） ============
class MajorConfig:
    """专业配置类 - 存储各专业的选修课清单和学分要求"""

    def __init__(self):
        # 23勘工
        self.major_23kg = {
            '专业名称': '23勘工',
            '专业代码': '23kg',
            '有卓越班': True,
            '卓越班级学号集': {
                '23040031037', '23040031038', '23040031016', '23040031068',
                '23040031051', '23040031023', '23040031008', '23040031050',
                '23040031049', '23040031036', '23040031024', '23040031069',
                '23040031061', '23040031035', '23040031009'
            },
            '学分要求': {
                '卓越': {
                    '学科基础课程': 1.0,
                    '专业知识课程': 1.0,
                    '工作技能课程': 0.0
                },
                '普通': {
                    '学科基础课程': 4.0,
                    '专业知识课程': 4.0,
                    '工作技能课程': 2.0
                }
            },
            '选修课列表': {
                '学科基础课程': [
                    '科学计算语言与编程', 'Python程序设计与实践', '海洋地质学概论',
                    '电工电子学', '数据结构', '计算机图形学', '地理信息系统',
                    '并行编程原理与程序设计', '专业英语与科技写作', '岩石物理学基础'
                ],
                '专业知识课程': [
                    '地球物理测井', '油气地质学', '工程与环境地球物理',
                    '地球物理大数据与人工智能', '海洋地球物理探测技术',
                    '计算地球物理原理', '国际课程-三维地震勘探', '非常规油气勘探开发',
                    '人工智能资料处理与解释', '海洋电磁学', '地学软件工程',
                    '地球物理前沿讲座'
                ],
                '工作技能课程': [
                    '地球物理技能训练', '地球物理软件设计实习', '工程实践'
                ]
            }
        }

        # 23地质
        self.major_23dz = {
            '专业名称': '23地质',
            '专业代码': '23dz',
            '有卓越班': False,
            '学分要求': {
                '学科基础课程': 6.0,
                '专业知识课程': 7.0,
                '工作技能课程': 4.0
            },
            '选修课列表': {
                '学科基础课程': [
                    '自然地理学', '地理信息系统', '线性代数', '物理化学',
                    '物理化学实验', '工程岩土学'
                ],
                '专业知识课程': [
                    '第四纪地质与环境', '海岸动力地貌', '海洋微体古生物学',
                    '层序地层学', '遥感地质学', '油气地质学', '国际课程周',
                    '中国区域大地构造', '海底岩石学', '沉积环境与沉积相',
                    '海洋工程地质', '海底矿产资源', '海洋地球化学',
                    '海洋工程环境', '海洋地质学前沿', '环境地质学',
                    '地球系统科学'
                ],
                '工作技能课程': [
                    '地质旅行I', '地质旅行II', '岩矿鉴定',
                    '地学大数据分析与人工智能', '地学建模与可视化',
                    '地质旅行Ⅲ', '现代分析测试方法', '地质学研究方法新进展'
                ]
            }
        }

        # 23地信
        self.major_23dx = {
            '专业名称': '23地信',
            '专业代码': '23dx',
            '有卓越班': False,
            '学分要求': {
                '学科基础课程': 6.0,
                '专业知识课程': 6.0,
                '工作技能课程': 0.0
            },
            '选修课列表': {
                '学科基础课程': [
                    'Matlab 语言与应用', '信号分析与处理', 'Python 程序设计与实践',
                    '误差理论与测量平差基础', '计算机图形学',
                    'GIS 二次开发', 'AutoCAD 制图与应用', '专业英语'
                ],
                '专业知识课程': [
                    'GNSS 测量与应用', '国际课程-基于机器学习的地学数据分析导论',
                    '海底探测数据处理与解译', '海洋工程环境', '海洋工程地质',
                    '海洋遥感概论', '计算地球物理原理', '专业前沿研讨',
                    '海洋沉积物分析', '地球系统科学'
                ],
                '工作技能课程': [
                    '地质旅行I', '地质旅行Ⅱ', '地质旅行Ⅲ'
                ]
            }
        }

    def get_major(self, major_code):
        """根据专业代码获取专业配置"""
        if major_code == '23kg':
            return self.major_23kg
        elif major_code == '23dz':
            return self.major_23dz
        elif major_code == '23dx':
            return self.major_23dx
        else:
            return None

    def get_all_majors(self):
        """获取所有专业列表"""
        return [
            {'code': '23kg', 'name': '23勘工（有卓越班）', 'color': '#3498db'},
            {'code': '23dz', 'name': '23地质（统一班级）', 'color': '#2ecc71'},
            {'code': '23dx', 'name': '23地信（统一班级）', 'color': '#e67e22'}
        ]


# ============ 成绩计算器类（精简Web版） ============
class StudentGradeCalculator:
    """学生成绩计算器 - Web适配版"""

    def __init__(self, df, major_config):
        self.df = df
        self.major_config = major_config
        self.current_major = None
        self.major_name = None
        self.has_excellent_class = False
        self.excellent_students = {}
        self.column_mapping = {}
        self.calc_mode = '保研'

        # 成绩映射
        self.grade_map = {
            '优': 90, '优秀': 90,
            '良': 80, '良好': 80,
            '中': 70, '中等': 70,
            '合格': 60, '及格': 60,
            '不合格': 0, '不及格': 0,
            '通过': 85,
            '不通过': 0
        }

    def auto_detect_columns(self):
        """自动识别列名"""
        columns = self.df.columns.tolist()

        # 关键词映射
        field_keywords = {
            '学号': ['学号', 'student id', 'student_id', 'id', '考生号'],
            '姓名': ['姓名', 'name', '学生姓名'],
            '学分': ['学分', 'credit', 'credits'],
            '总成绩': ['总成绩', '成绩', 'score', 'grade', '总评成绩', 'final score'],
            '取得方式': ['取得方式', '修读方式', 'exam type', 'acquire', '考试类型'],
            '成绩标志': ['成绩标志', '标志', 'flag', 'status', '考试状态'],
            '学年学期': ['学年学期', '学期', '学年', 'semester', 'term', 'academic year'],
            '课程名称': ['课程名称', '课程名', 'course', 'course name'],
            '课程编号': ['课程编号', '课程代码', 'course code', 'course_id']
        }

        for field, keywords in field_keywords.items():
            for col in columns:
                col_str = str(col).lower()
                for kw in keywords:
                    if kw.lower() in col_str:
                        self.column_mapping[field] = col
                        break
                if field in self.column_mapping:
                    break

        # 检查必要字段
        required = ['学号', '姓名', '学分', '总成绩']
        missing = [f for f in required if f not in self.column_mapping]
        return len(missing) == 0, missing

    def set_major(self, major_code):
        """设置专业"""
        major_config = self.major_config.get_major(major_code)
        if not major_config:
            return False

        self.current_major = major_config
        self.major_name = major_config['专业名称']
        self.has_excellent_class = major_config['有卓越班']

        if self.has_excellent_class:
            self.excellent_students = major_config.get('卓越班级学号集', {})

        return True

    def _get_student_id(self, row):
        """获取学号"""
        if '学号' not in self.column_mapping:
            return None
        id_col = self.column_mapping['学号']
        if id_col not in row or pd.isna(row[id_col]):
            return None
        val = row[id_col]
        if isinstance(val, float):
            if val.is_integer():
                return str(int(val))
            return str(val)
        return str(val).strip()

    def _get_credit(self, row):
        """获取学分"""
        if '学分' not in self.column_mapping:
            return 0
        credit_col = self.column_mapping['学分']
        if credit_col not in row or pd.isna(row[credit_col]):
            return 0
        try:
            return float(row[credit_col])
        except:
            return 0

    def _convert_score(self, row):
        """成绩换算"""
        if '总成绩' not in self.column_mapping:
            return None

        score_col = self.column_mapping['总成绩']
        if score_col not in row or pd.isna(row[score_col]):
            return None

        score_raw = row[score_col]

        # 获取取得方式
        exam_type = ''
        if '取得方式' in self.column_mapping:
            acquire_col = self.column_mapping['取得方式']
            if acquire_col in row and pd.notna(row[acquire_col]):
                exam_type = str(row[acquire_col])

        # 获取成绩标志
        score_flag = ''
        if '成绩标志' in self.column_mapping:
            flag_col = self.column_mapping['成绩标志']
            if flag_col in row and pd.notna(row[flag_col]):
                score_flag = str(row[flag_col])

        # 无效成绩
        if '旷考' in score_flag or '缺考' in score_flag:
            return None
        if '缓考' in score_flag and '缓考取得' not in exam_type:
            return None

        # 补考成绩
        if '补考取得' in exam_type or ('补考' in exam_type and '初修' not in exam_type):
            try:
                s = float(score_raw)
                return 60.0 if s >= 60 else s
            except:
                return None

        # 等级制换算
        if isinstance(score_raw, str):
            score_str = score_raw.strip()
            if score_str in self.grade_map:
                return self.grade_map[score_str]
            for key, value in self.grade_map.items():
                if key in score_str:
                    return value
            try:
                return float(score_str)
            except:
                return None

        try:
            return float(score_raw)
        except:
            return None

    def _get_student_class(self, student_id):
        """判断学生班级类型"""
        if student_id in self.excellent_students:
            return '卓越'
        return '普通'

    def _handle_duplicate_courses(self, df):
        """处理重复课程"""
        has_course_id = '课程编号' in self.column_mapping
        has_course_name = '课程名称' in self.column_mapping

        if not (has_course_id or has_course_name):
            return set()

        # 构建课程标识
        df['_课程标识'] = ''
        if has_course_id:
            id_col = self.column_mapping['课程编号']
            df['_课程标识'] += df[id_col].astype(str) + '_'
        if has_course_name:
            name_col = self.column_mapping['课程名称']
            df['_课程标识'] += df[name_col].astype(str)

        acquire_col = self.column_mapping.get('取得方式')
        courses_to_drop = set()

        for _, course_group in df.groupby('_课程标识'):
            if len(course_group) > 1:
                has_makeup = False
                makeup_idx = None
                makeup_score = None
                original_idx = None

                for idx, row in course_group.iterrows():
                    exam_type = ''
                    if acquire_col and acquire_col in row and pd.notna(row[acquire_col]):
                        exam_type = str(row[acquire_col])

                    is_makeup = '补考' in exam_type and '初修' not in exam_type

                    if is_makeup:
                        has_makeup = True
                        makeup_idx = idx
                        makeup_score = row['_计算成绩']
                    else:
                        original_idx = idx

                if has_makeup and makeup_idx is not None:
                    if makeup_score >= 60:
                        df.loc[makeup_idx, '_计算成绩'] = 60.0
                        if original_idx is not None:
                            courses_to_drop.add(original_idx)
                    else:
                        courses_to_drop.add(makeup_idx)

        if courses_to_drop:
            df.drop(index=courses_to_drop, inplace=True)

        return courses_to_drop

    def classify_course(self, row):
        """课程分类"""
        course_name = ''
        course_code = ''

        if '课程名称' in self.column_mapping:
            name_col = self.column_mapping['课程名称']
            if name_col in row and pd.notna(row[name_col]):
                course_name = str(row[name_col])

        if '课程编号' in self.column_mapping:
            code_col = self.column_mapping['课程编号']
            if code_col in row and pd.notna(row[code_col]):
                course_code = str(row[code_col])

        if not self.current_major:
            return '必修课程'

        elective_courses = self.current_major.get('选修课列表', {})

        for course_type, courses in elective_courses.items():
            for kw in courses:
                if kw in course_name or kw in course_code:
                    return course_type

        return '必修课程'

    def _get_credit_requirements(self, student_class):
        """获取学分要求"""
        if not self.current_major:
            return {}

        if self.has_excellent_class:
            return self.current_major['学分要求'].get(student_class, {})
        else:
            return self.current_major['学分要求']

    def format_significant_digits(self, value, digits=5):
        """格式化有效数字"""
        if value is None:
            return None
        try:
            value = float(value)
            return float(f"{value:.{digits}g}")
        except:
            return value

    def calculate_all_students(self, semester_filter=None, calc_mode='保研'):
        """计算所有学生成绩"""
        self.calc_mode = calc_mode
        df_calc = self.df.copy()

        # 获取学号
        df_calc['_学号'] = df_calc.apply(self._get_student_id, axis=1)
        df_calc = df_calc.dropna(subset=['_学号'])

        if df_calc.empty:
            return pd.DataFrame()

        # 获取姓名
        if '姓名' in self.column_mapping:
            name_col = self.column_mapping['姓名']
            df_calc['_姓名'] = df_calc[name_col].astype(str).str.strip()
        else:
            df_calc['_姓名'] = ''

        results = []

        for student_id, student_df in df_calc.groupby('_学号'):
            df = student_df.copy()

            # 成绩换算
            df['_计算成绩'] = df.apply(self._convert_score, axis=1)
            df['_学分'] = df.apply(self._get_credit, axis=1)

            df = df.dropna(subset=['_计算成绩'])
            df = df[df['_计算成绩'] > 0]

            if df.empty:
                continue

            # 处理重复课程
            self._handle_duplicate_courses(df)

            # 学期筛选
            if semester_filter and '学年学期' in self.column_mapping:
                sem_col = self.column_mapping['学年学期']
                if sem_col in df.columns:
                    df = df[df[sem_col].isin(semester_filter)]
                    if df.empty:
                        continue

            # 课程分类
            df['_课程类别'] = df.apply(self.classify_course, axis=1)

            student_class = self._get_student_class(student_id)

            # 保研模式：选修课折算
            if calc_mode == '保研':
                credit_req = self._get_credit_requirements(student_class)
                processed_list = []

                for course_type, group in df.groupby('_课程类别'):
                    if course_type in credit_req:
                        required = credit_req[course_type]
                        if required <= 0:
                            continue

                        group = group.sort_values('_计算成绩', ascending=False)
                        selected = []
                        total = 0

                        for _, row in group.iterrows():
                            if total < required:
                                credit = row['_学分']
                                if total + credit <= required:
                                    selected.append(row)
                                    total += credit
                                else:
                                    remaining = required - total
                                    new_row = row.copy()
                                    new_row['_学分'] = remaining
                                    selected.append(new_row)
                                    total = required
                                    break
                            else:
                                break

                        if selected:
                            processed_list.append(pd.DataFrame(selected))
                    else:
                        processed_list.append(group)

                if processed_list:
                    df = pd.concat(processed_list, ignore_index=True)

            # 计算加权平均
            total_weighted = (df['_计算成绩'] * df['_学分']).sum()
            total_credits = df['_学分'].sum()

            if total_credits == 0:
                continue

            avg_score = total_weighted / total_credits

            results.append({
                '学号': student_id,
                '姓名': df.iloc[0]['_姓名'] if '_姓名' in df.iloc[0] else '',
                '班级类型': student_class,
                '平均成绩': self.format_significant_digits(avg_score, 5),
                '总学分': self.format_significant_digits(total_credits, 5),
                '课程门数': len(df)
            })

        result_df = pd.DataFrame(results)

        if not result_df.empty:
            result_df = result_df.sort_values('平均成绩', ascending=False).reset_index(drop=True)
            result_df['排名'] = result_df['平均成绩'].rank(method='min', ascending=False).astype(int)

            if '班级类型' in result_df.columns:
                result_df['班级内排名'] = result_df.groupby('班级类型')['平均成绩'] \
                    .rank(method='min', ascending=False).astype(int)

        return result_df


# ============ Streamlit界面 ============

def main():
    """Streamlit主界面"""

    # 侧边栏 - 系统信息
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/student-male--v1.png", width=80)
        st.title("🎓 成绩测算系统")
        st.markdown("---")
        st.markdown("### 📋 系统特色")
        st.markdown("✅ 自动识别表头/列名")
        st.markdown("✅ 支持3个专业培养方案")
        st.markdown("✅ 卓越/普通班自动区分")
        st.markdown("✅ 保研/综测双模式")
        st.markdown("✅ 补考成绩智能处理")
        st.markdown("✅ 选修课择优折算")
        st.markdown("---")
        st.markdown("### 👨‍🏫 适用对象")
        st.markdown("- 23勘工（有卓越班）")
        st.markdown("- 23地质（统一班级）")
        st.markdown("- 23地信（统一班级）")
        st.markdown("---")
        st.markdown("### 📌 使用说明")
        st.markdown("1. 上传成绩表Excel")
        st.markdown("2. 选择专业和计算模式")
        st.markdown("3. 可选学期筛选")
        st.markdown("4. 下载计算结果")

    # 主界面
    st.title("📊 2023级学生成绩测算系统")
    st.markdown("---")

    # 初始化专业配置
    major_config = MajorConfig()

    # 步骤1：上传文件
    st.header("📁 1. 上传成绩表")
    uploaded_file = st.file_uploader(
        "选择Excel成绩表文件",
        type=['xlsx', 'xls'],
        help="支持任意格式的成绩表，系统会自动识别表头和列名"
    )

    if uploaded_file is not None:
        try:
            # 读取Excel
            df = pd.read_excel(uploaded_file)
            st.success(f"✅ 文件上传成功！共 {len(df)} 条记录")

            # 显示数据预览
            with st.expander("🔍 查看数据预览", expanded=True):
                st.dataframe(df.head(5), use_container_width=True)

            # 初始化计算器
            calculator = StudentGradeCalculator(df, major_config)

            # 自动识别列名
            success, missing = calculator.auto_detect_columns()

            if not success:
                st.error(f"❌ 无法自动识别必要字段，缺失: {missing}")
                st.stop()

            # 显示识别的列名
            with st.expander("📋 已识别的字段"):
                col_df = pd.DataFrame(
                    list(calculator.column_mapping.items()),
                    columns=['字段', '对应列名']
                )
                st.dataframe(col_df, use_container_width=True)

            st.markdown("---")

            # 步骤2：专业选择
            st.header("🎓 2. 选择专业")

            col1, col2, col3 = st.columns(3)

            with col1:
                kg_selected = st.button(
                    "📚 23勘工（有卓越班）",
                    use_container_width=True,
                    type="primary"
                )

            with col2:
                dz_selected = st.button(
                    "🗺️ 23地质（统一班级）",
                    use_container_width=True
                )

            with col3:
                dx_selected = st.button(
                    "🛰️ 23地信（统一班级）",
                    use_container_width=True
                )

            major_code = None
            if kg_selected:
                major_code = '23kg'
            elif dz_selected:
                major_code = '23dz'
            elif dx_selected:
                major_code = '23dx'

            if major_code:
                calculator.set_major(major_code)
                st.success(f"✅ 已选择专业: {calculator.major_name}")

                # 显示专业信息
                info_col1, info_col2 = st.columns(2)
                with info_col1:
                    st.info(f"🏫 专业名称：{calculator.major_name}")
                with info_col2:
                    if calculator.has_excellent_class:
                        st.info(f"🎓 卓越班人数：{len(calculator.excellent_students)} 人")
                    else:
                        st.info(f"📚 统一班级，无卓越班")

                st.markdown("---")

                # 步骤3：计算模式选择
                st.header("⚙️ 3. 选择计算模式")

                mode_col1, mode_col2 = st.columns(2)

                with mode_col1:
                    baoyan_mode = st.checkbox(
                        "🎯 保研模式",
                        value=True,
                        help="按选修课学分要求择优折算"
                    )

                with mode_col2:
                    cece_mode = st.checkbox(
                        "📊 综测模式",
                        value=False,
                        help="所有课程全部计入"
                    )

                calc_mode = '保研' if baoyan_mode else '综测'

                # 显示学分要求
                with st.expander("📖 查看学分要求"):
                    if calculator.has_excellent_class:
                        tab1, tab2 = st.tabs(["卓越班", "普通班"])

                        with tab1:
                            req_df = pd.DataFrame(
                                list(calculator.current_major['学分要求']['卓越'].items()),
                                columns=['课程类别', '要求学分']
                            )
                            st.dataframe(req_df, use_container_width=True)

                        with tab2:
                            req_df = pd.DataFrame(
                                list(calculator.current_major['学分要求']['普通'].items()),
                                columns=['课程类别', '要求学分']
                            )
                            st.dataframe(req_df, use_container_width=True)
                    else:
                        req_df = pd.DataFrame(
                            list(calculator.current_major['学分要求'].items()),
                            columns=['课程类别', '要求学分']
                        )
                        st.dataframe(req_df, use_container_width=True)

                st.markdown("---")

                # 步骤4：学期筛选（可选）
                st.header("📅 4. 学期筛选（可选）")

                semesters = []
                if '学年学期' in calculator.column_mapping:
                    sem_col = calculator.column_mapping['学年学期']
                    if sem_col in df.columns:
                        semesters = df[sem_col].dropna().unique().tolist()
                        semesters = sorted([str(s) for s in semesters])

                semester_filter = None
                if semesters:
                    use_semester_filter = st.checkbox("只计算特定学期")
                    if use_semester_filter:
                        selected_semesters = st.multiselect(
                            "选择要计算的学期",
                            options=semesters,
                            default=semesters[:1] if semesters else []
                        )
                        semester_filter = selected_semesters if selected_semesters else None

                st.markdown("---")

                # 步骤5：开始计算
                st.header("🚀 5. 开始计算")

                if st.button(
                        "🎯 生成成绩排名",
                        type="primary",
                        use_container_width=True
                ):
                    with st.spinner("正在计算成绩，请稍候..."):
                        # 执行计算
                        result_df = calculator.calculate_all_students(
                            semester_filter,
                            calc_mode
                        )

                        if not result_df.empty:
                            # 显示结果摘要
                            st.success("✅ 计算完成！")

                            # 统计信息
                            col1, col2, col3, col4 = st.columns(4)

                            with col1:
                                st.metric("总人数", len(result_df))

                            with col2:
                                avg_score = result_df['平均成绩'].mean()
                                st.metric("平均分", f"{avg_score:.2f}")

                            with col3:
                                max_score = result_df['平均成绩'].max()
                                st.metric("最高分", f"{max_score:.2f}")

                            with col4:
                                min_score = result_df['平均成绩'].min()
                                st.metric("最低分", f"{min_score:.2f}")

                            # 班级统计
                            if '班级类型' in result_df.columns:
                                st.subheader("📊 班级统计")
                                class_stats = result_df.groupby('班级类型').agg({
                                    '学号': 'count',
                                    '平均成绩': ['mean', 'max', 'min']
                                }).round(2)
                                class_stats.columns = ['人数', '平均分', '最高分', '最低分']
                                st.dataframe(class_stats, use_container_width=True)

                            # 显示前10名
                            st.subheader("🏆 前10名学生")
                            top10 = result_df.head(10)[['排名', '姓名', '班级类型', '平均成绩', '总学分']]
                            st.dataframe(top10, use_container_width=True)

                            # 下载按钮
                            st.subheader("📥 下载结果")

                            # 生成Excel文件
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                result_df.to_excel(writer, sheet_name='全校成绩排名', index=False)

                                if '班级类型' in result_df.columns:
                                    for class_type in ['卓越', '普通']:
                                        class_df = result_df[result_df['班级类型'] == class_type].copy()
                                        if not class_df.empty:
                                            class_df = class_df.sort_values('平均成绩', ascending=False)
                                            class_df['班级排名'] = range(1, len(class_df) + 1)
                                            class_df.to_excel(writer, sheet_name=f'{class_type}班级', index=False)

                                # 配置信息
                                config = pd.DataFrame([
                                    ['专业', calculator.major_name],
                                    ['计算模式', calc_mode],
                                    ['计算时间', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                                    ['总人数', len(result_df)]
                                ], columns=['配置项', '值'])
                                config.to_excel(writer, sheet_name='计算配置', index=False)

                            output.seek(0)

                            st.download_button(
                                label="📥 下载Excel成绩排名",
                                data=output,
                                file_name=f"{calculator.major_name}_成绩排名_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )

                        else:
                            st.error("❌ 计算失败，请检查数据格式")

        except Exception as e:
            st.error(f"❌ 处理文件时出错: {str(e)}")
            import traceback
            st.exception(traceback.format_exc())
    else:
        # 显示欢迎界面
        st.info("👆 请上传成绩表Excel文件开始使用")

        # 示例图片或说明
        st.markdown("""
        ### 📋 支持的成绩表格式

        **系统会自动识别以下字段：**
        - ✅ 学号、姓名
        - ✅ 课程名称、课程编号
        - ✅ 学分、总成绩
        - ✅ 取得方式（初修/补考）
        - ✅ 成绩标志（旷考/缺考/缓考）
        - ✅ 学年学期

        **支持任意列名、任意顺序，无需预处理！**
        """)


if __name__ == '__main__':
    main()