# -*- coding: utf-8 -*-
"""
更新 majors_24.py 和 majors_23.py
数据来源：
  - 24级：new_configs_24_fixed.py（从PDF提取），summary.txt 补充空课程列表
  - 23级：new_configs_23.py（从2022版PDF提取）
保留：24kg 和 23kg 的卓越班学号集
处理：移除重复 code（24shengx→24sx_aud, 24dx24→24dx, 24xny→24xnnclqj）
"""
import sys, re, ast, json
sys.stdout.reconfigure(encoding='utf-8')

# ========================= 加载24级数据 =========================
with open('new_configs_24_fixed.py', encoding='utf-8') as f:
    ns = {}
    exec(f.read(), ns)
configs24 = ns['NEW_CONFIGS_24']  # {code: {...}}

# ========================= 从 summary.txt 补充课程列表 =========================
def parse_summary():
    """解析 summary.txt，返回 {major_name: {cat: {credit, courses}}}"""
    with open('summary.txt', encoding='utf-8', errors='replace') as f:
        content = f.read()
    majors = {}
    current_major = None
    current_cat = None
    for line in content.split('\n'):
        if line.startswith('  专业: '):
            current_major = line[6:].strip()
            majors[current_major] = {}
        elif current_major and re.match(r'    [学专工]', line):
            m = re.match(r'    (.+?): 最低选修([\d.]+)学分', line)
            if m:
                current_cat = m.group(1)
                majors[current_major][current_cat] = {'credit': float(m.group(2)), 'courses': []}
        elif current_major and current_cat and '选修课: ' in line:
            raw = line.split('选修课: ', 1)[1].strip()
            if '未提取到' in raw:
                majors[current_major][current_cat]['courses'] = None
            else:
                courses = [c.strip() for c in raw.split(', ') if c.strip()]
                majors[current_major][current_cat]['courses'] = courses
    return majors

summary_data = parse_summary()

# summary major name → 24级 code 的映射
SUMMARY_TO_CODE = {
    '环境工程': '24hjgc',
    '环境科学': '24hjkx',
    '会计学': '24kuaiji',
    '会计学（ACCA方向）': '24kuaijiACCA',
    '工商管理（数字化创新管理方向）': '24gsgl',
    '市场营销（数智营销管理方向）': '24scyx',
    '旅游管理': '24lygl',
    '财务管理': '24cwgl',
    '国际经济与贸易': '24gjmy',
    '物流管理': '24wlgl',
    '经济学（海洋经济方向）': '24jjx',
    '金融学(CFA)培养方案2024版.pdf': '24jrxCFA',
    '金融学': '24jrx',
    '德语': '24dey',
    '日语': '24ry',
    '朝鲜语': '24cxy',
    '法语': '24fy',
    '英语': '24yy',
    '新闻学': '24xwx',
    '汉语言文学': '24hywx',
    '网络与新媒体2024培养方案.pdf': '24wlxmt',
    '法学': '24fx',
    '法学（中外合作办学）': '24fxzw',
    '公共事业管理': '24ggsy',
    '政治学与行政学': '24zzx',
    '行政管理': '24xzgl',
    '信息与计算科学': '24xxjskx',
    '数学与应用数学': '24sx',
    '新能源材料与器件': '24xnnclqj',
    '材料科学与工程': '24clkx',
    '高分子材料与工程': '24gfz',
    '运动训练': '24ydxl',
    '音乐表演': '24yybp',
    '大气科学': '24dqkx',
    '海洋科学（中外合作）': '24hykxzw',
    '海洋科学': '24hykx',
    '中国海洋大学2024版本科人才培养方案-海洋科学拔尖.pdf': '24hykxbj',
    '数学与应用数学（中外合作办学）': '24sxhd',
    '生物技术（中外合作办学）': '24swjshd',
    '食品科学与工程（中外合作办学）': '24spkxhd',
    '保密技术': '24bmjs',
    '光电信息科学与工程': '24gdxx',
    '声学': '24sx_aud',
    '微电子科学与工程': '24wdz',
    '数据科学与大数据技术': '24sjkx',
    '智能科学与技术': '24znkx',
    '海洋技术': '24hyjs',
    '物理学': '24wlx',
    '电子信息信息科学与技术': '24dzxxkx',
    '电子信息工程': '24dzxxgc',
    '网络空间安全': '24wlkjan',
    '计算机科学与技术（中外合作办学）': '24jsjkxzw',
    '计算机科学与技术': '24jsjkx',
    '软件工程': '24rjgc',
    '通信工程': '24txgc',
    '化学': '24hx',
    '化学工程与工艺': '24hxgc',
    '勘查技术与工程（卓越班）': '24kg',
    '地球信息科学与技术': '24dx',
    '地质学': '24dz24',
    '生态学': '24stx',
    '生物技术': '24swjs',
    '生物科学': '24swkx',
    '水产养殖学': '24scyz',
    '海洋渔业科学与技术': '24hyyy',
    '海洋资源与环境': '24hyzyhj',
    '海洋资源开发技术': '24hyzykf',
    '食品科学与工程': '24spkxgc',
    '食品营养与健康': '24spyy',
    '药学': '24yx',
    '土木工程': '24tmgc',
    '工业设计': '24gysj',
    '机械设计制造及其自动化': '24jxsj',
    '港口航道与海岸工程': '24gkhd',
    '自动化': '24zdh',
    '船舶与海洋工程': '24cb',
    '轮机工程': '24lj',
}

# 合并数据：
# 学分要求：优先 summary.txt（更准确），fallback 到 new_configs
# 课程列表：优先 new_configs（更完整），补充 summary.txt 的数据
merged_credits = 0
supplemented_courses = 0
for summ_name, code in SUMMARY_TO_CODE.items():
    if code not in configs24:
        continue
    if summ_name not in summary_data:
        continue
    cfg = configs24[code]
    summ = summary_data[summ_name]
    for cat in ['学科基础课程', '专业知识课程', '工作技能课程']:
        if cat not in summ:
            continue
        summ_info = summ[cat]
        # 更新学分要求：用 summary.txt 的值（更准确）
        summ_credit = summ_info['credit']
        cfg_credit = cfg['学分要求'].get(cat, 0.0)
        if summ_credit != cfg_credit:
            cfg['学分要求'][cat] = summ_credit
            merged_credits += 1
        # 如果 new_configs 里课程为空，且 summary 有数据，则补充
        if not cfg['选修课列表'][cat] and summ_info['courses']:
            cfg['选修课列表'][cat] = summ_info['courses']
            supplemented_courses += 1

print(f'从 summary.txt 修正了 {merged_credits} 个学分要求')
print(f'从 summary.txt 补充了 {supplemented_courses} 个课程列表')

# 手动修正 24kg 的学分要求和课程列表（PDF结构特殊，自动提取失败）
if '24kg' in configs24:
    configs24['24kg']['学分要求'] = {
        '学科基础课程': 4.0, '专业知识课程': 4.0, '工作技能课程': 2.0
    }  # 这里存普通班要求，卓越班单独处理
    configs24['24kg']['选修课列表'] = {
        '学科基础课程': ['科学计算语言与编程', 'Python程序设计与实践', '海洋地质学概论',
                      '电工电子学', '数据结构', '计算机图形学', '地理信息系统',
                      '并行编程原理与程序设计', '专业英语与科技写作', '岩石物理学基础'],
        '专业知识课程': ['地球物理测井', '油气地质学', '工程与环境地球物理',
                      '地球物理大数据与人工智能', '海洋地球物理探测技术', '计算地球物理原理',
                      '国际课程-三维地震勘探', '非常规油气勘探开发',
                      '人工智能资料处理与解释', '海洋电磁学', '地学软件工程', '地球物理前沿讲座'],
        '工作技能课程': ['地球物理技能训练', '地球物理软件设计实习', '工程实践'],
    }
    print('手动修正 24kg 学分要求和课程列表')

# ========================= 手动修正其余无法自动提取的条目 =========================
# 补充 summary.txt 用 v2 提取算法仍为空的课程列表
MANUAL_COURSE_OVERRIDES = {
    # 公共事业管理 工作技能课程 (10位代码，regex失效)
    ('24ggsy', '工作技能课程'): ['专题讲座', '面试理论与实务'],
    # 政治学与行政学 工作技能课程
    ('24zzx', '工作技能课程'): ['研究方法进阶', '秘书与写作'],
    # 新能源材料与器件 专业知识（四模块选修，选非*课程）
    ('24xnnclqj', '专业知识课程'): [
        '计算材料学', '化学电源原理及应用', '氢能原理及应用', '太阳电池原理及应用',
        '膜材料与电化学器件', '新型电池材料与器件', '电池利用与循环',
        '多孔能源与催化材料', '燃料电池技术', '储氢材料与技术',
        '光电子材料与器件', '新能源发电及并网技术', '柔性太阳能电池材料与器件',
        '材料腐蚀与防护技术', '海洋防护新材料与技术', '海水淡化新材料与技术',
        '海洋可再生能源概论', '海洋涂层技术与工艺', '海洋材料',
    ],
    # 轮机工程 工作技能课程
    ('24lj', '工作技能课程'): ['工业企业管理', '船舶电气与自动化实验', '沟通与工程写作（双语）'],
}
# 修正 24hykxbj 的学分要求（PDF实际为5学分，非summary的9学分）
if '24hykxbj' in configs24:
    configs24['24hykxbj']['学分要求']['专业知识课程'] = 5.0  # PDF确认
    print('修正 24hykxbj 专业知识课程学分: 9.0 → 5.0')

for (code, cat), courses in MANUAL_COURSE_OVERRIDES.items():
    if code in configs24 and not configs24[code]['选修课列表'].get(cat):
        configs24[code]['选修课列表'][cat] = courses
        print(f'手动补充 {code} {cat}: {len(courses)} 门课程')

# ========================= 对剩余空课程列表使用 v2 提取 =========================
import json as _json
with open('all_plans_full.json', encoding='utf-8') as _f:
    _full_data = _json.load(_f)

def _extract_v2(text, cat):
    CATS = ['学科基础课程', '专业知识课程', '工作技能课程']
    positions = [m.start() for m in re.finditer(re.escape(cat), text)]
    if not positions: return []
    idx = positions[1] if len(positions) > 1 else positions[0]
    cat_idx = CATS.index(cat)
    end_idx = len(text)
    for nc in CATS[cat_idx+1:]:
        npos = [m.start() for m in re.finditer(re.escape(nc), text)]
        for np in npos:
            if np > idx:
                end_idx = min(end_idx, np)
                break
    extend_end = min(end_idx + 1000, len(text))
    main_section = text[idx:end_idx]
    sel_markers = [m.start() for m in re.finditer(r'(?<!\S)选修(?!\S)', main_section)]
    if not sel_markers: return []
    elective_start = sel_markers[-1]
    extended_section = main_section[elective_start:] + text[end_idx:extend_end]
    lines = extended_section.split('\n')
    code_pattern = re.compile(r'^\d{12}$')
    skip_words = {'推荐','先修','讲授','课程','学时','修课','最低','其中','注：','学期',
                  '学分','必修','选修','实践','合计','要求','方向','模块','含','共','备注',
                  '工作技能课程','学科基础课程','专业知识课程','最低要求','通识'}
    courses = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line: i += 1; continue
        if code_pattern.match(line):
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt: j += 1; continue
                if code_pattern.match(nxt): break
                name = re.sub(r'^[*△◆●▲]+', '', nxt).strip()
                if (name and len(name) >= 2 and not name[0].isdigit()
                        and not any(name.startswith(w) for w in skip_words)):
                    if name not in courses: courses.append(name)
                break
            i = j; continue
        i += 1
    return courses

MISSING_V2 = [
    ('24kuaiji', '11管理', '会计学-2024培养方案.pdf', '专业知识课程'),
    ('24fy', '13外语', '法语-2024培养方案.pdf', '学科基础课程'),
    ('24clkx', '18材料', '材料科学与工程-2024培养方案.pdf', '学科基础课程'),
    ('24clkx', '18材料', '材料科学与工程-2024培养方案.pdf', '专业知识课程'),
    ('24ydxl', '19基教', '运动训练-2024培养方案.pdf', '学科基础课程'),
    ('24ydxl', '19基教', '运动训练-2024培养方案.pdf', '专业知识课程'),
    ('24dqkx', '1海气', '大气科学-2024培养方案.pdf', '学科基础课程'),
    ('24dzxxkx', '2信息', '电子信息信息科学与技术-2024培养方案.pdf', '专业知识课程'),
    ('24txgc', '2信息', '通信工程-2024培养方案.pdf', '专业知识课程'),
    ('24dx', '4地球', '地球信息科学与技术-2024培养方案.pdf', '学科基础课程'),
    ('24hyzykf', '7食品', '海洋资源开发技术-2024培养方案.pdf', '专业知识课程'),
]
v2_count = 0
for code, school, pdf, cat in MISSING_V2:
    if code not in configs24: continue
    if configs24[code]['选修课列表'].get(cat): continue  # already has data
    text = _full_data.get(school, {}).get(pdf, '')
    if not text: continue
    courses = _extract_v2(text, cat)
    if courses:
        configs24[code]['选修课列表'][cat] = courses
        v2_count += 1
print(f'v2 提取补充了 {v2_count} 个课程列表')

# ========================= 读取现有 majors_24.py 中的卓越班信息 =========================
with open('pangaocal-main/app/config/majors_24.py', encoding='utf-8') as f:
    cur24_content = f.read()

# 提取 24kg 的卓越班学号集（整段保留）
def extract_zuoyue_block(content, code):
    """返回 (卓越班级学号集 set, 显示名) 或 None"""
    pattern = rf"'{re.escape(code)}':\s*\{{[^{{}}]*?'卓越班级学号集':\s*\{{([^}}]+)\}}"
    m = re.search(pattern, content, re.DOTALL)
    if not m:
        return None
    names_str = m.group(1)
    names = re.findall(r"'([^']+)'", names_str)
    return set(names)

zuoyue_24kg = extract_zuoyue_block(cur24_content, '24kg')
print(f'24kg 卓越班学号集: {len(zuoyue_24kg) if zuoyue_24kg else 0} 人')

# ========================= 读取现有 DISPLAY_24 =========================
# DISPLAY_24 保持原有，只需要去掉旧重复 code，更新为新 code
OLD_TO_NEW_CODES = {
    '24shengx': '24sx_aud',
    '24dx24': '24dx',
    '24xny': '24xnnclqj',
}

# 从当前 majors_24.py 提取 DISPLAY_24（用 exec）
cur_ns = {}
try:
    exec(cur24_content, cur_ns)
    display24 = cur_ns.get('DISPLAY_24', [])
except:
    display24 = []

# 去重：遇到旧 code 替换为新 code（若已有新 code 则跳过旧 code）
new_display24 = []
seen_codes = set()
for entry in display24:
    code = entry.get('code', '')
    # 如果是旧重复 code，替换
    if code in OLD_TO_NEW_CODES:
        new_code = OLD_TO_NEW_CODES[code]
        if new_code not in seen_codes:
            new_entry = dict(entry)
            new_entry['code'] = new_code
            # 更新名称（去掉重复的旧名）
            new_display24.append(new_entry)
            seen_codes.add(new_code)
        # 跳过旧 code
        continue
    if code not in seen_codes:
        new_display24.append(entry)
        seen_codes.add(code)

print(f'DISPLAY_24 entries: {len(display24)} → {len(new_display24)}')

# ========================= 生成 majors_24.py =========================
# 格式化课程列表（每行一个课程）
def fmt_courses(courses):
    if not courses:
        return '[]'
    items = ',\n'.join(f"                               {repr(c)}" for c in courses)
    return f'[\n{items}]'

def fmt_credits(req):
    return (f"{{'学科基础课程': {req['学科基础课程']}, "
            f"'专业知识课程': {req['专业知识课程']}, "
            f"'工作技能课程': {req['工作技能课程']}}}")

lines = ['# -*- coding: utf-8 -*-\n',
         '"""24级（2024版培养方案）专业配置。新增专业：在 MAJORS_24 加一项，DISPLAY_24 加一行。"""\n',
         '\n',
         'MAJORS_24 = {\n']

# 排序顺序按 DISPLAY_24 的顺序
ordered_codes = [e['code'] for e in new_display24 if e['code'] in configs24]
# 确保所有 configs24 里的 code 都包含在内
remaining = [c for c in sorted(configs24.keys()) if c not in ordered_codes]
all_codes = ordered_codes + remaining

for code in all_codes:
    if code not in configs24:
        continue
    cfg = configs24[code]
    name = cfg['专业名称']
    req = cfg['学分要求']
    courses = cfg['选修课列表']

    lines.append(f"    '{code}': {{\n")
    lines.append(f"        '专业名称': '{name}',\n")
    lines.append(f"        '专业代码': '{code}',\n")

    if code == '24kg' and zuoyue_24kg:
        lines.append(f"        '有卓越班': True,\n")
        sorted_names = sorted(zuoyue_24kg)
        names_str = ', '.join(f"'{n}'" for n in sorted_names)
        lines.append(f"        '卓越班级学号集': {{{names_str}}},\n")
        lines.append(f"        '学分要求': {{\n")
        lines.append(f"            '卓越': {{'学科基础课程': 1.0, '专业知识课程': 1.0, '工作技能课程': 0.0}},\n")
        lines.append(f"            '普通': {{'学科基础课程': {req['学科基础课程']}, '专业知识课程': {req['专业知识课程']}, '工作技能课程': {req['工作技能课程']}}}\n")
        lines.append(f"        }},\n")
    else:
        lines.append(f"        '有卓越班': False,\n")
        lines.append(f"        '学分要求': {fmt_credits(req)},\n")

    lines.append(f"        '选修课列表': {{\n")
    for cat in ['学科基础课程', '专业知识课程', '工作技能课程']:
        c = courses.get(cat, [])
        lines.append(f"            '{cat}': {repr(c)},\n")
    lines.append(f"        }}\n")
    lines.append(f"    }},\n")

lines.append('}\n\n')

# 生成 DISPLAY_24
lines.append('DISPLAY_24 = [\n')
for entry in new_display24:
    code = entry['code']
    name = entry.get('name', code)
    emoji = entry.get('emoji', '📚')
    school = entry.get('school', '')
    year = entry.get('year', '2024')
    lines.append(f"    {{'code': '{code}', 'name': '{name}', 'emoji': '{emoji}', 'school': '{school}', 'year': '{year}'}},\n")
lines.append(']\n')

output = ''.join(lines)

# 语法检查
try:
    ast.parse(output)
    print('majors_24.py 语法检查: OK ✓')
except SyntaxError as e:
    print(f'语法错误: {e}')
    sys.exit(1)

with open('pangaocal-main/app/config/majors_24.py', 'w', encoding='utf-8') as f:
    f.write(output)
print(f'已写入 majors_24.py ({len(all_codes)} 个专业)')


# ========================= 更新 majors_23.py =========================
with open('new_configs_23.py', encoding='utf-8') as f:
    ns23 = {}
    exec(f.read(), ns23)
configs23 = ns23['NEW_CONFIGS_23']

# ========================= 从 all_plans_2022.json 补充23级课程列表 =========================
with open('all_plans_2022.json', encoding='utf-8') as _f2:
    _data22 = _json.load(_f2)

# 建立 major_name → key 的映射（key格式: 'N-学院-专业名-2022版培养方案.pdf'）
_name_to_key22 = {}
for _k in _data22.keys():
    _parts = _k.split('-')
    if len(_parts) >= 3:
        _name_to_key22[_parts[2]] = _k

def _extract_v3(text, cat):
    """V3：处理12位code+名，以及 'N.课程名（X课时...）' 两种格式"""
    CATS = ['学科基础课程', '专业知识课程', '工作技能课程']
    positions = [m.start() for m in re.finditer(re.escape(cat), text)]
    if not positions: return []
    idx = positions[1] if len(positions) > 1 else positions[0]
    cat_idx = CATS.index(cat)
    end_idx = len(text)
    for nc in CATS[cat_idx+1:]:
        npos = [m.start() for m in re.finditer(re.escape(nc), text)]
        for np in npos:
            if np > idx:
                end_idx = min(end_idx, np)
                break
    for stopper in ['学生发展模块', '十、学生', '十一、', '创新教育实践模块', '辅修培养', '三、原则上']:
        sp = text.find(stopper, idx)
        if sp > idx: end_idx = min(end_idx, sp)
    extend_end = min(end_idx + 1200, len(text))
    main_section = text[idx:end_idx]
    sel_markers = [m.start() for m in re.finditer(r'(?<!\S)选修(?!\S)', main_section)]
    if not sel_markers: return []
    elective_start = sel_markers[-1]
    extended_section = main_section[elective_start:] + text[end_idx:extend_end]
    skip_words = {'推荐','先修','讲授','课程','学时','修课','最低','其中','注：','学期',
                  '学分','必修','选修','实践','合计','要求','方向','模块','含','共','备注',
                  '工作技能课程','学科基础课程','专业知识课程','最低要求','通识','以上','原则上'}
    courses = []
    # Pattern 1: 12-digit code → name on next non-empty line
    code_pat = re.compile(r'^\d{12}$')
    lines = extended_section.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line: i += 1; continue
        if code_pat.match(line):
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt: j += 1; continue
                if code_pat.match(nxt): break
                name = re.sub(r'^[*△◆●▲]+', '', nxt).strip()
                if (name and len(name) >= 2 and not name[0].isdigit()
                        and not any(name.startswith(w) for w in skip_words)):
                    if name not in courses: courses.append(name)
                break
            i = j; continue
        i += 1
    # Pattern 2: N. 课程名（X课时...）
    p2 = re.findall(r'\d+[.、]\s*([^（\n]{2,30})（\d+\s*课时', extended_section)
    for name in p2:
        name = re.sub(r'^[*△◆●▲]+', '', name).strip()
        if name and name not in courses and len(name) >= 2 and not name[0].isdigit():
            if not any(name.startswith(w) for w in skip_words):
                courses.append(name)
    return courses

# 23级 code → 2022方案专业名
CODE_TO_MAJOR_23 = {
    '23hykx': '海洋科学', '23dqkx': '大气科学',
    '23wlx': '物理学', '23hyjs': '海洋技术',
    '23gdxx': '光电信息科学与工程', '23dzxxkx': '电子信息科学与技术',
    '23dzxxgc': '电子信息工程', '23txgc': '通信工程',
    '23jsjkx': '计算机科学与技术',
    '23jsjkxzw': '计算机科学与技术(中外合作办学)',
    '23znkx': '智能科学与技术', '23sjkx': '数据科学与大数据技术',
    '23wdz': '微电子科学与工程', '23wlkjan': '网络空间安全',
    '23bmjs': '保密技术', '23rjgc': '软件工程',
    '23hx': '化学', '23hxgc': '化学工程与工艺',
    '23kg': '勘查技术与工程', '23dz': '地质学', '23dx': '地球信息科学与技术',
    '23swkx': '生物科学', '23swjs': '生物技术', '23stx': '生态学',
    '23scyz': '水产养殖学', '23hyzyhj': '海洋资源与环境',
    '23hyyy': '海洋渔业科学与技术',
    '23spkxgc': '食品科学与工程', '23hyzykf': '海洋资源开发技术',
    '23yx': '药学', '23tmgc': '土木工程', '23gcgl': '工程管理',
    '23gkhd': '港口航道与海岸工程', '23cb': '船舶与海洋工程',
    '23jxsj': '机械设计制造及其自动化', '23gysj': '工业设计',
    '23zdh': '自动化', '23lj': '轮机工程',
    '23hjkx': '环境科学', '23hjgc': '环境工程',
    '23gsgl': '工商管理', '23kuaiji': '会计学', '23cwgl': '财务管理',
    '23scyx': '市场营销', '23dzsw': '电子商务', '23lygl': '旅游管理',
    '23jrx': '金融学', '23gjmy': '国际经济与贸易',
    '23wlgl': '物流管理', '23jjx': '经济学',
    '23yy': '英语', '23ry': '日语', '23cxy': '朝鲜语',
    '23fy': '法语', '23dey': '德语',
    '23hywx': '汉语言文学', '23whcygl': '文化产业管理',
    '23xwx': '新闻学', '23wlxmt': '网络与新媒体',
    '23fx': '法学', '23fxzw': '法学（中外合作办学）',
    '23zzx': '政治学与行政学', '23ggsy': '公共事业管理', '23xzgl': '行政管理',
    '23sx': '数学与应用数学', '23xxjskx': '信息与计算科学',
    '23clkx': '材料科学与工程', '23gfz': '高分子材料与工程',
    '23ydxl': '运动训练', '23yybp': '音乐表演',
    '23swjshd': '生物技术（中外合作办学）',
    '23spkxhd': '食品科学与工程（中外合作办学）',
    '23sxhd': '数学与应用数学（中外合作办学）',
    '23hykxbj': '海洋科学（拔尖人才培养）',
    '23swkxbj': '生物科学（拔尖人才培养）',
    '23hykxzw': '海洋科学（中外合作办学）',
    '23spyy': '食品营养与健康',
}

v3_23_count = 0
for code, major_name in CODE_TO_MAJOR_23.items():
    if code not in configs23: continue
    key = _name_to_key22.get(major_name, '')
    if not key: continue
    text = _data22[key]
    for cat in ['学科基础课程', '专业知识课程', '工作技能课程']:
        if configs23[code]['选修课列表'].get(cat): continue  # already has data
        courses = _extract_v3(text, cat)
        if courses:
            configs23[code]['选修课列表'][cat] = courses
            v3_23_count += 1
print(f'从 all_plans_2022.json v3 提取补充了 {v3_23_count} 个23级课程列表')

# ========================= 23级手动修正 =========================
# 23xxjskx 学科基础课程：V3算法选中了最后一个'选修'标记（工作技能区域），
# 正确的学科基础选修课在 PDF 靠前位置（选修marker offset≈990）
if '23xxjskx' in configs23 and not configs23['23xxjskx']['选修课列表'].get('学科基础课程'):
    configs23['23xxjskx']['选修课列表']['学科基础课程'] = [
        '统计计算', '矩阵计算', '一般拓扑学', '计算复杂性理论', '现代复分析导引'
    ]
    print('手动补充 23xxjskx 学科基础课程: 5 门课程')

# 读取现有 majors_23.py 的卓越班信息
with open('pangaocal-main/app/config/majors_23.py', encoding='utf-8') as f:
    cur23_content = f.read()

zuoyue_23kg = extract_zuoyue_block(cur23_content, '23kg')
print(f'23kg 卓越班学号集: {len(zuoyue_23kg) if zuoyue_23kg else 0} 人')

# 读取现有 DISPLAY_23
cur23_ns = {}
try:
    exec(cur23_content, cur23_ns)
    display23 = cur23_ns.get('DISPLAY_23', [])
except:
    display23 = []

# 对于 configs23 里没有的 code（如 23swkxbj 拔尖等），保留 majors_23 的原始数据
cur_majors23 = cur23_ns.get('MAJORS_23', {})
extra_codes_23 = [c for c in cur_majors23 if c not in configs23]
print(f'majors_23 中有但 new_configs_23 中没有的 code: {extra_codes_23}')

# 生成 majors_23.py
lines23 = ['# -*- coding: utf-8 -*-\n',
           '"""23级（2022版培养方案）专业配置。新增专业：在 MAJORS_23 加一项，DISPLAY_23 加一行。"""\n',
           '\n',
           'MAJORS_23 = {\n']

# 排序顺序按 DISPLAY_23 的顺序
ordered_codes_23 = [e['code'] for e in display23 if e['code'] in configs23 or e['code'] in cur_majors23]
remaining_23 = [c for c in sorted(list(configs23.keys()) + extra_codes_23) if c not in ordered_codes_23]
all_codes_23 = ordered_codes_23 + remaining_23

for code in all_codes_23:
    # 从 new_configs_23 获取，否则从当前 majors_23 获取
    if code in configs23:
        cfg = configs23[code]
    elif code in cur_majors23:
        cfg = cur_majors23[code]
        print(f'  保留原始 {code}: {cfg.get("专业名称")}')
    else:
        continue

    name = cfg['专业名称']
    req = cfg['学分要求']
    courses = cfg.get('选修课列表', {'学科基础课程': [], '专业知识课程': [], '工作技能课程': []})

    lines23.append(f"    '{code}': {{\n")
    lines23.append(f"        '专业名称': '{name}',\n")
    lines23.append(f"        '专业代码': '{code}',\n")

    if code == '23kg' and zuoyue_23kg:
        lines23.append(f"        '有卓越班': True,\n")
        sorted_names = sorted(zuoyue_23kg)
        names_str = ', '.join(f"'{n}'" for n in sorted_names)
        lines23.append(f"        '卓越班级学号集': {{{names_str}}},\n")
        # 对于卓越班学分要求，保留原始配置
        orig_req = cur_majors23.get('23kg', {}).get('学分要求', req)
        if isinstance(orig_req, dict) and '卓越' in orig_req:
            lines23.append(f"        '学分要求': {repr(orig_req)},\n")
        else:
            lines23.append(f"        '学分要求': {{\n")
            lines23.append(f"            '卓越': {{'学科基础课程': 1.0, '专业知识课程': 1.0, '工作技能课程': 0.0}},\n")
            lines23.append(f"            '普通': {{'学科基础课程': {req['学科基础课程']}, '专业知识课程': {req['专业知识课程']}, '工作技能课程': {req['工作技能课程']}}}\n")
            lines23.append(f"        }},\n")
    else:
        lines23.append(f"        '有卓越班': False,\n")
        lines23.append(f"        '学分要求': {fmt_credits(req)},\n")

    lines23.append(f"        '选修课列表': {{\n")
    for cat in ['学科基础课程', '专业知识课程', '工作技能课程']:
        c = courses.get(cat, [])
        lines23.append(f"            '{cat}': {repr(c)},\n")
    lines23.append(f"        }}\n")
    lines23.append(f"    }},\n")

lines23.append('}\n\n')

# 生成 DISPLAY_23
lines23.append('DISPLAY_23 = [\n')
# 添加 display23 条目
seen23 = set()
for entry in display23:
    code = entry['code']
    if code not in seen23:
        name = entry.get('name', code)
        emoji = entry.get('emoji', '📚')
        school = entry.get('school', '')
        year = entry.get('year', '2023')
        lines23.append(f"    {{'code': '{code}', 'name': '{name}', 'emoji': '{emoji}', 'school': '{school}', 'year': '{year}'}},\n")
        seen23.add(code)
lines23.append(']\n')

output23 = ''.join(lines23)

# 语法检查
try:
    ast.parse(output23)
    print('majors_23.py 语法检查: OK ✓')
except SyntaxError as e:
    print(f'语法错误: {e}')
    sys.exit(1)

with open('pangaocal-main/app/config/majors_23.py', 'w', encoding='utf-8') as f:
    f.write(output23)
print(f'已写入 majors_23.py ({len(all_codes_23)} 个专业)')
print('完成！')
