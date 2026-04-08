"""Insert generated configs into web.py."""

with open('E:/计算综测/pangaocal-main/web.py', encoding='utf-8') as f:
    web_content = f.read()

with open('E:/计算综测/new_configs.py', encoding='utf-8') as f:
    new_content = f.read()

# Extract only the config entries (between the two section headers)
config_start = new_content.find('            # ------------------- 24环境工程')
config_end = new_content.find('# ============ 以下添加到 self.major_display_list')
config_entries = new_content[config_start:config_end].rstrip()

# Extract display list entries
display_start = new_content.find("            {'code': '24hjgc'")
display_entries = new_content[display_start:].rstrip()

# --- Insert 1: config entries before 'other' ---
# Find the insertion point: after '24kg' ends, before 'other' block
insert_marker = "            # ------------------- 其他班级（仅综测） -------------------"
assert insert_marker in web_content, "Marker 1 not found!"

web_content = web_content.replace(
    insert_marker,
    config_entries + "\n\n" + insert_marker
)

# --- Insert 2: display list entries after '24kg' display entry ---
insert_marker2 = "            # === 新增：自定义专业入口 ==="
assert insert_marker2 in web_content, "Marker 2 not found!"

web_content = web_content.replace(
    insert_marker2,
    display_entries + "\n            # === 新增：自定义专业入口 ==="
)

with open('E:/计算综测/pangaocal-main/web.py', 'w', encoding='utf-8') as f:
    f.write(web_content)

print("Done! web.py updated.")

# Verify the changes
with open('E:/计算综测/pangaocal-main/web.py', encoding='utf-8') as f:
    updated = f.read()

# Count major entries
import re
codes = re.findall(r"'专业代码': '([^']+)'", updated)
print(f"Total major codes in web.py: {len(codes)}")
print("First 5:", codes[:5])
print("Last 5:", codes[-5:])
