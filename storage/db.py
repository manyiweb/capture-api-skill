import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class Database:
    """SQLite 数据库操作封装"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_table()

    def _init_table(self):
        """初始化表结构"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS captured_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                path TEXT NOT NULL,
                query_params TEXT,
                request_body TEXT,
                response_code INTEGER,
                response_body TEXT,
                selected INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    def save_or_update(self, data: Dict):
        """保存或更新记录（去重：相同 path + request_body 只保留最新）

        若已存在相同 (path, request_body) 的记录，则更新该记录；
        否则插入新记录。
        """
        cursor = self.conn.cursor()
        path = data.get('path', '')
        request_body = data.get('request_body')

        # 查找是否存在相同 path + request_body 的记录
        cursor.execute(
            'SELECT id FROM captured_requests WHERE path = ? AND (request_body = ? OR (request_body IS NULL AND ? IS NULL))',
            (path, request_body, request_body)
        )
        existing = cursor.fetchone()

        if existing:
            # 更新已有记录
            cursor.execute('''
                UPDATE captured_requests
                SET method = ?,
                    url = ?,
                    query_params = ?,
                    response_code = ?,
                    response_body = ?,
                    timestamp = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data.get('method', ''),
                data.get('url', ''),
                data.get('query_params'),
                data.get('response_code'),
                data.get('response_body'),
                existing['id']
            ))
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO captured_requests
                    (method, url, path, query_params, request_body, response_code, response_body)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('method', ''),
                data.get('url', ''),
                path,
                data.get('query_params'),
                request_body,
                data.get('response_code'),
                data.get('response_body'),
            ))

        self.conn.commit()

    def get_all(self, filters: Optional[Dict] = None) -> List[Dict]:
        """获取所有记录，支持过滤（method, keyword）

        filters 支持的键：
          - 'method'  : 精确匹配 HTTP 方法（大小写不敏感）
          - 'keyword' : 模糊匹配 url 或 path（LIKE）
        """
        cursor = self.conn.cursor()
        query = 'SELECT * FROM captured_requests'
        params: list = []
        conditions: list = []

        if filters:
            method = filters.get('method')
            keyword = filters.get('keyword')

            if method:
                conditions.append('UPPER(method) = UPPER(?)')
                params.append(method)

            if keyword:
                conditions.append('(url LIKE ? OR path LIKE ?)')
                like_pattern = f'%{keyword}%'
                params.extend([like_pattern, like_pattern])

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' ORDER BY timestamp DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def update_selected(self, ids: List[int], selected: bool):
        """更新选中状态"""
        if not ids:
            return
        selected_int = 1 if selected else 0
        placeholders = ','.join('?' * len(ids))
        cursor = self.conn.cursor()
        cursor.execute(
            f'UPDATE captured_requests SET selected = ? WHERE id IN ({placeholders})',
            [selected_int] + list(ids)
        )
        self.conn.commit()

    def get_selected(self) -> List[Dict]:
        """获取所有选中的记录"""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM captured_requests WHERE selected = 1 ORDER BY timestamp DESC'
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def clear(self):
        """清空所有数据"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM captured_requests')
        self.conn.commit()

    def close(self):
        """关闭数据库连接"""
        self.conn.close()
