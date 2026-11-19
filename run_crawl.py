# -*- coding: utf-8 -*-
"""抖音药娘爬虫入口"""
import argparse
from crawler import crawl

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="抖音关注列表滚雪球")
    ap.add_argument("--cookie", default="cookies/douyin.json")
    ap.add_argument("--scrolls", type=int, default=3, help="每个账号滚动几屏")
    ap.add_argument("--max-expand", type=int, default=200, help="最多扩展多少个账号")
    ap.add_argument("--browser-path", default=None, help="自定义 Chromium 路径")
    ap.add_argument("--no-headless", action="store_true", help="显示浏览器窗口（首跑过验证码用）")
    ap.add_argument("--profile", default=None, help="浏览器配置目录（默认 data/browser_profile）")
    a = ap.parse_args()
    crawl(a.cookie, scrolls=a.scrolls, max_expand=a.max_expand,
          headless=not a.no_headless, browser_path=a.browser_path,
          profile_dir=a.profile)
