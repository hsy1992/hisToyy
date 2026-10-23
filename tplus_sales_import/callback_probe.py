"""Standalone callback connectivity probe (Python 3.8+, standard library only).

Run: python callback_probe.py --port 18080
Map 127.0.0.1:18080 in Kuaijiexi, then register the public HTTPS URL plus
/chanjet/messages as the application's message receiving address.
This probe acknowledges delivery only: it does not decrypt/verify appTicket,
save message bodies, obtain tokens, or access the import program/database.
"""
import argparse
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import threading
from urllib.parse import urlsplit


PAGE = """<!doctype html>
<html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>畅捷通回调连通测试</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f6f9;color:#172333;
font:15px/1.7 'Microsoft YaHei',sans-serif}main{max-width:920px;margin:36px auto;padding:0 20px}
h1{font-size:27px;margin:0 0 8px}h2{font-size:18px;margin:0 0 12px}
.card{background:white;border:1px solid #dce3ec;border-radius:12px;padding:22px;margin-top:18px}
.muted{color:#5e6b7b}.note{background:#fff6de;border:1px solid #f0d58c;border-radius:8px;padding:12px}
input{width:100%;padding:10px;border:1px solid #bdc8d7;border-radius:6px;font:14px monospace}
button{background:#135dc1;color:white;border:0;border-radius:6px;padding:10px 18px;
font:inherit;cursor:pointer;margin:10px 8px 0 0}button:disabled{opacity:.5;cursor:wait}
table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #e5e9ef;padding:9px}
.counts{display:flex;gap:28px;flex-wrap:wrap}.counts strong{font-size:26px;color:#135dc1}
code{background:#edf1f7;padding:2px 5px;border-radius:4px}#feedback{min-height:26px}
</style><main>
<h1>畅捷通回调连通测试</h1>
<div class="muted">本地服务 + 快解析映射 + 消息接收状态，集中在这一页。</div>
<section class="card"><h2>1. 先配置快解析映射</h2>
<p>在快解析中添加网站映射：与本服务同机时，内网 IP 填 <code>127.0.0.1</code>，
应用程序端口填启动终端显示的端口（默认 <code>18080</code>），选择能提供公网 HTTPS 的映射类型。</p>
<p>映射完成后，用<strong>快解析生成的公网 HTTPS 地址</strong>打开本页；下方将自动给出公网回调地址。</p>
<input id="callback" readonly aria-label="当前访问地址对应的回调地址">
<button id="copy">复制回调地址</button>
<p id="address-note" class="muted"></p>
<p>把公网回调地址填写到畅捷通应用的<strong>消息接收地址</strong>中。</p>
</section>
<section class="card"><h2>2. 测试浏览器到本地的 POST 链路</h2>
<p>从公网地址点击按钮，可以检查 POST 是否经过快解析到达本服务。此操作发送模拟测试消息。</p>
<button id="send">发送连通测试</button><button id="refresh">刷新状态</button>
<div id="feedback" role="status"></div></section>
<section class="card"><h2>3. 查看接收记录</h2>
<div class="counts"><div>浏览器测试次数<br><strong id="probes">0</strong></div>
<div>回调消息次数<br><strong id="callbacks">0</strong></div></div>
<p class="note">回调只确认传输接收：尚未解密、尚未验证来源，也未确认获得有效 appTicket。
回调次数可包含人工模拟请求。不会保存或回显消息正文、密钥或 Token。</p>
<table><thead><tr><th>接收时间</th><th>类型</th><th>正文大小</th></tr></thead>
<tbody id="events"></tbody></table>
<p class="muted">记录保存在内存，最多显示最近 10 条；服务重启后清零。自动每 3 秒刷新。</p>
</section></main><script>
const callback=document.getElementById('callback');
callback.value=location.origin+'/chanjet/messages';
document.getElementById('address-note').textContent=
  location.protocol==='https:' && !['localhost','127.0.0.1'].includes(location.hostname)
  ? '请确认此域名是你的快解析公网地址；平台是否接受该地址，以控制台验证为准。'
  : '当前不是公网 HTTPS 访问，请勿直接把上面的地址登记到畅捷通。';
const feedback=document.getElementById('feedback');
document.getElementById('copy').onclick=async()=>{
  try{await navigator.clipboard.writeText(callback.value);feedback.textContent='已复制回调地址。'}
  catch(e){callback.select();feedback.textContent='请按 Ctrl+C 复制选中的地址。'}
};
async function refresh(){
  const response=await fetch('/api/status',{cache:'no-store'});
  if(!response.ok)throw new Error('状态读取失败');
  const state=await response.json();
  document.getElementById('probes').textContent=state.probe_count;
  document.getElementById('callbacks').textContent=state.callback_count;
  const body=document.getElementById('events');body.replaceChildren();
  for(const event of state.events){
    const row=document.createElement('tr');
    for(const value of [event.time,event.kind==='callback'?'回调（尚未解密）':'浏览器模拟测试',event.bytes+' B']){
      const cell=document.createElement('td');cell.textContent=value;row.appendChild(cell);
    }body.appendChild(row);
  }
}
document.getElementById('send').onclick=async()=>{
  const button=document.getElementById('send');button.disabled=true;
  try{
    const response=await fetch('/probe',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({test:'connectivity'})});
    if(!response.ok)throw new Error('POST 返回 HTTP '+response.status);
    feedback.textContent='POST 连通成功；这不代表已收到真实 appTicket。';await refresh();
  }catch(e){feedback.textContent='测试失败：'+e.message}finally{button.disabled=false}
};
document.getElementById('refresh').onclick=()=>refresh().catch(e=>feedback.textContent=e.message);
refresh().catch(e=>feedback.textContent=e.message);
setInterval(()=>refresh().catch(()=>feedback.textContent='状态刷新失败，请检查本地服务或快解析连接。'),3000);
</script></html>"""


class ProbeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address):
        self.lock = threading.Lock()
        self.probe_count = self.callback_count = 0
        self.events = deque(maxlen=10)
        super().__init__(address, ProbeHandler)

    def record(self, kind, size):
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        with self.lock:
            if kind == "callback":
                self.callback_count += 1
            else:
                self.probe_count += 1
            self.events.appendleft({"time": now, "kind": kind, "bytes": size})
        print("{} received={} bytes={} (delivery only)".format(now, kind, size), flush=True)

    def status(self):
        with self.lock:
            return {"probe_count": self.probe_count, "callback_count": self.callback_count,
                    "ticket_verified": False, "events": list(self.events)}


class ProbeHandler(BaseHTTPRequestHandler):
    server_version = "CallbackProbe/1.0"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, format, *args):
        # Never log raw request lines, query parameters, headers or bodies.
        pass

    def reply(self, status, payload, html=False):
        body = (payload if html else json.dumps(payload, ensure_ascii=False)).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                         "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            self.reply(200, PAGE, html=True)
        elif path == "/health":
            self.reply(200, {"status": "ok", "mode": "connectivity_only"})
        elif path == "/api/status":
            self.reply(200, self.server.status())
        else:
            self.reply(404, {"error": "not_found"})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in ("/probe", "/chanjet/messages"):
            self.reply(404, {"error": "not_found"})
            return
        length = self.headers.get("Content-Length", "")
        if self.headers.get("Transfer-Encoding") or not length.isdigit():
            self.reply(400, {"error": "content_length_required"})
            return
        length = int(length)
        if length > 65536:
            self.reply(413, {"error": "body_too_large"})
            return
        if self.headers.get_content_type() != "application/json":
            self.reply(415, {"error": "application_json_required"})
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError()
            payload = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(payload, dict):
                raise ValueError()
        except (ValueError, UnicodeError, socket.timeout):
            self.reply(400, {"error": "invalid_json"})
            return
        if path == "/chanjet/messages":
            encrypted = payload.get("encryptMsg")
            if not isinstance(encrypted, str) or not encrypted.strip():
                self.reply(400, {"error": "encryptMsg_required"})
                return
            self.server.record("callback", length)
            self.reply(200, {"result": "success"})
        else:
            self.server.record("probe", length)
            self.reply(200, {"status": "received", "ticket_verified": False})


def main():
    parser = argparse.ArgumentParser(description="Standalone callback connectivity probe; no credentials required.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=18080, help="Local HTTP port (default: 18080)")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        server = ProbeServer((args.host, args.port))
    except OSError as exc:
        parser.exit(1, "Cannot start listener ({}); check address/port or use --port.\n".format(type(exc).__name__))
    print("Test page: http://{}:{}/".format(args.host, args.port), flush=True)
    print("Kuaijiexi target: {}:{} (HTTP)".format(args.host, args.port), flush=True)
    print("Public callback: <public HTTPS origin>/chanjet/messages", flush=True)
    print("Connectivity only; no decryption, tokens or database access. Stop with Ctrl+C.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
