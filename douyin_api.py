# -*- coding: utf-8 -*-
"""抖音 Web 接口客户端：cookie + 本地 a_bogus 签名（不依赖浏览器）

签名由 abogus/sign.js（Node）完成，本模块负责拼参数、请求、解析、翻页。
"""
import json
import os
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

from config import ROOT

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")

BASE_PARAMS = {
    "device_platform": "webapp", "aid": "6383", "channel": "channel_pc_web",
    "pc_client_type": "1", "version_code": "170400", "version_name": "17.4.0",
    "cookie_enabled": "true", "screen_width": "1440", "screen_height": "900",
    "browser_language": "zh-CN", "browser_platform": "Win32",
    "browser_name": "Chrome", "browser_version": "138.0.0.0",
    "browser_online": "true", "engine_name": "Blink", "engine_version": "138.0.0.0",
    "os_name": "Windows", "os_version": "10", "cpu_core_num": "8",
    "device_memory": "8", "platform": "PC", "downlink": "10",
    "effective_type": "4g", "round_trip_time": "0",
}

SIGNER = os.path.join(ROOT, "abogus", "sign.js")


class DouyinAPI:
    def __init__(self, cookie_path, log=print):
        ck = json.load(open(cookie_path, encoding="utf-8"))
        if not ck.get("sessionid"):
            raise SystemExit(
                "cookie 文件缺少 sessionid。\n"
                "请在电脑浏览器登录 douyin.com → F12 → Application → Cookies，\n"
                "把包括 sessionid 在内的所有 cookie 导出成 JSON（见 README）。"
            )
        self.cookie = "; ".join("%s=%s" % (k, v) for k, v in ck.items())
        self.log = log
        if not os.path.exists(SIGNER):
            raise SystemExit("缺少签名脚本 abogus/sign.js（见 README 的安装说明）")

    # ---------- 底层 ----------

    def _sign(self, url):
        payload = {"cookie": self.cookie, "url": url, "ua": UA}
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        try:
            json.dump(payload, f, ensure_ascii=False)
            f.close()
            r = subprocess.run(["node", SIGNER, f.name], capture_output=True, text=True, timeout=120)
        finally:
            try:
                os.unlink(f.name)
            except Exception:
                pass
        lines = [l for l in (r.stdout or "").split("\n") if l.startswith("http")]
        if not lines:
            raise RuntimeError("签名失败: " + (r.stderr or "")[-160:])
        return lines[-1]

    def get(self, path, params=None, retries=3):
        q = dict(BASE_PARAMS)
        if params:
            q.update(params)
        url = "https://www.douyin.com" + path + "?" + urllib.parse.urlencode(q)
        for i in range(retries):
            signed = self._sign(url)
            req = urllib.request.Request(signed, headers={
                "User-Agent": UA, "Cookie": self.cookie,
                "Referer": "https://www.douyin.com/", "Accept": "application/json",
            })
            try:
                raw = urllib.request.urlopen(req, timeout=40).read().decode("utf-8")
                return json.loads(raw)
            except Exception as e:
                self.log("  请求失败(%d/%d): %s" % (i + 1, retries, str(e)[:60]))
                time.sleep(3 + i * 3)
        return {}

    # ---------- 业务 ----------

    def self_info(self):
        j = self.get("/aweme/v1/web/user/profile/self/")
        u = (j or {}).get("user") or {}
        return u

    def followings(self, sec_user_id, offset=0, count=20, max_time=None):
        params = {
            "sec_user_id": sec_user_id, "count": str(count), "offset": str(offset),
            "source_type": "1", "address_book_access": "1", "gps_access": "1", "is_top": "0",
        }
        if max_time:
            params["max_time"] = str(max_time)
        j = self.get("/aweme/v1/web/user/following/list/", params)
        return j

    def followings_all(self, sec_user_id, pages=20, delay=(2, 4)):
        """翻页抓取某个账号的全部关注"""
        import random
        out, max_time, offset = [], None, 0
        for p in range(pages):
            j = self.followings(sec_user_id, offset=offset, max_time=max_time)
            batch = j.get("followings") or j.get("user_list") or []
            if not batch:
                break
            out.extend(batch)
            if not j.get("has_more"):
                break
            new_max = j.get("max_time")
            if new_max and new_max != max_time:
                max_time = new_max
            else:
                offset += len(batch)
            time.sleep(random.uniform(*delay))
        return out


def to_user(raw):
    """接口返回的一坨字段 → 统一结构"""
    return {
        "id": raw.get("sec_uid") or "",
        "screen_name": raw.get("unique_id") or raw.get("short_id") or "",
        "name": raw.get("nickname") or "",
        "bio": raw.get("signature") or "",
        "followers": raw.get("follower_count") or 0,
        "following": raw.get("following_count") or 0,
        "tweets": raw.get("aweme_count") or 0,
        "platform": "douyin",
    }
