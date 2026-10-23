"""One connection configuration, resolved beside the application, never cwd."""
import configparser
import ipaddress
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from log_util import register_secret


def application_dir():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class TPlusApiConfig:
    url: str = "http://192.168.1.15:7777"
    account: str = "999"
    user: str = "范立志"
    password: str = field(default="", repr=False)
    app_key: str = ""
    app_secret: str = field(default="", repr=False)
    enabled: bool = False
    org_id: str = ""
    pem_path: str = field(default_factory=lambda: str(application_dir() / "cjet_pri.pem"))

    def __post_init__(self):
        if self.password:
            register_secret(self.password)
        if self.app_secret:
            register_secret(self.app_secret)


@dataclass(frozen=True)
class LoginConfig:
    url: str = ""
    user_name: str = ""
    password: str = field(default="", repr=False)
    acc_num: str = ""
    api: TPlusApiConfig = field(default_factory=TPlusApiConfig)

    def __post_init__(self):
        register_secret(self.password)


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str = field(repr=False)
    driver: str = "SQL Server Native Client 10.0"
    api: TPlusApiConfig = field(default_factory=TPlusApiConfig)
    login: LoginConfig = field(default_factory=LoginConfig)

    def __post_init__(self):
        register_secret(self.password)
        if any(char in self.host for char in "。．，、：；"):
            raise ValueError("服务器地址含中文或全角标点，请使用英文句点，例如127.0.0.1")
        if any(char.isspace() for char in self.host):
            raise ValueError("服务器地址不能包含空白字符")
        if re.fullmatch(r"[0-9.]+", self.host):
            try:
                ipaddress.IPv4Address(self.host)
            except ipaddress.AddressValueError:
                raise ValueError("服务器地址不是有效的IPv4地址，例如127.0.0.1") from None

    @classmethod
    def load(cls, path):
        parser = configparser.ConfigParser(interpolation=None)
        loaded = None
        for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
            try:
                loaded = parser.read(str(path), encoding=encoding)
                if loaded:
                    break
            except UnicodeDecodeError:
                continue
            except configparser.Error as exc:
                line = getattr(exc, "lineno", None)
                location = f"（第{line}行）" if line else ""
                # Parser messages can contain the original password line. Do not
                # expose them in UI/logs before secrets have even been parsed.
                raise ValueError("配置文件语法错误" + location + "：请检查节名、重复键或重复节 [" + type(exc).__name__ + "]") from None
        if not loaded:
            if not Path(path).exists():
                raise ValueError("找不到配置文件：" + str(path))
            raise ValueError("配置文件无法按常见编码（UTF-8/GBK）解码，请使用 UTF-8 编码保存：" + str(path))
        if not parser.has_section("sqlserver"):
            raise ValueError("配置文件缺少 [sqlserver]")
        section = parser["sqlserver"]
        if any(key not in section for key in ("ip", "port", "database", "user", "password")):
            raise ValueError("配置必须包含 ip、port、database、user、password")
        try:
            port = int(section["port"])
        except ValueError:
            raise ValueError("数据库端口必须为整数") from None
        if not 1 <= port <= 65535:
            raise ValueError("数据库端口必须在1至65535之间")
        if any(not section[key].strip() for key in ("ip", "database", "user")):
            raise ValueError("服务器、数据库名称及用户不能为空")
        api_config = TPlusApiConfig()
        if parser.has_section("tplus_api"):
            api_sec = parser["tplus_api"]
            pem_path = Path(api_sec.get("pem_path", "cjet_pri.pem").strip().strip('"\'') or "cjet_pri.pem")
            if not pem_path.is_absolute():
                pem_path = Path(path).resolve().parent / pem_path
            api_config = TPlusApiConfig(
                url=api_sec.get("url", "http://192.168.1.15:7777").strip(),
                account=api_sec.get("account", "999").strip(),
                user=api_sec.get("user", "范立志").strip(),
                password=api_sec.get("password", "").strip(),
                app_key=api_sec.get("app_key", api_sec.get("appkey", "")).strip(),
                app_secret=api_sec.get("app_secret", api_sec.get("appsecret", "")).strip(),
                enabled=api_sec.getboolean("enabled", True),
                org_id=api_sec.get("org_id", api_sec.get("orgid", "")).strip().strip('"\''),
                pem_path=str(pem_path),
            )
        login = LoginConfig()
        if parser.has_section("login"):
            sec = parser["login"]
            login = LoginConfig(url=sec.get("url", "").strip(),
                                user_name=sec.get("userName", "").strip(),
                                password=sec.get("password", "").strip(),
                                acc_num=sec.get("accNum", "").strip(),
                                api=api_config)
        return cls(section["ip"].strip(), port, section["database"].strip(),
                   section["user"].strip(), section["password"],
                   section.get("driver", "SQL Server Native Client 10.0").strip(),
                   api_config, login)

    @staticmethod
    def quote(value):
        return "{" + str(value).replace("}", "}}") + "}"

    def connection_string(self):
        q = self.quote
        return (f"DRIVER={q(self.driver)};SERVER={q(self.host + ',' + str(self.port))};"
                f"DATABASE={q(self.database)};UID={q(self.user)};PWD={q(self.password)};"
                "Connect Timeout=6;")

    def display(self):
        return f"服务器：{self.host}:{self.port}    账套：{self.database}    用户：{self.user}    密码：******"

    def safe_error(self, exc):
        # Never display arbitrary driver exception text: it can contain a URL or PWD.
        code = str(exc.args[0]) if getattr(exc, "args", None) else ""
        code = code if len(code) == 5 and code.isalnum() else ""
        return f"数据库操作失败（{type(exc).__name__}{' / ' + code if code else ''}），请检查连接、权限或表结构。"
