import oracledb
import os

# 1. 指定你解压的 Instant Client 路径
# Windows 示例: r"C:\oracle\instantclient_12_1"
# Linux 示例: "/opt/oracle/instantclient_12_1"

# 配置连接参数
user = "system"
password = "oracle"
# 如果是本机运行填 localhost，远程服务器填实际 IP
host = "118.190.202.74"
port = 1521
sid = "EE"

if __name__ == '__main__':
    try:
        # 如果是直接运行 .py
        base_path = os.path.dirname(os.path.abspath(__file__))
        # 2. 拼接内置客户端的路径
        client_path = os.path.join(base_path, "lib", "instantclient_11_2")
        # 2. 初始化 Thick 模式 (连接 11g 必须执行这一步)
        if os.name == 'nt':  # Windows 平台
            oracledb.init_oracle_client(lib_dir=client_path)
        else:  # Linux 平台
            oracledb.init_oracle_client()

        user = "system"
        password = "oracle"
        host = "118.190.202.74"
        port = 1521
        sid = "EE"

        # 使用显式的 SID 连接描述符
        dsn_tns = f"""(DESCRIPTION=
            (ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))
            (CONNECT_DATA=(SID={sid}))
        )"""

        connection = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn_tns
        )
        print("Successfully connected to Oracle 11g in Thick Mode!", dsn_tns)

    except oracledb.Error as e:
        print(f"Connection failed: {e}")



