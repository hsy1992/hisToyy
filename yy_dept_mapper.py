import os
import sys
import pandas as pd
from log_util import logger
"""
用友部门code映射
"""
df_dept = pd.DataFrame()
def load_dept():
    # if getattr(sys, 'frozen', False):
    #     # 如果是打包成了 .exe
    #     base_path = sys._MEIPASS
    # else:
    #     # 如果是直接运行 .py
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
    dept = os.path.join(base_path, "bumen.xlsx")
    global df_dept
    df_dept = pd.read_excel(dept, dtype=str)


def get_dept_code_mz(dept_name, type):
    """
    门诊使用
    """
    if df_dept.empty:
        load_dept()
    if df_dept.empty:
        logger.error("错误：部门表加载失败！")
        raise ValueError("错误：部门表加载失败！")
    df_dept[type] = df_dept[type].str.strip()
    dept_name = dept_name.strip()
    filtered_df = df_dept[df_dept[type].str.contains(dept_name, na=False, case=False, regex=False)]
    if filtered_df.empty:
        logger.error(f"未找到该部门:{dept_name}", df_dept[type].str)
        return None
    else:
        return filtered_df['cDepCode'].iloc[0]
