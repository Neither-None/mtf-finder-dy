# -*- coding: utf-8 -*-
"""抖音药娘爬虫入口（纯接口版：cookie + 本地签名，不需要浏览器）"""
import argparse
from crawl_api import crawl

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="抖音关注列表滚雪球（纯接口）")
    ap.add_argument("--cookie", default="cookies/douyin.json")
    ap.add_argument("--self-pages", type=int, default=100, help="自己关注列表最多翻几页（每页20）")
    ap.add_argument("--user-pages", type=int, default=3, help="每个账号翻几页")
    ap.add_argument("--max-expand", type=int, default=200, help="最多扩展多少个账号")
    a = ap.parse_args()
    crawl(a.cookie, self_pages=a.self_pages, user_pages=a.user_pages, max_expand=a.max_expand)
