"""Independent online token window; transport is disabled pending authorization."""
import json
import urllib.error
import urllib.parse
import urllib.request

from PyQt5.QtCore import QThread, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (QApplication, QCheckBox, QDialog, QFormLayout,
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout)


class OnlineTokenError(ValueError):
    pass


class OnlineTokenClient:
    ENDPOINT = "https://openapi.chanjet.com/auth/getToken"

    def __init__(self, requester=None):
        self.requester = requester

    def exchange(self, app_key, app_secret, redirect_uri, code):
        values = [str(value).strip() for value in (app_key, app_secret, redirect_uri, code)]
        app_key, app_secret, redirect_uri, code = values
        if not all(values):
            raise OnlineTokenError("请填写应用 appKey、appSecret、OAuth 回调地址和授权码 code。")
        callback = urllib.parse.urlsplit(redirect_uri)
        if callback.scheme not in ("http", "https") or not callback.netloc or callback.fragment:
            raise OnlineTokenError("OAuth 回调地址须为完整的 HTTP/HTTPS 地址，且与应用配置一致。")
        if self.requester is None:
            raise OnlineTokenError("在线请求尚未启用：需要授权将应用 appSecret 和授权码 code 发送至畅捷通开放平台。")
        query = urllib.parse.urlencode({"grantType": "authorization_code", "appKey": app_key,
                                       "redirectUri": redirect_uri, "code": code})
        request = urllib.request.Request(self.ENDPOINT + "?" + query, headers={
            "appKey": app_key, "appSecret": app_secret, "Accept": "application/json",
            "Content-Type": "application/json"}, method="GET")
        try:
            body = self.requester(request, timeout=15)
        except urllib.error.HTTPError as exc:
            raise OnlineTokenError(f"在线认证 HTTP {exc.code}；请检查应用配置或稍后重试。") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise OnlineTokenError("在线认证网络连接失败或超时，请检查互联网连接。") from None
        try:
            response = json.loads(body)
        except (ValueError, TypeError):
            raise OnlineTokenError("在线认证返回的不是有效 JSON。") from None
        if not isinstance(response, dict):
            raise OnlineTokenError("在线认证响应结构错误。")
        result = response.get("result")
        if str(response.get("code")) != "200":
            message = str(response.get("message") or "未返回成功状态")
            secrets = [app_secret, code]
            if isinstance(result, dict):
                secrets.extend(result.get(name) for name in ("access_token", "refresh_token", "sid"))
            for secret in secrets:
                if isinstance(secret, str) and secret:
                    message = message.replace(secret, "******")
            status = str(response.get("code", "未知"))
            status = status if status.isdigit() and len(status) <= 8 else "未知"
            raise OnlineTokenError(f"在线认证失败（{status}）：{message[:300]}")
        if (not isinstance(result, dict) or not isinstance(result.get("access_token"), str)
                or not result["access_token"].strip()):
            raise OnlineTokenError("认证响应缺少有效的 result.access_token。")
        return {name: result[name] for name in ("access_token", "refresh_token", "expires_in",
                "refresh_expires_in", "org_id", "user_id", "app_name")
                if name in result and isinstance(result[name], (str, int, float))}


class OnlineTokenWorker(QThread):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, client, values, parent):
        super().__init__(parent)
        self.client, self.values = client, values

    def run(self):
        try:
            self.completed.emit(self.client.exchange(*self.values))
        except OnlineTokenError as exc:
            self.failed.emit(str(exc))
        except Exception:
            self.failed.emit("在线认证异常，请检查网络和应用配置；未保存或应用 Token。")


class OnlineTokenDialog(QDialog):
    def __init__(self, parent=None, client=None):
        super().__init__(parent)
        self.client = client or OnlineTokenClient()
        self.worker = None
        self.setWindowTitle("在线获取 Token（独立操作）")
        self.resize(700, 520)
        layout = QVBoxLayout(self)
        guide = QLabel("使用开放平台应用的 appKey 和 appSecret。先在应用的授权管理中完成用户授权，"
                       "再从 OAuth 回调地址取得 code。回调地址必须与应用配置一致。\n"
                       "本窗口仅获取并展示 Token，不修改现有配置、不连接数据库、不执行导入。\n"
                       "在线请求尚未启用，当前仅可检查界面和输入。")
        guide.setWordWrap(True)
        layout.addWidget(guide)
        portal = QPushButton("打开开放平台（在应用中完成授权）")
        portal.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://open.chanjet.com/console")))
        layout.addWidget(portal)
        form = QFormLayout()
        self.app_key, self.app_secret, self.redirect_uri, self.code = (QLineEdit() for _ in range(4))
        self.app_secret.setEchoMode(QLineEdit.Password)
        self.code.setEchoMode(QLineEdit.Password)
        self.redirect_uri.setPlaceholderText("应用配置中的完整 OAuth 回调地址")
        self.code.setPlaceholderText("回调参数 code 的值；不要粘贴整个网址")
        for title, edit in (("应用 appKey", self.app_key), ("应用 appSecret", self.app_secret),
                            ("OAuth 回调地址", self.redirect_uri), ("授权码 code", self.code)):
            form.addRow(title, edit)
            edit.textChanged.connect(self.clear_result)
        layout.addLayout(form)
        self.fetch_button = QPushButton("获取 Token")
        self.fetch_button.clicked.connect(self.fetch)
        layout.addWidget(self.fetch_button)
        self.status = QLabel("接口：GET " + OnlineTokenClient.ENDPOINT)
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        results = QFormLayout()
        self.access_token, self.refresh_token = QLineEdit(), QLineEdit()
        for title, edit in (("access_token / openToken", self.access_token), ("refresh_token", self.refresh_token)):
            edit.setReadOnly(True)
            edit.setEchoMode(QLineEdit.Password)
            results.addRow(title, edit)
        layout.addLayout(results)
        show = QCheckBox("显示 Token")
        show.toggled.connect(self.show_tokens)
        layout.addWidget(show)
        actions = QHBoxLayout()
        self.copy_button = QPushButton("复制 access_token")
        self.copy_refresh_button = QPushButton("复制 refresh_token")
        self.copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.access_token.text()))
        self.copy_refresh_button.clicked.connect(lambda: QApplication.clipboard().setText(self.refresh_token.text()))
        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
        for button in (self.copy_button, self.copy_refresh_button, close):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.clear_result()

    def clear_result(self):
        if not hasattr(self, "access_token"):
            return
        self.access_token.clear()
        self.refresh_token.clear()
        self.copy_button.setEnabled(False)
        self.copy_refresh_button.setEnabled(False)
        self.status.setText("接口：GET " + OnlineTokenClient.ENDPOINT)

    def show_tokens(self, visible):
        for edit in (self.access_token, self.refresh_token):
            edit.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)

    def fetch(self):
        if self.worker is not None:
            return
        self.clear_result()
        values = tuple(edit.text() for edit in (self.app_key, self.app_secret, self.redirect_uri, self.code))
        self.set_busy(True)
        self.status.setText("正在获取 Token…")
        self.worker = OnlineTokenWorker(self.client, values, self)
        self.worker.completed.connect(self.received)
        self.worker.failed.connect(self.status.setText)
        self.worker.finished.connect(self.finished_request)
        self.worker.start()

    def received(self, result):
        self.access_token.setText(result["access_token"])
        self.refresh_token.setText(str(result.get("refresh_token", "")))
        self.copy_button.setEnabled(True)
        self.copy_refresh_button.setEnabled(bool(self.refresh_token.text()))
        details = [f"{name}={result[name]}" for name in ("expires_in", "refresh_expires_in", "org_id", "user_id")
                   if name in result]
        self.status.setText("获取成功，仅保存在当前窗口。有效期单位：秒。\n" + "；".join(details))

    def set_busy(self, busy):
        for widget in (self.app_key, self.app_secret, self.redirect_uri, self.code, self.fetch_button):
            widget.setEnabled(not busy)

    def finished_request(self):
        self.worker.deleteLater()
        self.worker = None
        self.set_busy(False)

    def reject(self):
        if self.worker is not None:
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
        else:
            super().closeEvent(event)
