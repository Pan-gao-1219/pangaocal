import unittest

import pandas as pd

from app.core.calculator import StudentGradeCalculator


class DuplicateCourseTests(unittest.TestCase):
    def setUp(self):
        self.calculator = StudentGradeCalculator(df=pd.DataFrame())
        self.calculator.column_mapping = {
            '课程编号': '课程编号',
            '课程名称': '课程名称',
            '总成绩': '总成绩',
            '取得方式': '取得方式',
            '修读类型': '修读类型',
        }

    @staticmethod
    def _row(code, name, score, acquire='初修取得', attempt='初修'):
        return {
            '课程编号': code,
            '课程名称': name,
            '总成绩': score,
            '取得方式': acquire,
            '修读类型': attempt,
            '_计算成绩': float(score),
            '_学分': 6.0,
        }

    def test_duplicate_initial_records_keep_first_valid_record(self):
        grades = pd.DataFrame([
            self._row(8401101045, '高等数学Ⅰ1', 70),
            self._row(8401101045, '高等数学Ⅰ1', 63.5),
        ])

        dropped = self.calculator._handle_duplicate_courses(grades)

        self.assertEqual(dropped, {1})
        self.assertEqual(len(grades), 1)
        self.assertEqual(grades.iloc[0]['_计算成绩'], 70)
        self.assertEqual(grades['_学分'].sum(), 6)

        detail_rows = self.calculator._analyze_duplicate_courses(pd.DataFrame([
            self._row(8401101045, '高等数学Ⅰ1', 70),
            self._row(8401101045, '高等数学Ⅰ1', 63.5),
        ]))
        self.assertEqual(detail_rows[0]['处理结果'], '保留第一条有效初修成绩')
        self.assertEqual(detail_rows[1]['处理结果'], '同一课程号重复的初修记录，不重复计入')

    def test_same_course_number_deduplicates_even_if_name_format_differs(self):
        grades = pd.DataFrame([
            self._row(8401101045.0, '高等数学Ⅰ1', 70),
            self._row('8401101045', '高等数学 I 1', 63.5),
        ])

        self.calculator._handle_duplicate_courses(grades)

        self.assertEqual(len(grades), 1)
        self.assertEqual(grades.iloc[0]['_计算成绩'], 70)

    def test_passing_makeup_replaces_initial_and_is_capped_at_60(self):
        grades = pd.DataFrame([
            self._row('A001', '大学英语Ⅱ', 54),
            self._row('A001', '大学英语Ⅱ', 78, '补考取得', '补考'),
        ])

        self.calculator._handle_duplicate_courses(grades)

        self.assertEqual(len(grades), 1)
        self.assertEqual(grades.iloc[0]['_计算成绩'], 60)
        self.assertEqual(grades.iloc[0]['取得方式'], '补考取得')

    def test_23kg_non_excellent_student_uses_ordinary_requirements(self):
        ok, _ = self.calculator.set_major('23kg')

        self.assertTrue(ok)
        self.assertEqual(self.calculator._get_student_class('22040031044'), '普通')
        self.assertEqual(
            self.calculator._get_credit_requirements('普通'),
            {'学科基础课程': 4.0, '专业知识课程': 4.0, '工作技能课程': 2.0},
        )
        ordinary_courses = self.calculator._get_elective_courses('普通')
        self.assertIn('Python程序设计与实践', ordinary_courses['学科基础课程'])
        self.assertIn('海洋地球物理探测技术', ordinary_courses['专业知识课程'])
        self.assertIn('地球物理软件设计实习', ordinary_courses['工作技能课程'])


if __name__ == '__main__':
    unittest.main()
