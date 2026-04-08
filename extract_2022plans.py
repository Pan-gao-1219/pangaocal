"""
提取 2022版培养方案 PDF 文本，生成 all_plans_2022.json
"""
import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from pdfminer.high_level import extract_text

PDF_DIR = 'C:/Users/18222/Desktop/新建文件夹 (2)/中国海洋大学2022版本科专业人才培养方案'
OUT_JSON = 'E:/计算综测/all_plans_2022.json'

results = {}
pdf_files = sorted([f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')])
print(f"共 {len(pdf_files)} 个 PDF")

for i, fname in enumerate(pdf_files, 1):
    path = os.path.join(PDF_DIR, fname)
    try:
        text = extract_text(path)
        results[fname] = text
        print(f"[{i:02d}/{len(pdf_files)}] OK  {fname}")
    except Exception as e:
        results[fname] = ''
        print(f"[{i:02d}/{len(pdf_files)}] ERR {fname}: {e}")

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n完成，已保存到 {OUT_JSON}")
