import json, re

with open('E:/计算综测/all_plans_full.json', encoding='utf-8') as f:
    data = json.load(f)

def extract_major_config(major_name, text):
    config = {'专业名称': major_name, '有卓越班': False, '学分要求': {}, '选修课列表': {}}
    categories = ['学科基础课程', '专业知识课程', '工作技能课程']
    for cat in categories:
        positions = [m.start() for m in re.finditer(re.escape(cat), text)]
        if len(positions) < 2:
            config['学分要求'][cat] = 0.0
            config['选修课列表'][cat] = []
            continue
        idx = positions[1]
        next_idx = len(text)
        for other_cat in categories:
            if other_cat == cat:
                continue
            for pos in [m.start() for m in re.finditer(re.escape(other_cat), text)]:
                if pos > idx:
                    next_idx = min(next_idx, pos)
                    break
        for em in ['学生发展模块', '十、学生', '创新教育实践模块']:
            ep = text.find(em, idx)
            if ep > idx:
                next_idx = min(next_idx, ep)
        section = text[idx:next_idx]
        m = re.search(r'其中[：:]\s*必修\s*[\d.]+\s*学分[，,]\s*选修\s*([\d.]+)\s*学分', section)
        if m:
            config['学分要求'][cat] = float(m.group(1))
        else:
            m2 = re.search(r'选修\s*([\d.]+)\s*学分', section)
            config['学分要求'][cat] = float(m2.group(1)) if m2 else 0.0
        lines = section.split('\n')
        in_elective = False
        elective_courses = []
        prev_was_code = False
        code_pattern = re.compile(r'^\d{12}$')
        skip_words = {'推荐','先修','讲授','课程','学时','修课','最低','其中','注：','学期','学分','必修','选修','实践','合计','要求'}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line == '选修':
                in_elective = True; prev_was_code = False; continue
            if line == '必修':
                prev_was_code = False; continue
            if in_elective:
                if code_pattern.match(line):
                    prev_was_code = True
                elif prev_was_code:
                    name = line.lstrip('*').strip()
                    if (name and len(name) > 1 and not name[0].isdigit()
                            and not any(name.startswith(w) for w in skip_words)
                            and name not in elective_courses):
                        elective_courses.append(name)
                    prev_was_code = False
        config['选修课列表'][cat] = elective_courses
    return config

# PDF name to (code, display_name, emoji) mapping - order matters for matching
major_patterns = [
    # 10环科
    ('环境工程', '24hjgc', '24环境工程', '🌿'),
    ('环境科学', '24hjkx', '24环境科学', '🌱'),
    # 11管理
    ('会计学（ACCA', '24kuaijiACCA', '24会计学(ACCA)', '💼'),
    ('会计学', '24kuaiji', '24会计学', '📊'),
    ('工商管理', '24gsgl', '24工商管理', '🏢'),
    ('市场营销', '24scyx', '24市场营销', '📈'),
    ('旅游管理', '24lygl', '24旅游管理', '✈️'),
    ('财务管理', '24cwgl', '24财务管理', '💰'),
    # 12经济
    ('国际经济与贸易', '24gjmy', '24国际经济与贸易', '🌐'),
    ('物流管理', '24wlgl', '24物流管理', '🚚'),
    ('经济学', '24jjx', '24经济学(海洋经济)', '📉'),
    ('金融学(CFA', '24jrxCFA', '24金融学(CFA)', '💹'),
    ('金融学', '24jrx', '24金融学', '🏦'),
    # 13外语
    ('德语', '24dey', '24德语', '🇩🇪'),
    ('日语', '24ry', '24日语', '🇯🇵'),
    ('朝鲜语', '24cxy', '24朝鲜语', '🇰🇷'),
    ('法语', '24fy', '24法语', '🇫🇷'),
    ('英语', '24yy', '24英语', '🇬🇧'),
    # 14文新
    ('新闻学', '24xwx', '24新闻学', '📰'),
    ('汉语言文学', '24hywx', '24汉语言文学', '📖'),
    ('网络与新媒体', '24wlxmt', '24网络与新媒体', '📱'),
    # 15法学
    ('法学（中外', '24fxzw', '24法学(中外合作)', '⚖️'),
    ('法学', '24fx', '24法学', '⚖️'),
    # 16国管
    ('公共事业管理', '24ggsy', '24公共事业管理', '🏛️'),
    ('政治学', '24zzx', '24政治学与行政学', '🏛️'),
    ('行政管理', '24xzgl', '24行政管理', '🏛️'),
    # 17数学
    ('信息与计算科学', '24xxjskx', '24信息与计算科学', '🔢'),
    ('数学与应用数学', '24sx', '24数学与应用数学', '📐'),
    # 18材料
    ('新能源材料', '24xny', '24新能源材料与器件', '⚡'),
    ('材料科学与工程', '24clkx', '24材料科学与工程', '🔬'),
    ('高分子', '24gfz', '24高分子材料与工程', '🧬'),
    # 19基教
    ('运动训练', '24ydxl', '24运动训练', '🏃'),
    ('音乐表演', '24yybp', '24音乐表演', '🎵'),
    # 1海气
    ('大气科学', '24dqkx', '24大气科学', '🌤️'),
    ('海洋科学（中外合作）', '24hykxzw', '24海洋科学(中外合作)', '🌊'),
    ('海洋科学', '24hykx', '24海洋科学', '🌊'),
    # 20崇本
    ('海洋科学拔尖', '24hykxbj', '24海洋科学(拔尖班)', '🌟'),
    # 21海德
    ('数学与应用数学（中外合作办学）', '24sxhd', '24数学与应用数学(海德)', '🔢'),
    ('生物技术（中外合作办学）', '24swjshd', '24生物技术(海德)', '🧬'),
    ('食品科学与工程（中外合作办学）', '24spkxhd', '24食品科学与工程(海德)', '🍽️'),
    # 2信息
    ('保密技术', '24bmjs', '24保密技术', '🔒'),
    ('光电信息科学与工程', '24gdxx', '24光电信息科学与工程', '💡'),
    ('声学', '24shengx', '24声学', '🔊'),
    ('微电子科学与工程', '24wdz', '24微电子科学与工程', '🔌'),
    ('数据科学与大数据技术', '24sjkx', '24数据科学与大数据技术', '📊'),
    ('智能科学与技术', '24znkx', '24智能科学与技术', '🤖'),
    ('海洋技术', '24hyjs', '24海洋技术', '⚓'),
    ('物理学', '24wlx', '24物理学', '⚛️'),
    ('电子信息信息科学与技术', '24dzxxkx', '24电子信息科学与技术', '💻'),
    ('电子信息工程', '24dzxxgc', '24电子信息工程', '📡'),
    ('网络空间安全', '24wlkjan', '24网络空间安全', '🛡️'),
    ('计算机科学与技术（中外合作办学）', '24jsjkxzw', '24计算机科学(中外合作)', '💻'),
    ('计算机科学与技术', '24jsjkx', '24计算机科学与技术', '💻'),
    ('软件工程', '24rjgc', '24软件工程', '⚙️'),
    ('通信工程', '24txgc', '24通信工程', '📶'),
    # 3化学
    ('化学工程与工艺', '24hxgc', '24化学工程与工艺', '⚗️'),
    ('化学', '24hx', '24化学', '🧪'),
    # 4地球 (already have 24kg, adding others)
    ('地球信息科学与技术', '24dx24', '24地球信息科学与技术', '🛰️'),
    ('地质学', '24dz24', '24地质学', '🗺️'),
    # 5生命
    ('生态学', '24stx', '24生态学', '🌿'),
    ('生物技术', '24swjs', '24生物技术', '🧬'),
    ('生物科学', '24swkx', '24生物科学', '🔬'),
    # 6水产
    ('水产养殖学', '24scyz', '24水产养殖学', '🐟'),
    ('海洋渔业科学与技术', '24hyyy', '24海洋渔业科学与技术', '🎣'),
    ('海洋资源与环境', '24hyzyhj', '24海洋资源与环境', '🌊'),
    # 7食品
    ('海洋资源开发技术', '24hyzykf', '24海洋资源开发技术', '🔧'),
    ('食品科学与工程', '24spkxgc', '24食品科学与工程', '🍽️'),
    ('食品营养与健康', '24spyy', '24食品营养与健康', '🥗'),
    # 8医药
    ('药学', '24yx', '24药学', '💊'),
    # 9工程
    ('土木工程', '24tmgc', '24土木工程', '🏗️'),
    ('工业设计', '24gysj', '24工业设计', '✏️'),
    ('机械设计制造及其自动化', '24jxsj', '24机械设计制造及其自动化', '⚙️'),
    ('港口航道与海岸工程', '24gkhd', '24港口航道与海岸工程', '⚓'),
    ('自动化', '24zdh', '24自动化', '🤖'),
    ('船舶与海洋工程', '24cb', '24船舶与海洋工程', '🚢'),
    ('轮机工程', '24lj', '24轮机工程', '⚙️'),
]

# Collect all PDF texts
all_pdfs = {}
for school_key, school_data in data.items():
    for pdf_name, text in school_data.items():
        # Clean up PDF name
        clean_name = pdf_name.replace('-2024培养方案.pdf', '').replace('-2024级培养方案.pdf', '').replace('-2024级培养方案-20250109.pdf', '').replace('金融学(CFA)培养方案2024版.pdf', '金融学(CFA)').replace('网络与新媒体2024培养方案.pdf', '网络与新媒体').replace('中国海洋大学2024版本科人才培养方案-海洋科学拔尖', '海洋科学拔尖')
        all_pdfs[clean_name] = (pdf_name, text)

# Match patterns to PDFs
output_lines = []
display_list_lines = []

matched_count = 0
for pattern, code, display_name, emoji in major_patterns:
    # Find matching PDF
    matched_text = None
    matched_name = None
    for clean_name, (pdf_name, text) in all_pdfs.items():
        if pattern in clean_name or pattern in pdf_name:
            matched_text = text
            matched_name = clean_name
            break

    if not matched_text:
        output_lines.append(f"# WARNING: No PDF found for pattern '{pattern}'")
        continue

    cfg = extract_major_config(display_name, matched_text)
    cfg['专业代码'] = code
    matched_count += 1

    req = cfg['学分要求']
    courses = cfg['选修课列表']

    output_lines.append(f"            # ------------------- {display_name} -------------------")
    output_lines.append(f"            '{code}': {{")
    output_lines.append(f"                '专业名称': '{display_name}',")
    output_lines.append(f"                '专业代码': '{code}',")
    output_lines.append(f"                '有卓越班': False,")
    output_lines.append(f"                '学分要求': {{")
    output_lines.append(f"                    '学科基础课程': {req['学科基础课程']},")
    output_lines.append(f"                    '专业知识课程': {req['专业知识课程']},")
    output_lines.append(f"                    '工作技能课程': {req['工作技能课程']}")
    output_lines.append(f"                }},")
    output_lines.append(f"                '选修课列表': {{")
    output_lines.append(f"                    '学科基础课程': {repr(courses['学科基础课程'])},")
    output_lines.append(f"                    '专业知识课程': {repr(courses['专业知识课程'])},")
    output_lines.append(f"                    '工作技能课程': {repr(courses['工作技能课程'])}")
    output_lines.append(f"                }}")
    output_lines.append(f"            }},")
    output_lines.append("")

    display_list_lines.append(f"            {{'code': '{code}', 'name': '{display_name}', 'emoji': '{emoji}'}},")

with open('E:/计算综测/new_configs.py', 'w', encoding='utf-8') as f:
    f.write("# ============ 新增：全校各专业配置（2024级培养方案）============\n")
    f.write("# 以下代码添加到 MajorConfig.__init__ 的 self.majors 字典中\n\n")
    f.write('\n'.join(output_lines))
    f.write("\n\n# ============ 以下添加到 self.major_display_list 中 ============\n")
    f.write('\n'.join(display_list_lines))

print(f"Generated {matched_count} major configs")
print("Written to E:/计算综测/new_configs.py")
