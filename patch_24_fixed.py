"""
精确更新 web.py 中24级学分要求
策略：找每个 code 块的开始和结束，整块替换
"""
import sys, re, ast
sys.stdout.reconfigure(encoding='utf-8')

with open('E:/计算综测/new_configs_24_fixed.py', encoding='utf-8') as f:
    ns = {}
    exec(f.read(), ns)
configs = ns['NEW_CONFIGS_24']
display_list = ns['NEW_DISPLAY_24']

with open('E:/计算综测/pangaocal-main/web.py', encoding='utf-8') as f:
    content = f.read()

SKIP = {'24kg', '24kgzx'}
updated, added = [], []

for code, cfg in configs.items():
    if code in SKIP:
        continue

    new_req = repr(cfg['学分要求'])
    new_courses = repr(cfg['选修课列表'])

    if f"'{code}':" not in content:
        # 新增专业块
        name = cfg['专业名称']
        block = (
            f"\n            # ------------------- {name} -------------------\n"
            f"            '{code}': {{\n"
            f"                '专业名称': '{name}',\n"
            f"                '专业代码': '{code}',\n"
            f"                '有卓越班': False,\n"
            f"                '学分要求': {new_req},\n"
            f"                '选修课列表': {new_courses}\n"
            f"            }},\n"
        )
        anchor = "            # ------------------- 其他班级（仅综测） -------------------\n            'other':"
        content = content.replace(anchor, block + anchor)
        added.append(code)
        continue

    # 找该 code 块，只更新学分要求和选修课列表两行/段
    # 格式示例：
    #   '学分要求': {'学科基础课程': 0.0, ...},
    #   '选修课列表': {'学科基础课程': [...], ...}
    # 用"从 '代码': { 到下一个顶级 '代码': 或 }"来定位块
    code_start = content.find(f"'{code}':")
    if code_start == -1:
        continue

    # 找该块结尾（下一个同缩进级别的 ' 开头，或 'other':）
    # 简单做法：在该 code_start 后找 '学分要求' 并替换其值
    req_key = "'学分要求':"
    req_pos = content.find(req_key, code_start)
    if req_pos == -1:
        continue
    # 找该行的值（从 : 后到行尾或下一行）
    # 值可能是单行 {'...'} 或多行 {\n...\n}
    val_start = req_pos + len(req_key)
    # 跳过空白
    while val_start < len(content) and content[val_start] in ' \t\n':
        val_start += 1
    if content[val_start] != '{':
        continue
    # 找匹配的 }
    depth = 0
    val_end = val_start
    for i in range(val_start, len(content)):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                val_end = i + 1
                break
    content = content[:val_start] + new_req + content[val_end:]

    # 同样替换选修课列表
    courses_key = "'选修课列表':"
    courses_pos = content.find(courses_key, content.find(f"'{code}':"))
    if courses_pos == -1:
        updated.append(code)
        continue
    val_start = courses_pos + len(courses_key)
    while val_start < len(content) and content[val_start] in ' \t\n':
        val_start += 1
    if content[val_start] != '{':
        updated.append(code)
        continue
    depth = 0
    val_end = val_start
    for i in range(val_start, len(content)):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                val_end = i + 1
                break
    content = content[:val_start] + new_courses + content[val_end:]
    updated.append(code)

# 补充 display_list 中新增的条目
for entry in display_list:
    if isinstance(entry, dict):
        code = entry.get('code', '')
        name = entry.get('name', '')
        emoji = entry.get('emoji', '')
        school = entry.get('school', '')
        year = entry.get('year', '2024')
        entry_str = f"            {{'code': '{code}', 'name': '{name}', 'emoji': '{emoji}', 'school': '{school}', 'year': '{year}'}},"
    else:
        code_m = re.search(r"'code': '([^']+)'", entry)
        if not code_m:
            continue
        code = code_m.group(1)
        entry_str = entry
    if code in SKIP:
        continue
    if f"'code': '{code}'" not in content:
        # 加到2024级按钮列表最后（other 前）
        anchor = "            {'code': 'other'"
        content = content.replace(anchor, entry_str + '\n' + anchor)
        print(f'[display新增] {code}')

with open('E:/计算综测/pangaocal-main/web.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'更新了 {len(updated)} 个: {updated}')
print(f'新增了 {len(added)} 个: {added}')

with open('E:/计算综测/pangaocal-main/web.py', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    print('语法检查: OK ✓')
except SyntaxError as e:
    print(f'语法错误: {e}')
