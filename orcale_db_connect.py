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
from yongyou_coe import is_build
from PyQt5.QtCore import QThread, pyqtSignal

def init_oracle():
    try:
        # 1. 获取当前脚本运行的绝对路径
        if getattr(sys, 'frozen', False):
            # 如果是打包成了 .exe
            base_path = sys._MEIPASS
        else:
            # 如果是直接运行 .py
            base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
        # 2. 拼接内置客户端的路径
        client_path = os.path.join(base_path, "instantclient_11_21")
        # 假设你的 client 路径是 client_path
        # 3. 核心步骤：初始化 Thick 模式
        # 只要指定了 lib_dir，python-oracledb 就会进入 Thick 模式并兼容 11g
        logger.info(f"client_path！{client_path}")
        oracledb.init_oracle_client(lib_dir=client_path)
        logger.info("Oracle 内置客户端加载成功！", client_path)
    except Exception as e:
        logger.info(f"内置客户端加载失败: {e}")



def connect_to_oracle(user, pwd, host, port, service_name):
    try:
        init_oracle()
        dsn = f"""(DESCRIPTION=
                       (ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))
                       (CONNECT_DATA=(SID={service_name}))
                   )""" if not is_build else f"""
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
    except Exception as e:
        logger.info(f"数据库连接失败: {e}")
        return None


def connect_to_oracle_test(user, pwd, host, port, service_name):
    try:
        init_oracle()
        dsn = f"""(DESCRIPTION=
                         (ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))
                         (CONNECT_DATA=(SID={service_name}))
                     )""" if not is_build else f"""
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
    except Exception as e:
        logger.info(f"oracle 连接失败: {e}, {dsn}")
        return False

# 定义类型配置映射表
# 格式: type_id: (中文前缀, 详情视图名, 汇总视图名)
TYPE_CONFIG = {
    0: ("门诊收入", "v_门诊人员缴款书收入项目", "v_门诊人员缴款书结算方式", "扎帐时间", "扎帐时间"),
    1: ("住院结算", "v_住院人员缴款书收入项目", "v_住院人员缴款书结算方式", "扎帐时间", "扎帐时间"),
    2: ("全院病人费用", "v_全院病人费用汇总住院", None, "日期", ""),  # 没有汇总视图
    3: ("门诊自助机", "v_门诊人员缴款书自助机收入项目", "v_门诊人员缴款书自助机结算方式", "登记时间", "收款时间"),
    4: ("门诊扫码", "v_门诊人员缴款书扫码付收入项目", "v_门诊人员缴款书扫码付结算方式", "登记时间", "收款时间"),
}

def get_his_data(oracle_config, start_str, end_str, type, shouyin_list, zz_code):
    try:
        # 链接数据库
        conn = connect_to_oracle(oracle_config.get('user'), oracle_config.get('password'), oracle_config.get('ip'), oracle_config.get('port'),
                               oracle_config.get('service_name'))
        full_path = ""
        row_count = 0
        # 确保export_data文件夹是否存咋
        Path("export_data").mkdir(parents=True, exist_ok=True)
        # 获取配置
        config = TYPE_CONFIG.get(type)
        if not config:
            logger.error(f"未知类型: {type}")
            return
        prefix, detail_view, total_view, time_type, time_type_total = config
        # 测试环境下重写表名
        if not is_build and type == 0:
            detail_view, total_view = 'SYSTEM."zhuyuan"', 'SYSTEM."zhuyuan_total"'
        else:
            detail_view = f'{detail_view}'
            total_view = f'{total_view}' if total_view else None

        shoukuan_df = pd.DataFrame()
        total_df = pd.DataFrame()
        if detail_view:
            # 详情
            where_clause = f' WHERE "{time_type}" >= TO_DATE(\'{start_str}\', \'YYYY-MM-DD HH24:MI:SS\') ' \
                           f'AND "{time_type}" < TO_DATE(\'{end_str}\', \'YYYY-MM-DD HH24:MI:SS\')'
            if type == 0 or type == 1:
                if shouyin_list:
                    in_name_list = ",".join([f"'{name}'" for name in shouyin_list])
                    where_clause += f' AND "收款员" IN ({in_name_list})'
                if zz_code:
                    code = f"'{zz_code}'"
                    where_clause += f' AND "扎账单号" = {code} '
            logger.info(f"查询sql: SELECT * FROM {detail_view}{where_clause}")
            shoukuan_df = pd.read_sql(f"SELECT * FROM {detail_view}{where_clause}", conn)

        if total_view:
            where_clause = f' WHERE "{time_type_total}" >= TO_DATE(\'{start_str}\', \'YYYY-MM-DD HH24:MI:SS\') ' \
                           f'AND "{time_type_total}" < TO_DATE(\'{end_str}\', \'YYYY-MM-DD HH24:MI:SS\')' if type != 2 else ''
            if type == 0 or type == 1:
                if shouyin_list:
                    in_name_list = ",".join([f"'{name}'" for name in shouyin_list])
                    where_clause += f' AND "收款员" IN ({in_name_list})'
                if zz_code:
                    code = f"'{zz_code}'"
                    where_clause += f' AND "扎账单号" = {code} '
            logger.info(f"查询totalsql: SELECT * FROM {total_view}{where_clause}")
            total_df = pd.read_sql(f"SELECT * FROM {total_view}{where_clause}", conn) if total_view else None

        # 文件导出处理
        s = datetime.now().strftime("%H:%M:%S")
        file_name = f"{prefix}{start_str}_{end_str}导出时间{s}.xlsx".replace(":", "_")
        full_path = os.path.join(resource_path("export_data"), file_name)

        # 写入详情页
        shoukuan_df.to_excel(full_path, sheet_name=f'收款数据', index=False)
        # 如果有汇总页，追加写入
        if total_df is not None:
            with pd.ExcelWriter(full_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                total_df.to_excel(writer, sheet_name='汇总数据', index=False)

        logger.info(f"文件已保存至: {full_path}, 已成功导出 {row_count} 条数据！")
        conn.close()
        return shoukuan_df, total_df, full_path
    except Exception as e:
        df_empty = pd.DataFrame()
        logger.info(f"获取数据失败:: {e}")
        return df_empty, df_empty, ''

class HisWorker(QThread):
    finished = pyqtSignal(pd.DataFrame, pd.DataFrame, str)  # 任务完成后发送结果信号

    def __init__(self, oracle_config, start_str, end_str, type, shouyin_list, zz_code):
        super().__init__()
        self.oracle_config = oracle_config
        self.start_str = start_str
        self.end_str = end_str
        self.type = type
        self.shouyin_list = shouyin_list
        self.zz_code = zz_code

    def run(self):
        try:
            shoukuan_df, total_df, full_path = get_his_data(self.oracle_config, self.start_str, self.end_str, self.type, self.shouyin_list, self.zz_code)
            self.finished.emit(shoukuan_df, total_df, full_path)
        except Exception as e:
            df_empty = pd.DataFrame()
            logger.info(f"获取数据失败:: {e}")
            self.finished.emit(df_empty, df_empty, '')

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
