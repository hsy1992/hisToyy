# sqlserver 操作类
import traceback

import numpy as np
import pandas as pd
import pyodbc
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (QProgressDialog)
from sqlalchemy import create_engine
from datetime import datetime
from config import ConfigManager
from log_util import logger
from py_sqlite import SQLiteHelper
from yongyou_coe import get_men_zhen_ccode, is_build, get_zhu_yuan_ccode2, get_zhu_yuan_ccode3, get_jiesuan_ccode, get_feiyong_menzhen_code
from yy_dept_mapper import get_dept_code_mz


def connect_to_sqlserver_test(host, port, db_name, user, password):
    # 查看你电脑上已有的驱动，选一个填入下面的 DRIVER
    print(pyodbc.drivers())

    conn_str = (
        "DRIVER={SQL Server};"  # 使用系统自带驱动
        f"SERVER={host},{port};"
        f"DATABASE={db_name};"
        f"UID={user};"
        f"PWD={password};"
        "Connect Timeout=5;"
    )

    # 针对 SQL 2008 的特殊处理
    try:
        # 1. 建立连接
        conn = pyodbc.connect(conn_str)
        conn.close()
        logger.info(f"sqlserver 连接成功, {conn_str}")
        return True
    except Exception as e:
        logger.info(f"sqlserver 连接失败: {e}, {conn_str}")
        return False


def import_data_to_yy(sqlserver_config, shoukuan_df, total_df, finished_signal):
    """ 导入数据导用友 """
    conn_str = (
        "DRIVER={SQL Server};"  # 使用系统自带驱动
        f"SERVER={sqlserver_config.get('ip')},{sqlserver_config.get('port')};"
        f"DATABASE={sqlserver_config.get('database')};"
        f"UID={sqlserver_config.get('user')};"
        f"PWD={sqlserver_config.get('password')};"
        "Connect Timeout=5;"
    )
    logger.info(conn_str)
    # 针对 SQL 2008 的特殊处理
    try:
        #  建立连接
        conn = pyodbc.connect(conn_str)
        logger.info(f"sqlserver 连接成功, {conn_str}")
        read_excel_real(conn, sqlserver_config, shoukuan_df, total_df, finished_signal)
    except Exception as e:
        traceback.print_exc()  # 打印完整的报错路径
        logger.info(f"sqlserver 导入失败: {e}, {conn_str}")
        finished_signal.emit(False, f"失败{e}", {})


def read_excel_real(conn, sqlserver_config, shoukuan_df, total_df, finished_signal):
    """
    根据配置读取数据
    """
    data_type = record['data_type']
    # 创建一个完全空的
    df_empty = pd.DataFrame()
    period_list = []
    if data_type == "0":
        # 门诊收入
        df_empty, period_list = build_menzhen_df(conn, shoukuan_df, total_df)
    elif data_type == "1":
        # 住院结算
        df_empty, period_list = build_zhuyuan_js_df(conn, shoukuan_df, total_df)
    elif data_type == "2":
        # 全院病人费用
        df_empty, period_list = build_zhuyuan_shouru(conn, shoukuan_df, total_df)
    elif data_type == "3":
        # 门诊自助机
        df_empty, period_list = build_menzhen_zizhuji(conn, shoukuan_df, total_df)
    elif data_type == "4":
        # 门诊扫码
        df_empty, period_list = build_menzhen_saoma(conn, shoukuan_df, total_df)

    # for index, row in df_empty.iterrows():
    #     print(f"--- 正在处理第 {index} 行 ---")
    #     for col in df_empty.columns:
    #         value = row[col]
    #         # 打印：列名 | 数据值 | Python类型
    #         print(f"列名: {col} | 值: {value} | 类型: {type(value)}")
    #         if isinstance(value, str):
    #             print(f"警告：第 {col} 个参数超长！长度: {len(value)}")
    #
    #     # 为了方便调试，只打印第一行就中断（或者根据需要去掉 break）
    #     break
    try:
        if not df_empty.empty:
            mssql_url = f"mssql+pyodbc://{sqlserver_config.get('user')}:{sqlserver_config.get('password')}@{sqlserver_config.get('ip')}:{sqlserver_config.get('port')}/{'UFDATA_001_2026' if is_build else 'UFDATA_999_2012'}?driver=SQL+Server"
            logger.info(f"sqlserver 连接成功, {mssql_url}")
            # 对于 SQL Server，强烈建议开启 fast_executemany 以提升 to_sql 速度
            engine = create_engine(mssql_url, fast_executemany=True, echo=False)
            # 使用 with 语句开启显式事务
            with engine.begin() as connection:
                df_empty.to_sql(
                    name='GL_accvouch',
                    con=connection,
                    schema='dbo',
                    if_exists='append',
                    index=False,
                    chunksize=1000,
                )
            logger.info("所有数据写入成功，事务已自动提交")
            record['import_yy_num'] = len(df_empty)
            finished_signal.emit(True, f"{','.join(map(str, period_list))}", record)
    except Exception as e:
        logger.info(f"写入失败，事务已回滚。错误详情: {e}")
        finished_signal.emit(False, f"写入失败, 失败{e}", record)


def build_menzhen_df(conn, shoukuan_df, total_df):
    """
    构建门诊数据
    """
    df_empty = pd.DataFrame()
    df_shoukuan = shoukuan_df.replace({np.nan: None})
    df_total = total_df.replace({np.nan: None})
    # 自动去除所有列名两端的空格
    df_shoukuan.columns = df_shoukuan.columns.str.strip()
    df_total.columns = df_total.columns.str.strip()
    # 将日期列转为日期格式（确保排序逻辑正确）
    df_shoukuan['扎帐时间'] = pd.to_datetime(df_shoukuan['扎帐时间'])
    date_val = pd.to_datetime(datetime.now().date().strftime("%Y-%m-%d %H:%M:%S"))
    period_list = []

    # 先查找汇总表 根据扎帐单号分组处理
    for i, (zz_code, total_group) in enumerate(df_total.groupby('扎账单号', sort=False)):
        if pd.notnull(zz_code):
            # 从明细表查找该单号的所有数据
            zz_code_result_df = df_shoukuan.query(f'扎账单号 == {zz_code}')
            # 获取该扎账单号的时间
            # date_val = pd.to_datetime(zz_code_result_df.iloc[0]['扎帐时间'])
            period = date_val.month
            # 每个单号都去获取下凭证
            start_ino_id = get_next_ino_id(conn, period)
            row_list = []
            ino_id = start_ino_id + i
            period_list.append(str(ino_id))
            # 贷方对方科目
            mc_ccode_equal = set()
            # 借方对方科目
            md_ccode_equal = set()
            inid = 0
            # 重置索引
            zz_code_result_df = zz_code_result_df.reset_index(drop=True)
            for index, row in zz_code_result_df.iterrows():
                inid = index + 1
                dbill_date = date_val
                user_name = row['收款员']
                # 摘要
                cdigest = f"门诊收入,扎账单号:{'' if pd.isna(row['扎账单号']) else row['扎账单号']},{'' if pd.isna(user_name) else user_name}"
                md = 0.0
                # 贷方
                mc_v = pd.to_numeric(row.get('金额', 0))
                mc = 0.0 if pd.isna(mc_v) else float(mc_v)
                # 部门
                cdept_id = get_dept_code_mz(row['开单科室'], 'his_mz')
                # 科目
                ccode = get_men_zhen_ccode(row, 1)
                ccode = str(ccode or "").strip()
                if not ccode:
                    # 抛出内置的“值错误”异常
                    raise ValueError("错误：科目编码(ccode)不能为空或纯空格！")
                # 贷方对方科目
                mc_ccode_equal.add(ccode)
                row_list.append(
                    transform_to_yonyou(period, ino_id, inid, dbill_date, '李红霞', md, mc, cdept_id, ccode, cdigest))
                print(
                    f"period是: {period},inid是: {inid},dbill_date: {dbill_date}, cdigest: {cdigest}, user_name: {user_name}, 借方: {md}, 贷方: {mc}, cdept_id: {cdept_id}, ccode:{ccode}")
            # 继续去插入汇总数据
            for index, row in total_group.iterrows():
                if row['项目'] != '合计':
                    inid = inid + 1
                    user_name = row['收款员']
                    # 摘要
                    cdigest = f"门诊收入,{user_name}"
                    # 收款金额
                    # 借方
                    md_v = pd.to_numeric(row.get('金额', 0))
                    md = 0.0 if pd.isna(md_v) else float(md_v)
                    # 贷方
                    mc = 0.0
                    # 科目
                    ccode = get_men_zhen_ccode(row, 2)
                    ccode = str(ccode or "").strip()
                    if not ccode:
                        # 抛出内置的“值错误”异常
                        raise ValueError("错误：科目编码(ccode)不能为空或纯空格！")
                    md_ccode_equal.add(ccode)
                    row_list.append(
                        transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, mc, None, ccode, cdigest))
                    print(
                        f"period是: {period},inid是: {inid},dbill_date: {date_val}, cdigest: {cdigest}, user_name: {user_name}, 借方: {md}, 贷方: {mc}, cdept_id: NONE, ccode:{ccode}")

            for yongyou_row in row_list:
                if yongyou_row["md"] > 0:
                    yongyou_row["ccode_equal"] = ",".join(list(md_ccode_equal)[:4])
                else:
                    yongyou_row["ccode_equal"] = ",".join(list(mc_ccode_equal)[:4])
            new_row = pd.DataFrame(row_list)
            df_empty = pd.concat([df_empty, new_row], ignore_index=True)
    return df_empty, period_list


def build_zhuyuan_js_df(conn, shoukuan_df, total_df):
    """
    构建住院结算数据
    """
    df_empty = pd.DataFrame()
    df_shoukuan = shoukuan_df.replace({np.nan: None})
    df_total = total_df.replace({np.nan: None})
    # 自动去除所有列名两端的空格
    df_shoukuan.columns = df_shoukuan.columns.str.strip()
    df_total.columns = df_total.columns.str.strip()
    # 将日期列转为日期格式（确保排序逻辑正确）
    df_shoukuan['扎帐时间'] = pd.to_datetime(df_shoukuan['扎帐时间'])
    period_list = []

    date_val = pd.to_datetime(datetime.now().date().strftime("%Y-%m-%d %H:%M:%S"))
    # 先只找出结账数据
    jiezhang_total_df = df_total[df_total['扎帐类别'].str.contains('结帐', na=False, regex=False)]

    # 处理汇总表数据 根据扎帐单号分组
    for i, (zz_code, zz_group) in enumerate(jiezhang_total_df.groupby('扎账单号', sort=False)):
        if pd.notnull(zz_code):
            # 从汇总表查找该单号的所有数据
            zz_code_result_df = df_total.query(f'扎账单号 == {zz_code}')
            # 先只找出结账数据
            jiezhang_df = zz_code_result_df[zz_code_result_df['扎帐类别'].str.contains('结帐', na=False, regex=False)]
            period = date_val.month
            # 每个单号都去获取下凭证
            start_ino_id = get_next_ino_id(conn, period)
            row_list = []
            ino_id = start_ino_id + i
            period_list.append(str(ino_id))
            inid = 0
            # 病人返押金票据冲住院预收款 230502  找出病人返押金票据数据
            fanya_df = jiezhang_df[jiezhang_df['项目'].str.contains('病人返押金票据', na=False, regex=False)]
            # 结账退款数据
            tuikuan_df = jiezhang_df[jiezhang_df['项目'].str.contains('结帐退款', na=False, regex=False)]
            # 对方科目设置 应收与现金
            ccode_set = {'121101', '1001'}
            ccode_set1 = set()
            # 重置索引
            tuikuan_df = tuikuan_df.reset_index(drop=True)
            # 先处理结账退款数据
            for index, row in tuikuan_df.iterrows():
                inid = index + 1
                name = row['收款员']
                cdigest = f"结算住院费,扎账单号:{zz_code},{'' if pd.isna(name) else name}"
                # 科目
                ccode = get_zhu_yuan_ccode2(row)
                # 其他
                # 借方
                md = pd.to_numeric(row.get('金额', 0))
                # 贷方
                mc = 0.0
                ccode_set1.add(ccode)
                row_list.append(
                    transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, mc, None, ccode, cdigest))
            # 添加病人返押金票据冲住院预收款 230502 凭证 为负 贷方
            """
            病人返押金票据:	260129000018	结帐	刘春丽	2026-01-29 10:49:31	自助微信	37000
            病人返押金票据:	260129000018	结帐	刘春丽	2026-01-29 10:49:31	支付宝扫码付	50830.04
            病人返押金票据:	260129000018	结帐	刘春丽	2026-01-29 10:49:31	现金	35100
            病人返押金票据:	260129000018	结帐	刘春丽	2026-01-29 10:49:31	微信扫码付	145120.24
            """
            total_fanya = fanya_df['金额'].sum()
            if total_fanya > 0:
                inid = inid + 1
                name = fanya_df.iloc[0]['收款员']
                zz_code = fanya_df.iloc[0]['扎账单号']
                cdigest = f"结算住院费,扎账单号:{zz_code},{'' if pd.isna(name) else name}"
                # 科目
                ccode = '230502'
                md = 0.0
                # 贷方
                mc = -pd.to_numeric(total_fanya)
                row_list.append(
                    transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, mc, None, ccode, cdigest))
            """
            贷方 充 121101 应收  结账数据总和
            """
            total_jiezhang = jiezhang_df['金额'].sum()
            if total_jiezhang > 0:
                inid = inid + 1
                name = jiezhang_df.iloc[0]['收款员']
                zz_code = jiezhang_df.iloc[0]['扎账单号']
                cdigest = f"结算住院费,扎账单号:{zz_code},{'' if pd.isna(name) else name}"
                # 科目
                ccode = '121101'
                md = 0.0
                # 贷方
                mc = pd.to_numeric(total_jiezhang)
                row_list.append(
                    transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, mc, None, ccode, cdigest))

            for yongyou_row in row_list:
                if yongyou_row["md"] > 0.0 or yongyou_row["mc"] < 0.0:
                    yongyou_row["ccode_equal"] = ",".join(list(ccode_set)[:4])
                else:
                    yongyou_row["ccode_equal"] = ",".join(list(ccode_set1)[:4])
            new_row = pd.DataFrame(row_list)
            df_empty = pd.concat([df_empty, new_row], ignore_index=True)

    return df_empty, period_list


def build_zhuyuan_shouru(conn, shoukuan_df, total_df):
    """
    住院收入
    """
    df_empty = pd.DataFrame()
    row_list = []
    period_list = []
    df_shoukuan = shoukuan_df.replace({np.nan: None})
    # 自动去除所有列名两端的空格
    df_shoukuan.columns = df_shoukuan.columns.str.strip()
    # 将日期列转为日期格式（确保排序逻辑正确）
    df_shoukuan['日期'] = pd.to_datetime(df_shoukuan['日期'])
    # 贷方对方科目
    mc_ccode_equal = set()
    # 今天时期
    date_val = pd.to_datetime(datetime.now().date().strftime("%Y-%m-%d %H:%M:%S"))
    period = date_val.month
    # 只生成一张凭证
    # 每个单号都去获取下凭证
    if not df_shoukuan.empty:
        # 获取该扎账单号的时间
        ino_id = get_next_ino_id(conn, period)
        period_list.append(ino_id)
        inid = 0

        for (dept, project), group in df_shoukuan.groupby(["部门名称", "收入项目"], sort=False):
            inid += 1
            md = 0.0
            # 贷方
            mc_v = pd.to_numeric(group['折扣后'].sum())
            mc = 0.0 if pd.isna(mc_v) else float(mc_v)
            # 部门
            cdept_id = get_dept_code_mz(dept, 'his_zy')
            # 科目
            ccode = get_zhu_yuan_ccode3(project)
            ccode = str(ccode or "").strip()
            if not ccode:
                # 抛出内置的“值错误”异常
                raise ValueError("错误：科目编码(ccode)不能为空或纯空格！")
            # 贷方对方科目
            mc_ccode_equal.add(ccode)
            row_df = transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, mc, cdept_id, ccode, "住院收入")
            row_df["ccode_equal"] = "100201"
            row_list.append(row_df)
        # 最后加一个121101 应收
        inid += 1
        md_v = pd.to_numeric(df_shoukuan['折扣后'].sum())
        md = 0.0 if pd.isna(md_v) else float(md_v)
        # 贷方
        mc = 0.0
        # 科目
        ccode = "100201"
        row_df = transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, mc, None, ccode, "住院收入")
        row_df["ccode_equal"] = ",".join(list(mc_ccode_equal)[:4])
        row_list.append(row_df)
        new_row = pd.DataFrame(row_list)
        df_empty = pd.concat([df_empty, new_row], ignore_index=True)
    return df_empty, period_list


def build_menzhen_zizhuji(conn, shoukuan_df, total_df):
    """
    门诊自助机
    """
    df_empty = pd.DataFrame()
    row_list = []
    period_list = []
    df_shoukuan = shoukuan_df.replace({np.nan: None})
    df_total = total_df.replace({np.nan: None})
    # 自动去除所有列名两端的空格
    df_shoukuan.columns = df_shoukuan.columns.str.strip()
    df_total.columns = df_total.columns.str.strip()
    # 将日期列转为日期格式（确保排序逻辑正确）
    df_shoukuan['登记时间'] = pd.to_datetime(df_shoukuan['登记时间'])
    df_total['收款时间'] = pd.to_datetime(df_total['收款时间'])
    # 贷方对方科目
    mc_ccode_equal = set()
    # 今天时期
    date_val = pd.to_datetime(datetime.now().date().strftime("%Y-%m-%d %H:%M:%S"))
    period = date_val.month
    # 只生成一张凭证
    # 每个单号都去获取下凭证
    if not df_shoukuan.empty:
        # 获取该扎账单号的时间
        ino_id = get_next_ino_id(conn, period)
        period_list.append(ino_id)
        inid = 0
        for (dept, project), group in df_shoukuan.groupby(["开单科室", "项目"], sort=False):
            if not pd.isna(dept):
                inid += 1
                md = 0.0
                # 贷方
                mc_v = pd.to_numeric(group['金额'].sum())
                mc = 0.0 if pd.isna(mc_v) else float(mc_v)
                # 部门
                cdept_id = get_dept_code_mz(dept, 'his_mz')
                # 科目
                ccode = get_feiyong_menzhen_code(project)
                ccode = str(ccode or "").strip()
                if not ccode:
                    # 抛出内置的“值错误”异常
                    raise ValueError("错误：科目编码(ccode)不能为空或纯空格！")
                # 贷方对方科目
                mc_ccode_equal.add(ccode)
                row_list.append(
                    transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, mc, cdept_id, ccode, "自助门诊收入"))
        # 自助机收入进 100201
        shoufei_df = df_total[df_total['项目'].str.contains('收费情况', na=False, regex=False)]
        if not shoufei_df.empty:
            for type, group in shoufei_df.groupby("内容", sort=False):
                inid += 1
                md_v = pd.to_numeric(group['金额'].sum())
                md = 0.0 if pd.isna(md_v) else float(md_v)
                # 贷方
                mc = 0.0
                # 科目
                ccode = get_jiesuan_ccode(type)
                row_df = transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, mc, None, ccode,
                                             "自助门诊收入")
                row_df["ccode_equal"] = ",".join(list(mc_ccode_equal)[:4])
                row_list.append(row_df)
        # 预存进 借 100201 应收 贷 230502 预存住院
        yujiao_df = df_total[df_total['项目'].str.contains('住院预交', na=False, regex=False)]
        if not yujiao_df.empty:
            inid += 1
            dbill_date = pd.to_datetime(yujiao_df.iloc[0]['收款时间'])
            md_v = pd.to_numeric(yujiao_df['金额'].sum())
            md = 0.0 if pd.isna(md_v) else float(md_v)
            # 科目
            ccode = "100201"
            row_df = transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, 0.0, None, ccode, "预收医疗款")
            row_df["ccode_equal"] = "230502"
            row_list.append(row_df)
            # 贷 230502
            inid += 1
            mc_v = pd.to_numeric(yujiao_df['金额'].sum())
            mc = 0.0 if pd.isna(mc_v) else float(mc_v)
            # 科目
            ccode = "230502"
            row_df = transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', 0.0, mc, None, ccode, "预收医疗款")
            row_df["ccode_equal"] = "100201"
            row_list.append(row_df)
        new_row = pd.DataFrame(row_list)
        df_empty = pd.concat([df_empty, new_row], ignore_index=True)
    return df_empty, period_list

def build_menzhen_saoma(conn, shoukuan_df, total_df):
    """
    门诊扫码
    """
    df_empty = pd.DataFrame()
    row_list = []
    period_list = []
    df_shoukuan = shoukuan_df.replace({np.nan: None})
    df_total = total_df.replace({np.nan: None})
    # 自动去除所有列名两端的空格
    df_shoukuan.columns = df_shoukuan.columns.str.strip()
    df_total.columns = df_total.columns.str.strip()
    # 将日期列转为日期格式（确保排序逻辑正确）
    df_shoukuan['登记时间'] = pd.to_datetime(df_shoukuan['登记时间'])
    df_total['收款时间'] = pd.to_datetime(df_total['收款时间'])
    # 贷方对方科目
    mc_ccode_equal = set()
    # 今天时期
    date_val = pd.to_datetime(datetime.now().date().strftime("%Y-%m-%d %H:%M:%S"))
    period = date_val.month
    # 只生成一张凭证
    # 每个单号都去获取下凭证
    if not df_shoukuan.empty:
        # 获取该扎账单号的时间
        ino_id = get_next_ino_id(conn, period)
        period_list.append(ino_id)
        inid = 0
        for (dept, project), group in df_shoukuan.groupby(["开单科室", "项目"], sort=False):
            # 根据开单科室、项目分组
            if not pd.isna(dept):
                inid += 1
                md = 0.0
                # 贷方
                mc_v = pd.to_numeric(group['金额'].sum())
                mc = 0.0 if pd.isna(mc_v) else float(mc_v)
                # 部门
                cdept_id = get_dept_code_mz(dept, 'his_mz')
                # 科目
                ccode = get_feiyong_menzhen_code(project)
                ccode = str(ccode or "").strip()
                if not ccode:
                    # 抛出内置的“值错误”异常
                    raise ValueError("错误：科目编码(ccode)不能为空或纯空格！")
                # 贷方对方科目
                mc_ccode_equal.add(ccode)
                row_list.append(
                    transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, mc, cdept_id, ccode, "门诊扫码收入"))
        # 扫码收入分类
        shoufei_df = df_total[df_total['项目'].str.contains('收费情况', na=False, regex=False)]
        if not shoufei_df.empty:
            for type, group in shoufei_df.groupby("内容", sort=False):
                inid += 1
                md_v = pd.to_numeric(group['金额'].sum())
                md = 0.0 if pd.isna(md_v) else float(md_v)
                # 贷方
                mc = 0.0
                # 科目
                ccode = get_jiesuan_ccode(type)
                row_df = transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, mc, None, ccode, "门诊扫码收入")
                row_df["ccode_equal"] = ",".join(list(mc_ccode_equal)[:4])
                row_list.append(row_df)
        # 预存进 借 100201 应收 贷 230502 预存住院
        yujiao_df = df_total[df_total['项目'].str.contains('住院预交', na=False, regex=False)]
        if not yujiao_df.empty:
            inid += 1
            md_v = pd.to_numeric(yujiao_df['金额'].sum())
            md = 0.0 if pd.isna(md_v) else float(md_v)
            # 科目
            ccode = "100201"
            row_df = transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', md, 0.0, None, ccode, "预收医疗款")
            row_df["ccode_equal"] = "230502"
            row_list.append(row_df)
            # 贷 230502
            inid += 1
            mc_v = pd.to_numeric(yujiao_df['金额'].sum())
            mc = 0.0 if pd.isna(mc_v) else float(mc_v)
            # 科目
            ccode = "230502"
            row_df = transform_to_yonyou(period, ino_id, inid, date_val, '李红霞', 0.0, mc, None, ccode, "预收医疗款")
            row_df["ccode_equal"] = "100201"
            row_list.append(row_df)
        new_row = pd.DataFrame(row_list)
        df_empty = pd.concat([df_empty, new_row], ignore_index=True)
    return df_empty, period_list

def get_next_ino_id(conn, period):
    """
    获取下一个可用的凭证号
    :param engine: SQLAlchemy engine
    :param period: 会计期间 (int)
    :param csign: 凭证类别 (str)
    """
    sql = f"""
        SELECT MAX(ino_id) FROM [UFDATA_999_2012].[dbo].[GL_accvouch] WHERE [iperiod] = {period};
    """
    if is_build:
        sql = f"""
                SELECT MAX(ino_id) FROM [UFDATA_001_2026].[dbo].[GL_accvouch] WHERE [iperiod] = {period};
            """
    result = conn.execute(sql).fetchone()
    max_id = result[0] if result and result[0] is not None else 0
    # 如果结果为 None (新月份第一张单)，则返回 1，否则返回 最大值 + 1
    return max_id + 1


def transform_to_yonyou(period, ino_id, inid, dbill_date, user_name, md, mc, cdept_id, ccode, cdigest):
    """
    将HIS数据转换为用友GL_accvouch格式
    :param df: 原始DataFrame
    :param start_vouch_id: 起始凭证号
    :param period: 期间 (tinyint)
    :param user_name: 制单人 (varchar 20)
    :param csign: 凭证类别 (varchar 8)
    486 凭证门诊收入
    489#凭证门诊收入（含自助退费）
    496#凭证结算住院费
    540#凭证门诊扫码收入
    541 自助门诊
    544 凭证住院收入
    """
    # 建立副本，避免影响原始数据
    new_df = {}

    # --- 1. 必填基础字段 (NOT NULL) ---
    # 会计期间 0为期初往来明细帐,21为期初待核银行帐,20为银行帐科目调整前余额,1-12为凭证及明细	UA_Period.iId
    # 一般为月份 F52会计期间
    new_df['iperiod'] = int(period)
    # 凭证类别 凭证类别字		Dsign.csign F2类别
    new_df['csign'] = '记'
    new_df['isignseq'] = 1  # 凭证类别排序，通常记账为1  dsign.isignseq F53类别顺序号
    # 凭证序号 由系统分配凭证号,期初时可为null F3凭证号 取最大值+1 F82唯一标识
    new_df['ino_id'] = ino_id
    # inid 分录行号：从1开始递增 F59行号
    new_df['inid'] = inid

    # dbill_date 凭证日期：确保是datetime类型
    # 假设原df中有'date'列，如果没有则取当前日期 凭证日期 F1日期  yy-MM-dd
    new_df['dbill_date'] = dbill_date

    # --- 2. 核心财务字段 (NOT NULL / money) ---
    # 映射摘要 (从原df的'summary'取，最大60个字符)   F5摘要
    new_df['cdigest'] = cdigest
    # 映射科目编码 (从原df的'subject_code'取) code.ccode  F6科目编码
    new_df['ccode'] = ccode
    new_df['cbill'] = user_name  # 制单人 (varchar 20) F12制单人
    # 金额处理 (money类型)
    new_df['md'] = md  # 借方  F7借方
    new_df['mc'] = mc  # 贷方  F8贷方

    new_df['cdept_id'] = cdept_id  # 部门  Department.cDepCode 外键    todo 需要 F16部门编码
    # new_df['ccode_equal'] = df.get('ccode_equal', None)  # 对方科目编码 code.ccode todo 需要解决 F70对方科目
    new_df['ccus_id'] = None  # F50核算单位

    # 附件数 -1 0
    new_df['idoc'] = 1  # 附件数 (smallint, NOT NULL) F4附单据数
    new_df['ccheck'] = None  # 审核人 (varchar 20)  F55审核人
    new_df['cbook'] = None  # 记账人 (varchar 20)   F56记账人
    new_df['ibook'] = 0  # 记账标志 (tinyint, 默认0未记账) 记账标志	1_已记账 0_未记账（建索引用） F57是否记账
    new_df['ccashier'] = None  # 出纳签字人 F58出纳人
    new_df['iflag'] = None  # null_有效凭证,1_作废凭证,2_有错凭证(作废凭证可取消作废/进行凭证整理)
    # 外币相关字段 (根据DDL要求，通常补0)
    new_df['md_f'] = 0
    new_df['mc_f'] = 0
    new_df['nfrat'] = 0
    new_df['nd_s'] = 0
    new_df['nc_s'] = 0

    # --- 3. 辅助核算字段 (允许为 NULL，但业务上可能必填) ---
    # 假设原df中有对应核算项，没有则填充None 结算方式编码	SettleStyle.cSSCode
    new_df['csettle'] = None  # 结算方式编码 外键 F13结算方式
    new_df['cn_id'] = None  # 票据号 F14票号
    new_df['dt_date'] = None  # 票号发生日期 F15发生日期
    new_df['cperson_id'] = None  # 职员编码 Person.cPersonCode 外键
    new_df['ccus_id'] = None  # 客户 Customer.cCusCode 外键
    new_df['csup_id'] = None  # 供应商 Vendor.cVenCode 外键
    new_df['citem_id'] = None  # fitemss**.citemcode F21项目编码
    new_df['citem_class'] = None  # 项目大类编码 fitem.citem_class F68项目大类编码
    new_df['cname'] = None  # 业务员  Person.cPersonName F20业务员
    new_df['iflagbank'] = 0  # 银行账两清标志 Null_未达,<1-12> =自动两清期间 <13-24> -12=手工两清期间 F71银行两清标志
    new_df['iflagPerson'] = 0  # 往来账两清标志 Null_未达,<1-12> =自动两清期间 <13-24> -12=手工两清期间 F72往来两清标志
    new_df['coutaccset'] = None  # 外部凭证账套号  F75外部账套号
    new_df['ioutyear'] = 0  # 外部凭证会计年度  F76外部会计年度

    # --- 4. 外部系统关联字段 (用于追踪HIS来源) ---
    new_df['coutsysname'] = 'HIS'  # 外部凭证系统名称 F74外部系统名称
    new_df['bFlagOut'] = 1  # 是否输出标志 1其他子系统  手动录入

    new_df['coutsysver'] = None  # 外部凭证系统版本号 F79外部系统版本
    new_df['doutbilldate'] = None  # 外部凭证制单日期 F78外部制单日期
    new_df['ioutperiod'] = 0  # 外部凭证会计期间 F77外部会计期间
    new_df['coutsign'] = ''  # 外部凭证业务类型
    new_df['coutno_id'] = None  # 外部凭证业务号
    new_df['doutdate'] = None  # 外部凭证单据日期
    new_df['coutbillsign'] = None  # 外部凭证单据类型
    new_df['coutid'] = None  # 外部凭证单据号

    new_df['bvouchedit'] = False  # 凭证是否可修改 True_可修改,False_不可修改
    new_df['bvouchAddordele'] = False  # 凭证分录是否可增删 True_可增删,False_不可增删
    new_df['bvouchmoneyhold'] = False  # 凭证合计金额是否保值 True_必须保值,False_可不保值
    new_df['bvalueedit'] = False  # 分录数值是否可修改 True_可修改,False_不可修改，金额/数量/外币
    new_df['bcodeedit'] = False  # 分录科目是否可修改 True_可修改,False_不可修改
    new_df['ccodecontrol'] = False  # 分录受控科目可用状态 Null_均不可用,****_均可用,!_指定不可用,ID_指定可用
    new_df['bPCSedit'] = False  # 分录往来项是否可修改 True_可修改,False_不可修改，个人/客户/供应商
    new_df['bDeptedit'] = False  # 分录部门是否可修改
    new_df['bItemedit'] = False  # 分录项目是否可修改
    new_df['bCusSupInput'] = False  # 分录往来项是否必输
    # 自定义项1
    new_df['cDefine1'] = None
    new_df['cDefine2'] = None
    new_df['cDefine3'] = None
    new_df['cDefine4'] = None
    new_df['cDefine5'] = None
    new_df['cDefine6'] = None
    new_df['cDefine7'] = None
    new_df['cDefine8'] = None
    new_df['cDefine9'] = None
    new_df['cDefine10'] = None
    new_df['cDefine11'] = None
    new_df['cDefine12'] = None
    new_df['cDefine13'] = None
    new_df['cDefine14'] = None
    new_df['cDefine15'] = None
    new_df['cDefine16'] = None

    new_df['dReceive'] = None
    new_df['cWLDZFlag'] = None
    new_df['dWLDZTime'] = None
    new_df['iBG_OverFlag'] = None
    new_df['cBG_Auditor'] = None
    new_df['dBG_AuditTime'] = None
    new_df['cBG_AuditOpinion'] = None
    new_df['bWH_BgFlag'] = None
    new_df['cAssistant1_id'] = None
    new_df['cAssistant2_id'] = None
    new_df['cAssistant3_id'] = None
    new_df['cAssistant4_id'] = None
    new_df['cAssistant5_id'] = None
    new_df['cAssistant6_id'] = None
    new_df['cAssistant7_id'] = None
    new_df['coutid'] = None
    new_df['bvouchedit'] = False  # 允许修改

    # --- 5. 补全其他 DDL 中的默认逻辑值 ---
    # 删除 是否核销	银行帐核销标志
    new_df['bdelete'] = False  # 默认先不作废凭证
    new_df['bvouchAddordele'] = False  # 凭证分录是否可增删	True_可增删,False_不可增删

    new_df['assidentify'] = ''

    return new_df


class ImportWorker(QThread):
    finished_signal = pyqtSignal(bool, str, dict)

    def __init__(self, config, shoukuan_df, total_df):
        super().__init__()
        self.config = config
        self.shoukuan_df = shoukuan_df
        self.total_df = total_df

    def run(self):
        try:
            # 这里是真正的耗时操作，在子线程运行，不影响界面
            import_data_to_yy(self.config, self.shoukuan_df, self.total_df, self.finished_signal)
        except Exception as e:
            self.finished_signal.emit(False, str(e), -1)


# --- 在主界面调用 ---
def sqlserver_start_import(parent, config, record, callback=None):
    """
    开始导入用友
    :param parent: 父窗口
    :param config: 数据库配置
    :param record: 记录
    :param callback: 回调函数，接受两个参数 (success, message)
    """
    progress = QProgressDialog("正在写入用友系统...", None, 0, 0, parent)
    progress.setWindowTitle("请等待")
    progress.setWindowModality(2)  # Qt.WindowModal
    progress.setCancelButton(None)
    progress.show()

    # 创建并启动线程
    worker = ImportWorker(config, record)

    # 将worker绑定到parent上，防止被垃圾回收
    parent._import_worker = worker

    def on_import_finished(success, message, int):
        progress.close()
        if callback:
            callback(success, message, int)

        # 清理 worker 引用
        if hasattr(parent, '_import_worker'):
            del parent._import_worker

    worker.finished_signal.connect(on_import_finished)
    worker.start()

# --- 在主界面调用 ---
def sqlserver_start_import(parent, config, shoukuan_df, total_df, callback=None):
    """
    开始导入用友
    :param parent: 父窗口
    :param config: 数据库配置
    :param shoukuan_df: 收款数据
    :param total_df: 总数数据
    :param callback: 回调函数，接受两个参数 (success, message)
    """
    progress = QProgressDialog("正在写入用友系统...", None, 0, 0, parent)
    progress.setWindowTitle("请等待")
    progress.setWindowModality(2)  # Qt.WindowModal
    progress.setCancelButton(None)
    progress.show()

    # 创建并启动线程
    worker = ImportWorker(config, shoukuan_df, total_df)

    # 将worker绑定到parent上，防止被垃圾回收
    parent._import_worker = worker

    def on_import_finished(success, message, record):
        progress.close()
        if callback:
            callback(success, message, record)

        # 清理 worker 引用
        if hasattr(parent, '_import_worker'):
            del parent._import_worker

    worker.finished_signal.connect(on_import_finished)
    worker.start()


if __name__ == '__main__':
    sqlite_helper = SQLiteHelper()
    record = sqlite_helper.get_record_by_id(1)


    def on_complete(success, message, record):
        # 更新本地数据库状态
        print(record)
        if success:
            logger.info("导入成功，刷新列表")
            # self.sqlite_helper.import_yy_result(record["id"], success, message, num)
        else:
            logger.info("导入失败，刷新列表")
            # self.sqlite_helper.import_yy_result(record["id"], success, "", -1)


    # finished_signal = pyqtSignal(bool, str, dict)
    # finished_signal.connect(on_complete)

    record['data_type'] = '0'
    record['export_file_path'] = r"C:\Users\Administrator\Desktop\线上his\门诊2026-01-29 00_00_00数据导出.xlsx"
    config_manager = ConfigManager()
    import_data_to_yy(config_manager.get_db_config('sqlserver'), record, finished_signal)
