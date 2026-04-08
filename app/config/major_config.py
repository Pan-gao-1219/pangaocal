# -*- coding: utf-8 -*-
"""
MajorConfig 类 — 聚合所有年级专业配置。

设计原则：
  - 25级 自动继承 24级 培养方案（选修课/学分要求完全相同）
  - 22级 自动继承 23级 培养方案
  - 显示顺序：25级 → 24级 → 23级 → 22级 → 自定义
  - 新增专业：只需编辑 majors_24.py 或 majors_23.py，此文件无需改动
  - 新增年级（如26级）：在 __init__ 中参照25级添加别名两行即可
"""

from app.config.majors_24 import MAJORS_24, DISPLAY_24
from app.config.majors_23 import MAJORS_23, DISPLAY_23

# ===== 其他/自定义专业 =====
_OTHER_MAJORS = {
    'other': {
        '专业名称': '其他班级（仅综测）',
        '专业代码': 'other',
        '有卓越班': False,
        '学分要求': {'学科基础课程': 0.0, '专业知识课程': 0.0, '工作技能课程': 0.0},
        '选修课列表': {'学科基础课程': [], '专业知识课程': [], '工作技能课程': []},
    }
}

_DISPLAY_OTHER = [
    {'code': 'custom', 'name': '其他专业（若想加入到系统中请联系我）',
     'emoji': '⚡', 'school': '其他', 'year': ''},
]


def _make_year_alias(source_majors: dict, old_year: str, new_year: str) -> dict:
    """
    将旧年级所有配置复制为新年级别名。
    - 学分要求、选修课列表 与原配置共享（培养方案相同）
    - 有卓越班的专业：别名年级设为 False（学号集暂未录入）
    - 若已知新年级卓越班名单，在各自 majors_XX.py 中显式添加配置即可覆盖
    """
    aliases = {}
    for code, cfg in source_majors.items():
        new_code = new_year + code[len(old_year):]
        old_name = cfg.get('专业名称', code)
        new_name = (new_year + old_name[len(old_year):]
                    if old_name.startswith(old_year) else old_name)
        alias = dict(cfg)
        alias['专业代码'] = new_code
        alias['专业名称'] = new_name
        alias['有卓越班'] = False
        alias.pop('卓越班级学号集', None)
        aliases[new_code] = alias
    return aliases


def _make_display_alias(source_display: list, old_year: str, new_year: str) -> list:
    """将旧年级显示列表生成新年级别名。"""
    result = []
    for entry in source_display:
        new_entry = dict(entry)
        new_entry['code'] = new_year + entry['code'][len(old_year):]
        name = entry.get('name', '')
        new_entry['name'] = (new_year + name[len(old_year):]
                             if name.startswith(old_year) else name)
        new_entry['year'] = new_year
        result.append(new_entry)
    return result


# 自动生成 25级（继承24级）和 22级（继承23级）
_MAJORS_25 = _make_year_alias(MAJORS_24, '24', '25')
_MAJORS_22 = _make_year_alias(MAJORS_23, '23', '22')
_DISPLAY_25 = _make_display_alias(DISPLAY_24, '24', '25')
_DISPLAY_22 = _make_display_alias(DISPLAY_23, '23', '22')


class MajorConfig:
    """
    所有专业配置的唯一入口。

    使用方式：
        mc = MajorConfig()
        cfg = mc.get_major('24hykx')   # 获取单个专业配置
        all_list = mc.get_all_majors() # 获取完整显示列表（用于按钮渲染）
    """

    def __init__(self):
        # 合并顺序决定了代码冲突时谁优先：后者覆盖前者
        # 25/22级别名放在最前，允许 majors_24/23 中的显式条目覆盖
        self.majors = {
            **_MAJORS_25,
            **MAJORS_24,
            **_MAJORS_22,
            **MAJORS_23,
            **_OTHER_MAJORS,
        }
        # 显示顺序：最新年级在前，方便当年用户快速找到
        self.major_display_list = (
            _DISPLAY_25 + DISPLAY_24 + DISPLAY_23 + _DISPLAY_22 + _DISPLAY_OTHER
        )

    def get_major(self, major_code: str) -> dict | None:
        """根据专业代码获取配置，未找到返回 None。"""
        return self.majors.get(major_code)

    def get_all_majors(self) -> list:
        """获取全部专业显示列表（用于 UI 按钮渲染）。"""
        return self.major_display_list
