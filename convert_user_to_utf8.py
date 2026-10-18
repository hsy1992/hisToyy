import sys, os

src_path = 'c:/Users/Administrator/Desktop/医药/script_user.sql'
dst_path = 'c:/Users/Administrator/Desktop/医药/script_user_utf8.sql'

print(f"Reading {src_path} (UTF-16 LE)...")
with open(src_path, 'r', encoding='utf-16') as f:
    content = f.read()

print(f"Original char length: {len(content)}")
lines = content.splitlines(keepends=True)
print(f"Original lines count: {len(lines)}")

print(f"Writing to {dst_path} (UTF-8 with BOM)...")
with open(dst_path, 'w', encoding='utf-8-sig') as f:
    f.write(content)

src_size = os.path.getsize(src_path)
dst_size = os.path.getsize(dst_path)
print(f"Source size: {src_size} bytes")
print(f"Destination size: {dst_size} bytes")

# 完整性双向校验
with open(dst_path, 'r', encoding='utf-8-sig') as f:
    dst_content = f.read()

assert content == dst_content, "Content mismatch!"
print("Verification passed! Content is 100% identical.")

# 检查中文样本
print("Checking Chinese sample lines:")
for l in dst_content.splitlines():
    if 'INSERT' in l and any('\u4e00' <= ch <= '\u9fff' for ch in l):
        print("  Sample line with Chinese:", l.strip()[:100])
        break
