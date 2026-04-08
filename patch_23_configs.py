"""
将 23级专业配置注入 web.py 的 MajorConfig，并在 display_list 中追加23级条目。
跳过已存在的 23kg / 23dz / 23dx（它们已有特殊配置含卓越班等信息）。
"""
import sys, re, ast
sys.stdout.reconfigure(encoding='utf-8')

WEB_PY = 'E:/计算综测/pangaocal-main/web.py'

# ---- 读取生成的配置 ----
with open('E:/计算综测/new_configs_23.py', encoding='utf-8') as f:
    src23 = f.read()

# 执行 new_configs_23.py 以获取字典和列表
ns = {}
exec(src23, ns)
configs23 = ns['NEW_CONFIGS_23']
display23 = ns['NEW_DISPLAY_23']

# 跳过已存在的三个专业（有卓越班特殊配置）
SKIP_CODES = {'23kg', '23dz', '23dx'}

# ---- 构建要插入的 config 字符串 ----
cfg_lines = ['\n            # =========== 23级（2022版培养方案）===========\n']
for code, cfg in sorted(configs23.items()):
    if code in SKIP_CODES:
        continue
    major_name = cfg['专业名称']
    credits = cfg['学分要求']
    courses = cfg['选修课列表']
    cfg_lines.append(f"            # ------------------- {major_name} -------------------\n")
    cfg_lines.append(f"            '{code}': {{\n")
    cfg_lines.append(f"                '专业名称': '{major_name}',\n")
    cfg_lines.append(f"                '专业代码': '{code}',\n")
    cfg_lines.append(f"                '有卓越班': False,\n")
    cfg_lines.append(f"                '学分要求': {{\n")
    for cat, cr in credits.items():
        cfg_lines.append(f"                    '{cat}': {cr},\n")
    cfg_lines.append(f"                }},\n")
    cfg_lines.append(f"                '选修课列表': {{\n")
    for cat, cs in courses.items():
        cfg_lines.append(f"                    '{cat}': {cs!r},\n")
    cfg_lines.append(f"                }}\n")
    cfg_lines.append(f"            }},\n")

insert_cfg = ''.join(cfg_lines)

# ---- 构建要插入的 display_list 条目字符串 ----
disp_lines = []
for entry in display23:
    if entry['code'] in SKIP_CODES:
        continue
    disp_lines.append(
        f"            {{'code': '{entry['code']}', 'name': '{entry['name']}', "
        f"'emoji': '{entry['emoji']}', 'school': '{entry['school']}', 'year': '2023'}},\n"
    )
insert_disp = ''.join(disp_lines)

# ---- 读取 web.py ----
with open(WEB_PY, encoding='utf-8') as f:
    content = f.read()

# ---- 插入 configs：在 'other' 条目之前 ----
target_cfg = "            # ------------------- 其他班级（仅综测） -------------------\n            'other': {"
assert target_cfg in content, "找不到 'other' 插入锚点！"
content = content.replace(target_cfg, insert_cfg + target_cfg)

# ---- 插入 display_list：在 24kg 行之前（保持23级在列表前面） ----
target_disp = "            {'code': '24kg', 'name': '24勘工（卓越工程师）'"
assert target_disp in content, "找不到 display_list 插入锚点！"
content = content.replace(target_disp, insert_disp + "            " + target_disp.lstrip())

# ---- 写回 ----
with open(WEB_PY, 'w', encoding='utf-8') as f:
    f.write(content)

print("web.py 已更新")

# ---- 语法验证 ----
with open(WEB_PY, encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    print("语法检查: OK ✓")
except SyntaxError as e:
    print(f"语法错误: {e}")

# 统计
added_cfg = src.count("'专业代码': '23") - 3  # 减去原有的 3 个
print(f"共新增 23级 配置: {added_cfg} 个")
added_disp = src.count("'year': '2023'") - 3
print(f"display_list 中 23级 条目: {added_disp + 3} 个（含原有3个）")
