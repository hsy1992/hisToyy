import logging
import os
import sys
from datetime import datetime

# 1. 创建日志文件夹
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 2. 配置日志格式
log_format = '%(asctime)s - %(levelname)s - %(module)s - %(message)s'
today = datetime.now().strftime("%Y-%m-%d")
log_file = os.path.join(log_dir, f"app{today}.log")

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'), # 写入文件
        logging.StreamHandler(sys.stdout)                        # 同时输出到控制台
    ]
)

logger = logging.getLogger("ImportTool")
