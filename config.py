import configparser
import os

""" 配置管理 """
class ConfigManager:
    def __init__(self, file_path='config.ini'):
        self.file_path = file_path
        self.config = configparser.ConfigParser()
        self._load()

    def _load(self):
        """内部方法：加载文件，如果不存在则创建"""
        if os.path.exists(self.file_path):
            self.config.read(self.file_path, encoding='utf-8')
        else:
            # 如果文件不存在，初始化空的结构
            with open(self.file_path, 'w', encoding='utf-8') as f:
                self.config.write(f)

    def get_db_config(self, section):
        """
        读取指定数据库的配置
        :param section: 'sqlserver' 或 'oracle'
        :return: 字典格式的配置
        """
        if self.config.has_section(section):
            return dict(self.config.items(section))
        return None

    def update_config(self, section, **kwargs):
        """
        写入/更新配置
        :param section: 配置段名称
        :param kwargs: 键值对，例如 host='127.0.0.1', user='sa'
        """
        if not self.config.has_section(section):
            self.config.add_section(section)

        for key, value in kwargs.items():
            self.config.set(section, key, str(value))

        # 写入物理文件
        with open(self.file_path, 'w', encoding='utf-8') as f:
            self.config.write(f)
        print(f"[{section}] 配置更新成功！")

