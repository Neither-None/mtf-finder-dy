# -*- coding: utf-8 -*-
"""分类、简介解析、统计报告"""
import re
import statistics
from collections import Counter

from config import CATEGORIES, KEYWORDS, MENTAL, NAME_MARKERS, YN_KEYWORDS

CURRENT_YEAR = 2026
CJK = re.compile(r"[\u4e00-\u9fff]")

CN_AGE = {"十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15, "十六": 16,
          "十七": 17, "十八": 18, "十九": 19, "二十": 20}
GRADES = [("初一", 13), ("初二", 14), ("初三", 15), ("高一", 16), ("高二", 17),
          ("高三", 18), ("大一", 19), ("大二", 20), ("大三", 21), ("大四", 22)]


def has_cjk(text):
    return bool(CJK.search(text or ""))


def kw_hit(low, kw):
    """中文直接包含；英文按词边界（避免 sync 里的 yn）"""
    if re.fullmatch(r"[a-z]+", kw):
        return re.search(r"(?<![a-z])" + kw + r"(?![a-z])", low) is not None
    return kw in low


def is_yaoniang(user):
    bio = user.get("bio") or user.get("signature") or ""
    if not has_cjk((user.get("name") or "") + bio):
        return False
    low = bio.lower()
    return any(kw_hit(low, k) for k in YN_KEYWORDS)


def has_name_marker(user):
    name = user.get("name") or ""
    return any(m in name for m in NAME_MARKERS)


def parse_profile(bio):
    """从简介提取 年龄/出生年/身高/体重"""
    info = {}
    if not bio:
        return info
    text = bio

    # 出生日期 2008.07.09 / 2008年7月9日
    m = re.search(r"(?<!\d)((?:19|20)\d{2})[./\-年]\s*(\d{1,2})(?:[./\-月]\s*(\d{1,2}))?", text)
    if m:
        year = int(m.group(1))
        if 1985 <= year <= 2016:
            info["出生年"] = year
            info["年龄"] = CURRENT_YEAR - year

    # 04年 / 08后 / 09的
    if "出生年" not in info:
        clean = re.sub(r"(?:从业|工作|入行|做了|住了|学了|玩了)\s*\d{1,2}\s*年", " " * 12, text)
        m = re.search(r"(?<!\d)(0[0-9]|1[0-9])\s*(?:年|后|的|出生|底|初)", clean)
        if m:
            year = 2000 + int(m.group(1))
            if 1985 <= year <= 2016:
                info["出生年"] = year
                info["年龄"] = CURRENT_YEAR - year

    # 活了15年
    if "年龄" not in info:
        m = re.search(r"活了\s*(\d{1,2})\s*年", text)
        if m and 5 <= int(m.group(1)) <= 45:
            info["年龄"] = int(m.group(1))

    # 16岁 / 十六岁 / 年龄:16 / 今年16
    if "年龄" not in info:
        m = re.search(r"(\d{1,2})\s*(?:周岁|岁|歲)", text)
        if m and 12 <= int(m.group(1)) <= 45:
            info["年龄"] = int(m.group(1))
    if "年龄" not in info:
        m = re.search(r"([一二三四五六七八九十]{2,3})\s*(?:周岁|岁|歲)", text)
        if m and CN_AGE.get(m.group(1)):
            info["年龄"] = CN_AGE[m.group(1)]
    if "年龄" not in info:
        m = re.search(r"(?:年龄|今年)\s*[:：\s]*(\d{1,2})", text)
        if m and 12 <= int(m.group(1)) <= 45:
            info["年龄"] = int(m.group(1))

    # 年级
    if "年龄" not in info:
        for g, age in GRADES:
            if g in text:
                info["年龄"] = age
                info["年级"] = g
                break

    # 身高 170cm / 1米7 / 身高170
    m = re.search(r"(?i)(?<![\d.])(\d{3})\s*(?:cm|厘米)", text)
    if m and 130 <= int(m.group(1)) <= 215:
        info["身高"] = int(m.group(1))
    if "身高" not in info:
        m = re.search(r"身高[:：\s]*(\d{3})", text)
        if m and 130 <= int(m.group(1)) <= 215:
            info["身高"] = int(m.group(1))
    if "身高" not in info:
        m = re.search(r"1\s*[米m]\s*([5-9]\d?)", text)
        if m:
            info["身高"] = 100 + int(m.group(1))

    # 体重 50kg / 100斤 / 体重50
    m = re.search(r"(?i)(?<![\d.])(\d{2,3}(?:\.\d)?)\s*(?:kg|公斤|千克)", text)
    if m:
        info["体重"] = float(m.group(1))
    if "体重" not in info:
        m = re.search(r"(?<![\d.])(\d{2,3})\s*斤", text)
        if m:
            info["体重"] = round(float(m.group(1)) / 2, 1)
            info["体重原文"] = m.group(1) + "斤"
    if "体重" not in info:
        m = re.search(r"体重[:：\s]*(\d{2,3}(?:\.\d)?)", text)
        if m:
            v = float(m.group(1))
            info["体重"] = round(v / 2, 1) if v >= 100 else v

    # 身高/体重组合 172/55 或 172 55kg
    if "身高" not in info or "体重" not in info:
        m = re.search(r"(?<!\d)(1[3-9]\d)\s*[｜|/、,，\s]\s*(\d{2,3}(?:\.\d)?)", text)
        if m:
            h, w = float(m.group(1)), float(m.group(2))
            if 130 <= h <= 215:
                info.setdefault("身高", int(h))
                if "体重" not in info:
                    if w >= 80:
                        info["体重"] = round(w / 2, 1)
                        info["体重原文"] = "%g斤" % w
                    elif 25 <= w <= 150:
                        info["体重"] = w

    # 过滤异常值
    if "体重" in info and not (25 <= info["体重"] <= 200):
        info.pop("体重", None)
    if "身高" in info and not (140 <= info["身高"] <= 210):
        info.pop("身高", None)
    if "年龄" in info and not (12 <= info["年龄"] <= 45):
        info.pop("年龄", None)
    return info


def analyze(users):
    """返回统计 dict"""
    users = list(users.values()) if isinstance(users, dict) else list(users)
    yn = [u for u in users if is_yaoniang(u)]
    named = [u for u in users if has_name_marker(u) and not is_yaoniang(u)]

    ages, weights, heights = [], [], []
    mental = Counter()
    kwc = Counter()
    for u in yn:
        low = ((u.get("bio") or u.get("signature") or "")).lower()
        for k in KEYWORDS:
            if kw_hit(low, k):
                kwc[k] += 1
        for label, kws in MENTAL:
            if any(kw_hit(low, k) for k in kws):
                mental[label] += 1
        info = parse_profile(u.get("bio") or u.get("signature") or "")
        if "年龄" in info:
            ages.append(info["年龄"])
        if "体重" in info:
            weights.append(info["体重"])
        if "身高" in info:
            heights.append(info["身高"])

    ages.sort()
    weights.sort()
    heights.sort()
    med = lambda a: statistics.median(a) if a else 0
    age_cnt = Counter(ages)

    cats = []
    for name, kws in CATEGORIES:
        total = sum(kwc.get(k, 0) for k in kws)
        uniq = sum(
            1 for u in yn
            if any(kw_hit(((u.get("bio") or u.get("signature") or "")).lower(), k) for k in kws)
        )
        cats.append({"name": name, "total": total, "uniq": uniq,
                     "detail": ", ".join("%s=%d" % (k, kwc.get(k, 0)) for k in kws)})

    return {
        "total": len(users),
        "yaoniang": len(yn),
        "named_only": len(named),
        "age_n": len(ages), "age_min": ages[0] if ages else 0, "age_max": ages[-1] if ages else 0,
        "age_med": med(ages),
        "age_avg": round(statistics.mean(ages), 1) if ages else 0,
        "age_dist": {str(k): age_cnt[k] for k in sorted(age_cnt)},
        "w_n": len(weights), "w_min": weights[0] if weights else 0,
        "w_max": weights[-1] if weights else 0, "w_med": med(weights),
        "h_n": len(heights), "h_min": heights[0] if heights else 0,
        "h_max": heights[-1] if heights else 0, "h_med": med(heights),
        "mental": dict(mental.most_common()),
        "keywords": dict(kwc.most_common()),
        "categories": cats,
    }


def render_text(stat, users, title="抖音关注分类结果"):
    """生成 txt 报告"""
    yn = [u for u in (users.values() if isinstance(users, dict) else users) if is_yaoniang(u)]
    L = ["# " + title,
         "# 总数 %d | 药娘 %d | 仅昵称标记 %d" % (stat["total"], stat["yaoniang"], stat["named_only"]),
         "", "【统计摘要】"]
    if stat["age_n"]:
        L.append("年龄：样本 %d 人 | 最小 %d | 最大 %d | 中位数 %g | 平均 %.1f"
                 % (stat["age_n"], stat["age_min"], stat["age_max"], stat["age_med"], stat["age_avg"]))
    if stat["w_n"]:
        L.append("体重：样本 %d 人 | 最轻 %gkg | 最重 %gkg | 中位数 %gkg"
                 % (stat["w_n"], stat["w_min"], stat["w_max"], stat["w_med"]))
    if stat["h_n"]:
        L.append("身高：样本 %d 人 | 最矮 %gcm | 最高 %gcm | 中位数 %gcm"
                 % (stat["h_n"], stat["h_min"], stat["h_max"], stat["h_med"]))
    L.append("")
    if stat["age_dist"]:
        L.append("年龄分布：")
        for a, n in stat["age_dist"].items():
            L.append("  %s岁：%d 人" % (a, n))
        L.append("")
    L.append("【精神疾病自述】")
    for k, v in stat["mental"].items():
        L.append("  %s：%d 人" % (k, v))
    L.append("")
    L.append("【关键词命中统计】（可重复命中）")
    for k, v in stat["keywords"].items():
        L.append("  %s：%d 人" % (k, v))
    L.append("")
    L.append("【关键词分类统计】")
    for c in stat["categories"]:
        L.append("%s：计数合计 %d | 去重人数 %d" % (c["name"], c["total"], c["uniq"]))
        L.append("    " + c["detail"])
    L.append("")
    L.append("【明细】")
    for u in yn:
        bio = (u.get("bio") or u.get("signature") or "").replace("\n", " ")
        handle = u.get("screen_name") or u.get("unique_id") or ""
        L.append("@%s | %s | 粉丝 %s | %s" % (handle, u.get("name", ""), u.get("followers", 0), bio[:100]))
    return "\n".join(L)
