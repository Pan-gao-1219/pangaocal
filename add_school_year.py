"""
Add school + year fields to major_display_list entries in web.py,
and rewrite the major selection UI to group by year → school.
"""
import re

# Mapping: major_code → (school_name, year)
MAJOR_META = {
    # 2023级
    '23kg':  ('海洋地球科学学院', '2023'),
    '23dz':  ('海洋地球科学学院', '2023'),
    '23dx':  ('海洋地球科学学院', '2023'),
    # 2024级
    '24kg':      ('海洋地球科学学院', '2024'),
    '24kgzx':    ('海洋地球科学学院', '2024'),
    '24dx24':    ('海洋地球科学学院', '2024'),
    '24dz24':    ('海洋地球科学学院', '2024'),
    '24hjgc':    ('环境科学与工程学院', '2024'),
    '24hjkx':    ('环境科学与工程学院', '2024'),
    '24kuaiji':       ('管理学院', '2024'),
    '24kuaijiACCA':   ('管理学院', '2024'),
    '24gsgl':         ('管理学院', '2024'),
    '24scyx':         ('管理学院', '2024'),
    '24lygl':         ('管理学院', '2024'),
    '24cwgl':         ('管理学院', '2024'),
    '24gjmy':    ('经济学院', '2024'),
    '24wlgl':    ('经济学院', '2024'),
    '24jjx':     ('经济学院', '2024'),
    '24jrxCFA':  ('经济学院', '2024'),
    '24jrx':     ('经济学院', '2024'),
    '24dey':  ('外国语学院', '2024'),
    '24ry':   ('外国语学院', '2024'),
    '24cxy':  ('外国语学院', '2024'),
    '24fy':   ('外国语学院', '2024'),
    '24yy':   ('外国语学院', '2024'),
    '24xwx':   ('文学与新闻传播学院', '2024'),
    '24hywx':  ('文学与新闻传播学院', '2024'),
    '24wlxmt': ('文学与新闻传播学院', '2024'),
    '24fxzw':  ('法学院', '2024'),
    '24fx':    ('法学院', '2024'),
    '24ggsy':  ('国际事务与公共管理学院', '2024'),
    '24zzx':   ('国际事务与公共管理学院', '2024'),
    '24xzgl':  ('国际事务与公共管理学院', '2024'),
    '24xxjskx': ('数学科学学院', '2024'),
    '24sx':     ('数学科学学院', '2024'),
    '24xny':  ('材料科学与工程学院', '2024'),
    '24clkx': ('材料科学与工程学院', '2024'),
    '24gfz':  ('材料科学与工程学院', '2024'),
    '24ydxl': ('基础教育学院', '2024'),
    '24yybp': ('基础教育学院', '2024'),
    '24dqkx':    ('海洋与大气学院', '2024'),
    '24hykx':    ('海洋与大气学院', '2024'),
    '24hykxzw':  ('海洋与大气学院', '2024'),
    '24hykxbj':  ('崇本学堂', '2024'),
    '24sxhd':    ('海德学院', '2024'),
    '24swjshd':  ('海德学院', '2024'),
    '24spkxhd':  ('海德学院', '2024'),
    '24bmjs':    ('信息科学与工程学部', '2024'),
    '24gdxx':    ('信息科学与工程学部', '2024'),
    '24shengx':  ('信息科学与工程学部', '2024'),
    '24wdz':     ('信息科学与工程学部', '2024'),
    '24sjkx':    ('信息科学与工程学部', '2024'),
    '24znkx':    ('信息科学与工程学部', '2024'),
    '24hyjs':    ('信息科学与工程学部', '2024'),
    '24wlx':     ('信息科学与工程学部', '2024'),
    '24dzxxkx':  ('信息科学与工程学部', '2024'),
    '24dzxxgc':  ('信息科学与工程学部', '2024'),
    '24wlkjan':  ('信息科学与工程学部', '2024'),
    '24jsjkxzw': ('信息科学与工程学部', '2024'),
    '24jsjkx':   ('信息科学与工程学部', '2024'),
    '24rjgc':    ('信息科学与工程学部', '2024'),
    '24txgc':    ('信息科学与工程学部', '2024'),
    '24hxgc':    ('化学化工学院', '2024'),
    '24hx':      ('化学化工学院', '2024'),
    '24stx':  ('生命科学学院', '2024'),
    '24swjs': ('生命科学学院', '2024'),
    '24swkx': ('生命科学学院', '2024'),
    '24scyz':    ('水产学院', '2024'),
    '24hyyy':    ('水产学院', '2024'),
    '24hyzyhj':  ('水产学院', '2024'),
    '24hyzykf':  ('食品科学与工程学院', '2024'),
    '24spkxgc':  ('食品科学与工程学院', '2024'),
    '24spyy':    ('食品科学与工程学院', '2024'),
    '24yx':      ('医药学院', '2024'),
    '24tmgc':    ('工程学院', '2024'),
    '24gysj':    ('工程学院', '2024'),
    '24jxsj':    ('工程学院', '2024'),
    '24gkhd':    ('工程学院', '2024'),
    '24zdh':     ('工程学院', '2024'),
    '24cb':      ('工程学院', '2024'),
    '24lj':      ('工程学院', '2024'),
    'other':     ('其他', ''),
    'custom':    ('其他', ''),
    'custom_manual': ('其他', ''),
}

with open('E:/计算综测/pangaocal-main/web.py', encoding='utf-8') as f:
    content = f.read()

# ---- Step 1: Add school + year to each display list entry ----
def add_meta_to_entry(match):
    """Replace {'code': 'xxx', 'name': ..., 'emoji': ...} with added school/year."""
    entry_str = match.group(0)
    # Extract code
    code_match = re.search(r"'code'\s*:\s*'([^']+)'", entry_str)
    if not code_match:
        return entry_str
    code = code_match.group(1)

    # Already has school/year? skip
    if "'school'" in entry_str or "'year'" in entry_str:
        return entry_str

    meta = MAJOR_META.get(code, ('未分类', '2024'))
    school, year = meta

    # Insert school and year before the closing }
    new_entry = entry_str.rstrip('}').rstrip().rstrip(',')
    new_entry = new_entry + f", 'school': '{school}', 'year': '{year}'" + "}"
    # Preserve trailing comma if original had one
    if entry_str.rstrip().endswith(','):
        new_entry += ','
    return new_entry

# Match display list entries: {'code': '...', 'name': '...', 'emoji': '...'},
entry_pattern = re.compile(r"\{[^{}]*'code'\s*:\s*'[^']*'[^{}]*\}", re.DOTALL)
content = entry_pattern.sub(add_meta_to_entry, content)

# ---- Step 2: Replace UI major selection section ----
old_ui = """    # 获取所有专业列表
    major_list = calc.major_config.get_all_majors()

    # 动态生成列
    cols = st.columns(len(major_list))

    for i, major in enumerate(major_list):
        with cols[i]:
            if st.button(
                    f"{major['emoji']} {major['name']}",
                    use_container_width=True,
                    type="primary" if st.session_state.major_code == major['code'] else "secondary"
            ):
                st.session_state.major_code = major['code']
                success, major_name = calc.set_major(major['code'])
                if success:
                    st.session_state.major_name = major_name
                    st.session_state.has_excellent_class = calc.has_excellent_class
                    st.session_state.excellent_students = calc.excellent_students
                    st.session_state.current_major = calc.current_major  # 新增：保存当前专业配置
                    st.session_state.calc = calc
                    st.session_state.just_selected_major = True
                st.rerun()"""

new_ui = """    # 获取所有专业列表
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
                        success, major_name = calc.set_major(major['code'])
                        if success:
                            st.session_state.major_name = major_name
                            st.session_state.has_excellent_class = calc.has_excellent_class
                            st.session_state.excellent_students = calc.excellent_students
                            st.session_state.current_major = calc.current_major
                            st.session_state.calc = calc
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
                    success, major_name = calc.set_major(major['code'])
                    if success:
                        st.session_state.major_name = major_name
                        st.session_state.has_excellent_class = calc.has_excellent_class
                        st.session_state.excellent_students = calc.excellent_students
                        st.session_state.current_major = calc.current_major
                        st.session_state.calc = calc
                        st.session_state.just_selected_major = True
                    st.rerun()"""

assert old_ui in content, "Old UI section not found! Check whitespace."
content = content.replace(old_ui, new_ui)

with open('E:/计算综测/pangaocal-main/web.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")

# Verify syntax
import ast
with open('E:/计算综测/pangaocal-main/web.py', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    print("Syntax OK ✓")
except SyntaxError as e:
    print(f"Syntax Error: {e}")

# Verify entries got school/year
import re
entries_with_school = re.findall(r"'school'\s*:", src)
print(f"Entries with 'school' field: {len(entries_with_school)}")
