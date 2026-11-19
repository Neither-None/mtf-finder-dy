# -*- coding: utf-8 -*-
"""抖音药娘爬虫控制面板  http://127.0.0.1:8790"""
import csv
import http.server
import json
import os
import signal
import subprocess
import sys
import threading
import time

from analyze import analyze, is_yaoniang, parse_profile, render_text
from config import DATA, MENTAL, ROOT
from store import Store

PORT = 8790
STORE_PATH = os.path.join(DATA, "douyin_users.jsonl")
LOG_PATH = os.path.join(DATA, "crawl.log")
REPORT_TXT = os.path.join(DATA, "report.txt")
REPORT_CSV = os.path.join(DATA, "report.csv")
COOKIE_PATH = os.path.join(ROOT, "cookies", "douyin.json")

_lock = threading.Lock()
_proc = {"p": None}
_report = {"last": "-", "busy": False}


def store():
    return Store(STORE_PATH)


def is_running():
    p = _proc["p"]
    return bool(p and p.poll() is None)


def start():
    with _lock:
        if is_running():
            return "已经在运行"
        if not os.path.exists(COOKIE_PATH):
            return "缺少 cookies/douyin.json，请先导出 cookie（见 README）"
        os.makedirs(DATA, exist_ok=True)
        log = open(LOG_PATH, "a", encoding="utf-8")
        log.write("\n=== 启动 %s ===\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        log.flush()
        p = subprocess.Popen([sys.executable, "run_crawl.py"],
                             cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        _proc["p"] = p
        return "已启动（pid %d）" % p.pid


def stop():
    with _lock:
        p = _proc["p"]
        if not p or p.poll() is not None:
            return "没有在运行"
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception:
            try:
                p.terminate()
            except Exception:
                pass
        return "已停止"


def make_report():
    if _report["busy"]:
        return "正在生成"
    _report["busy"] = True

    def work():
        try:
            users = store().load()
            s = analyze(users)
            text = render_text(s, users, title="抖音关注分类结果")
            os.makedirs(DATA, exist_ok=True)
            open(REPORT_TXT, "w", encoding="utf-8").write(text)

            rows = []
            for u in users.values():
                if not is_yaoniang(u):
                    continue
                bio = u.get("bio") or ""
                info = parse_profile(bio)
                low = bio.lower()
                mental = [lab for lab, kws in MENTAL if any(k in low for k in kws)]
                rows.append({
                    "unique_id": u.get("screen_name", ""),
                    "nickname": u.get("name", ""),
                    "followers": u.get("followers", 0),
                    "age": info.get("年龄", ""),
                    "height_cm": info.get("身高", ""),
                    "weight_kg": info.get("体重", ""),
                    "mental": ";".join(mental),
                    "bio": bio.replace("\n", " "),
                })
            if rows:
                with open(REPORT_CSV, "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                    w.writeheader()
                    w.writerows(rows)
            _report["last"] = time.strftime("%H:%M:%S")
        except Exception as e:
            _report["last"] = "失败: " + str(e)[:40]
        finally:
            _report["busy"] = False

    threading.Thread(target=work, daemon=True).start()
    return "开始生成报告"


def auto_report(interval=300):
    while True:
        time.sleep(interval)
        if not _report["busy"]:
            make_report()


def stats():
    users = store().load()
    s = analyze(users)
    s["running"] = is_running()
    s["last_report"] = _report["last"]
    tail = []
    try:
        with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
            tail = [l.rstrip() for l in f.readlines()[-10:]]
    except Exception:
        pass
    s["log"] = tail
    s["has_cookie"] = os.path.exists(COOKIE_PATH)
    return s


HTML = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>抖音药娘爬虫面板</title>
<style>
:root{--bg:#0b0f16;--card:#141b26;--line:#233044;--fg:#e8eef7;--mut:#8fa0b8;--blue:#5BCEFA;--pink:#F5A9B8;--ok:#35d07f;--bad:#ff6b6b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,"Noto Sans SC",sans-serif;padding:14px}
h1{font-size:17px;margin:0 0 12px}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;flex:1;min-width:110px}
.k{font-size:12px;color:var(--mut)}.v{font-size:25px;font-weight:600;margin-top:4px}
.v.blue{color:var(--blue)}
.btn{flex:1;padding:12px;border-radius:12px;border:1px solid var(--line);background:#1b2534;color:var(--fg);font-size:14px;font-weight:600}
.btn.start{border-color:#2f7d55;background:#12351f;color:#7fe3ab}
.btn.stop{border-color:#7d2f2f;background:#351212;color:#ff9c9c}
.dot{display:inline-block;width:9px;height:9px;border-radius:5px;margin-right:6px}
.bars{display:flex;align-items:flex-end;gap:3px;height:80px;margin-top:8px}
.bar{flex:1;background:linear-gradient(180deg,var(--blue),#2b6f92);border-radius:3px 3px 0 0;min-height:2px}
.barlbl{font-size:9px;color:var(--mut);text-align:center;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:13px}td{padding:3px 0;border-bottom:1px solid #1b2534;color:var(--mut)}
td:last-child{text-align:right;color:var(--fg)}
pre{background:#0e1420;border:1px solid var(--line);border-radius:10px;padding:10px;font-size:11px;line-height:1.5;overflow:auto;max-height:160px;color:#9fb2c9;white-space:pre-wrap}
.warn{background:#2a1b1b;border-color:#7d2f2f;color:#ffb3b3;font-size:13px}
</style></head><body>
<h1>抖音药娘爬虫面板</h1>
<div id="warn" class="card warn" style="display:none;margin-bottom:10px"></div>
<div class="row">
  <div class="card"><div class="k">状态</div><div class="v" id="st" style="font-size:18px">-</div></div>
  <div class="card"><div class="k">总账号</div><div class="v" id="total">-</div></div>
  <div class="card"><div class="k">药娘</div><div class="v blue" id="yn">-</div></div>
</div>
<div class="row">
  <button class="btn start" onclick="ctl('start')">开始抓取</button>
  <button class="btn stop" onclick="ctl('stop')">停止</button>
  <button class="btn" onclick="ctl('report')">生成报告</button>
</div>
<div class="row">
  <div class="card"><div class="k">年龄中位</div><div class="v" id="amed">-</div></div>
  <div class="card"><div class="k">体重中位</div><div class="v" id="wmed">-</div></div>
  <div class="card"><div class="k">身高中位</div><div class="v" id="hmed">-</div></div>
</div>
<div class="card" style="margin-bottom:10px"><div class="k">年龄分布</div><div class="bars" id="bars"></div><div id="barlbls" style="display:flex;gap:3px"></div></div>
<div class="row">
  <div class="card"><div class="k">数据样本</div><div id="body" style="font-size:13px;line-height:1.8;margin-top:6px"></div></div>
  <div class="card"><div class="k">精神疾病自述</div><div id="mental" style="font-size:13px;line-height:1.8;margin-top:6px"></div></div>
</div>
<div class="card" style="margin-bottom:10px"><div class="k">关键词命中</div><table id="kw"></table></div>
<div class="card"><div class="k">最近日志 <span id="lastrep" style="float:right"></span></div><pre id="log"></pre></div>
<script>
async function ctl(a){const r=await fetch('/api/'+a,{method:'POST'});alert(await r.text());load();}
const set=(id,v)=>document.getElementById(id).textContent=v;
async function load(){
  try{
    const d=await (await fetch('/api/stats')).json();
    document.getElementById('st').innerHTML='<span class="dot" style="background:'+(d.running?'var(--ok)':'var(--bad)')+'"></span>'+(d.running?'运行中':'已停止');
    set('total',d.total);set('yn',d.yaoniang);
    set('amed',d.age_med+' 岁');set('wmed',d.w_med+' kg');set('hmed',d.h_med+' cm');
    set('lastrep','报告：'+(d.last_report||'-'));
    const w=document.getElementById('warn');
    if(!d.has_cookie){w.style.display='block';w.textContent='还没有 cookies/douyin.json —— 请按 README 导出 cookie 后再开始抓取';}
    else if(!d.total){w.style.display='block';w.textContent='还没有数据，点「开始抓取」先从你自己的关注列表开始滚雪球';}
    else {w.style.display='none';}
    const dist=d.age_dist||{},ks=Object.keys(dist),mx=Math.max(1,...ks.map(k=>dist[k]));
    document.getElementById('bars').innerHTML=ks.map(k=>'<div class="bar" style="height:'+Math.max(2,dist[k]/mx*76)+'px" title="'+k+'岁 '+dist[k]+'人"></div>').join('');
    document.getElementById('barlbls').innerHTML=ks.map(k=>'<div class="barlbl" style="flex:1">'+k+'</div>').join('');
    document.getElementById('body').innerHTML='年龄 '+d.age_n+' 样本 · '+d.age_min+'-'+d.age_max+' 岁 · 中位 '+d.age_med+'<br>体重 '+d.w_n+' 样本 · 中位 '+d.w_med+'kg<br>身高 '+d.h_n+' 样本 · 中位 '+d.h_med+'cm';
    document.getElementById('mental').innerHTML=Object.entries(d.mental||{}).map(([k,v])=>k+' <b style="float:right;color:var(--fg)">'+v+'</b>').join('<br>');
    document.getElementById('kw').innerHTML=Object.entries(d.keywords||{}).slice(0,14).map(([k,v])=>'<tr><td>'+k+'</td><td>'+v+'</td></tr>').join('');
    document.getElementById('log').textContent=(d.log||[]).join('\\n');
  }catch(e){set('st','连接失败');}
}
load();setInterval(load,4000);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/stats"):
            self._send(200, json.dumps(stats(), ensure_ascii=False), "application/json; charset=utf-8")
        elif self.path == "/" or self.path.startswith("/index"):
            self._send(200, HTML)
        else:
            self._send(404, "not found")

    def do_POST(self):
        if self.path.startswith("/api/start"):
            self._send(200, start(), "text/plain; charset=utf-8")
        elif self.path.startswith("/api/stop"):
            self._send(200, stop(), "text/plain; charset=utf-8")
        elif self.path.startswith("/api/report"):
            self._send(200, make_report(), "text/plain; charset=utf-8")
        else:
            self._send(404, "not found")

    def log_message(self, *a):
        pass


def serve(port=PORT):
    auto_report_started = True
    make_report()
    threading.Thread(target=auto_report, daemon=True).start()
    print("panel: http://127.0.0.1:%d" % port, flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
