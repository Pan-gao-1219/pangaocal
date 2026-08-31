# -*- coding: utf-8 -*-
"""学生成绩计算器核心模块"""
import datetime
import os
import subprocess
import tempfile
import zipfile
from io import BytesIO

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import streamlit as st
import warnings
warnings.filterwarnings('ignore')

from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.config.major_config import MajorConfig


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
        self.major_school = None
        self.has_excellent_class = False
        self.excellent_students = {}
        self.apply_low_credit_penalty = False
        self.apply_course_credit_bonus = False
        self.semester_filter = None

        # 通识课保研规则
        self.tongshi_rule = '不设限'       # '折算' | '不折算' | '不设限'
        self.tongshi_credit_limit = 9      # 折算/不折算时的学分上限
        self.tongshi_course_names = set()  # 由外部注入（课程名集合）

        # 字段关键词（完全不变）
        self.required_fields = {
            '学号': ['学号', 'student id', 'student_id', 'id', '学号', '考生号'],
            '姓名': ['姓名', 'name', '学生姓名'],
            '学分': ['学分', 'credit', 'credits'],
            '总成绩': ['总成绩', '成绩', 'score', 'grade', '总评成绩', 'final score', '综合成绩', '综合'],  # ← 加这两个
            '取得方式': ['取得方式', '修读方式', 'exam type', 'acquire', '考试类型'],
            '修读类型': ['修读类型', '修读类别', 'course attempt type'],
            '成绩标志': ['成绩标志', '标志', 'flag', 'status', '考试状态'],
            '学年学期': ['学年学期', '学期', '学年', 'semester', 'term', 'academic year'],
            '课程名称': ['课程名称', '课程名', 'course', 'course name'],
            '课程编号': ['课程编号', '课程代码', 'course code', 'course_id'],
            '课程性质': ['课程性质', '课程属性', 'course nature', 'course property'],
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

    def setup_chinese_font(self):
        """设置 matplotlib 中文字体"""
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm

        try:
            # 方法1：尝试使用系统常见中文字体
            import platform
            system = platform.system()

            if system == 'Windows':
                plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
            elif system == 'Darwin':  # macOS
                plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti SC', 'Songti SC']
            else:  # Linux (包括 Streamlit Cloud)
                # Streamlit Cloud 常用的中文字体
                plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'WenQuanYi Zen Hei',
                                                   'Droid Sans Fallback', 'Noto Sans CJK SC']

            plt.rcParams['axes.unicode_minus'] = False

            # 方法2：如果上述字体不可用，尝试查找系统中的中文字体
            font_list = fm.findSystemFonts(fontpaths=None, fontext='ttf')
            chinese_fonts = []

            for font in font_list:
                try:
                    prop = fm.FontProperties(fname=font)
                    font_name = prop.get_name()
                    # 检查是否可能是中文字体
                    if any(keyword in font_name.lower() for keyword in
                           ['hei', 'yahei', 'song', 'kai', 'sim', 'arial',
                            'dejavu', 'wenquanyi', 'noto', 'cjk']):
                        chinese_fonts.append(font_name)
                except:
                    continue

            if chinese_fonts:
                plt.rcParams['font.sans-serif'] = chinese_fonts[:3]
                plt.rcParams['axes.unicode_minus'] = False

        except Exception as e:
            print(f"设置中文字体失败: {e}，将使用默认字体")
    # ============ 核心检测函数（完全不变） ============
    def detect_header_row(self):
        """
        核心功能：自动检测表头在第几行
        """
        # 静默检测，不输出任何内容
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

        for idx, row in self.raw_data.iterrows():
            row_score = 0
            row_text = ' '.join([str(cell).lower() for cell in row.values if pd.notna(cell)])

            for keyword, score in keywords.items():
                if keyword.lower() in row_text:
                    row_score += score

            non_empty = row.count()
            row_score += non_empty * 0.5

            if row_score > best_score:
                best_score = row_score
                best_row = idx

        self.header_row = best_row
        return self.header_row

    # ============ 自动识别列名（完全不变） ============
    def auto_detect_columns(self):
        """自动识别列名 - 基于检测到的表头行"""
        columns = self.df.columns.tolist()

        # 列名模糊匹配
        col_lower = {col: str(col).lower() for col in columns}

        for field, keywords in self.required_fields.items():
            found = False
            for col in columns:
                col_low = col_lower[col]
                for kw in keywords:
                    if kw.lower() in col_low:
                        self.column_mapping[field] = col
                        found = True
                        break
                if found:
                    break

        # 必须字段检查
        required = ['学号', '姓名', '学分', '总成绩']
        missing = [f for f in required if f not in self.column_mapping]
        if missing:
            return False, missing

        return True, missing

    # ============ 设置专业（修改版） ============
    def set_major(self, major_code):
        """设置专业（根据用户选择）"""
        major_config = self.major_config.get_major(major_code)
        if not major_config:
            st.error(f"❌ 无效的专业代码: {major_code}")
            return False, None

        self.current_major = major_config
        self.major_name = major_config['专业名称']
        display_entry = next(
            (item for item in self.major_config.get_all_majors()
             if item.get('code') == major_code),
            None
        )
        self.major_school = display_entry.get('school') if display_entry else None
        self.has_excellent_class = major_config['有卓越班']

        # === 确保学分要求存在 ===
        if '学分要求' not in self.current_major:
            st.error(f"❌ 专业 {self.major_name} 未配置学分要求")
            return False, None

        if self.has_excellent_class:
            self.excellent_students = major_config.get('卓越班级学号集', {})
            if '卓越' not in self.current_major['学分要求']:
                st.error(f"❌ 卓越班学分要求未配置")
                return False, None
            if '普通' not in self.current_major['学分要求']:
                st.error(f"❌ 普通班学分要求未配置")
                return False, None
        else:
            self.excellent_students = {}

        return True, self.major_name

    # ============ 成绩换算（完全不变） ============
    def _convert_score(self, row, include_retake=False):
        """成绩换算；综测学分规则可选择保留重修成绩用于判断是否取得学分。"""
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

        if self._is_retake_record(row) and not include_retake:
            return None

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

    def _get_attempt_text(self, row):
        """获取修读/取得方式文本，用于判断初修、补考、重修"""
        parts = []
        for field in ['修读类型', '取得方式']:
            col = self.column_mapping.get(field)
            if col and pd.notna(row.get(col)):
                parts.append(str(row[col]))
        return ' '.join(parts)

    def _is_retake_record(self, row):
        """重修成绩不参与计算"""
        return '重修' in self._get_attempt_text(row)

    def _is_makeup_record(self, row):
        """判断是否为初修后的补考记录"""
        text = self._get_attempt_text(row)
        return '补考' in text and '重修' not in text

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
    def classify_course(self, row, student_class=None):
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

        elective_courses = self._get_elective_courses(student_class)

        for course_type, courses in elective_courses.items():
            for kw in courses:
                if kw in course_name or kw in course_code:
                    return course_type

        # 通识教育选修课识别（命中数据库则单独归类）
        if self.tongshi_course_names and course_name in self.tongshi_course_names:
            return '通识教育选修课程'

        return '必修课程'

    def _get_elective_courses(self, student_class=None):
        """获取当前学生班级对应的选修课清单"""
        if not self.current_major:
            return {}

        elective_courses = self.current_major.get('选修课列表', {})
        if student_class in ('卓越', '普通') and student_class in elective_courses:
            return elective_courses.get(student_class, {})
        return elective_courses

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

    # ============ 处理重复课程 ============
    def _get_course_identity(self, row):
        """生成稳定的课程标识：优先课程号，缺失时回退到课程名。"""
        for field, prefix in [('课程编号', '编号'), ('课程名称', '名称')]:
            col = self.column_mapping.get(field)
            if not col or pd.isna(row.get(col)):
                continue

            value = row[col]
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            normalized = ''.join(str(value).strip().split()).casefold()
            if normalized and normalized not in {'nan', 'none', 'nat'}:
                return f'{prefix}:{normalized}'

        return ''

    def _get_duplicate_decisions(self, course_group):
        """返回同一课程每条记录的处理决定，供计算和明细共同使用。"""
        decisions = {}
        retake_indices = []
        makeup_indices = []
        original_indices = []

        for idx, row in course_group.iterrows():
            if self._is_retake_record(row):
                retake_indices.append(idx)
            elif self._is_makeup_record(row):
                makeup_indices.append(idx)
            else:
                original_indices.append(idx)

        for idx in retake_indices:
            decisions[idx] = ('drop', None, '重修成绩不参与计算，按初修/初修补考规则处理')

        passing_makeups = [
            idx for idx in makeup_indices
            if pd.notna(course_group.loc[idx, '_计算成绩'])
            and float(course_group.loc[idx, '_计算成绩']) >= 60
        ]

        if passing_makeups:
            kept_idx = passing_makeups[0]
            decisions[kept_idx] = ('keep', 60.0, '初修补考通过，成绩计60分')
            for idx in makeup_indices:
                if idx != kept_idx:
                    decisions[idx] = ('drop', None, '重复补考记录，不重复计入')
            for idx in original_indices:
                decisions[idx] = ('drop', None, '初修成绩，因补考通过不参与计算')
            return decisions

        for idx in makeup_indices:
            decisions[idx] = ('drop', None, '初修补考未通过，不采用补考成绩')

        if original_indices:
            # 教务导出偶尔会把同一课程号的再次修读仍标成“初修”。
            # 此时按源表顺序保留第一条有效初修记录，避免学分被重复累计。
            kept_idx = original_indices[0]
            decisions[kept_idx] = ('keep', None, '保留第一条有效初修成绩')
            for idx in original_indices[1:]:
                decisions[idx] = ('drop', None, '同一课程号重复的初修记录，不重复计入')

        return decisions

    def _handle_duplicate_courses(self, df):
        """处理同一课程的初修、补考、重修及误标重复记录。"""
        if not any(field in self.column_mapping for field in ('课程编号', '课程名称')):
            return set()

        df['_课程标识'] = df.apply(self._get_course_identity, axis=1)
        courses_to_drop = set()

        identified_df = df[df['_课程标识'] != '']
        for _, course_group in identified_df.groupby('_课程标识', sort=False):
            if len(course_group) <= 1:
                continue
            for idx, (action, score, _) in self._get_duplicate_decisions(course_group).items():
                if action == 'drop':
                    courses_to_drop.add(idx)
                elif score is not None:
                    df.loc[idx, '_计算成绩'] = score

        if courses_to_drop:
            df.drop(index=courses_to_drop, inplace=True)

        return courses_to_drop

    # ============ 判断是否为补考（完全不变） ============
    def _is_makeup_exam(self, row):
        """判断是否为补考"""
        if self._is_retake_record(row):
            return '否（重修不计）'
        if self._is_makeup_record(row):
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

        if self._is_retake_record(row):
            return '重修成绩不参与计算，按初修/初修补考规则处理'

        if pd.isna(converted):
            return '成绩无效（旷考/缺考/缓考未取得）'

        if isinstance(score_raw, str):
            if score_raw.strip() in self.grade_map:
                return f'等级制换算：{score_raw}→{converted}分'
            for key, value in self.grade_map.items():
                if key in score_raw:
                    return f'等级制换算：{score_raw}→{converted}分'

        if self._is_makeup_record(row):
            if converted == 60:
                return f'初修补考通过，成绩记60分'
            else:
                return f'初修补考未通过，不采用补考成绩，保留初修成绩'

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

    def _low_credit_penalty_is_available(self):
        """低学分扣分规则仅适用于海洋地球科学学院。"""
        return self.major_school == '海洋地球科学学院'

    @staticmethod
    def _merge_summer_autumn_semester(semester):
        """将同一年度夏季学期归并到秋季学期，用于12学分规则。"""
        if pd.isna(semester):
            return semester
        semester_text = str(semester).strip()
        if '夏季学期' in semester_text:
            year = semester_text.replace('夏季学期', '').strip()
            return f'{year}秋季学期'
        return semester

    def _get_earned_credit_mask(self, df):
        """返回获得学分且不属于已获学分后重复重修的记录掩码。"""
        passed_mask = (df['_计算成绩'] >= 60) & (df['_学分'] > 0)
        if not passed_mask.any():
            return passed_mask

        already_earned_retake = self._get_already_earned_retake_mask(df)
        course_identity = df.apply(self._get_course_identity, axis=1)
        eligible_mask = passed_mask & ~already_earned_retake

        # 同一课程即使出现多条通过记录，获得学分也只计算一次。
        identified = eligible_mask & (course_identity != '')
        duplicate_indices = course_identity[identified][
            course_identity[identified].duplicated(keep='first')
        ].index
        eligible_mask.loc[duplicate_indices] = False
        return eligible_mask

    def _get_already_earned_retake_mask(self, df):
        """识别同一数据中已有通过初修记录的重复重修。"""
        course_identity = df.apply(self._get_course_identity, axis=1)
        is_retake = df.apply(self._is_retake_record, axis=1)
        passed_non_retake = (
            (df['_计算成绩'] >= 60)
            & (df['_学分'] > 0)
            & ~is_retake
        )
        already_earned = set(course_identity[passed_non_retake]) - {''}
        return is_retake & course_identity.isin(already_earned)

    def _calculate_low_credit_penalty(self, student_df, semester_filter=None):
        """按学期计算通过学分不足12分的扣分及明细。"""
        if '学年学期' not in self.column_mapping:
            return 0.0, []

        df = student_df.copy()
        sem_col = self.column_mapping['学年学期']

        if semester_filter:
            selected = [semester_filter] if isinstance(semester_filter, str) else semester_filter
            df = df[df[sem_col].isin(selected)]

        if df.empty:
            return 0.0, []

        combined_sem_col = '_综测合并学期'
        df[combined_sem_col] = df[sem_col].apply(self._merge_summer_autumn_semester)

        df['_计算成绩'] = df.apply(
            lambda row: self._convert_score(row, include_retake=True), axis=1
        )
        df['_学分'] = df.apply(self._get_credit, axis=1)
        earned_credit_mask = self._get_earned_credit_mask(df)
        # 综测模式的12学分门槛按所有通过课程计算，通识课和任选课也计入。
        passed = df[earned_credit_mask].copy()
        passed_credits = passed.groupby(combined_sem_col)['_学分'].sum().to_dict()

        details = []
        total_penalty = 0.0
        for semester in df[combined_sem_col].dropna().drop_duplicates().tolist():
            credits = float(passed_credits.get(semester, 0.0))
            missing = max(0.0, 12.0 - credits)
            penalty = missing * 5.0
            total_penalty += penalty
            details.append({
                '学期': semester,
                '通过学分': credits,
                '缺少学分': missing,
                '扣分': penalty,
            })

        return total_penalty, details

    def _calculate_course_credit_bonus(self, student_df, semester_filter=None):
        """按学期计算必修课与限选课的学分加分及明细。"""
        if '学年学期' not in self.column_mapping:
            return 0.0, []

        df = student_df.copy()
        sem_col = self.column_mapping['学年学期']

        if semester_filter:
            selected = [semester_filter] if isinstance(semester_filter, str) else semester_filter
            df = df[df[sem_col].isin(selected)]

        if df.empty:
            return 0.0, []

        combined_sem_col = '_综测合并学期'
        df[combined_sem_col] = df[sem_col].apply(self._merge_summer_autumn_semester)

        student_id = self._get_student_id(df.iloc[0])
        student_class = self._get_student_class(student_id)
        df['_计算成绩'] = df.apply(
            lambda row: self._convert_score(row, include_retake=True), axis=1
        )
        df['_学分'] = df.apply(self._get_credit, axis=1)
        df['_课程类别'] = df.apply(
            lambda row: self.classify_course(row, student_class), axis=1
        )

        optional_mask = df['_课程类别'] == '通识教育选修课程'
        nature_col = self.column_mapping.get('课程性质')
        if nature_col:
            nature = df[nature_col].fillna('').astype(str)
            optional_mask = optional_mask | nature.str.contains('任选')
            bonus_course_mask = nature.str.contains('必修|限选')
        else:
            # 无课程性质列时，使用系统能够识别的非任选课程作为必修/限选课程。
            bonus_course_mask = ~optional_mask

        earned_credit_mask = self._get_earned_credit_mask(df)
        passed_courses = df[earned_credit_mask].copy()
        bonus_courses = df[earned_credit_mask & ~optional_mask & bonus_course_mask].copy()
        optional_courses = df[earned_credit_mask & optional_mask].copy()

        # 所有通过课程（含任选课）均用于判断是否达到12学分；
        # 达标后的加分仍只按必修课与限选课学分计算。
        passed_credits = passed_courses.groupby(combined_sem_col)['_学分'].sum().to_dict()
        bonus_credits = bonus_courses.groupby(combined_sem_col)['_学分'].sum().to_dict()
        optional_credits = optional_courses.groupby(combined_sem_col)['_学分'].sum().to_dict()

        course_name_col = self.column_mapping.get('课程名称')
        optional_course_names = {}
        if course_name_col:
            for semester, group in optional_courses.groupby(combined_sem_col, sort=False):
                optional_course_names[semester] = [
                    str(name).strip()
                    for name in group[course_name_col].dropna().tolist()
                    if str(name).strip()
                ]

        details = []
        total_bonus = 0.0
        for semester in df[combined_sem_col].dropna().drop_duplicates().tolist():
            credits = float(passed_credits.get(semester, 0.0))
            eligible_credits = float(bonus_credits.get(semester, 0.0))
            qualified = credits >= 12.0
            bonus = eligible_credits * 0.2 if qualified else 0.0
            total_bonus += bonus
            details.append({
                '学期': semester,
                '通过学分': credits,
                '必修及限选学分': eligible_credits,
                '任选课学分（仅计入门槛）': float(optional_credits.get(semester, 0.0)),
                '任选课明细': optional_course_names.get(semester, []),
                '是否达到12学分': qualified,
                '加分': bonus,
            })

        return total_bonus, details

    # ============ 分析重复课程 ============
    def _analyze_duplicate_courses(self, df):
        """生成与实际去重逻辑一致的重复课程处理明细。"""
        duplicate_records = []

        if not any(field in self.column_mapping for field in ('课程编号', '课程名称')):
            return duplicate_records

        df = df.copy()
        df['_课程标识'] = df.apply(self._get_course_identity, axis=1)

        identified_df = df[df['_课程标识'] != '']
        for course_id, course_group in identified_df.groupby('_课程标识', sort=False):
            if len(course_group) <= 1:
                continue

            decisions = self._get_duplicate_decisions(course_group)
            for idx, row in course_group.iterrows():
                _, score_override, reason = decisions.get(
                    idx, ('keep', None, '保留参与计算')
                )
                converted_score = row.get('_计算成绩', '')
                if score_override is not None:
                    converted_score = score_override
                duplicate_records.append({
                    '课程标识': course_id,
                    '课程名称': row[self.column_mapping['课程名称']] if '课程名称' in self.column_mapping else '',
                    '考试类型': self._get_attempt_text(row) or '初修',
                    '原始成绩': row[self.column_mapping['总成绩']] if '总成绩' in self.column_mapping else '',
                    '换算后成绩': converted_score,
                    '处理结果': reason
                })

        return duplicate_records

    # ============ 重复课程规则说明（完全不变） ============
    def _get_duplicate_rule_description(self):
        """获取重复课程处理规则描述"""
        return """
        1. 存在补考记录时：
           - 若初修补考成绩≥60分，则按60分计入，初修成绩不再参与
           - 若初修补考成绩<60分，则不采用补考成绩，保留初修成绩
        2. 重修成绩不参与计算，只按初修/初修补考规则处理
        3. 缓考且取得成绩的，按正常成绩计算
        4. 同一课程号存在多条“初修”记录时，只保留源表中的第一条有效记录
        """

    # ============ 课程处理说明（完全不变） ============
    def _get_course_processing_note(self, row):
        """获取课程处理说明（用于明细表）"""
        notes = []

        if self._is_retake_record(row):
            return '重修成绩不参与计算，按初修/初修补考规则处理'

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

        if self._is_makeup_record(row):
            if row['_计算成绩'] == 60:
                notes.append('初修补考通过，计60分')
            else:
                notes.append('初修补考未过，不采用补考成绩')

        score_col = self.column_mapping.get('总成绩')
        if score_col and isinstance(row[score_col], str):
            score_str = row[score_col].strip()
            if score_str in self.grade_map:
                notes.append(f'等级制：{score_str}→{row["_计算成绩"]}')

        return '；'.join(notes) if notes else '正常成绩'

    # ============ 计算单个学生成绩（完全不变） ============
    def calculate_student_gpa(self, student_df, semester_filter=None, calc_mode='保研',
                              apply_low_credit_penalty=False,
                              apply_course_credit_bonus=False):
        """计算单个学生成绩"""
        df = student_df.copy()

        student_id = self._get_student_id(df.iloc[0])
        student_class = self._get_student_class(student_id)

        df['_学号'] = student_id
        df['_姓名'] = df[self.column_mapping.get('姓名')].astype(str).str.strip()

        include_retake = calc_mode == '综测'
        df['_计算成绩'] = df.apply(
            lambda row: self._convert_score(row, include_retake=include_retake), axis=1
        )
        df['_学分'] = df.apply(self._get_credit, axis=1)

        if include_retake:
            df = df[~self._get_already_earned_retake_mask(df)].copy()

        df = df.dropna(subset=['_计算成绩'])
        df = df[df['_计算成绩'] > 0]

        if len(df) == 0:
            return None

        # 保研按课程唯一计入；综测允许同一课程的多条有效记录分别计入。
        if calc_mode == '保研':
            self._handle_duplicate_courses(df)

        if semester_filter and '学年学期' in self.column_mapping:
            sem_col = self.column_mapping['学年学期']
            if isinstance(semester_filter, str):
                semester_filter = [semester_filter]
            df = df[df[sem_col].isin(semester_filter)]
            if len(df) == 0:
                return None

        df['_课程类别'] = df.apply(lambda row: self.classify_course(row, student_class), axis=1)

        if calc_mode == '保研':
            credit_requirements = self._get_credit_requirements(student_class)
            processed_list = []

            for course_type, group in df.groupby('_课程类别'):
                if course_type == '通识教育选修课程':
                    # 按通识规则处理
                    rule = self.tongshi_rule
                    limit = self.tongshi_credit_limit
                    if rule == '不设限':
                        processed_list.append(group)
                    else:
                        group = group.sort_values('_计算成绩', ascending=False).copy()
                        selected = []
                        total = 0
                        for _, row in group.iterrows():
                            credit = row['_学分']
                            if total >= limit:
                                break
                            if rule == '折算':
                                if total + credit <= limit:
                                    selected.append(row)
                                    total += credit
                                else:
                                    new_row = row.copy()
                                    new_row['_学分'] = limit - total
                                    selected.append(new_row)
                                    total = limit
                                    break
                            else:  # '不折算'：整门计入，不拆分
                                if total + credit <= limit:
                                    selected.append(row)
                                    total += credit
                                # 超出上限则跳过整门
                        if selected:
                            processed_list.append(pd.DataFrame(selected))
                elif course_type in credit_requirements:
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

        penalty_enabled = (
            calc_mode == '综测'
            and apply_low_credit_penalty
            and self._low_credit_penalty_is_available()
        )
        low_credit_penalty = 0.0
        penalty_details = []
        if penalty_enabled:
            low_credit_penalty, penalty_details = self._calculate_low_credit_penalty(
                student_df, semester_filter
            )

        bonus_enabled = (
            calc_mode == '综测'
            and apply_course_credit_bonus
            and self._low_credit_penalty_is_available()
        )
        course_credit_bonus = 0.0
        bonus_details = []
        if bonus_enabled:
            course_credit_bonus, bonus_details = self._calculate_course_credit_bonus(
                student_df, semester_filter
            )

        comprehensive_score = min(
            100.0,
            max(0.0, avg_score + course_credit_bonus - low_credit_penalty),
        )

        return {
            '学号': student_id,
            '姓名': df.iloc[0]['_姓名'],
            '班级类型': student_class,
            '平均成绩': self.format_significant_digits(avg_score, 5),
            '课程学分加分': self.format_significant_digits(course_credit_bonus, 5),
            '低学分扣分': self.format_significant_digits(low_credit_penalty, 5),
            '综测成绩': self.format_significant_digits(comprehensive_score, 5),
            '课程学分加分明细': '；'.join(
                (
                    f"{item['学期']}：通过{item['通过学分']:g}学分"
                    + (
                        f"（其中任选课{item['任选课学分（仅计入门槛）']:g}学分计入12学分门槛："
                        f"{'、'.join(item['任选课明细'])}）"
                        if item['任选课学分（仅计入门槛）'] > 0 else ''
                    )
                    + (
                        f"，必修及限选课{item['必修及限选学分']:g}学分，加{item['加分']:g}分"
                        if item['加分'] > 0 else '，未达到12学分，不加分'
                    )
                )
                for item in bonus_details
            ) or '无',
            '低学分扣分明细': '；'.join(
                f"{item['学期']}：通过{item['通过学分']:g}学分，扣{item['扣分']:g}分"
                for item in penalty_details if item['扣分'] > 0
            ) or '无',
            '总学分': self.format_significant_digits(total_credits, 5),
            '课程门数': len(df),
            '计算模式': calc_mode
        }

    # ============ 计算所有学生（完全不变） ============
    def calculate_all_students(self, semester_filter=None, calc_mode='保研',
                               apply_low_credit_penalty=False,
                               apply_course_credit_bonus=False):
        """计算所有学生 - 统一排名"""
        self.calc_mode = calc_mode
        self.semester_filter = semester_filter
        self.apply_low_credit_penalty = (
            calc_mode == '综测'
            and apply_low_credit_penalty
            and self._low_credit_penalty_is_available()
        )
        self.apply_course_credit_bonus = (
            calc_mode == '综测'
            and apply_course_credit_bonus
            and self._low_credit_penalty_is_available()
        )
        df_calc = self.df.copy()
        df_calc['_学号'] = df_calc.apply(self._get_student_id, axis=1)
        df_calc['_姓名'] = df_calc[self.column_mapping.get('姓名')].astype(str).str.strip()
        df_calc = df_calc.dropna(subset=['_学号'])

        all_students = df_calc['_学号'].unique()
        excellent_count = sum(1 for sid in all_students if sid in self.excellent_students)
        normal_count = len(all_students) - excellent_count

        results = []
        for student_id, student_df in df_calc.groupby('_学号'):
            res = self.calculate_student_gpa(
                student_df,
                semester_filter,
                calc_mode,
                self.apply_low_credit_penalty,
                self.apply_course_credit_bonus,
            )
            if res:
                results.append(res)

        result_df = pd.DataFrame(results)

        if not result_df.empty:
            ranking_column = '综测成绩' if calc_mode == '综测' else '平均成绩'
            result_df = result_df.sort_values(ranking_column, ascending=False).reset_index(drop=True)
            result_df['排名'] = result_df[ranking_column].rank(method='min', ascending=False).astype(int)
            cols = ['排名'] + [col for col in result_df.columns if col != '排名']
            result_df = result_df[cols]
            result_df['班级内排名'] = result_df.groupby('班级类型')[ranking_column] \
                .rank(method='min', ascending=False) \
                .astype(int)

        return result_df, excellent_count, normal_count

    # ============ 生成学生明细（带完整错误输出） ============
    # ============ 生成学生明细（静默版） ============
    def export_student_calculation_details(self, output_dir):
        """为每个学生生成单独的成绩计算明细Excel文件"""
        import os

        # === 确保输出目录存在 ===
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
        except Exception as e:
            return 0, 0, []

        # 准备数据
        df_calc = self.df.copy()

        # 获取学号
        df_calc['_学号'] = df_calc.apply(self._get_student_id, axis=1)
        df_calc['_姓名'] = df_calc[self.column_mapping.get('姓名')].astype(str).str.strip()

        # 学号统计
        total_with_id = df_calc['_学号'].notna().sum()
        if total_with_id == 0:
            return 0, 0, []

        # 删除无学号记录
        df_calc = df_calc.dropna(subset=['_学号'])
        df_calc['_学号'] = df_calc['_学号'].astype(str)

        # 确保卓越班学号集也是字符串
        if self.excellent_students:
            self.excellent_students = {str(sid) for sid in self.excellent_students}

        student_count = 0
        error_count = 0
        detail_files = []

        # 分组处理
        grouped = df_calc.groupby('_学号')

        for i, (student_id, student_df) in enumerate(grouped):
            try:
                student_name = student_df.iloc[0]['_姓名']
                student_class = self._get_student_class(student_id)

                detail_file = self._generate_student_detail_file(
                    student_id, student_name, student_class,
                    student_df, output_dir
                )

                if detail_file and os.path.exists(detail_file):
                    student_count += 1
                    detail_files.append(detail_file)
            except Exception as e:
                error_count += 1

        return student_count, error_count, detail_files

    def _generate_student_detail_file(self, student_id, student_name, student_class,
                                      student_df, output_dir):
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
        if '修读类型' in self.column_mapping:
            original_columns.append(self.column_mapping['修读类型'])
        if '成绩标志' in self.column_mapping:
            original_columns.append(self.column_mapping['成绩标志'])

        df['_计算成绩'] = df.apply(self._convert_score, axis=1)
        df['_学分'] = df.apply(self._get_credit, axis=1)
        df['_课程类别'] = df.apply(lambda row: self.classify_course(row, student_class), axis=1)
        df['_是否补考'] = df.apply(self._is_makeup_exam, axis=1)
        df['_处理说明'] = df.apply(self._get_course_processing_note, axis=1)

        # 分类、折算和加权计算必须与正式排名使用同一批有效记录。
        processed_df = df.dropna(subset=['_计算成绩']).copy()
        processed_df = processed_df[processed_df['_计算成绩'] > 0].copy()
        if self.calc_mode == '保研':
            duplicate_record = self._analyze_duplicate_courses(processed_df)
            self._handle_duplicate_courses(processed_df)
        else:
            duplicate_record = []

        file_name = f"{student_id}_{student_name}_{student_class}班_计算明细.xlsx"
        file_path = os.path.join(output_dir, file_name)

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            info_df = pd.DataFrame([
                ['学号', student_id],
                ['姓名', student_name],
                ['班级类型', student_class],
                ['计算模式', self.calc_mode],
                ['课程总数', len(df)],
                ['有效成绩课程数', len(processed_df)],
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

            credit_req = self._get_credit_requirements(student_class)

            for _, row in processed_df.iterrows():
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

                if self.calc_mode == '保研':
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

                    # 通识课使用与正式排名相同的独立上限和折算规则。
                    tongshi_mask = class_df['课程类别'] == '通识教育选修课程'
                    if tongshi_mask.any():
                        tongshi = class_df[tongshi_mask].sort_values('成绩', ascending=False).copy()
                        non_tongshi = class_df[~tongshi_mask].copy()
                        rule = self.tongshi_rule
                        limit = self.tongshi_credit_limit
                        total_credits = 0.0

                        for idx, row in tongshi.iterrows():
                            credit = float(row['学分'])
                            if rule == '不设限':
                                tongshi.loc[idx, '学分计入'] = '是（全部计入）'
                                tongshi.loc[idx, '折算说明'] = '通识课不设限，全部计入'
                            elif total_credits >= limit:
                                tongshi.loc[idx, '学分计入'] = '否'
                                tongshi.loc[idx, '折算说明'] = f'通识课已达到{limit}学分上限'
                            elif rule == '折算':
                                counted_credit = min(credit, limit - total_credits)
                                tongshi.loc[idx, '学分'] = counted_credit
                                total_credits += counted_credit
                                if counted_credit < credit:
                                    tongshi.loc[idx, '学分计入'] = '是（部分计入）'
                                    tongshi.loc[idx, '折算说明'] = (
                                        f'通识课超额，仅计入{counted_credit:.1f}学分（原{credit}学分）'
                                    )
                                else:
                                    tongshi.loc[idx, '学分计入'] = '是（全部计入）'
                                    tongshi.loc[idx, '折算说明'] = '通识课按成绩择优计入'
                            elif total_credits + credit <= limit:
                                total_credits += credit
                                tongshi.loc[idx, '学分计入'] = '是（全部计入）'
                                tongshi.loc[idx, '折算说明'] = '通识课按成绩择优整门计入'
                            else:
                                tongshi.loc[idx, '学分计入'] = '否'
                                tongshi.loc[idx, '折算说明'] = (
                                    f'整门计入将超过{limit}学分上限，此课程不参与计算'
                                )

                        class_df = pd.concat([non_tongshi, tongshi], ignore_index=True)

                class_df.to_excel(writer, sheet_name='课程分类与折算', index=False)

            # 加权平均计算：只使用真正计入的课程（学分计入 != 否），与排名结果保持一致
            if classification_data and 'class_df' in dir():
                counted_df = class_df[class_df['学分计入'] != '否'].copy()
            else:
                counted_df = processed_df.copy()

            if not counted_df.empty:
                calc_process = []
                for _, row in counted_df.iterrows():
                    course_name = row.get('课程名称', row.get(
                        self.column_mapping.get('课程名称', ''), ''))
                    calc_process.append({
                        '课程名称': course_name,
                        '成绩': row['成绩'] if '成绩' in row else row.get('_计算成绩', 0),
                        '学分': row['学分'] if '学分' in row else row.get('_学分', 0),
                        '成绩×学分': (row['成绩'] if '成绩' in row else row.get('_计算成绩', 0)) *
                                    (row['学分'] if '学分' in row else row.get('_学分', 0)),
                        '课程类别': row['课程类别'] if '课程类别' in row else row.get('_课程类别', ''),
                        '是否折算': row.get('折算说明', '必修课程，全部计入')
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

                process_df.to_excel(writer, sheet_name='加权平均计算', index=False)
                wb = writer.book
                ws = wb['加权平均计算']
                ws.append([])
                ws.append(['=== 成绩汇总 ===', '', '', '', '', ''])
                for row in dataframe_to_rows(summary, index=False, header=True):
                    ws.append(row)

            rules = [
                ['规则类别', '详细说明'],
                ['成绩换算规则', '1. 等级制成绩换算：优→90、良→80、中→70、合格→60、不合格→0、通过→85、不通过→0'],
                ['', '2. 补考成绩：补考通过计60分，不通过保留原始成绩'],
                ['', '3. 无效成绩：旷考、缺考、缓考未取得等情况不计入'],
                ['重复课程处理', f'同一课程存在初修/补考/重修记录时，{self._get_duplicate_rule_description()}'],
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
    def export_to_excel(self, output_buffer, semester_filter=None, calc_mode='保研',
                        apply_low_credit_penalty=False,
                        apply_course_credit_bonus=False):
        """导出结果 - 返回BytesIO"""
        result_df, excellent_count, normal_count = self.calculate_all_students(
            semester_filter,
            calc_mode,
            apply_low_credit_penalty,
            apply_course_credit_bonus,
        )

        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            result_df.to_excel(writer, sheet_name='全校成绩排名', index=False)

            if not result_df.empty:
                excellent_df = result_df[result_df['班级类型'] == '卓越'].copy()
                if not excellent_df.empty:
                    ranking_column = '综测成绩' if calc_mode == '综测' else '平均成绩'
                    excellent_df = excellent_df.sort_values(ranking_column, ascending=False)
                    excellent_df['班级排名'] = range(1, len(excellent_df) + 1)
                    excellent_df.to_excel(writer, sheet_name='卓越班级', index=False)

                normal_df = result_df[result_df['班级类型'] == '普通'].copy()
                if not normal_df.empty:
                    ranking_column = '综测成绩' if calc_mode == '综测' else '平均成绩'
                    normal_df = normal_df.sort_values(ranking_column, ascending=False)
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
                    '专业', '表头行', '学期筛选', '计算模式', '课程学分加分规则',
                    '低学分扣分规则', '有效数字', '计算时间',
                    '卓越班级人数', '普通班级人数', '总人数',
                    '卓越-学科基础', '卓越-专业知识', '卓越-工作技能',
                    '普通-学科基础', '普通-专业知识', '普通-工作技能'
                ],
                '值': [
                    self.major_name,
                    f'第{self.header_row + 1}行',
                    str(semester_filter),
                    calc_mode,
                    '启用（每学期达到12学分后，必修及限选课每学分加0.2分）'
                    if self.apply_course_credit_bonus else '未启用',
                    '启用（每学期不足12学分，每缺1学分扣5分）'
                    if self.apply_low_credit_penalty else '未启用',
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

    def analyze_learning_status(self, student_id=None):
        """分析学生学习状态 - 基于成绩趋势、稳定性和整体水平（改进版）"""
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        import warnings
        warnings.filterwarnings('ignore')

        # 准备数据
        df_calc = self.df.copy()

        # 获取学号和学期
        df_calc['_学号'] = df_calc.apply(self._get_student_id, axis=1)
        df_calc['_姓名'] = df_calc[self.column_mapping.get('姓名')].astype(str).str.strip()

        # 成绩换算
        df_calc['_计算成绩'] = df_calc.apply(self._convert_score, axis=1)
        df_calc = df_calc.dropna(subset=['_计算成绩'])

        # 检查是否有学期字段
        has_semester = '学年学期' in self.column_mapping

        # 如果指定了学生ID，只分析该学生
        if student_id:
            df_calc = df_calc[df_calc['_学号'] == str(student_id)]
            if df_calc.empty:
                return None

        # 按学生分组分析
        results = []
        all_scores = []  # 收集所有成绩用于计算全局统计

        for sid, student_df in df_calc.groupby('_学号'):
            student_name = student_df.iloc[0]['_姓名']
            student_class = self._get_student_class(sid)

            # 按学期排序（如果有学期字段）
            if has_semester:
                sem_col = self.column_mapping['学年学期']
                try:
                    student_df['_学期序号'] = student_df[sem_col].apply(
                        lambda x: float(str(x).split('-')[-1]) if '-' in str(x) else 0
                    )
                    student_df = student_df.sort_values('_学期序号')
                except:
                    student_df = student_df.sort_values(sem_col)

            # 计算各项指标
            scores = student_df['_计算成绩'].values
            all_scores.extend(scores)  # 收集所有成绩

            if len(scores) < 3:  # 数据太少无法分析趋势
                status = {
                    '学号': sid,
                    '姓名': student_name,
                    '班级类型': student_class,
                    '平均成绩': self.format_significant_digits(np.mean(scores), 5),
                    '最高成绩': self.format_significant_digits(np.max(scores), 5),
                    '最低成绩': self.format_significant_digits(np.min(scores), 5),
                    '标准差': self.format_significant_digits(np.std(scores), 5),
                    '斜率': 0,
                    '下滑拐点': 0,
                    '学习状态': '数据不足',
                    '状态说明': '成绩记录不足3条，无法分析趋势',
                    '建议': '请积累更多成绩数据'
                }
                results.append(status)
                continue

            # 1. 计算趋势（斜率）
            x = np.arange(len(scores))
            slope = np.polyfit(x, scores, 1)[0]

            # 2. 计算稳定性（变异系数 = 标准差/均值，更合理的稳定性指标）
            std = np.std(scores)
            cv = std / np.mean(scores) if np.mean(scores) > 0 else 0  # 变异系数

            # 3. 检测下滑拐点（更宽松的检测）
            drop_inflection = 0
            drop_count = 0
            for i in range(1, len(scores)):
                if scores[i] < scores[i - 1] - 3:  # 下降超过3分就算
                    drop_count += 1
            if drop_count >= 2:  # 有两次以上明显下降
                drop_inflection = 1

            # 4. 计算整体水平
            avg_score = np.mean(scores)

            # 5. 根据规则分类（使用更合理的阈值）
            if avg_score >= 85:
                if slope > 0.2 and cv < 0.1:
                    status_label = '🌟 进步稳定型（高分段）'
                    status_desc = '高分段且稳步上升，学习状态极佳'
                    suggestion = '保持当前学习节奏，可参与科研项目'
                elif -0.2 <= slope <= 0.2 and cv < 0.1:
                    status_label = '🟢 稳定优秀型'
                    status_desc = '高分且成绩稳定，学习状态平稳'
                    suggestion = '继续保持，可挑战更高难度课程'
                elif slope > 0.2:
                    status_label = '📈 进步型（高分段）'
                    status_desc = '高分段且持续进步'
                    suggestion = '保持进步势头，巩固优势'
                elif slope < -0.2:
                    status_label = '📉 退步预警（高分段）'
                    status_desc = '高分段但成绩有下滑趋势'
                    suggestion = '分析下滑原因，及时调整'
                else:
                    status_label = '✨ 优秀型'
                    status_desc = '成绩优秀'
                    suggestion = '继续保持'

            elif avg_score >= 75:
                if slope > 0.3 and cv < 0.15:
                    status_label = '🌟 进步稳定型（中分段）'
                    status_desc = '中等成绩稳步上升，有潜力'
                    suggestion = '保持进步势头，冲击高分段'
                elif -0.2 <= slope <= 0.2 and cv < 0.12:
                    status_label = '🟡 稳定中等型'
                    status_desc = '成绩稳定在中等水平'
                    suggestion = '尝试突破现有水平'
                elif slope > 0.3:
                    status_label = '📈 进步型'
                    status_desc = '成绩持续进步'
                    suggestion = '保持学习节奏'
                elif slope < -0.3:
                    status_label = '📉 退步型'
                    status_desc = '成绩有下滑趋势'
                    suggestion = '需要关注学习状态'
                else:
                    status_label = '🟠 波动型'
                    status_desc = '成绩波动较大'
                    suggestion = '注意稳定性'

            else:  # avg_score < 75
                if slope > 0.4:
                    status_label = '📈 进步型（低分段）'
                    status_desc = '基础较弱但进步明显'
                    suggestion = '保持进步势头，巩固基础'
                elif -0.2 <= slope <= 0.2 and cv < 0.15:
                    status_label = '⚫ 稳定待提升型'
                    status_desc = '成绩稳定但偏低'
                    suggestion = '需要加大学习投入'
                elif slope < -0.2:
                    status_label = '🔴 退步型（需关注）'
                    status_desc = '成绩偏低且有下滑趋势'
                    suggestion = '建议与老师沟通，制定学习计划'
                else:
                    status_label = '🔸 待提升型'
                    status_desc = '成绩有提升空间'
                    suggestion = '从基础课程重新巩固'

            # 记录结果
            status = {
                '学号': sid,
                '姓名': student_name,
                '班级类型': student_class,
                '平均成绩': self.format_significant_digits(avg_score, 5),
                '最高成绩': self.format_significant_digits(np.max(scores), 5),
                '最低成绩': self.format_significant_digits(np.min(scores), 5),
                '标准差': self.format_significant_digits(std, 5),
                '变异系数': self.format_significant_digits(cv, 5),
                '斜率': self.format_significant_digits(slope, 5),
                '下滑次数': drop_count,
                '下滑拐点': drop_inflection,
                '学习状态': status_label,
                '状态说明': status_desc,
                '建议': suggestion,
                '课程数': len(scores)
            }
            results.append(status)

        # 转换为DataFrame
        result_df = pd.DataFrame(results)

        # 使用K-Means进行聚类分析
        if len(result_df) >= 10:
            try:
                # 选择特征进行聚类
                features = ['平均成绩', '标准差', '斜率']
                cluster_df = result_df[features].copy()

                # 标准化
                scaler = StandardScaler()
                scaled_features = scaler.fit_transform(cluster_df)

                # 确定合适的聚类数（根据数据量动态调整）
                n_clusters = min(5, len(result_df) // 3)
                n_clusters = max(3, n_clusters)  # 至少3类

                # K-Means聚类
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                result_df['聚类簇'] = kmeans.fit_predict(scaled_features)

                # 分析每个聚类的特征
                for i in range(n_clusters):
                    mask = result_df['聚类簇'] == i
                    cluster_avg = result_df.loc[mask, '平均成绩'].mean()
                    cluster_std = result_df.loc[mask, '标准差'].mean()
                    cluster_slope = result_df.loc[mask, '斜率'].mean()

                    if cluster_avg >= 85:
                        result_df.loc[mask, '聚类说明'] = '高分段'
                    elif cluster_avg >= 75:
                        result_df.loc[mask, '聚类说明'] = '中分段'
                    else:
                        result_df.loc[mask, '聚类说明'] = '低分段'

                    if cluster_slope > 0.2:
                        result_df.loc[mask, '聚类说明'] += '-进步趋势'
                    elif cluster_slope < -0.2:
                        result_df.loc[mask, '聚类说明'] += '-退步趋势'
                    else:
                        result_df.loc[mask, '聚类说明'] += '-稳定'

            except Exception as e:
                result_df['聚类簇'] = -1
                result_df['聚类说明'] = '聚类分析失败'

        return result_df
# ============ Streamlit主程序（翻译Tkinter界面） ============
    def export_learning_status_report(self, output_buffer, include_clustering=True):
        """导出学习状态分析报告"""
        # 获取学习状态分析结果
        status_df = self.analyze_learning_status()

        if status_df is None or status_df.empty:
            # 返回空的Excel文件
            with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                pd.DataFrame().to_excel(writer, sheet_name='无数据', index=False)
            return None

        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            # 学习状态总览
            status_df.to_excel(writer, sheet_name='学习状态分析', index=False)

            # 按状态统计
            if '学习状态' in status_df.columns:
                stats = status_df.groupby('学习状态').agg({
                    '学号': 'count',
                    '平均成绩': 'mean',
                    '标准差': 'mean'
                }).round(2)
                stats.columns = ['人数', '平均成绩', '平均标准差']
                stats.to_excel(writer, sheet_name='状态统计', index=True)

            # 班级分布
            if '班级类型' in status_df.columns and '学习状态' in status_df.columns:
                pivot = pd.crosstab(
                    status_df['班级类型'],
                    status_df['学习状态'],
                    margins=True,
                    margins_name='总计'
                )
                pivot.to_excel(writer, sheet_name='班级分布')

            # 建议汇总
            advice = status_df[['学号', '姓名', '学习状态', '建议']].copy()
            advice.to_excel(writer, sheet_name='学习建议', index=False)

            # 聚类结果
            if include_clustering and '聚类簇' in status_df.columns:
                cluster_summary = status_df.groupby('聚类簇').agg({
                    '学号': 'count',
                    '平均成绩': 'mean',
                    '标准差': 'mean',
                    '斜率': 'mean'
                }).round(2)
                cluster_summary['聚类说明'] = status_df.groupby('聚类簇')['聚类说明'].first()
                cluster_summary.to_excel(writer, sheet_name='聚类分析', index=True)

        return status_df

    def analyze_academic_warning(self):
        """
        学业警示分析：
        1. 计算每个学年学期（夏季+秋季合并）的学分
        2. 标记未修满12学分的学生为"学业警示"
        3. 使用随机森林进行成绩预警分析
        """
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_squared_error, r2_score

        # 准备数据
        df_calc = self.df.copy()

        # 获取学号和姓名
        df_calc['_学号'] = df_calc.apply(self._get_student_id, axis=1)
        df_calc['_姓名'] = df_calc[self.column_mapping.get('姓名')].astype(str).str.strip()
        df_calc['_计算成绩'] = df_calc.apply(self._convert_score, axis=1)
        df_calc['_学分'] = df_calc.apply(self._get_credit, axis=1)

        # 检查是否有学期字段
        if '学年学期' not in self.column_mapping:
            # 返回6个值，第一个为None表示失败
            return None, None, None, None, None, "错误：缺少学期字段，无法进行学业警示分析"

        sem_col = self.column_mapping['学年学期']

        # ============ 1. 合并同一年度的夏季学期和秋季学期 ============
        df_calc['_合并学期'] = df_calc[sem_col].apply(self._merge_summer_autumn_semester)

        # ============ 2. 筛选出通过的成绩（≥60分） ============
        df_passed = df_calc[df_calc['_计算成绩'] >= 60].copy()

        # ============ 3. 计算每个学生每个合并学期的通过学分总和 ============
        if len(df_passed) == 0:
            return None, None, None, None, None, "没有找到通过的课程记录"

        semester_credits = df_passed.groupby(['_学号', '_合并学期'])['_学分'].sum().reset_index()
        semester_credits.columns = ['_学号', '学期', '通过学分']
        semester_credits['学号'] = semester_credits['_学号']
        semester_credits['学业警示'] = semester_credits['通过学分'] < 12

        # ============ 4. 汇总每个学生的警示情况 ============
        warning_summary = semester_credits.groupby('学号').agg({
            '学期': list,
            '通过学分': list,
            '学业警示': lambda x: list(x)
        }).reset_index()

        # 添加姓名
        name_map = df_calc.groupby('_学号')['_姓名'].first().to_dict()
        warning_summary['姓名'] = warning_summary['学号'].map(name_map)

        # 计算警示次数和最近警示
        warning_summary['学业警示次数'] = warning_summary['学业警示'].apply(lambda x: sum(x))
        warning_summary['最近有学业警示'] = warning_summary.apply(
            lambda row: any(row['学业警示'][-2:]) if len(row['学业警示']) >= 2 else any(row['学业警示']),
            axis=1
        )

        # ============ 5. 构建特征用于随机森林预测 ============
        features = []
        targets = []
        student_ids = []

        # 自定义学期排序函数
        def semester_sort_key(sem):
            s = str(sem)
            if '秋季学期' in s:
                try:
                    year = int(''.join(filter(str.isdigit, s)))
                    return (year, 1)
                except:
                    return (0, 1)
            elif '春季学期' in s:
                try:
                    year = int(''.join(filter(str.isdigit, s)))
                    return (year, 2)
                except:
                    return (0, 2)
            else:
                return (0, 0)

        for student_id, student_df in df_calc.groupby('_学号'):
            # 按合并学期排序
            student_merged = student_df.groupby('_合并学期').agg({
                '_计算成绩': 'mean',
                '_学分': 'sum'
            }).reset_index()

            student_merged['_排序键'] = student_merged['_合并学期'].apply(semester_sort_key)
            student_merged = student_merged.sort_values('_排序键').drop('_排序键', axis=1)

            if len(student_merged) >= 3:
                for i in range(len(student_merged) - 1):
                    prev_scores = student_merged['_计算成绩'].values[:i + 1]
                    prev_credits = student_merged['_学分'].values[:i + 1]

                    feature = [
                        np.mean(prev_scores),
                        np.std(prev_scores) if len(prev_scores) > 1 else 0,
                        prev_scores[-1] if len(prev_scores) > 0 else 0,
                        np.mean(prev_credits),
                        len(prev_scores),
                        np.polyfit(range(len(prev_scores)), prev_scores, 1)[0] if len(prev_scores) > 1 else 0
                    ]
                    features.append(feature)
                    targets.append(student_merged['_计算成绩'].values[i + 1])
                    student_ids.append(student_id)

        if len(features) < 10:
            return warning_summary, None, None, None, None, f"数据不足，无法进行随机森林分析（需要至少10个样本，当前{len(features)}个）"

        X = np.array(features)
        y = np.array(targets)

        # ============ 6. 训练随机森林模型 ============
        try:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            rf_model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=5)
            rf_model.fit(X_train, y_train)

            # ============ 7. 模型评估 ============
            y_pred = rf_model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            # ============ 8. 特征重要性分析 ============
            feature_names = ['历史平均成绩', '成绩波动', '最近成绩', '平均学分', '学期数', '成绩趋势']
            feature_importance = pd.DataFrame({
                '特征': feature_names,
                '重要性': rf_model.feature_importances_
            }).sort_values('重要性', ascending=False)

            # ============ 9. 为当前学期生成预警 ============
            latest_predictions = []
            for student_id, student_df in df_calc.groupby('_学号'):
                student_merged = student_df.groupby('_合并学期').agg({
                    '_计算成绩': 'mean',
                    '_学分': 'sum'
                }).reset_index()

                student_merged['_排序键'] = student_merged['_合并学期'].apply(semester_sort_key)
                student_merged = student_merged.sort_values('_排序键').drop('_排序键', axis=1)

                if len(student_merged) >= 2:
                    prev_scores = student_merged['_计算成绩'].values
                    prev_credits = student_merged['_学分'].values

                    latest_feature = [
                        np.mean(prev_scores),
                        np.std(prev_scores) if len(prev_scores) > 1 else 0,
                        prev_scores[-1],
                        np.mean(prev_credits),
                        len(prev_scores),
                        np.polyfit(range(len(prev_scores)), prev_scores, 1)[0] if len(prev_scores) > 1 else 0
                    ]

                    pred_score = rf_model.predict([latest_feature])[0]
                    student_name = student_df.iloc[0]['_姓名']

                    if pred_score < 60:
                        warning_level = '🔴 严重预警'
                    elif pred_score < 70:
                        warning_level = '🟠 中等预警'
                    elif pred_score < 75:
                        warning_level = '🟡 关注'
                    else:
                        warning_level = '🟢 安全'

                    latest_predictions.append({
                        '学号': student_id,
                        '姓名': student_name,
                        '预测下一学期成绩': round(pred_score, 2),
                        '预警等级': warning_level,
                        '当前平均分': round(np.mean(prev_scores), 2),
                        '趋势斜率': round(latest_feature[5], 3)
                    })

            prediction_df = pd.DataFrame(latest_predictions)

            # 返回6个值：warning_summary, feature_importance, prediction_df, rf_model, mse, r2
            return warning_summary, feature_importance, prediction_df, rf_model, mse, r2

        except Exception as e:
            return warning_summary, None, None, None, None, f"模型训练失败: {str(e)}"


    def plot_feature_importance(self, feature_importance):
        """绘制特征重要性图（英文版，确保显示）"""
        import matplotlib.pyplot as plt

        # 使用英文字体
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False

        # 将特征名称翻译为英文
        name_map = {
            '历史平均成绩': 'Historical Avg',
            '成绩波动': 'Volatility',
            '最近成绩': 'Recent Score',
            '平均学分': 'Avg Credits',
            '学期数': 'Semesters',
            '成绩趋势': 'Trend'
        }

        # 创建英文特征名称
        feature_names_en = [name_map.get(name, name) for name in feature_importance['特征']]

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = plt.cm.RdYlGn(feature_importance['重要性'].values / feature_importance['重要性'].max())
        bars = ax.barh(feature_names_en, feature_importance['重要性'], color=colors)

        for i, (bar, val) in enumerate(zip(bars, feature_importance['重要性'])):
            ax.text(val + 0.01, bar.get_y() + bar.get_height() / 2, f'{val:.3f}',
                    va='center', fontsize=10, fontweight='bold')

        ax.set_xlabel('Importance', fontsize=12, fontweight='bold')
        ax.set_title('Random Forest Feature Importance', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')

        plt.tight_layout()
        return fig

    def plot_student_trend(self, student_id, save_path=None):
        """绘制单个学生的成绩趋势图（纯英文版本，确保显示）"""

        # 获取学生数据
        df_calc = self.df.copy()
        df_calc['_学号'] = df_calc.apply(self._get_student_id, axis=1)
        df_calc['_计算成绩'] = df_calc.apply(self._convert_score, axis=1)

        student_df = df_calc[df_calc['_学号'] == str(student_id)].copy()
        if student_df.empty:
            return None

        student_name = student_df.iloc[0][self.column_mapping.get('姓名')]

        # 按学期排序
        if '学年学期' in self.column_mapping:
            sem_col = self.column_mapping['学年学期']
            try:
                student_df['_学期序号'] = student_df[sem_col].apply(
                    lambda x: float(str(x).split('-')[-1]) if '-' in str(x) else 0
                )
                student_df = student_df.sort_values('_学期序号')
            except:
                student_df = student_df.sort_values(sem_col)
        # 按学期聚合成绩 - 获取每个学期的平均分
        if '学年学期' in self.column_mapping:
            sem_col = self.column_mapping['学年学期']
            # 按学期分组计算平均分
            semester_avg = student_df.groupby(sem_col)['_计算成绩'].mean().reset_index()
            semester_avg = semester_avg.sort_values(sem_col)  # 按学期排序

            scores = semester_avg['_计算成绩'].values
            if len(scores) < 2:
                return None

            # 创建学期标签（取学期代码的后几位）
            x_labels = []
            for s in semester_avg[sem_col].values:
                s_str = str(s)
                if len(s_str) > 5:
                    x_labels.append(s_str[-5:])  # 取最后5个字符
                else:
                    x_labels.append(s_str)
        else:
            # 如果没有学期字段，才使用课程序号
            scores = student_df['_计算成绩'].dropna().values
            if len(scores) < 2:
                return None
            x_labels = [f'Sem {i + 1}' for i in range(len(scores))]

        # 创建图形
        fig, ax = plt.subplots(figsize=(12, 7))

        # 使用最通用的字体设置（纯英文字体）
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False

        # 绘制成绩折线图
        x = np.arange(len(scores))
        ax.plot(x, scores, 'o-', linewidth=2.5, markersize=10, color='#3498db',
                label='Score', markeredgecolor='white', markeredgewidth=1)

        # 添加趋势线
        if len(scores) >= 2:
            z = np.polyfit(x, scores, 1)
            p = np.poly1d(z)
            ax.plot(x, p(x), "--", color='#e74c3c', linewidth=2,
                    label=f'Trend (slope={z[0]:.2f})')

        # 设置图表（全部使用英文）
        ax.set_xlabel('Exam Order', fontsize=14, fontweight='bold')
        ax.set_ylabel('Score', fontsize=14, fontweight='bold')
        ax.set_title(f'{student_id} {student_name} Score Trend', fontsize=16, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, rotation=45, fontsize=11)
        ax.tick_params(axis='y', labelsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(fontsize=12, framealpha=0.9)

        # 添加成绩区域标记（英文）
        ax.axhspan(85, 100, alpha=0.15, color='green', label='Excellent')
        ax.axhspan(70, 85, alpha=0.15, color='yellow', label='Good')
        ax.axhspan(60, 70, alpha=0.15, color='orange', label='Pass')
        ax.axhspan(0, 60, alpha=0.15, color='red', label='Fail')

        # 设置y轴范围
        ax.set_ylim(max(0, min(scores) - 5), min(100, max(scores) + 5))

        # 添加成绩数值标签
        for i, score in enumerate(scores):
            ax.annotate(f'{score:.1f}', (x[i], score), textcoords="offset points",
                        xytext=(0, 10), ha='center', fontsize=10, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()
            return save_path
        else:
            return fig

    def create_encrypted_zip(self, student_details_dir, password_file_path):
        """
        为每位学生的计算明细创建加密压缩包

        Args:
            student_details_dir: 包含学生明细文件的目录
            password_file_path: 包含姓名和密码的Excel文件路径
        """
        import os
        import pandas as pd
        import zipfile
        from io import BytesIO

        # 检查7-Zip是否可用
        seven_zip_path = self._find_7zip_executable()
        has_7zip = seven_zip_path is not None
        if not has_7zip:
            st.warning("⚠️ 未检测到7-Zip，将使用Python内置的ZIP加密（安全性较低）")

        try:
            # 读取密码文件
            df = pd.read_excel(password_file_path, sheet_name=0, header=0)
            # 假设Excel有两列：姓名 和 密码
            password_dict = dict(zip(df.iloc[:, 0].astype(str), df.iloc[:, 1].astype(str)))
            st.success(f"✅ 成功读取密码文件，共 {len(password_dict)} 组密码")
        except Exception as e:
            st.error(f"❌ 读取密码文件失败：{str(e)}")
            return None

        # 创建临时目录存放加密后的文件
        encrypted_dir = tempfile.mkdtemp()
        success_count = 0
        failed_files = []

        # 获取所有学生明细文件
        detail_files = [f for f in os.listdir(student_details_dir)
                        if f.endswith('.xlsx') and '计算明细' in f]

        with st.spinner(f"正在为 {len(detail_files)} 位学生创建加密压缩包..."):
            progress_bar = st.progress(0)

            for i, filename in enumerate(detail_files):
                progress_bar.progress((i + 1) / len(detail_files))

                # 从文件名中提取姓名（文件名格式：学号_姓名_班级_计算明细.xlsx）
                try:
                    # 假设文件名格式：23040031037_张三_卓越班_计算明细.xlsx
                    parts = filename.split('_')
                    if len(parts) >= 2:
                        student_name = parts[1]  # 第二部分是姓名
                    else:
                        # 如果格式不匹配，跳过
                        continue
                except:
                    failed_files.append(f"{filename} (无法提取姓名)")
                    continue

                # 查找对应的密码
                password = None
                for name in password_dict:
                    if student_name in name or name in student_name:
                        password = password_dict[name]
                        break

                if not password:
                    failed_files.append(f"{filename} (未找到密码)")
                    continue

                source_path = os.path.join(student_details_dir, filename)
                # 创建加密压缩包
                zip_filename = f"{student_name}_评审细则.zip"
                zip_path = os.path.join(encrypted_dir, zip_filename)

                try:
                    if has_7zip:
                        # 使用7-Zip创建加密压缩包
                        success = self._create_7z_encrypted_zip(source_path, zip_path, password, seven_zip_path)
                    else:
                        # 使用Python内置的ZIP加密（简单密码保护）
                        success = self._create_python_encrypted_zip(source_path, zip_path, password)

                    if success:
                        success_count += 1
                    else:
                        failed_files.append(f"{filename} (加密失败)")
                except Exception as e:
                    failed_files.append(f"{filename} (错误: {str(e)[:50]})")

        # 创建最终下载的压缩包（包含所有加密后的文件）
        final_zip_buffer = BytesIO()
        with zipfile.ZipFile(final_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in os.listdir(encrypted_dir):
                if filename.endswith('.zip'):
                    file_path = os.path.join(encrypted_dir, filename)
                    zf.write(file_path, filename)

        # 清理临时文件
        import shutil
        shutil.rmtree(encrypted_dir)

        return final_zip_buffer, success_count, failed_files

    def _find_7zip_executable(self):
        """查找7-Zip程序，兼容未加入PATH的Windows默认安装路径"""
        import os
        import shutil
        import subprocess

        candidates = [
            shutil.which('7z'),
            shutil.which('7za'),
            r'C:\Program Files\7-Zip\7z.exe',
            r'C:\Program Files (x86)\7-Zip\7z.exe',
        ]

        for path in candidates:
            if not path:
                continue
            if os.path.exists(path) or shutil.which(path):
                try:
                    subprocess.run([path, '--help'], capture_output=True, check=True)
                    return path
                except Exception:
                    continue
        return None

    def _create_7z_encrypted_zip(self, source_file, zip_path, password, seven_zip_path=None):
        """使用7-Zip创建加密压缩包"""
        import subprocess

        seven_zip_path = seven_zip_path or self._find_7zip_executable() or '7z'
        try:
            # 尝试AES-256加密
            cmd = [
                seven_zip_path, 'a',
                '-tzip',
                f'-p{password}',
                '-mem=AES256',
                zip_path,
                source_file
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except:
            # 如果AES失败，尝试传统加密
            try:
                cmd = [
                    seven_zip_path, 'a',
                    '-tzip',
                    f'-p{password}',
                    zip_path,
                    source_file
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            except:
                return False

    def _create_python_encrypted_zip(self, source_file, zip_path, password):
        """使用Python内置的ZIP加密（简单密码保护）"""
        try:
            import pyzipper
            with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_DEFLATED,
                                     encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(password.encode('utf-8'))
                zf.write(source_file, os.path.basename(source_file))
            return True
        except:
            # 如果没有pyzipper，使用标准库（但标准库不支持加密）
            try:
                import zipfile
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(source_file, os.path.basename(source_file))
                st.warning(f"⚠️ {os.path.basename(source_file)} 未加密（请安装pyzipper库支持加密）")
                return True
            except:
                return False
