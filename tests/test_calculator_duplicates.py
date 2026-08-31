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
            '学分': '学分',
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
            '学分': 6.0,
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

    def test_comprehensive_evaluation_keeps_duplicate_valid_courses(self):
        grades = pd.DataFrame([
            {
                '学号': '22040031044', '姓名': '王千寻',
                **self._row(8401101045, '高等数学Ⅰ1', 70),
            },
            {
                '学号': '22040031044', '姓名': '王千寻',
                **self._row(8401101045, '高等数学Ⅰ1', 63.5),
            },
        ])
        self.calculator.column_mapping.update({'学号': '学号', '姓名': '姓名'})
        self.calculator.set_major('23kg')

        result = self.calculator.calculate_student_gpa(grades, calc_mode='综测')

        self.assertEqual(result['课程门数'], 2)
        self.assertEqual(result['总学分'], 12)
        self.assertEqual(result['平均成绩'], 66.75)

    def test_earth_sciences_low_credit_penalty_is_optional(self):
        grades = pd.DataFrame([
            {
                '学号': '22040031044', '姓名': '王千寻', '学年学期': '2024秋季学期',
                '课程性质': '必修',
                **self._row('A001', '高等数学Ⅰ1', 80),
            },
            {
                '学号': '22040031044', '姓名': '王千寻', '学年学期': '2024秋季学期',
                '课程性质': '限选',
                **self._row('A002', '大学英语Ⅰ', 80),
            },
            {
                '学号': '22040031044', '姓名': '王千寻', '学年学期': '2024秋季学期',
                '课程性质': '任选',
                **self._row('A003', '任选课程', 80),
            },
        ])
        grades.loc[0, '学分'] = 5
        grades.loc[1, '学分'] = 5
        grades.loc[2, '学分'] = 2
        self.calculator.column_mapping.update({
            '学号': '学号', '姓名': '姓名', '学年学期': '学年学期',
            '课程性质': '课程性质',
        })
        self.calculator.set_major('23kg')

        disabled = self.calculator.calculate_student_gpa(
            grades, calc_mode='综测', apply_low_credit_penalty=False
        )
        enabled = self.calculator.calculate_student_gpa(
            grades, calc_mode='综测', apply_low_credit_penalty=True
        )
        penalty, details = self.calculator._calculate_low_credit_penalty(grades)

        self.assertEqual(disabled['低学分扣分'], 0)
        self.assertEqual(disabled['综测成绩'], 80)
        self.assertEqual(enabled['低学分扣分'], 0)
        self.assertEqual(enabled['综测成绩'], 80)
        self.assertEqual(enabled['低学分扣分明细'], '无')
        self.assertEqual(penalty, 0)
        self.assertEqual(details[0]['通过学分'], 12)

    def test_low_credit_penalty_cannot_apply_to_other_schools(self):
        grades = pd.DataFrame([{
            '学号': '23000000001', '姓名': '测试学生', '学年学期': '2024秋季学期',
            **self._row('A001', '高等数学Ⅰ1', 80),
        }])
        grades.loc[0, '学分'] = 6
        self.calculator.column_mapping.update({
            '学号': '学号', '姓名': '姓名', '学年学期': '学年学期'
        })
        self.calculator.set_major('23sx')

        result = self.calculator.calculate_student_gpa(
            grades,
            calc_mode='综测',
            apply_low_credit_penalty=True,
            apply_course_credit_bonus=True,
        )

        self.assertEqual(result['课程学分加分'], 0)
        self.assertEqual(result['低学分扣分'], 0)
        self.assertEqual(result['综测成绩'], 80)

    def test_earth_sciences_course_credit_bonus_is_optional(self):
        grades = pd.DataFrame([
            {
                '学号': '22040031044', '姓名': '王千寻', '学年学期': '2024夏季学期',
                '课程性质': '必修',
                **self._row('B001', '高等数学Ⅰ1', 80),
            },
            {
                '学号': '22040031044', '姓名': '王千寻', '学年学期': '2024秋季学期',
                '课程性质': '限选',
                **self._row('B002', '专业限选课', 80),
            },
            {
                '学号': '22040031044', '姓名': '王千寻', '学年学期': '2024秋季学期',
                '课程性质': '任选',
                **self._row('B003', '任选课程', 80),
            },
        ])
        grades.loc[0, '学分'] = 4
        grades.loc[1, '学分'] = 8
        grades.loc[2, '学分'] = 2
        self.calculator.column_mapping.update({
            '学号': '学号', '姓名': '姓名', '学年学期': '学年学期',
            '课程性质': '课程性质',
        })
        self.calculator.set_major('23kg')

        disabled = self.calculator.calculate_student_gpa(
            grades, calc_mode='综测', apply_course_credit_bonus=False
        )
        enabled = self.calculator.calculate_student_gpa(
            grades,
            calc_mode='综测',
            apply_low_credit_penalty=True,
            apply_course_credit_bonus=True,
        )

        self.assertEqual(disabled['课程学分加分'], 0)
        self.assertEqual(disabled['综测成绩'], 80)
        self.assertEqual(enabled['课程学分加分'], 2.4)
        self.assertEqual(enabled['低学分扣分'], 0)
        self.assertEqual(enabled['综测成绩'], 82.4)
        self.assertIn(
            '2024秋季学期：通过14学分（其中任选课2学分计入12学分门槛：任选课程），'
            '必修及限选课12学分，加2.4分',
            enabled['课程学分加分明细'],
        )

    def test_passing_retake_counts_when_recovering_unearned_credit(self):
        grades = pd.DataFrame([
            {
                '学号': '22040031044', '姓名': '王千寻', '学年学期': '2026春季学期',
                **self._row('C001', '正常课程', 80),
            },
            {
                '学号': '22040031044', '姓名': '王千寻', '学年学期': '2026春季学期',
                **self._row('C002', '补回学分课程', 75, '重修取得', '重修'),
            },
        ])
        grades.loc[0, '学分'] = 9
        grades.loc[1, '学分'] = 3
        self.calculator.column_mapping.update({
            '学号': '学号', '姓名': '姓名', '学年学期': '学年学期'
        })
        self.calculator.set_major('23kg')

        result = self.calculator.calculate_student_gpa(
            grades,
            calc_mode='综测',
            apply_low_credit_penalty=True,
            apply_course_credit_bonus=True,
        )

        self.assertEqual(result['总学分'], 12)
        self.assertEqual(result['平均成绩'], 78.75)
        self.assertEqual(result['课程学分加分'], 2.4)
        self.assertEqual(result['低学分扣分'], 0)
        self.assertIn(
            '2026春季学期：通过12学分，必修及限选课12学分，加2.4分',
            result['课程学分加分明细'],
        )

    def test_retake_does_not_repeat_credit_already_earned_in_input(self):
        grades = pd.DataFrame([
            {
                '学号': '22040031044', '姓名': '王千寻', '学年学期': '2026春季学期',
                **self._row('D001', '正常课程', 80),
            },
            {
                '学号': '22040031044', '姓名': '王千寻', '学年学期': '2026春季学期',
                **self._row('D002', '已获学分课程', 70),
            },
            {
                '学号': '22040031044', '姓名': '王千寻', '学年学期': '2026春季学期',
                **self._row('D002', '已获学分课程', 90, '重修取得', '重修'),
            },
        ])
        grades.loc[0, '学分'] = 9
        grades.loc[1, '学分'] = 3
        grades.loc[2, '学分'] = 3
        self.calculator.column_mapping.update({
            '学号': '学号', '姓名': '姓名', '学年学期': '学年学期'
        })
        self.calculator.set_major('23kg')

        result = self.calculator.calculate_student_gpa(
            grades,
            calc_mode='综测',
            apply_course_credit_bonus=True,
        )
        bonus, details = self.calculator._calculate_course_credit_bonus(grades)

        self.assertEqual(result['总学分'], 12)
        self.assertEqual(result['平均成绩'], 77.5)
        self.assertAlmostEqual(bonus, 2.4)
        self.assertEqual(details[0]['通过学分'], 12)


if __name__ == '__main__':
    unittest.main()
