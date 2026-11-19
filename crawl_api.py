# -*- coding: utf-8 -*-
"""抖音药娘爬虫（纯接口版）：cookie + 本地 a_bogus 签名，不需要浏览器

流程：
1. 用自己的 cookie 调 /user/profile/self/ 拿到自己的 sec_uid
2. 翻页抓自己的关注列表 → 入库
3. 从库里挑「像药娘 + 关注数多」的账号，抓他们的关注列表 → 新账号入库
4. 重复第 3 步（滚雪球），状态存 data/state.json 可断点续跑
"""
import json
import os
import random
import time

from analyze import has_cjk, is_yaoniang
from config import DATA
from douyin_api import DouyinAPI, to_user
from store import Store

STATE = os.path.join(DATA, "state.json")


def _load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except Exception:
            pass
    return {"visited": [], "self_done": False}


def _save_state(st):
    os.makedirs(DATA, exist_ok=True)
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False)


def _save_batch(store, raw_list, log, label=""):
    added = 0
    for raw in raw_list:
        u = to_user(raw)
        if u["id"] and store.add(u):
            added += 1
    if label:
        log("  %s +%d（累计 %d）" % (label, added, store.count()))
    return added


def crawl(cookie_path, self_pages=100, user_pages=3, max_expand=200, log=print):
    os.makedirs(DATA, exist_ok=True)
    store = Store(os.path.join(DATA, "douyin_users.jsonl"))
    st = _load_state()
    visited = set(st.get("visited", []))
    log("已有 %d 条记录，已扩展 %d 个账号" % (store.count(), len(visited)))

    api = DouyinAPI(cookie_path, log=log)
    me = api.self_info()
    if not me.get("sec_uid"):
        log("❌ 拿不到自己的账号信息，cookie 可能失效")
        return store.count()
    my_sec = me["sec_uid"]
    log("登录账号：%s（关注 %s）" % (me.get("nickname"), me.get("following_count")))

    # 第一步：自己的关注列表
    if not st.get("self_done"):
        log("抓取自己的关注列表…")
        raws = api.followings_all(my_sec, pages=self_pages)
        _save_batch(store, raws, log, "自己的关注")
        st["self_done"] = True
        _save_state(st)

    # 第二步：滚雪球
    expanded = 0
    while expanded < max_expand:
        users = store.load()
        queue = [u for u in users.values()
                 if u["id"] not in visited
                 and (u.get("following") or 0) >= 20
                 and has_cjk(u.get("name") or "")]
        queue.sort(key=lambda x: (-(1 if is_yaoniang(x) else 0), -(x.get("following") or 0)))
        if not queue:
            log("队列空了，抓取结束")
            break
        t = queue[0]
        visited.add(t["id"])
        st["visited"] = sorted(visited)
        _save_state(st)

        log("扩展 @%s（关注 %d）…" % ((t.get("name") or "")[:14], t.get("following") or 0))
        raws = api.followings_all(t["id"], pages=user_pages)
        _save_batch(store, raws, log, "  ")
        expanded += 1
        time.sleep(random.uniform(1.5, 3.0))

    log("完成：共 %d 条记录" % store.count())
    return store.count()
