"""
荟城减重 WSP 报告生成系统 - 数据库连接模块
"""
import pymysql
import json
import os
from datetime import datetime, date

# 从环境变量读取数据库配置，支持Docker部署
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'huicheng'),
    'password': os.getenv('DB_PASSWORD', 'Huicheng@2026'),
    'database': os.getenv('DB_NAME', 'huicheng_wsp'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


def get_conn():
    """获取数据库连接"""
    conn = pymysql.connect(**DB_CONFIG)
    conn.autocommit(True)
    return conn


def json_serial(obj):
    """JSON 序列化辅助函数"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def serialize_row(row):
    """将数据库行转换为可 JSON 序列化的字典，解析 JSON 字段"""
    if row is None:
        return None
    result = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            result[k] = v.isoformat() if isinstance(v, date) and not isinstance(v, datetime) else v.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(v, str) and v.startswith('[') or (isinstance(v, str) and v.startswith('{')):
            try:
                result[k] = json.loads(v)
            except (json.JSONDecodeError, ValueError):
                result[k] = v
        elif isinstance(v, bytes):
            result[k] = v.decode('utf-8')
        elif hasattr(v, 'isoformat'):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result
