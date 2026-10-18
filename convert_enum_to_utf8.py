import sys, os

src_path = 'c:/Users/Administrator/Desktop/医药/script_enum.sql'
dst_path = 'c:/Users/Administrator/Desktop/医药/script_enum_utf8.sql'

print(f"Reading {src_path} (UTF-16 LE)...")
with open(src_path, 'r', encoding='utf-16') as f:
    content = f.read()

print(f"Original char length: {len(content)}")
lines = content.splitlines(keepends=True)
print(f"Original lines count: {len(lines)}")

print(f"Writing to {dst_path} (UTF-8)...")
with open(dst_path, 'w', encoding='utf-8') as f:
    f.write(content)

src_size = os.path.getsize(src_path)
dst_size = os.path.getsize(dst_path)
print(f"Source size: {src_size} bytes")
print(f"Destination size: {dst_size} bytes")

# 验证转换后文件
with open(dst_path, 'r', encoding='utf-8') as f:
    dst_content = f.read()

assert content == dst_content, "Content mismatch!"
print("Verification passed! Content is 100% identical.")
print(f"Sample line 1: {lines[0].strip()}")
print(f"Sample line 5: {lines[4].strip()[:120]}")
print(f"Sample last line: {lines[-1].strip()}")
