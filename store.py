# -*- coding: utf-8 -*-
"""JSONL 存储：追加写、去重加载"""
import json
import os


class Store:
    def __init__(self, path):
        self.path = path
        self._seen = set()
        self._cache = None
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def load(self):
        """返回 {id: user}"""
        if self._cache is not None:
            return self._cache
        users = {}
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        u = json.loads(line)
                    except Exception:
                        continue
                    uid = u.get("id")
                    if uid:
                        users[uid] = u
        self._cache = users
        self._seen = set(users.keys())
        return users

    def has(self, uid):
        if self._cache is None:
            self.load()
        return uid in self._seen

    def add(self, user):
        if self._cache is None:
            self.load()
        uid = user.get("id")
        if not uid or uid in self._seen:
            return False
        self._seen.add(uid)
        self._cache[uid] = user
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(user, ensure_ascii=False) + "\n")
        return True

    def count(self):
        if self._cache is None:
            self.load()
        return len(self._cache)
