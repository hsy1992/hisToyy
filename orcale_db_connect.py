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
        client_path = os.path.join(base_path, "lib", "plsql")
        # 假设你的 client 路径是 client_path
        # 3. 核心步骤：初始化 Thick 模式
        # 只要指定了 lib_dir，python-oracledb 就会进入 Thick 模式并兼容 11g
        oracledb.init_oracle_client(lib_dir=client_path)
        print("Oracle 内置客户端加载成功！")

    except Exception as e:
        print(f"内置客户端加载失败: {e}")


def connect_to_oracle(user, pwd, host, port, service_name):
    try:
        dsn = f"""(DESCRIPTION=
                       (ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))
                       (CONNECT_DATA=(SID={service_name}))
                   )"""
        dsn = f"""
                 (DESCRIPTION =
                   (ADDRESS =(PROTOCOL=TCP)(HOST ={host})(PORT={port}))
                   (CONNECT_DATA=
                     (SERVER=DEDICATED)
                     (SERVICE_NAME={service_name}))
                 )"""
        logger.info(dsn)
        conn = oracledb.connect(
            user=user,
            password=pwd,
            dsn=dsn
        )
        return conn
    except oracledb.Error as e:
        logger.info(f"数据库连接失败: {e}")
        return None


def connect_to_oracle_test(user, pwd, host, port, service_name):
    try:
        init_oracle()
        dsn = f"""(DESCRIPTION=
                         (ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))
                         (CONNECT_DATA=(SID={service_name}))
                     )"""
        dsn = f"""
              (DESCRIPTION =
                (ADDRESS =(PROTOCOL=TCP)(HOST ={host})(PORT={port}))
                (CONNECT_DATA=
                  (SERVER=DEDICATED)
                  (SERVICE_NAME={service_name}))
              )"""
        logger.info(dsn)
        conn = oracledb.connect(
            user=user,
            password=pwd,
            dsn=dsn
        )
        conn.close()
        logger.info(f"oracle 连接成功: {dsn}")
        return True
    except oracledb.Error as e:
        print(f"数据库连接失败: {e}")
        logger.info(f"oracle 连接失败: {e}, {dsn}")
        return False


def get_his_data(oracle_config, start_str, end_str, type):
    try:
        init_oracle()
        dsn = oracledb.makedsn(oracle_config.get('ip'), oracle_config.get('port'),
                               service_name=oracle_config.get('service_name'))
        conn = oracledb.connect(
            user=oracle_config.get('user'),
            password=oracle_config.get('password'),
            dsn=dsn
        )

        # 进行查询his数据
        if type == 0:
            # 门诊
            # sql = f'SELECT * FROM SYSTEM."zhuyuan"'
            # sql_total = f'SELECT * FROM SYSTEM."zhuyuan_total"'

            sql = f'SELECT * FROM ZL_YY."v_门诊人员缴款书收入项目" WHERE "扎帐时间" >= TO_DATE(\'{start_str}\', \'YYYY-MM-DD HH24:MI:SS\') and "扎帐时间" < TO_DATE(\'{end_str}\', \'YYYY-MM-DD HH24:MI:SS\')'
            sql_total = f'SELECT * FROM ZL_YY."v_门诊人员缴款书结算方式" WHERE "扎帐时间" >= TO_DATE(\'{start_str}\', \'YYYY-MM-DD HH24:MI:SS\') and "扎帐时间" < TO_DATE(\'{end_str}\', \'YYYY-MM-DD HH24:MI:SS\')'
            # 直接使用 pandas 读取
            # 注意：oracledb 建议配合 sql 字符串使用
            shoukuan_df = pd.read_sql(sql, conn)
            # 合计
            total_df = pd.read_sql(sql_total, conn)

            # 获取行数
            row_count = len(shoukuan_df)
            # 导出到 Excel
            Path("export_data").mkdir(parents=True, exist_ok=True)
            full_path = os.path.join(resource_path("export_data"),
                                     f"门诊{start_str}数据导出.xlsx".replace(
                                         ":", "_"))
            # column_map = {
            #     'id': '序号',
            #     'bumen': '开单科室',
            #     'zz_code': '扎帐单号',
            #     'shoukuantype': '扎帐类别',
            #     'shouyin': '收款员',
            #     'date': '扎帐时间',
            #     'bianma': '编码',
            #     'feiyongmingcheng': '项目',
            #     'jine': '金额'
            # }
            # 转换表头
            shoukuan_df.rename(columns=column_map).to_excel(full_path, sheet_name='收款数据', index=False)
            with pd.ExcelWriter(full_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                total_df.to_excel(writer, sheet_name='汇总数据', index=False)
            logger.info(f"文件已保存至: {full_path}, 已成功导出 {row_count} 条数据！")
        else:
            conn.close()
            return "", 0
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
