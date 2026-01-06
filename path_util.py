# 资源路径工具类
import sys
import os

def resource_path(relative_path):
    """ 获取资源绝对路径，兼容开发环境和打包后的环境 """
    # if hasattr(sys, '_MEIPASS'):
    #     # 打包后的临时目录
    #     return os.path.join(sys._MEIPASS, relative_path)
    # 开发环境的当前目录
    return os.path.join(os.path.abspath("."), relative_path)


def open_with_default_app(full_path):
    try:
        # 仅限 Windows，相当于双击文件
        os.startfile(full_path)
    except Exception as e:
        print(f"打开文件失败: {e}")

