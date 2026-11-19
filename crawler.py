# -*- coding: utf-8 -*-
"""抖音关注列表抓取：cookie + 真实浏览器 + 关注关系滚雪球

流程：
1. 用 cookie 打开自己的关注列表 → 抓分页接口 → 得到第一批账号
2. 从这批账号里挑出「关注数多 + 像药娘」的，逐个打开他们的关注列表
3. 重复第 2 步，像滚雪球一样扩大

为什么用浏览器：抖音接口需要 a_bogus 签名，只有页面自己会算，
我们只负责监听页面发出的请求、读取响应，不碰签名。
"""
import json
import os
import random
import re
import time

from playwright.sync_api import sync_playwright

from config import DATA, DOUYIN_FOLLOW_API
from analyze import has_cjk, is_yaoniang
from store import Store

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")


def parse_user(u):
    if not isinstance(u, dict):
        return None
    sec = u.get("sec_uid")
    if not sec:
        return None
    return {
        "id": sec,
        "screen_name": u.get("unique_id") or u.get("short_id") or "",
        "name": u.get("nickname") or "",
        "bio": u.get("signature") or "",
        "followers": u.get("follower_count") or 0,
        "following": u.get("following_count") or 0,
        "tweets": u.get("aweme_count") or 0,
        "platform": "douyin",
    }


def extract_users(payload):
    out = []
    for item in (payload.get("user_list") or payload.get("followings") or []):
        u = item.get("user") or item
        pu = parse_user(u)
        if pu:
            out.append(pu)
    return out


class DouyinCrawler:
    def __init__(self, cookie_path, headless=True, browser_path=None, log=print):
        if not os.path.exists(cookie_path):
            raise SystemExit(
                "找不到 cookie 文件：%s\n"
                "请在电脑浏览器登录 douyin.com → F12 → Application → Cookies，\n"
                "导出成 JSON 存到该路径（见 README 的「准备 cookie」一节）。" % cookie_path
            )
        ck = json.load(open(cookie_path, encoding="utf-8"))
        if not ck.get("sessionid"):
            raise SystemExit(
                "cookie 文件缺少 sessionid。\n"
                "请在电脑浏览器登录 douyin.com → F12 → Application → Cookies，\n"
                "把包括 sessionid 在内的所有 cookie 导出成 JSON（见 README）。"
            )
        self.log = log
        self.captured = []
        self.p = sync_playwright().start()
        kw = dict(headless=headless, args=["--no-sandbox", "--disable-dev-shm-usage"])
        if browser_path:
            kw["executable_path"] = browser_path
        self.b = self.p.chromium.launch(**kw)
        self.ctx = self.b.new_context(
            user_agent=UA,
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
        )
        self.ctx.add_cookies([
            {"name": k, "value": str(v), "domain": ".douyin.com", "path": "/", "secure": True}
            for k, v in ck.items()
        ])
        self.page = self.ctx.new_page()
        self.page.set_default_timeout(45000)
        self.page.on("response", self._on_response)

    def _on_response(self, resp):
        if DOUYIN_FOLLOW_API not in resp.url:
            return
        try:
            self.captured.append(resp.json())
        except Exception:
            pass

    # ---------- 页面操作 ----------

    def goto(self, url, wait=4500):
        try:
            self.page.goto(url, timeout=90000, wait_until="domcontentloaded")
        except Exception as e:
            self.log("  打开失败：%s" % str(e)[:60])
            return False
        self.page.wait_for_timeout(wait)
        return True

    def click_follow_tab(self):
        """部分账号需要点一下「关注」才会加载列表"""
        try:
            ok = self.page.evaluate("""() => {
                const nodes = [...document.querySelectorAll('div,span,a,li,p')];
                for (const el of nodes) {
                    const t = (el.textContent || '').trim();
                    if (!t) continue;
                    if (/^关注\\s*[·\\s]*\\d+/.test(t) || t === '关注') {
                        const r = el.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) { el.click(); return true; }
                    }
                }
                return false;
            }""")
            if ok:
                self.page.wait_for_timeout(3000)
            return ok
        except Exception:
            return False

    def harvest(self, scrolls=3, pause=(1400, 2400)):
        """把当前页面已捕获的数据取出并继续滚动加载"""
        got = []
        for payload in self.captured:
            got.extend(extract_users(payload))
        self.captured.clear()
        for _ in range(scrolls):
            self.page.mouse.wheel(0, 2400)
            self.page.wait_for_timeout(random.randint(*pause))
            for payload in self.captured:
                got.extend(extract_users(payload))
            self.captured.clear()
        return got

    # ---------- 抓取 ----------

    def fetch_following(self, sec_uid=None, scrolls=3):
        """sec_uid 为 None 时抓自己的关注列表"""
        self.captured.clear()
        if sec_uid:
            url = "https://www.douyin.com/user/%s?showTab=following" % sec_uid
        else:
            url = "https://www.douyin.com/user/self?showTab=following"
        if not self.goto(url):
            return []
        if not self.captured:
            self.click_follow_tab()
        users = self.harvest(scrolls=scrolls)
        # 去重
        seen, out = set(), []
        for u in users:
            if u["id"] not in seen:
                seen.add(u["id"])
                out.append(u)
        return out

    def close(self):
        try:
            self.b.close()
        finally:
            self.p.stop()


def crawl(cookie_path, scrolls=3, max_expand=200, headless=True, browser_path=None,
          log=print, state_path=None):
    os.makedirs(DATA, exist_ok=True)
    store = Store(os.path.join(DATA, "douyin_users.jsonl"))
    state_path = state_path or os.path.join(DATA, "state.json")
    state = {"visited": [], "done": False}
    if os.path.exists(state_path):
        try:
            state = json.load(open(state_path, encoding="utf-8"))
        except Exception:
            pass
    visited = set(state.get("visited", []))
    log("已有 %d 条记录，已扩展 %d 个账号" % (store.count(), len(visited)))

    c = DouyinCrawler(cookie_path, headless=headless, browser_path=browser_path, log=log)
    try:
        # 第一步：自己的关注列表
        if not state.get("self_done"):
            log("打开自己的关注列表…")
            users = c.fetch_following(None, scrolls=max(6, scrolls))
            for u in users:
                store.add(u)
            log("自己的关注列表：抓到 %d 个账号（累计 %d）" % (len(users), store.count()))
            if not users:
                log("⚠️ 没抓到任何账号：可能是 cookie 失效、未登录，或页面结构变了。")
                log("   请用 --no-headless 打开窗口看一眼页面状态。")
                return 0
            state["self_done"] = True
            json.dump(state, open(state_path, "w", encoding="utf-8"), ensure_ascii=False)

        # 第二步：滚雪球
        expanded = 0
        while expanded < max_expand:
            users = store.load()
            queue = [
                u for u in users.values()
                if u["id"] not in visited
                and (u.get("following") or 0) >= 20
                and has_cjk(u.get("name") or "")
            ]
            queue.sort(key=lambda x: (-(is_yaoniang(x)), -(x.get("following") or 0)))
            if not queue:
                log("队列已空，没有可扩展的账号了")
                break
            target = queue[0]
            visited.add(target["id"])
            state["visited"] = sorted(visited)
            json.dump(state, open(state_path, "w", encoding="utf-8"), ensure_ascii=False)

            log("扩展 @%s（关注 %d）…" % ((target.get("name") or "")[:14], target.get("following") or 0))
            got = c.fetch_following(target["id"], scrolls=scrolls)
            added = 0
            for u in got:
                if store.add(u):
                    added += 1
            expanded += 1
            log("  +%d 人，累计 %d 条（已扩展 %d）" % (added, store.count(), len(visited)))
            time.sleep(random.uniform(2.5, 4.5))
    finally:
        c.close()

    log("完成：共 %d 条记录" % store.count())
    return store.count()
