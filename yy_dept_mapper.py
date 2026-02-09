import os

import pandas as pd

from log_util import logger
from path_util import resource_path

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
    dept = os.path.join(resource_path("config"), "bumen.xlsx")
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

def get_shoukuan():
    """
    获取收款员
    """
    base_path = os.path.join(base_path, "eee.txt")
    with open(base_path, 'r', encoding='utf-8') as f:
        # 使用列表推导式去掉每行末尾的换行符 \n
        my_list = [line.strip() for line in f.readlines()]
    if filtered_df.empty:
        logger.error(f"未找到该部门:{dept_name}", df_dept[type].str)
        return None
    else:
        return filtered_df['cDepCode'].iloc[0]

# if __name__ == '__main__':
#     base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
#     base_path = os.path.join(base_path, "eee.txt")
#     with open(base_path, 'r', encoding='utf-8') as f:
#         # 使用列表推导式去掉每行末尾的换行符 \n
#         my_list = [line.strip() for line in f.readlines()]
#     print(my_list)
#     load_dept()
#     illegal_depts = df_dept[~df_dept['cDepCode'].isin(my_list)]['cDepCode'].unique()
#
#     print(f"以下部门编码在系统中不存在，导致了冲突: {illegal_depts}")

