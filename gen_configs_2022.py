"""
从 all_plans_2022.json 生成 23级专业配置，输出到 new_configs_23.py
"""
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('E:/计算综测/all_plans_2022.json', encoding='utf-8') as f:
    plans = json.load(f)

# ---- 文件名 → (major_code, 专业名称, 学院) 映射 ----
# 顺序很重要：长的/精确的放前面避免误匹配
FILENAME_MAP = [
    # 拔尖
    ('75-拔尖-海洋科学（拔尖人才培养',  '23hykxbj',  '23海洋科学(拔尖)',  '崇本学堂'),
    ('76-拔尖-生物科学（拔尖人才培养',  '23swkxbj',  '23生物科学(拔尖)',  '崇本学堂'),
    # 海德学院
    ('72-海德学院-生物技术',            '23swjshd',  '23生物技术(海德)',  '海德学院'),
    ('73-海德学院-食品科学与工程',      '23spkxhd',  '23食品科学(海德)',  '海德学院'),
    ('74-海德学院-数学与应用数学',      '23sxhd',    '23数学(海德)',      '海德学院'),
    # 基础教学中心
    ('70-基础教学中心-运动训练',        '23ydxl',    '23运动训练',        '基础教育学院'),
    ('71-基础教学中心-音乐表演',        '23yybp',    '23音乐表演',        '基础教育学院'),
    # 材料
    ('68-材料科学与工程学院-材料科学与工程',  '23clkx', '23材料科学与工程', '材料科学与工程学院'),
    ('69-材料科学与工程学院-高分子材料',      '23gfz',  '23高分子材料与工程','材料科学与工程学院'),
    # 数学
    ('66-数学科学学院-数学与应用数学',  '23sx',     '23数学与应用数学',  '数学科学学院'),
    ('67-数学科学学院-信息与计算科学',  '23xxjskx', '23信息与计算科学',  '数学科学学院'),
    # 国际事务
    ('63-国际事务与公共管理学院-政治学', '23zzx',   '23政治学与行政学',  '国际事务与公共管理学院'),
    ('64-国际事务与公共管理学院-公共',   '23ggsy',  '23公共事业管理',    '国际事务与公共管理学院'),
    ('65-国际事务与公共管理学院-行政',   '23xzgl',  '23行政管理',        '国际事务与公共管理学院'),
    # 法学
    ('61-法学院-法学-',                 '23fx',    '23法学',            '法学院'),
    ('62-法学院-法学（中外',            '23fxzw',  '23法学(中外合作)',   '法学院'),
    # 文学与新闻传播
    ('57-文学与新闻传播学院-汉语言文学','23hywx',  '23汉语言文学',      '文学与新闻传播学院'),
    ('58-文学与新闻传播学院-文化产业',  '23whcygl','23文化产业管理',    '文学与新闻传播学院'),
    ('59-文学与新闻传播学院-新闻学',    '23xwx',   '23新闻学',          '文学与新闻传播学院'),
    ('60-文学与新闻传播学院-网络与新媒体','23wlxmt','23网络与新媒体',   '文学与新闻传播学院'),
    # 外国语
    ('52-外国语学院-英语',  '23yy',  '23英语',  '外国语学院'),
    ('53-外国语学院-日语',  '23ry',  '23日语',  '外国语学院'),
    ('54-外国语学院-朝鲜语','23cxy', '23朝鲜语','外国语学院'),
    ('55-外国语学院-法语',  '23fy',  '23法语',  '外国语学院'),
    ('56-外国语学院-德语',  '23dey', '23德语',  '外国语学院'),
    # 经济
    ('48-经济学院-金融学',     '23jrx',  '23金融学',      '经济学院'),
    ('49-经济学院-国际经济',   '23gjmy', '23国际经济与贸易','经济学院'),
    ('50-经济学院-物流管理',   '23wlgl', '23物流管理',    '经济学院'),
    ('51-经济学院-经济学',     '23jjx',  '23经济学',      '经济学院'),
    # 管理学院
    ('42-管理学院-工商管理',   '23gsgl',   '23工商管理',  '管理学院'),
    ('43-管理学院-会计学',     '23kuaiji', '23会计学',    '管理学院'),
    ('44-管理学院-财务管理',   '23cwgl',   '23财务管理',  '管理学院'),
    ('45-管理学院-市场营销',   '23scyx',   '23市场营销',  '管理学院'),
    ('46-管理学院-电子商务',   '23dzsw',   '23电子商务',  '管理学院'),
    ('47-管理学院-旅游管理',   '23lygl',   '23旅游管理',  '管理学院'),
    # 环境
    ('40-环境科学与工程学院-环境科学','23hjkx','23环境科学','环境科学与工程学院'),
    ('41-环境科学与工程学院-环境工程','23hjgc','23环境工程','环境科学与工程学院'),
    # 工程学院
    ('32-工程学院-土木工程',            '23tmgc', '23土木工程',            '工程学院'),
    ('33-工程学院-工程管理',            '23gcgl', '23工程管理',            '工程学院'),
    ('34-工程学院-港口航道',            '23gkhd', '23港口航道与海岸工程',  '工程学院'),
    ('35-工程学院-船舶与海洋工程',      '23cb',   '23船舶与海洋工程',      '工程学院'),
    ('36-工程学院-机械设计',            '23jxsj', '23机械设计制造及自动化','工程学院'),
    ('37-工程学院-工业设计',            '23gysj', '23工业设计',            '工程学院'),
    ('38-工程学院-自动化',              '23zdh',  '23自动化',              '工程学院'),
    ('39-工程学院-轮机工程',            '23lj',   '23轮机工程',            '工程学院'),
    # 医药
    ('31-医药学院-药学',    '23yx',   '23药学',   '医药学院'),
    # 食品
    ('29-食品科学与工程学院-食品科学与工程','23spkxgc','23食品科学与工程','食品科学与工程学院'),
    ('30-食品科学与工程学院-海洋资源开发', '23hyzykf','23海洋资源开发技术','食品科学与工程学院'),
    # 水产
    ('26-水产学院-水产养殖学',      '23scyz',  '23水产养殖学',        '水产学院'),
    ('27-水产学院-海洋资源与环境',  '23hyzyhj','23海洋资源与环境',    '水产学院'),
    ('28-水产学院-海洋渔业',        '23hyyy',  '23海洋渔业科学与技术','水产学院'),
    # 海洋生命
    ('23-海洋生命学院-生物科学',    '23swkx', '23生物科学', '生命科学学院'),
    ('24-海洋生命学院-生物技术',    '23swjs', '23生物技术', '生命科学学院'),
    ('25-海洋生命学院-生态学',      '23stx',  '23生态学',   '生命科学学院'),
    # 海洋地球科学（已存在 23kg 23dz 23dx，但仍需提取配置）
    ('20-海洋地球科学学院-地质学',          '23dz',  '23地质',             '海洋地球科学学院'),
    ('21-海洋地球科学学院-勘查技术与工程',  '23kg',  '23勘工',             '海洋地球科学学院'),
    ('22-海洋地球科学学院-地球信息科学',    '23dx',  '23地信',             '海洋地球科学学院'),
    # 化学
    ('18-化学化工学院-化学-',       '23hx',   '23化学',       '化学化工学院'),
    ('19-化学化工学院-化学工程',    '23hxgc', '23化学工程与工艺','化学化工学院'),
    # 信息学部（长的放前面）
    ('15-信息科学与工程学部-计算机科学与技术(中外', '23jsjkxzw', '23计算机(中外合作)', '信息科学与工程学部'),
    ('10-信息科学与工程学部-计算机科学与技术',       '23jsjkx',   '23计算机科学与技术', '信息科学与工程学部'),
    ('11-信息科学与工程学部-智能科学',               '23znkx',    '23智能科学与技术',   '信息科学与工程学部'),
    ('12-信息科学与工程学部-数据科学',               '23sjkx',    '23数据科学与大数据', '信息科学与工程学部'),
    ('13-信息科学与工程学部-微电子',                 '23wdz',     '23微电子科学与工程', '信息科学与工程学部'),
    ('14-信息科学与工程学部-网络空间安全',           '23wlkjan',  '23网络空间安全',     '信息科学与工程学部'),
    ('16-信息科学与工程学部-保密技术',               '23bmjs',    '23保密技术',         '信息科学与工程学部'),
    ('17-信息科学与工程学部-软件工程',               '23rjgc',    '23软件工程',         '信息科学与工程学部'),
    ('4-信息科学与工程学部-物理学',                  '23wlx',     '23物理学',           '信息科学与工程学部'),
    ('5-信息科学与工程学部-海洋技术',                '23hyjs',    '23海洋技术',         '信息科学与工程学部'),
    ('6-信息科学与工程学部-光电信息',                '23gdxx',    '23光电信息科学与工程','信息科学与工程学部'),
    ('7-信息科学与工程学部-电子信息科学与技术',      '23dzxxkx',  '23电子信息科学与技术','信息科学与工程学部'),
    ('8-信息科学与工程学部-电子信息工程',            '23dzxxgc',  '23电子信息工程',     '信息科学与工程学部'),
    ('9-信息科学与工程学部-通信工程',                '23txgc',    '23通信工程',         '信息科学与工程学部'),
    # 海洋与大气（长的放前面）
    ('2-海洋与大气学院-海洋科学（中外', '23hykxzw', '23海洋科学(中外合作)', '海洋与大气学院'),
    ('1-海洋与大气学院-海洋科学-',     '23hykx',   '23海洋科学',           '海洋与大气学院'),
    ('3-海洋与大气学院-大气科学',      '23dqkx',   '23大气科学',           '海洋与大气学院'),
]

# ---- 提取选修课的函数 (与24级相同) ----
CATEGORIES = ['学科基础课程', '专业知识课程', '工作技能课程']

def extract_elective_credits(text, cat):
    """提取某个课程类别的选修学分要求"""
    patterns = [
        rf'{cat}.*?其中[：:]\s*必修\s*[\d.]+\s*学分[，,]\s*选修\s*([\d.]+)\s*学分',
        rf'其中[：:]\s*必修\s*[\d.]+\s*学分[，,]\s*选修\s*([\d.]+)\s*学分',
    ]
    positions = [m.start() for m in re.finditer(re.escape(cat), text)]
    if not positions:
        return 0.0
    # 在第二次出现附近搜索（第一次通常在汇总表）
    search_start = positions[1] if len(positions) > 1 else positions[0]
    snippet = text[search_start:search_start + 500]
    m = re.search(r'其中[：:]\s*必修\s*[\d.]+\s*学分[，,]\s*选修\s*([\d.]+)\s*学分', snippet)
    if m:
        return float(m.group(1))
    return 0.0

def extract_elective_courses(text, cat):
    """提取某个课程类别下的选修课名称列表（12位课程代码后跟课程名）"""
    positions = [m.start() for m in re.finditer(re.escape(cat), text)]
    if not positions:
        return []
    idx = positions[1] if len(positions) > 1 else positions[0]
    cat_idx = CATEGORIES.index(cat)
    next_cats = CATEGORIES[cat_idx+1:]
    end_idx = len(text)
    for nc in next_cats:
        npos = [m.start() for m in re.finditer(re.escape(nc), text)]
        if len(npos) > 1:
            end_idx = min(end_idx, npos[1])
        elif len(npos) == 1:
            end_idx = min(end_idx, npos[0])
    section = text[idx:end_idx]
    # 找到"选修"标记位置
    elective_markers = [m.start() for m in re.finditer(r'选修', section)]
    if not elective_markers:
        return []
    sel_start = elective_markers[-1]
    elective_section = section[sel_start:]
    # 提取12位代码后的课程名
    courses = re.findall(r'\d{12}\s+([^\n\d]{2,30}?)(?:\s+[\d.]+|\n|$)', elective_section)
    # 清理
    cleaned = []
    for c in courses:
        c = c.strip().rstrip('▲●★◆■□△○◇')
        suffix = ''
        for sym in ['▲','●','★','◆','■','□','△','○','◇']:
            if sym in c:
                suffix = sym
                c = c.replace(sym,'').strip()
        if c and len(c) >= 2:
            cleaned.append(c + suffix if suffix else c)
    return cleaned

# ---- 主处理逻辑 ----
configs = {}

for fname, text in plans.items():
    # 找到匹配的条目
    matched = None
    for prefix, code, name, school in FILENAME_MAP:
        if prefix in fname:
            matched = (code, name, school)
            break
    if not matched:
        print(f'[WARN] 未匹配: {fname}')
        continue
    code, name, school = matched

    credits = {}
    courses = {}
    for cat in CATEGORIES:
        cr = extract_elective_credits(text, cat)
        cs = extract_elective_courses(text, cat)
        credits[cat] = cr
        courses[cat] = cs

    configs[code] = {
        '专业名称': name,
        '专业代码': code,
        '学院': school,
        '有卓越班': False,
        '学分要求': credits,
        '选修课列表': courses,
    }
    print(f"  {code} ({name}): 选修学分 {credits}")

print(f'\n共生成 {len(configs)} 个配置')

# ---- 输出 Python 文件 ----
lines = ['# 23级（2022版培养方案）专业配置\n']
lines.append('NEW_CONFIGS_23 = {\n')
for code, cfg in sorted(configs.items()):
    lines.append(f"    '{code}': {{\n")
    lines.append(f"        '专业名称': '{cfg['专业名称']}',\n")
    lines.append(f"        '专业代码': '{cfg['专业代码']}',\n")
    lines.append(f"        '有卓越班': False,\n")
    lines.append(f"        '学分要求': {cfg['学分要求']!r},\n")
    lines.append(f"        '选修课列表': {cfg['选修课列表']!r},\n")
    lines.append(f"    }},\n")
lines.append('}\n\n')

# 也输出 display list entries
lines.append('# display list entries (school + year 已填)\n')
lines.append('NEW_DISPLAY_23 = [\n')
EMOJI_MAP = {
    '海洋与大气学院': '🌊', '信息科学与工程学部': '💻', '化学化工学院': '⚗️',
    '海洋地球科学学院': '🏔️', '生命科学学院': '🔬', '水产学院': '🐟',
    '食品科学与工程学院': '🍽️', '医药学院': '💊', '工程学院': '⚙️',
    '环境科学与工程学院': '🌿', '管理学院': '📊', '经济学院': '💹',
    '外国语学院': '🌐', '文学与新闻传播学院': '📝', '法学院': '⚖️',
    '国际事务与公共管理学院': '🏛️', '数学科学学院': '📐', '材料科学与工程学院': '🔧',
    '基础教育学院': '🎓', '海德学院': '🏫', '崇本学堂': '⭐',
}
for _, code, name, school in FILENAME_MAP:
    if code not in configs:
        continue
    emoji = EMOJI_MAP.get(school, '📚')
    lines.append(f"    {{'code': '{code}', 'name': '{name}', 'emoji': '{emoji}', 'school': '{school}', 'year': '2023'}},\n")
lines.append(']\n')

out_path = 'E:/计算综测/new_configs_23.py'
with open(out_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'\n输出至 {out_path}')
