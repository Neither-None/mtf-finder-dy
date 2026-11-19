# -*- coding: utf-8 -*-
"""抖音滑块验证码自动求解

原理：
1. 验证码在 iframe 里，背景图 `.captcha-verify-image` 里同时有「拼图块」和「缺口」
2. 用拼图块的形状做模板，在「局部变暗图」上滑动匹配，得分最高的位置就是缺口
3. 拖动底部滑块按钮 `.captcha-slider-btn`，距离 = 缺口 x - 拼图块 x
"""
import random
import time

import cv2
import numpy as np


def _decode(png_bytes):
    return cv2.imdecode(np.frombuffer(png_bytes, np.uint8), cv2.IMREAD_COLOR)


def _piece_mask(piece_img):
    """从拼图块截图中提取形状 mask"""
    hsv = cv2.cvtColor(piece_img, cv2.COLOR_BGR2HSV)
    v, s = hsv[:, :, 2], hsv[:, :, 1]
    # 拼图块有白色描边
    white = ((v > 205) & (s < 90)).astype(np.uint8) * 255
    white = cv2.morphologyEx(white, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    cnts, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < 300:
        return None
    mask = np.zeros(piece_img.shape[:2], np.uint8)
    cv2.drawContours(mask, [c], -1, 255, -1)
    return mask


def find_offset(bg_img, piece_img, piece_x=0):
    """返回需要拖动的水平距离 dx，失败返回 None"""
    gray = cv2.cvtColor(bg_img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    # 局部变暗：原图明显比周围暗的地方 = 缺口
    diff = cv2.GaussianBlur(gray, (0, 0), 22) - gray
    mask = _piece_mask(piece_img)
    if mask is None:
        return None
    m = mask.astype(np.float32) / 255.0
    area = float(m.sum())
    if area < 100:
        return None
    res = cv2.matchTemplate(diff, m, cv2.TM_CCORR) / area
    # 排除拼图块自身所在的位置
    cut = max(20, int(piece_x) + mask.shape[1] + 10)
    res[:, :cut] = -1e9
    _, score, _, loc = cv2.minMaxLoc(res)
    if score < 8:
        return None
    return int(loc[0] - piece_x), loc


def human_drag(page, x, y, dx):
    """带加速减速的拟人拖动"""
    page.mouse.move(x, y)
    time.sleep(random.uniform(0.05, 0.15))
    page.mouse.down()
    time.sleep(random.uniform(0.1, 0.2))
    steps = random.randint(22, 32)
    moved = 0.0
    for i in range(1, steps + 1):
        t = i / steps
        target = dx * (1 - (1 - t) ** 2.4)
        moved = target
        page.mouse.move(x + moved, y + random.uniform(-1.0, 1.0))
        time.sleep(random.uniform(0.008, 0.028))
    page.mouse.move(x + dx, y)
    time.sleep(random.uniform(0.12, 0.28))
    page.mouse.up()


def _captcha_frame(page):
    for f in page.frames:
        if "captcha" in (f.url or ""):
            return f
    return None


def captcha_visible(page):
    try:
        return _captcha_frame(page) is not None
    except Exception:
        return False


def solve(page, attempts=4, log=print):
    """尝试自动过验证码，成功返回 True"""
    for i in range(attempts):
        fr = _captcha_frame(page)
        if not fr:
            return True
        try:
            bg = fr.query_selector(".captcha-verify-image")
            pc = fr.query_selector(".captcha-verify-image-slide")
            btn = fr.query_selector(".captcha-slider-btn")
            if not (bg and pc and btn):
                time.sleep(1.5)
                continue
            bb, pb, bt = bg.bounding_box(), pc.bounding_box(), btn.bounding_box()
            piece_x = pb["x"] - bb["x"]
            bg_img = _decode(bg.screenshot())
            pc_img = _decode(pc.screenshot())
            got = find_offset(bg_img, pc_img, piece_x)
            if not got:
                log("  验证码：没定位到缺口，点刷新重试")
                _refresh(fr)
                continue
            dx, loc = got
            log("  验证码：缺口 x=%.0f 拼图块 x=%.0f → 拖动 %.0f px（第 %d 次）"
                % (loc[0], piece_x, dx, i + 1))
            human_drag(page, bt["x"] + bt["width"] / 2, bt["y"] + bt["height"] / 2, dx)
            page.wait_for_timeout(2200)
            if not captcha_visible(page):
                log("  验证码已通过 ✅")
                return True
        except Exception as e:
            log("  验证码处理异常：%s" % str(e)[:60])
        _refresh(fr)
        page.wait_for_timeout(1500)
    return not captcha_visible(page)


def _refresh(fr):
    try:
        el = fr.query_selector(".captcha-refresh, [class*=refresh]")
        if el:
            el.click()
    except Exception:
        pass
