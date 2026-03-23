"""Skill 配置"""
from pathlib import Path

# 路径配置
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
DEFAULT_DB_PATH = BASE_DIR / "capture.db"
DEFAULT_PROXY_PORT = 18527  # 使用不常见的端口避免冲突
DEFAULT_WEB_PORT = 18528     # Web UI 端口

# 输出子目录
API_OUTPUT_DIR = OUTPUT_DIR / "api"
DATA_OUTPUT_DIR = OUTPUT_DIR / "data"
CASE_OUTPUT_DIR = OUTPUT_DIR / "case"

# 过滤配置
EXCLUDED_EXTENSIONS = {'.js', '.css', '.png', '.jpg', '.gif', '.ico', '.woff', '.svg', '.woff2'}
EXCLUDED_PATHS = {'/health', '/ping', '/actuator', '/ready'}
EXCLUDED_KEYWORDS = {'analytics', 'sentry', 'track', 'log', 'metrics'}

# 动态值识别
DYNAMIC_FIELD_PATTERNS = [
    r'.*[iI]d$',               # id, Id, tokenId, user_id
    r'.*[tT]ime.*',            # time, timestamp, createTime
    r'.*[nN]o$',               # no, orderNo
    r'.*[sS]ign.*',            # sign, signature
    r'^\d{13}$',               # 13位时间戳
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',  # UUID
]

# 框架扫描配置
TARGET_FILES = [
    "conftest.py",
    "api/base.py",
    "config.py",
]
