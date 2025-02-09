import logging
import os
from datetime import datetime

# 创建logs目录（如果不存在）
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 生成日志文件名（使用当前时间）
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"app_{current_time}.log")

# 创建日志记录器
logger = logging.getLogger("DeepReach")
logger.setLevel(logging.DEBUG)

# 创建文件处理器
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 创建格式化器
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 设置处理器的格式化器
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 添加处理器到日志记录器
logger.addHandler(file_handler)
logger.addHandler(console_handler) 