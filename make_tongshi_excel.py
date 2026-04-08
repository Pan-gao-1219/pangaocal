"""
读取 code_20260404.csv，生成 通识课程数据库.xlsx
放在 pangaocal-main/ 旁边，供 web.py 调用。
"""
import pandas as pd

CSV_PATH = 'C:/Users/18222/Downloads/code_20260404.csv'
OUT_PATH = 'E:/计算综测/pangaocal-main/通识课程数据库.xlsx'

# 读取
df = pd.read_csv(CSV_PATH, encoding='utf-8', dtype=str)
df.columns = [c.strip() for c in df.columns]
# 去掉空列
df = df.dropna(axis=1, how='all')
df = df.dropna(subset=['课程名'])

# 重命名列（统一）
col_map = {}
for c in df.columns:
    if '序号' in c or c == '0':
        col_map[c] = '序号'
    elif '开课' in c or '单位' in c:
        col_map[c] = '开课单位'
    elif '课程名' in c or ('课程' in c and '代码' not in c):
        col_map[c] = '课程名'
    elif '学分' in c:
        col_map[c] = '学分'
    elif '2024' in c:
        col_map[c] = '2024级模块'
    elif '2023' in c:
        col_map[c] = '2023级模块'
df = df.rename(columns=col_map)

# 确保必要列存在
needed = ['课程名', '学分', '2024级模块', '2023级模块']
for col in needed:
    if col not in df.columns:
        df[col] = ''

# 学分转数字
df['学分'] = pd.to_numeric(df['学分'], errors='coerce').fillna(0)

# 统计各模块课程数
print("2024级模块分布：")
print(df['2024级模块'].value_counts().to_string())
print("\n2023级模块分布：")
print(df['2023级模块'].value_counts().to_string())
print(f"\n总课程数: {len(df)}")

# 生成 Excel，多Sheet
with pd.ExcelWriter(OUT_PATH, engine='openpyxl') as writer:
    # Sheet1: 全量数据
    df.to_excel(writer, sheet_name='全量课程', index=False)

    # Sheet2~: 按2024级模块分组
    for mod in sorted(df['2024级模块'].dropna().unique()):
        sub = df[df['2024级模块'] == mod].reset_index(drop=True)
        sheet_name = mod[:28]  # Excel sheet名最长31字符
        sub.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"\nExcel 已生成: {OUT_PATH}")
print("Sheet 列表:")
import openpyxl
wb = openpyxl.load_workbook(OUT_PATH)
for name in wb.sheetnames:
    print(f"  {name}")
