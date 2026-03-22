"""Skill 配置"""
from pathlib import Path

# 路径配置
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
DEFAULT_DB_PATH = BASE_DIR / "capture.db"
DEFAULT_PROXY_PORT = 8080
DEFAULT_WEB_PORT = 8888

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
    r'[a-z]*[iI]d$',           # id, Id, tokenId
    r'[a-z]*[tT]ime$',         # time, timestamp
    r'[a-z]*[nN]o$',           # no, orderNo
    r'[a-z]*[sS]ign$',         # sign, signature
    r'^\d{13}$',               # 13位时间戳
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',  # UUID
]

# 框架扫描配置
TARGET_FILES = [
    "conftest.py",
    "api/base.py",
    "config.py",
]
