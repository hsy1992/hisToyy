# 本地sqlite操作类
import sqlite3
import os
from datetime import datetime, time
from pathlib import Path

class SQLiteHelper:
    def __init__(self, db_name="app_config.db"):
        self.db_name = db_name
        # 初始化时自动检查并创建表
        self._init_db()

    def get_connection(self):
        """获取数据库连接，并设置 row_factory 以便按列名访问数据"""
        self.db_path = os.path.join('db', self.db_name)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 这样查询结果可以通过 ['column_name'] 访问
        return conn

    def _init_db(self):
        """
        初始化数据库：在此定义你需要的所有表结构
        创建记录表
        start_time、end_time 导出的开始结束时间
        create_time 创建时间 export_time 导出成功的时间
        export_num 导出数量
        export_file_name 导出名称
        export_file_path 导出路径
        status 状态 1 初始状态 2导出成功 3 导出失败 4 用友导入成功 5 用友导入失败
        import_yy_start 用友导入开始游标
        import_yy_num 用友导入数据量
        data_type 数据类型
        """
        sql_create_config = """
        CREATE TABLE IF NOT EXISTS sys_export_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            end_time TEXT,
            create_time TEXT,
            export_time TEXT,
            data_type TEXT,
            export_num TEXT,
            export_file_name TEXT,
            export_file_path TEXT,
            import_yy_start TEXT,
            import_yy_num INTEGER,
            shouyin_list TEXT,
            zz_code TEXT,
            status INTEGER
        );
        """

        self.execute_non_query(sql_create_config)
        Path("db").mkdir(parents=True, exist_ok=True)


    def execute_non_query(self, sql, params=None):
        """
        执行增、删、改等非查询 SQL 语句
        :param sql: SQL 语句
        :param params: 参数元组 (arg1, arg2...)
        :return: 受影响的行数
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            print(f"SQLite 执行错误: {e}")
            return -1

    def fetch_all(self, sql, params=None):
        """
        执行查询，返回所有结果
        :return: 列表，每个元素是字典格式 {'col1': val1, 'col2': val2}
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                # 转换为字典列表
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"SQLite 查询错误: {e}")
            return []

    def fetch_one(self, sql, params=None):
        """查询单条记录"""
        res = self.fetch_all(sql, params)
        return res[0] if res else None

    def insert_record(self, data):
        """
        插入新记录
        data: 字典格式，例如 {'data_type': '凭证', 'status': 1}
        """
        # 自动添加创建时间
        data['create_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data['status'] = 1
        fields = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO sys_export_record ({fields}) VALUES ({placeholders})"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, list(data.values()))
            return cursor.lastrowid  # 返回新插入行的 ID

    def update_status(self, record_id, status, extra_data=None):
        """更新状态和相关信息（如导出成功后更新导出时间）"""
        if extra_data is None:
            extra_data = {}

        extra_data['status'] = status
        # 如果是导出成功(2)或导入成功(4)，自动记录时间
        extra_data['export_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        set_clause = ", ".join([f"{k} = ?" for k in extra_data.keys()])
        sql = f"UPDATE sys_export_record SET {set_clause} WHERE id = ?"

        with self.get_connection() as conn:
            conn.execute(sql, list(extra_data.values()) + [record_id])

    def export_his_success(self, record_id, export_file_name, export_file_path):
        """
        导出his成功后更改数据库
            export_file_name TEXT,
            export_file_path TEXT,
        """
        self.update_status(record_id, 2, {
            "export_file_name": export_file_name,
            "export_file_path": export_file_path
        })

    def get_record_by_id(self, record_id):
        """根据ID查询记录"""
        return self.fetch_one("SELECT * FROM sys_export_record WHERE id = :record_id", {"record_id": record_id})

    def import_yy_result(self, record_id, success, import_yy_start, num):
        """
            导入后更改数据库
            import_yy_start TEXT,
            import_yy_num INTEGER,
        """
        if success:
            self.update_status(record_id, 4, {
                "import_yy_num": num,
                "import_yy_start": import_yy_start
            })
        else:
            self.update_status(record_id, 5, {})

if __name__ == '__main__':
    db = SQLiteHelper()


