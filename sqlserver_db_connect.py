# sqlserver 操作类
import pyodbc
from log_util import logger
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (QMessageBox, QProgressDialog)


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

def import_data_to_yy(sqlserver_config, record, finished_signal):
    """ 导入数据导用友 """
    conn_str = (
        "DRIVER={SQL Server};"  # 使用系统自带驱动
        f"SERVER={sqlserver_config.get.get('host')},{sqlserver_config.get.get('port')};"
        f"DATABASE={sqlserver_config.get.get('db_name')};"
        f"UID={sqlserver_config.get.get('user')};"
        f"PWD={sqlserver_config.get.get('password')};"
        "Connect Timeout=5;"
    )
    # 针对 SQL 2008 的特殊处理
    try:
        # 1. 建立连接
        conn = pyodbc.connect(conn_str)
        logger.info(f"sqlserver 连接成功, {conn_str}")
        # 1. 读取 Excel 文件
        full_path = record['export_file_path']
        df = pd.read_excel(full_path)

        conn.close()
        finished_signal.emit(True, "成功")
    except Exception as e:
        logger.info(f"sqlserver 导出失败: {e}, {conn_str}")
        finished_signal.emit(False, f"失败{e}")


def transform_to_yonyou(df, start_vouch_id, period, user_name):
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
    new_df = pd.DataFrame()

    # --- 1. 必填基础字段 (NOT NULL) ---
    # 会计期间 0为期初往来明细帐,21为期初待核银行帐,20为银行帐科目调整前余额,1-12为凭证及明细	UA_Period.iId
    # 一般为月份 F52会计期间
    new_df['iperiod'] = int(period)
    # 凭证类别 凭证类别字		Dsign.csign F2类别
    new_df['csign'] = '记'
    new_df['isignseq'] = 1  # 凭证类别排序，通常记账为1  dsign.isignseq F53类别顺序号
    # 凭证序号 由系统分配凭证号,期初时可为null F3凭证号 取最大值+1 F82唯一标识
    new_df['ino_id'] = int(start_vouch_id)
    # inid 分录行号：从1开始递增 F59行号
    new_df['inid'] = range(1, len(df) + 1)

    # dbill_date 凭证日期：确保是datetime类型
    # 假设原df中有'date'列，如果没有则取当前日期 凭证日期 F1日期  yy-MM-dd
    new_df['dbill_date'] = pd.to_datetime(df['date'])

    # --- 2. 核心财务字段 (NOT NULL / money) ---
    # 映射摘要 (从原df的'summary'取，最大60个字符)   F5摘要
    new_df['cdigest'] = df['summary'].astype(str).str.slice(0, 60)
    # 映射科目编码 (从原df的'subject_code'取) code.ccode  F6科目编码
    new_df['ccode'] = None
    new_df['cbill'] = user_name  # 制单人 (varchar 20) F12制单人
    # 金额处理 (money类型)
    new_df['md'] = pd.to_numeric(df.get('debit', 0)).fillna(0.0)  # 借方  F7借方
    new_df['mc'] = pd.to_numeric(df.get('credit', 0)).fillna(0.0)  # 贷方  F8贷方

    new_df['cdept_id'] = df.get('dept_id', None)  # 部门  Department.cDepCode 外键    todo 需要 F16部门编码
    new_df['ccode_equal'] = df.get('ccode_equal', None)  # 对方科目编码 code.ccode todo 需要解决 F70对方科目

    # 附件数 -1 0
    new_df['idoc'] = 1  # 附件数 (smallint, NOT NULL) F4附单据数
    new_df['ccheck'] = None  # 审核人 (varchar 20)  F55审核人
    new_df['cbook'] = None  # 记账人 (varchar 20)   F56记账人
    new_df['ibook'] = 1  # 记账标志 (tinyint, 默认0未记账) 记账标志	1_已记账 0_未记账（建索引用） F57是否记账
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
    new_df['coutsign'] = None  # 外部凭证业务类型
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
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, config, record):
        super().__init__()
        self.config = config
        self.record = record

    def run(self):
        try:
            # 这里是真正的耗时操作，在子线程运行，不影响界面
            import_data_to_yy(self.config, self.record, self.finished_signal)
        except Exception as e:
            self.finished_signal.emit(False, str(e))

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

    def on_import_finished(success, message):
        progress.close()
        if callback:
            callback(success, message)
        
        # 清理 worker 引用
        if hasattr(parent, '_import_worker'):
            del parent._import_worker

    worker.finished_signal.connect(on_import_finished)
    worker.start()

if __name__ == '__main__':
    connect_to_sqlserver_test('127.0.0.1', '1433', 'master', 'sa', '123456')
