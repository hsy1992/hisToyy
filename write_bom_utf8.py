import sys, os

src_path = 'c:/Users/Administrator/Desktop/医药/script_enum.sql'
dst_path = 'c:/Users/Administrator/Desktop/医药/script_enum_utf8.sql'

with open(src_path, 'r', encoding='utf-16') as f:
    content = f.read()

# 写入 UTF-8 with BOM (utf-8-sig)，与医药目录下的 script_utf8.sql 保持完全一致的编码规范
with open(dst_path, 'w', encoding='utf-8-sig') as f:
    f.write(content)

print(f"Successfully written to {dst_path}")
print(f"File size: {os.path.getsize(dst_path)} bytes")

# 验证前几个字节
with open(dst_path, 'rb') as f:
    head = f.read(15)
    print("Head bytes:", repr(head))
