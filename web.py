import streamlit as st
import pandas as pd
import numpy as np
import datetime
import os
import tempfile
import zipfile
from io import BytesIO


# ============ 专业配置类（完全不变） ============
class MajorConfig:
    """专业配置类 - 存储各专业的选修课清单和学分要求"""

    def __init__(self):
        # ============ 23勘工（原专业，保留卓越/普通分班） ============
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

        # ============ 23地质 ============
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

        # ============ 23地信 ============
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
        if major_code == '23kg':
            return self.major_23kg
        elif major_code == '23dz':
            return self.major_23dz
        elif major_code == '23dx':
            return self.major_23dx
        else:
            return None

    def get_all_majors(self):
        return [
            {'code': '23kg', 'name': '23勘工（有卓越班）'},
            {'code': '23dz', 'name': '23地质（统一班级）'},
            {'code': '23dx', 'name': '23地信（统一班级）'}
        ]


# ============ 成绩计算器类（完全不变，只改文件读取方式） ============
class StudentGradeCalculator:
    """
    学生成绩计算器 —— 2023级成绩测算要求
    核心功能：自动检测表头行 + 自动识别列名
    Streamlit版 - 完全保留原逻辑
    """

    def __init__(self, file_path=None, df=None):
        """支持两种初始化：文件路径或DataFrame"""
        self.file_path = file_path
        self.df = df
        self.raw_data = None
        self.header_row = 0
        self.column_mapping = {}
        self.calc_mode = '保研'

        # 专业配置
        self.major_config = MajorConfig()
        self.current_major = None
        self.major_name = None
        self.has_excellent_class = False
        self.excellent_students = {}

        # 字段关键词（完全不变）
        self.required_fields = {
            '学号': ['学号', 'student id', 'student_id', 'id', '学号', '考生号'],
            '姓名': ['姓名', 'name', '学生姓名'],
            '学分': ['学分', 'credit', 'credits'],
            '总成绩': ['总成绩', '成绩', 'score', 'grade', '总评成绩', 'final score'],
            '取得方式': ['取得方式', '修读方式', 'exam type', 'acquire', '考试类型'],
            '成绩标志': ['成绩标志', '标志', 'flag', 'status', '考试状态'],
            '学年学期': ['学年学期', '学期', '学年', 'semester', 'term', 'academic year'],
            '课程名称': ['课程名称', '课程名', 'course', 'course name'],
            '课程编号': ['课程编号', '课程代码', 'course code', 'course_id'],
            '开课单位': ['开课单位', '开课院系', '开课系', 'department', 'dept'],
            '绩点': ['绩点', 'gpa', 'grade point']
        }

        # 成绩映射（完全不变）
        self.grade_map = {
            '优': 90, '优秀': 90,
            '良': 80, '良好': 80,
            '中': 70, '中等': 70,
            '合格': 60, '及格': 60,
            '不合格': 0, '不及格': 0,
            '通过': 85,
            '不通过': 0
        }

        self.plan_credits = {}
        self.class_credit_requirements = {
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
        }

        # 计算明细存储
        self.calculation_details = {}
        self.duplicate_courses_record = {}

    # ============ 核心检测函数（完全不变） ============
    def detect_header_row(self):
        """
        核心功能：自动检测表头在第几行
        策略：
        1. 先读取前20行，不设表头
        2. 找包含最多关键词的行（学号、姓名、课程、成绩等）
        3. 该行就是表头行
        """
        st.write("\n🔍 正在自动检测表头行...")

        # 关键词权重表（完全不变）
        keywords = {
            '学号': 10, 'student': 8, 'id': 5,
            '姓名': 10, 'name': 8,
            '课程': 8, 'course': 6,
            '成绩': 8, 'score': 6, 'grade': 6,
            '学分': 8, 'credit': 6,
            '学期': 5, 'semester': 4,
            '院系': 3, 'department': 3,
            '教师': 2, 'teacher': 2
        }

        best_score = 0
        best_row = 0

        # 遍历前20行，计算每行的关键词得分
        for idx, row in self.raw_data.iterrows():
            row_score = 0
            row_text = ' '.join([str(cell).lower() for cell in row.values if pd.notna(cell)])

            for keyword, score in keywords.items():
                if keyword.lower() in row_text:
                    row_score += score

            # 额外检查：这一行有多少个非空单元格
            non_empty = row.count()
            row_score += non_empty * 0.5

            st.write(f"   第{idx + 1}行: 得分 {row_score:.1f} - {row_text[:50]}...")

            if row_score > best_score:
                best_score = row_score
                best_row = idx

        self.header_row = best_row
        st.write(f"\n✅ 检测到表头在第 {self.header_row + 1} 行")
        st.write(f"   表头内容: {list(self.raw_data.iloc[self.header_row].values)}")

        return self.header_row

    # ============ 自动识别列名（完全不变） ============
    def auto_detect_columns(self):
        """自动识别列名 - 基于检测到的表头行"""
        columns = self.df.columns.tolist()

        st.write(f"\n🔍 正在自动识别列名...")
        st.write(f"📋 表头共 {len(columns)} 列:")
        for i, col in enumerate(columns, 1):
            st.write(f"  {i:2d}. '{col}'")

        # 列名模糊匹配
        col_lower = {col: str(col).lower() for col in columns}

        for field, keywords in self.required_fields.items():
            found = False
            for col in columns:
                col_low = col_lower[col]
                for kw in keywords:
                    if kw.lower() in col_low:
                        self.column_mapping[field] = col
                        st.write(f"  ✅ {field:10} → '{col}'")
                        found = True
                        break
                if found:
                    break
            if not found:
                st.write(f"  ⚠️ {field:10} → 未找到匹配列")

        # 必须字段检查
        required = ['学号', '姓名', '学分', '总成绩']
        missing = [f for f in required if f not in self.column_mapping]
        if missing:
            st.write(f"\n❌ 错误: 缺少必要字段: {missing}")
            return False, missing

        st.write(f"\n✅ 列名识别完成，共识别 {len(self.column_mapping)} 个字段")
        return True, missing

    # ============ 设置专业（完全不变） ============
    def set_major(self, major_code):
        """设置专业（根据用户选择）"""
        major_config = self.major_config.get_major(major_code)
        if not major_config:
            st.write(f"❌ 无效的专业代码: {major_code}")
            return False

        self.current_major = major_config
        self.major_name = major_config['专业名称']
        self.has_excellent_class = major_config['有卓越班']

        if self.has_excellent_class:
            self.excellent_students = major_config.get('卓越班级学号集', {})
            st.write(f"✅ 已设置专业: {self.major_name}")
            st.write(f"   📋 卓越班学生: {len(self.excellent_students)} 人")
        else:
            self.excellent_students = {}
            st.write(f"✅ 已设置专业: {self.major_name}（无卓越班）")

        return True

    # ============ 成绩换算（完全不变） ============
    def _convert_score(self, row):
        """成绩换算"""
        score_col = self.column_mapping.get('总成绩')
        if not score_col or pd.isna(row[score_col]):
            return None

        score_raw = row[score_col]
        exam_type = ''
        if '取得方式' in self.column_mapping:
            acquire_col = self.column_mapping['取得方式']
            exam_type = str(row[acquire_col]) if pd.notna(row[acquire_col]) else ''

        score_flag = ''
        if '成绩标志' in self.column_mapping:
            flag_col = self.column_mapping['成绩标志']
            score_flag = str(row[flag_col]) if pd.notna(row[flag_col]) else ''

        if '旷考' in score_flag or '缺考' in score_flag:
            return None
        if '缓考' in score_flag and '缓考取得' not in exam_type:
            return None

        if '补考取得' in exam_type or ('补考' in exam_type and '初修' not in exam_type):
            try:
                s = float(score_raw)
                return 60.0 if s >= 60 else s
            except:
                return None

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

    # ============ 获取学号（完全不变） ============
    def _get_student_id(self, row):
        """获取学号"""
        id_col = self.column_mapping.get('学号')
        if not id_col or pd.isna(row[id_col]):
            return None
        val = row[id_col]
        if isinstance(val, float):
            if val.is_integer():
                return str(int(val))
            return str(val)
        return str(val).strip()

    # ============ 获取学分（完全不变） ============
    def _get_credit(self, row):
        """获取学分"""
        credit_col = self.column_mapping.get('学分')
        if not credit_col or pd.isna(row[credit_col]):
            return 0
        try:
            return float(row[credit_col])
        except:
            return 0

    # ============ 获取学生班级（完全不变） ============
    def _get_student_class(self, student_id):
        """判断学生班级类型：卓越 或 普通"""
        if student_id in self.excellent_students:
            return '卓越'
        else:
            return '普通'

    # ============ 格式化有效数字（完全不变） ============
    def format_significant_digits(self, value, digits=5):
        """格式化数值为指定位数的有效数字"""
        if value is None:
            return None
        try:
            value = float(value)
            formatted = f"{value:.{digits}g}"
            if '.' not in formatted:
                if len(formatted) < digits:
                    decimal_zeros = digits - len(formatted)
                    return float(f"{formatted}.{'0' * decimal_zeros}")
                else:
                    return float(f"{formatted}.0")
            else:
                integer_part, decimal_part = formatted.split('.')
                total_digits = len(integer_part) + len(decimal_part)
                if total_digits < digits:
                    need_zeros = digits - total_digits
                    return float(f"{formatted}{'0' * need_zeros}")
                else:
                    return float(formatted)
        except:
            return value

    # ============ 课程分类（完全不变） ============
    def classify_course(self, row):
        """课程分类 - 根据当前专业配置的选修课列表"""
        course_name = ''
        course_code = ''

        if '课程名称' in self.column_mapping:
            name_col = self.column_mapping['课程名称']
            course_name = str(row[name_col]) if pd.notna(row[name_col]) else ''

        if '课程编号' in self.column_mapping:
            code_col = self.column_mapping['课程编号']
            course_code = str(row[code_col]) if pd.notna(row[code_col]) else ''

        if not self.current_major:
            return self._classify_course_legacy(course_name, course_code)

        elective_courses = self.current_major.get('选修课列表', {})

        for course_type, courses in elective_courses.items():
            for kw in courses:
                if kw in course_name or kw in course_code:
                    return course_type

        return '必修课程'

    # ============ 旧分类方法（完全不变） ============
    def _classify_course_legacy(self, course_name, course_code):
        """原有的分类方法（23勘工）"""
        basic_courses = [
            '科学计算语言与编程', 'Python程序设计与实践', '海洋地质学概论',
            '电工电子学', '数据结构', '计算机图形学', '地理信息系统',
            '并行编程原理与程序设计', '专业英语与科技写作', '岩石物理学基础'
        ]

        major_courses = [
            '地球物理测井', '油气地质学', '工程与环境地球物理',
            '地球物理大数据与人工智能', '海洋地球物理探测技术',
            '计算地球物理原理', '国际课程-三维地震勘探', '非常规油气勘探开发',
            '人工智能资料处理与解释', '海洋电磁学', '地学软件工程',
            '地球物理前沿讲座'
        ]

        skill_courses = [
            '地球物理技能训练', '地球物理软件设计实习', '工程实践'
        ]

        for kw in basic_courses:
            if kw in course_name or kw in course_code:
                return '学科基础课程'

        for kw in major_courses:
            if kw in course_name or kw in course_code:
                return '专业知识课程'

        for kw in skill_courses:
            if kw in course_name or kw in course_code:
                return '工作技能课程'

        return '必修课程'

    # ============ 获取学分要求（完全不变） ============
    def _get_credit_requirements(self, student_class):
        """获取学分要求"""
        if not self.current_major:
            return {}
        if self.has_excellent_class:
            return self.current_major['学分要求'].get(student_class, {})
        else:
            return self.current_major['学分要求']

    # ============ 处理重复课程（完全不变） ============
    def _handle_duplicate_courses(self, df):
        """处理同一课程多次考试的情况（补考）"""
        has_course_id = '课程编号' in self.column_mapping
        has_course_name = '课程名称' in self.column_mapping

        if not (has_course_id or has_course_name):
            return set()

        df['_课程标识'] = ''
        if has_course_id:
            id_col = self.column_mapping['课程编号']
            df['_课程标识'] += df[id_col].astype(str) + '_'
        if has_course_name:
            name_col = self.column_mapping['课程名称']
            df['_课程标识'] += df[name_col].astype(str)

        acquire_col = self.column_mapping.get('取得方式', None)
        courses_to_drop = set()

        for course_id, course_group in df.groupby('_课程标识'):
            if len(course_group) > 1:
                has_makeup = False
                makeup_idx = None
                makeup_score = None
                original_idx = None

                for idx, row in course_group.iterrows():
                    exam_type = ''
                    if acquire_col and pd.notna(row.get(acquire_col)):
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

    # ============ 判断是否为补考（完全不变） ============
    def _is_makeup_exam(self, row):
        """判断是否为补考"""
        if '取得方式' not in self.column_mapping:
            return '否'
        acquire_col = self.column_mapping['取得方式']
        if pd.isna(row[acquire_col]):
            return '否'
        exam_type = str(row[acquire_col])
        if '补考' in exam_type and '初修' not in exam_type:
            return '是（补考）'
        return '否'

    # ============ 成绩换算说明（完全不变） ============
    def _get_conversion_note(self, row):
        """获取成绩换算说明"""
        score_col = self.column_mapping.get('总成绩')
        if not score_col or pd.isna(row[score_col]):
            return '无原始成绩'

        score_raw = row[score_col]
        converted = row['_计算成绩'] if '_计算成绩' in row else None

        if pd.isna(converted):
            return '成绩无效（旷考/缺考/缓考未取得）'

        if isinstance(score_raw, str):
            if score_raw.strip() in self.grade_map:
                return f'等级制换算：{score_raw}→{converted}分'
            for key, value in self.grade_map.items():
                if key in score_raw:
                    return f'等级制换算：{score_raw}→{converted}分'

        if '取得方式' in self.column_mapping:
            acquire_col = self.column_mapping['取得方式']
            if pd.notna(row.get(acquire_col)):
                exam_type = str(row[acquire_col])
                if '补考' in exam_type and '初修' not in exam_type:
                    if converted == 60:
                        return f'补考通过，成绩记60分'
                    else:
                        return f'补考未通过，保留原始成绩{converted}分'

        return f'原始成绩{score_raw}→{converted}分'

    # ============ 学分折算说明（完全不变） ============
    def _get_credit_conversion_note(self, row, student_class):
        """获取学分折算说明"""
        course_type = row['_课程类别']
        credit_req = self.class_credit_requirements.get(student_class, {})

        if self.calc_mode == '综测':
            return '综测模式：全部课程计入'

        if course_type not in credit_req:
            return '必修课程，全部计入'

        required = credit_req.get(course_type, 0)
        if required <= 0:
            return f'{student_class}班{course_type}不计入成绩'

        return f'{student_class}班{course_type}需择优计入{required}学分'

    # ============ 分析重复课程（完全不变） ============
    def _analyze_duplicate_courses(self, df):
        """分析重复课程处理情况"""
        duplicate_records = []

        has_course_id = '课程编号' in self.column_mapping
        has_course_name = '课程名称' in self.column_mapping

        if not (has_course_id or has_course_name):
            return duplicate_records

        df = df.copy()
        df['_课程标识'] = ''
        if has_course_id:
            id_col = self.column_mapping['课程编号']
            df['_课程标识'] += df[id_col].astype(str) + '_'
        if has_course_name:
            name_col = self.column_mapping['课程名称']
            df['_课程标识'] += df[name_col].astype(str)

        acquire_col = self.column_mapping.get('取得方式', None)

        for course_id, course_group in df.groupby('_课程标识'):
            if len(course_group) > 1:
                has_makeup = False
                makeup_records = []
                original_records = []

                for idx, row in course_group.iterrows():
                    exam_type = ''
                    if acquire_col and pd.notna(row.get(acquire_col)):
                        exam_type = str(row[acquire_col])

                    is_makeup = '补考' in exam_type and '初修' not in exam_type

                    record = {
                        '课程标识': course_id,
                        '课程名称': row[self.column_mapping['课程名称']] if '课程名称' in self.column_mapping else '',
                        '考试类型': exam_type if exam_type else '初修',
                        '原始成绩': row[self.column_mapping['总成绩']] if '总成绩' in self.column_mapping else '',
                        '换算后成绩': row['_计算成绩'] if '_计算成绩' in row else '',
                        '处理结果': ''
                    }

                    if is_makeup:
                        has_makeup = True
                        makeup_records.append(record)
                    else:
                        original_records.append(record)

                if has_makeup and makeup_records:
                    for record in makeup_records:
                        if record['换算后成绩'] >= 60:
                            record['处理结果'] = '补考通过，成绩计60分，初修成绩不参与计算'
                        else:
                            record['处理结果'] = '补考未通过，保留此补考成绩'

                    for record in original_records:
                        if makeup_records[0]['换算后成绩'] >= 60:
                            record['处理结果'] = '初修成绩，因补考通过不参与计算'
                        else:
                            record['处理结果'] = '初修成绩，保留参与计算'

                    duplicate_records.extend(makeup_records)
                    duplicate_records.extend(original_records)

        return duplicate_records

    # ============ 重复课程规则说明（完全不变） ============
    def _get_duplicate_rule_description(self):
        """获取重复课程处理规则描述"""
        return """
        1. 存在补考记录时：
           - 若补考成绩≥60分，则按60分计入，初修成绩无效
           - 若补考成绩<60分，则保留补考成绩，初修成绩无效
        2. 无补考记录时，取成绩最高的一次
        3. 缓考且取得成绩的，按正常成绩计算
        """

    # ============ 课程处理说明（完全不变） ============
    def _get_course_processing_note(self, row):
        """获取课程处理说明（用于明细表）"""
        notes = []

        if pd.isna(row['_计算成绩']):
            if '成绩标志' in self.column_mapping:
                flag_col = self.column_mapping['成绩标志']
                flag = row[flag_col] if pd.notna(row[flag_col]) else ''
                if '旷考' in flag:
                    notes.append('旷考，无效成绩')
                elif '缺考' in flag:
                    notes.append('缺考，无效成绩')
                elif '缓考' in flag:
                    notes.append('缓考且未取得成绩，无效')
            notes.append('不参与计算')
            return '；'.join(notes)

        if '取得方式' in self.column_mapping:
            acquire_col = self.column_mapping['取得方式']
            if pd.notna(row.get(acquire_col)):
                exam_type = str(row[acquire_col])
                if '补考' in exam_type and '初修' not in exam_type:
                    if row['_计算成绩'] == 60:
                        notes.append('补考通过，计60分')
                    else:
                        notes.append(f'补考未过，保留{row["_计算成绩"]}分')

        score_col = self.column_mapping.get('总成绩')
        if score_col and isinstance(row[score_col], str):
            score_str = row[score_col].strip()
            if score_str in self.grade_map:
                notes.append(f'等级制：{score_str}→{row["_计算成绩"]}')

        return '；'.join(notes) if notes else '正常成绩'

    # ============ 计算单个学生成绩（完全不变） ============
    def calculate_student_gpa(self, student_df, semester_filter=None, calc_mode='保研'):
        """计算单个学生成绩"""
        df = student_df.copy()

        student_id = self._get_student_id(df.iloc[0])
        student_class = self._get_student_class(student_id)

        df['_学号'] = student_id
        df['_姓名'] = df[self.column_mapping.get('姓名')].astype(str).str.strip()

        df['_计算成绩'] = df.apply(self._convert_score, axis=1)
        df['_学分'] = df.apply(self._get_credit, axis=1)

        df = df.dropna(subset=['_计算成绩'])
        df = df[df['_计算成绩'] > 0]

        if len(df) == 0:
            return None

        self._handle_duplicate_courses(df)

        if semester_filter and '学年学期' in self.column_mapping:
            sem_col = self.column_mapping['学年学期']
            if isinstance(semester_filter, str):
                semester_filter = [semester_filter]
            df = df[df[sem_col].isin(semester_filter)]
            if len(df) == 0:
                return None

        df['_课程类别'] = df.apply(self.classify_course, axis=1)

        if calc_mode == '保研':
            credit_requirements = self._get_credit_requirements(student_class)
            processed_list = []

            for course_type, group in df.groupby('_课程类别'):
                if course_type in credit_requirements:
                    required_credits = credit_requirements[course_type]

                    if required_credits <= 0:
                        continue

                    group = group.sort_values('_计算成绩', ascending=False)

                    selected_courses = []
                    total_credits = 0

                    for _, row in group.iterrows():
                        if total_credits < required_credits:
                            credit = row['_学分']

                            if total_credits + credit <= required_credits:
                                selected_courses.append(row)
                                total_credits += credit
                            else:
                                remaining = required_credits - total_credits
                                new_row = row.copy()
                                new_row['_学分'] = remaining
                                selected_courses.append(new_row)
                                total_credits = required_credits
                                break
                        else:
                            break

                    if selected_courses:
                        processed_list.append(pd.DataFrame(selected_courses))
                else:
                    processed_list.append(group)

            if processed_list:
                df = pd.concat(processed_list, ignore_index=True)

        total_weighted = (df['_计算成绩'] * df['_学分']).sum()
        total_credits = df['_学分'].sum()

        if total_credits == 0:
            return None

        avg_score = total_weighted / total_credits

        return {
            '学号': student_id,
            '姓名': df.iloc[0]['_姓名'],
            '班级类型': student_class,
            '平均成绩': self.format_significant_digits(avg_score, 5),
            '总学分': self.format_significant_digits(total_credits, 5),
            '课程门数': len(df),
            '计算模式': calc_mode
        }

    # ============ 计算所有学生（完全不变） ============
    def calculate_all_students(self, semester_filter=None, calc_mode='保研'):
        """计算所有学生 - 统一排名"""
        df_calc = self.df.copy()
        df_calc['_学号'] = df_calc.apply(self._get_student_id, axis=1)
        df_calc['_姓名'] = df_calc[self.column_mapping.get('姓名')].astype(str).str.strip()
        df_calc = df_calc.dropna(subset=['_学号'])

        all_students = df_calc['_学号'].unique()
        excellent_count = sum(1 for sid in all_students if sid in self.excellent_students)
        normal_count = len(all_students) - excellent_count

        results = []
        for student_id, student_df in df_calc.groupby('_学号'):
            res = self.calculate_student_gpa(student_df, semester_filter, calc_mode)
            if res:
                results.append(res)

        result_df = pd.DataFrame(results)

        if not result_df.empty:
            result_df = result_df.sort_values('平均成绩', ascending=False).reset_index(drop=True)
            result_df['排名'] = result_df['平均成绩'].rank(method='min', ascending=False).astype(int)
            cols = ['排名'] + [col for col in result_df.columns if col != '排名']
            result_df = result_df[cols]
            result_df['班级内排名'] = result_df.groupby('班级类型')['平均成绩'] \
                .rank(method='min', ascending=False) \
                .astype(int)

        return result_df, excellent_count, normal_count

    # ============ 生成学生明细（完全不变，只改文件保存方式） ============
    def export_student_calculation_details(self, output_dir):
        """为每个学生生成单独的成绩计算明细Excel文件"""
        import os

        df_calc = self.df.copy()
        df_calc['_学号'] = df_calc.apply(self._get_student_id, axis=1)
        df_calc['_姓名'] = df_calc[self.column_mapping.get('姓名')].astype(str).str.strip()
        df_calc = df_calc.dropna(subset=['_学号'])

        student_count = 0
        error_count = 0
        detail_files = []

        for student_id, student_df in df_calc.groupby('_学号'):
            try:
                student_name = student_df.iloc[0]['_姓名']
                student_class = self._get_student_class(student_id)

                detail_file = self._generate_student_detail_file(
                    student_id, student_name, student_class,
                    student_df, output_dir
                )

                if detail_file:
                    student_count += 1
                    detail_files.append(detail_file)
            except Exception as e:
                error_count += 1

        return student_count, error_count, detail_files

    # ============ 生成单个学生明细（完全不变） ============
    def _generate_student_detail_file(self, student_id, student_name, student_class,
                                      student_df, output_dir):
        """生成单个学生的计算明细Excel文件"""
        import os
        from openpyxl import load_workbook
        from openpyxl.utils.dataframe import dataframe_to_rows

        df = student_df.copy()

        original_columns = []
        if '课程名称' in self.column_mapping:
            original_columns.append(self.column_mapping['课程名称'])
        if '课程编号' in self.column_mapping:
            original_columns.append(self.column_mapping['课程编号'])
        if '学年学期' in self.column_mapping:
            original_columns.append(self.column_mapping['学年学期'])
        if '学分' in self.column_mapping:
            original_columns.append(self.column_mapping['学分'])
        if '总成绩' in self.column_mapping:
            original_columns.append(self.column_mapping['总成绩'])
        if '取得方式' in self.column_mapping:
            original_columns.append(self.column_mapping['取得方式'])
        if '成绩标志' in self.column_mapping:
            original_columns.append(self.column_mapping['成绩标志'])

        df['_计算成绩'] = df.apply(self._convert_score, axis=1)
        df['_学分'] = df.apply(self._get_credit, axis=1)
        df['_课程类别'] = df.apply(self.classify_course, axis=1)
        df['_是否补考'] = df.apply(self._is_makeup_exam, axis=1)
        df['_处理说明'] = df.apply(self._get_course_processing_note, axis=1)

        duplicate_record = self._analyze_duplicate_courses(df)

        file_name = f"{student_id}_{student_name}_{student_class}班_计算明细.xlsx"
        file_path = os.path.join(output_dir, file_name)

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            info_df = pd.DataFrame([
                ['学号', student_id],
                ['姓名', student_name],
                ['班级类型', student_class],
                ['计算模式', self.calc_mode],
                ['课程总数', len(df)],
                ['有效成绩课程数', df['_计算成绩'].notna().sum()],
                ['生成时间', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            ], columns=['项目', '内容'])
            info_df.to_excel(writer, sheet_name='基本信息', index=False)

            if original_columns:
                original_display = df[original_columns].copy()
                original_display.to_excel(writer, sheet_name='原始成绩', index=False)

            conversion_data = []
            for _, row in df.iterrows():
                score_col = self.column_mapping.get('总成绩')
                original_score = row[score_col] if score_col else ''
                acquire_col = self.column_mapping.get('取得方式')
                acquire = row[acquire_col] if acquire_col and pd.notna(row[acquire_col]) else ''
                flag_col = self.column_mapping.get('成绩标志')
                flag = row[flag_col] if flag_col and pd.notna(row[flag_col]) else ''
                converted = row['_计算成绩'] if pd.notna(row['_计算成绩']) else '无效'

                conversion_data.append({
                    '课程名称': row[self.column_mapping['课程名称']] if '课程名称' in self.column_mapping else '',
                    '原始成绩': original_score,
                    '取得方式': acquire,
                    '成绩标志': flag,
                    '换算后成绩': converted,
                    '换算说明': self._get_conversion_note(row)
                })

            pd.DataFrame(conversion_data).to_excel(writer, sheet_name='成绩换算', index=False)

            if duplicate_record:
                duplicate_df = pd.DataFrame(duplicate_record)
                duplicate_df.to_excel(writer, sheet_name='重复课程处理', index=False)

            classification_data = []

            if self.current_major and not self.has_excellent_class:
                credit_req = self.current_major['学分要求']
            else:
                credit_req = self.class_credit_requirements.get(student_class, {})

            for _, row in df.iterrows():
                if pd.notna(row['_计算成绩']):
                    classification_data.append({
                        '课程名称': row[self.column_mapping['课程名称']] if '课程名称' in self.column_mapping else '',
                        '课程类别': row['_课程类别'],
                        '学分': row['_学分'],
                        '成绩': row['_计算成绩'],
                        '是否选修课': '是' if row['_课程类别'] in credit_req else '否',
                        '学分计入': '是',
                        '折算说明': self._get_credit_conversion_note(row, student_class)
                    })

            if classification_data:
                class_df = pd.DataFrame(classification_data)

                if self.calc_mode == '保研' and credit_req:
                    final_selected = []

                    for course_type, group in class_df[class_df['是否选修课'] == '是'].groupby('课程类别'):
                        required_credits = credit_req.get(course_type, 0)
                        if required_credits > 0:
                            group = group.sort_values('成绩', ascending=False).copy()
                            total_credits = 0
                            for idx, row in group.iterrows():
                                credit = row['学分']
                                if total_credits < required_credits:
                                    if total_credits + credit <= required_credits:
                                        group.loc[idx, '学分计入'] = '是（全部计入）'
                                        group.loc[idx, '折算说明'] = f'成绩排名前列，学分{credit}全部计入'
                                        total_credits += credit
                                    else:
                                        remaining = required_credits - total_credits
                                        group.loc[idx, '学分计入'] = f'是（部分计入）'
                                        group.loc[idx, '折算说明'] = f'超额，仅计入{remaining:.1f}学分（原{credit}学分）'
                                        group.loc[idx, '学分'] = remaining
                                        total_credits = required_credits
                                else:
                                    group.loc[idx, '学分计入'] = '否'
                                    group.loc[idx, '折算说明'] = f'已满足{required_credits}学分要求，此课程不参与计算'
                            final_selected.append(group)
                        else:
                            group['学分计入'] = '否'
                            group['折算说明'] = f'该类别选修课不计入{student_class}班成绩'
                            final_selected.append(group)

                    if final_selected:
                        processed_class_df = pd.concat(final_selected, ignore_index=True)
                        non_elective = class_df[class_df['是否选修课'] == '否'].copy()
                        non_elective['学分计入'] = '是'
                        non_elective['折算说明'] = '必修课程，全部计入'
                        class_df = pd.concat([processed_class_df, non_elective], ignore_index=True)

                class_df.to_excel(writer, sheet_name='课程分类与折算', index=False)

            calculation_df = df[df['_计算成绩'].notna()].copy()
            if not calculation_df.empty:
                calc_process = []
                for _, row in calculation_df.iterrows():
                    calc_process.append({
                        '课程名称': row[self.column_mapping['课程名称']] if '课程名称' in self.column_mapping else '',
                        '成绩': row['_计算成绩'],
                        '学分': row['_学分'],
                        '成绩×学分': row['_计算成绩'] * row['_学分'],
                        '课程类别': row['_课程类别']
                    })

                process_df = pd.DataFrame(calc_process)
                total_weighted = process_df['成绩×学分'].sum()
                total_credits = process_df['学分'].sum()
                avg_score = total_weighted / total_credits if total_credits > 0 else 0

                summary = pd.DataFrame([
                    ['加权总分（∑成绩×学分）', f"{total_weighted:.2f}"],
                    ['总学分（∑学分）', f"{total_credits:.2f}"],
                    ['加权平均分', f"{avg_score:.2f}"],
                    ['保留5位有效数字', self.format_significant_digits(avg_score, 5)]
                ], columns=['项目', '数值'])

                with pd.ExcelWriter(file_path, engine='openpyxl', mode='a') as writer:
                    process_df.to_excel(writer, sheet_name='加权平均计算', index=False)
                    wb = writer.book
                    ws = wb['加权平均计算']
                    ws.append([])
                    ws.append(['=== 成绩汇总 ===', '', '', '', ''])
                    for row in dataframe_to_rows(summary, index=False, header=True):
                        ws.append(row)

            rules = [
                ['规则类别', '详细说明'],
                ['成绩换算规则', '1. 等级制成绩换算：优→90、良→80、中→70、合格→60、不合格→0、通过→85、不通过→0'],
                ['', '2. 补考成绩：补考通过计60分，不通过保留原始成绩'],
                ['', '3. 无效成绩：旷考、缺考、缓考未取得等情况不计入'],
                ['重复课程处理', f'同一课程多次考试，取成绩最高的有效成绩，{self._get_duplicate_rule_description()}'],
                ['课程分类规则', '学科基础课程：科学计算语言与编程、Python程序设计与实践、海洋地质学概论等'],
                ['', '专业知识课程：地球物理测井、油气地质学、工程与环境地球物理等'],
                ['', '工作技能课程：地球物理技能训练、地球物理软件设计实习、工程实践'],
                [f'{student_class}班学分要求', f'学科基础课程：{credit_req.get("学科基础课程", 0)}学分'],
                ['', f'专业知识课程：{credit_req.get("专业知识课程", 0)}学分'],
                ['', f'工作技能课程：{credit_req.get("工作技能课程", 0)}学分'],
                ['计算模式',
                 f'{self.calc_mode}模式 - {"按选修课学分要求折算" if self.calc_mode == "保研" else "所有课程全部计入"}']
            ]
            pd.DataFrame(rules[1:], columns=rules[0]).to_excel(writer, sheet_name='计算规则', index=False)

        return file_path

    # ============ 导出Excel（完全不变，只改输出方式） ============
    def export_to_excel(self, output_buffer, semester_filter=None, calc_mode='保研'):
        """导出结果 - 返回BytesIO"""
        result_df, excellent_count, normal_count = self.calculate_all_students(semester_filter, calc_mode)

        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            result_df.to_excel(writer, sheet_name='全校成绩排名', index=False)

            if not result_df.empty:
                excellent_df = result_df[result_df['班级类型'] == '卓越'].copy()
                if not excellent_df.empty:
                    excellent_df = excellent_df.sort_values('平均成绩', ascending=False)
                    excellent_df['班级排名'] = range(1, len(excellent_df) + 1)
                    excellent_df.to_excel(writer, sheet_name='卓越班级', index=False)

                normal_df = result_df[result_df['班级类型'] == '普通'].copy()
                if not normal_df.empty:
                    normal_df = normal_df.sort_values('平均成绩', ascending=False)
                    normal_df['班级排名'] = range(1, len(normal_df) + 1)
                    normal_df.to_excel(writer, sheet_name='普通班级', index=False)

                stats = []
                for class_type in ['卓越', '普通']:
                    class_df = result_df[result_df['班级类型'] == class_type]
                    if not class_df.empty:
                        stats.append({
                            '班级': class_type,
                            '人数': len(class_df),
                            '平均分': self.format_significant_digits(class_df['平均成绩'].mean(), 5),
                            '最高分': self.format_significant_digits(class_df['平均成绩'].max(), 5),
                            '最低分': self.format_significant_digits(class_df['平均成绩'].min(), 5),
                            '总学分平均': self.format_significant_digits(class_df['总学分'].mean(), 5)
                        })
                if stats:
                    pd.DataFrame(stats).to_excel(writer, sheet_name='班级统计', index=False)

            config = {
                '配置项': [
                    '专业', '表头行', '学期筛选', '计算模式', '有效数字', '计算时间',
                    '卓越班级人数', '普通班级人数', '总人数',
                    '卓越-学科基础', '卓越-专业知识', '卓越-工作技能',
                    '普通-学科基础', '普通-专业知识', '普通-工作技能'
                ],
                '值': [
                    self.major_name,
                    f'第{self.header_row + 1}行',
                    str(semester_filter),
                    calc_mode,
                    '5位',
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    excellent_count,
                    normal_count,
                    len(result_df) if not result_df.empty else 0,
                    '1学分', '1学分', '0学分（无选修）',
                    '4学分', '4学分', '2学分'
                ]
            }
            pd.DataFrame(config).to_excel(writer, sheet_name='计算配置', index=False)

        return result_df, excellent_count, normal_count


# ============ Streamlit主程序（翻译Tkinter界面） ============
def main():
    """主函数 - Streamlit版，完全对应原Tkinter逻辑"""

    # ============ 页面配置 ============
    st.set_page_config(
        page_title="2023级学生成绩测算系统",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # ============ 侧边栏：系统特色（对应原print） ============
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center;'>
            <h1 style='color: #2c3e50;'>🎓 2023级</h1>
            <h3 style='color: #3498db;'>成绩测算系统</h3>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 对应原控制台打印的特色列表
        st.markdown("""
        ### ✨ 系统特色
        - ✅ 自动检测表头在哪一行
        - ✅ 自动识别列名
        - ✅ 适配任意格式Excel
        - ✅ 补考通过计60，不通过保留原始
        - ✅ 成绩保留5位有效数字
        - ✅ 每位学生生成独立计算明细
        - ✅ 支持23勘工/23地质/23地信
        """)

        st.markdown("---")
        st.markdown("### 📋 使用流程")
        st.markdown("""
        1. 上传Excel文件
        2. 选择专业
        3. 选择学期（可选）
        4. 选择计算模式
        5. 生成明细（可选）
        6. 下载结果
        """)

    # ============ 主界面标题（对应原print） ============
    st.title("🎓 2023级学生成绩测算系统")

    st.markdown("""
    <div style='background-color: #f0f8ff; padding: 20px; border-radius: 10px; border-left: 5px solid #3498db; margin-bottom: 20px;'>
        <strong>中国海洋大学 海洋地球科学学院</strong> · 23级勘工/地质/地信专业
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

    uploaded_file = st.file_uploader(
        "请选择Excel成绩表文件",
        type=['xlsx', 'xls'],
        help="支持 .xlsx .xls 格式"
    )

    if uploaded_file is None:
        st.info("👆 请上传Excel文件开始使用")
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

    # ============ 3. 专业选择对话框（对应Tkinter专业选择） ============
    st.header("🎓 第二步：选择专业")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📚 23勘工（有卓越班）", use_container_width=True,
                     type="primary" if st.session_state.major_code == '23kg' else "secondary"):
            st.session_state.major_code = '23kg'
            calc.set_major('23kg')
            st.rerun()

    with col2:
        if st.button("🗺️ 23地质（统一班级）", use_container_width=True,
                     type="primary" if st.session_state.major_code == '23dz' else "secondary"):
            st.session_state.major_code = '23dz'
            calc.set_major('23dz')
            st.rerun()

    with col3:
        if st.button("🛰️ 23地信（统一班级）", use_container_width=True,
                     type="primary" if st.session_state.major_code == '23dx' else "secondary"):
            st.session_state.major_code = '23dx'
            calc.set_major('23dx')
            st.rerun()

    if st.session_state.major_code is None:
        st.warning("⚠️ 请先选择专业")
        st.stop()

    # 显示专业信息
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.info(f"🏫 **当前专业**：{calc.major_name}")
    with info_col2:
        if calc.has_excellent_class:
            st.info(f"🎓 **卓越班**：{len(calc.excellent_students)} 人")
        else:
            st.info(f"📚 **班级类型**：统一班级")

    # 显示学分要求（对应原print学分要求）
    with st.expander("📖 查看学分要求"):
        if calc.has_excellent_class:
            tab1, tab2 = st.tabs(["🎓 卓越班", "📚 普通班"])
            with tab1:
                req_df = pd.DataFrame(
                    list(calc.current_major['学分要求']['卓越'].items()),
                    columns=['课程类别', '要求学分']
                )
                st.dataframe(req_df, use_container_width=True)
            with tab2:
                req_df = pd.DataFrame(
                    list(calc.current_major['学分要求']['普通'].items()),
                    columns=['课程类别', '要求学分']
                )
                st.dataframe(req_df, use_container_width=True)
        else:
            req_df = pd.DataFrame(
                list(calc.current_major['学分要求'].items()),
                columns=['课程类别', '要求学分']
            )
            st.dataframe(req_df, use_container_width=True)

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
    st.header("⚙️ 第四步：选择计算模式")

    mode_choice = st.radio(
        "请选择计算模式",
        options=['保研模式', '综测模式'],
        horizontal=True,
        help="保研模式：按选修课学分要求择优折算；综测模式：所有课程全部计入"
    )

    calc_mode = '保研' if mode_choice == '保研模式' else '综测'
    st.session_state.calc_mode = calc_mode
    st.info(f"✅ 已选择: {calc_mode}模式")

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

            # 导出汇总结果到BytesIO
            output_buffer = BytesIO()
            result_df, excellent_count, normal_count = calc.export_to_excel(
                output_buffer,
                st.session_state.semester_filter,
                st.session_state.calc_mode
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

    st.markdown("---")

    # ============ 8. 显示结果（对应原print结果） ============
    if st.session_state.result_df is not None:
        result_df = st.session_state.result_df

        st.header("📊 计算结果")

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
                '平均成绩': ['mean', 'max', 'min'],
                '总学分': 'mean'
            }).round(2)
            class_stats.columns = ['人数', '平均分', '最高分', '最低分', '平均学分']
            st.dataframe(class_stats, use_container_width=True)

        # 前10名（对应原print前10名）
        st.subheader("🏆 前10名学生")

        top10 = result_df.head(10)[['排名', '姓名', '班级类型', '平均成绩', '总学分']].copy()
        top10['平均成绩'] = top10['平均成绩'].apply(lambda x: f"{x:.2f}")
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
        top10 = top10[['名次', '姓名', '班级类型', '平均成绩', '总学分']]

        st.dataframe(top10, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ============ 9. 下载结果（对应原文件保存对话框） ============
        st.header("📥 第七步：下载结果")

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
                    type="primary"
                )

        with col2:
            # 下载明细压缩包
            if generate_details and hasattr(st.session_state, 'detail_zip'):
                st.download_button(
                    label="📁 下载学生明细压缩包",
                    data=st.session_state.detail_zip.getvalue(),
                    file_name=f"{calc.major_name}_计算明细_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )

                if hasattr(st.session_state, 'student_count'):
                    st.info(f"📋 共生成 {st.session_state.student_count} 位学生的计算明细文件")


if __name__ == '__main__':
    main()