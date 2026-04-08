# -*- coding: utf-8 -*-
"""通识课程数据库加载模块"""
import os
import pandas as pd
import streamlit as st


@st.cache_data
def load_tongshi_db():
    """加载通识课程数据库 Excel，返回 DataFrame（全量课程 Sheet）
    文件路径：pangaocal-main/通识课程数据库.xlsx
    """
    # app/core/tongshi.py → 上两级目录 = pangaocal-main/
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, '通识课程数据库.xlsx')
    if not os.path.exists(db_path):
        return None
    df = pd.read_excel(db_path, sheet_name='全量课程', dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df['课程名'] = df['课程名'].str.strip()
    df['2024级模块'] = df['2024级模块'].str.strip()
    df['2023级模块'] = df['2023级模块'].str.strip()
    df['学分'] = pd.to_numeric(df['学分'], errors='coerce').fillna(0)
    return df
