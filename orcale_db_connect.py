# orcale 操作类
import os
import sys
import oracledb
from log_util import logger
from config import ConfigManager
import pandas as pd
from path_util import resource_path
from datetime import datetime, time
from pathlib import Path


def init_oracle():
    try:
        # 1. 获取当前脚本运行的绝对路径
        if getattr(sys, 'frozen', False):
            # 如果是打包成了 .exe
            base_path = sys._MEIPASS
        else:
            # 如果是直接运行 .py
            base_path = os.path.dirname(os.path.abspath(__file__))
        # 2. 拼接内置客户端的路径
        print(base_path)
        client_path = os.path.join(base_path, "lib", "instantclient_11_2")
        # 假设你的 client 路径是 client_path
        # 3. 核心步骤：初始化 Thick 模式
        # 只要指定了 lib_dir，python-oracledb 就会进入 Thick 模式并兼容 11g
        oracledb.init_oracle_client(lib_dir=client_path)
        print("Oracle 内置客户端加载成功！")

    except Exception as e:
        print(f"内置客户端加载失败: {e}")


def connect_to_oracle(user, pwd, host, port, service_name):
    try:
        # 使用显式的 SID 连接描述符
        dsn_tns = f"""(DESCRIPTION=
                 (ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))
                 (CONNECT_DATA=(SID={service_name}))
             )"""
        logger.info(dsn_tns)
        conn = oracledb.connect(
            user=user,
            password=pwd,
            dsn=dsn_tns
        )
        return conn
    except oracledb.Error as e:
        print(f"数据库连接失败: {e}")
        return None


def connect_to_oracle_test(user, pwd, host, port, service_name):
    try:
        init_oracle()
        # 使用显式的 SID 连接描述符
        dsn_tns = f"""(DESCRIPTION=
                        (ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))
                        (CONNECT_DATA=(SID={service_name}))
                    )"""
        logger.info(dsn_tns)
        conn = oracledb.connect(
            user=user,
            password=pwd,
            dsn=dsn_tns
        )
        conn.close()
        logger.info(f"oracle 连接成功: {dsn_tns}")
        return True
    except oracledb.Error as e:
        logger.info(f"oracle 连接失败: {e}, {dsn_tns}")
        return False


def get_his_data(oracle_config, start_str, end_str):
    try:
        init_oracle()
        dsn = oracledb.makedsn(oracle_config.get('ip'), oracle_config.get('port'),
                               service_name=oracle_config.get('service_name'))
        conn = oracledb.connect(
            user=oracle_config.get('user'),
            password=oracle_config.get('password'),
            dsn=dsn
        )

        sql = 'SELECT * FROM SYSTEM."zhuyuan"'
        # 直接使用 pandas 读取
        # 注意：oracledb 建议配合 sql 字符串使用
        df = pd.read_sql(sql, conn)
        # 获取行数
        row_count = len(df)
        # 导出到 Excel
        Path("export_data").mkdir(parents=True, exist_ok=True)
        full_path = os.path.join(resource_path("export_data"), f"{start_str}-{end_str}住院数据导出{datetime.now().strftime('%Y-%m-%d %H_%M_%S')}.xlsx".replace(":", "_"))
        column_map = {
            'id': 'id',
            'date': '日期（按天到出）',
            'shouyin': '收银员（一个业务员一个表）',
            'shoukuantype': '收款类型',
            'zhanghao': '账号',
            'bumen': '部门',
            'feiyongmingcheng': '费用名称',
            'shoukuanjine': '收款金额',
            'jine': '金额'
        }

        # 转换表头
        df.rename(columns=column_map).to_excel(full_path, index=False)
        print(f"文件已保存至: {full_path}, 已成功导出 {row_count} 条数据！")
        logger.info(f"文件已保存至: {full_path}, 已成功导出 {row_count} 条数据！")
        conn.close()
        return full_path, row_count
    except oracledb.Error as e:
        print(f"获取数据失败: {e}")
        logger.info(f"获取数据失败:: {e}")
        return "", 0

# 定义转换函数
def make_dict_factory(cursor):
    column_names = [d[0] for d in cursor.description]
    def create_row(*args):
        return dict(zip(column_names, args))
    return create_row


if __name__ == '__main__':
    # connect_to_oracle_test('system', 'oracle', '118.190.202.74', '1521', 'orcl')
    config_manager = ConfigManager()
    get_his_data(config_manager.get_db_config('oracle'), '123', '123')
