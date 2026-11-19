# mtf-finder-dy

**抖音「关注列表滚雪球」爬虫 · 纯 cookie 接口版 · 自带网页面板**

从你自己的关注列表出发，顺着「谁关注了谁」一层层扩展，抓取公开简介里的年龄、身高、体重、精神疾病自述，并统计关键词。

> 仅用于个人数据整理，只抓公开信息。请遵守平台条款、控制频率。

---

## 中文说明

### 原理

```
你的关注列表（约几百~几千人）
      │  /aweme/v1/web/user/following/list/ （cookie + 本地 a_bogus 签名）
      ▼
   第一批账号 ──► 挑出「关注数≥20 且像药娘」的
                        │ 打开 ta 的关注列表继续抓
                        ▼
                   新账号入队 ──► 重复（滚雪球）
```

- **不需要浏览器**：签名由内置的 Node 签名器本地计算，直接调接口
- **不会弹验证码**：没有无头浏览器特征，纯 HTTP 请求
- **断点续跑**：已扩展的账号记在 `data/state.json`

### 安装

需要 **Python 3.9+** 和 **Node.js 16+**：

```bash
git clone https://github.com/<you>/mtf-finder-dy.git
cd mtf-finder-dy
node -v          # 确认 Node 可用
# 无需 pip install，纯标准库
```

### 准备 cookie

1. 电脑浏览器登录 <https://www.douyin.com>
2. `F12` → **Application** → **Cookies** → `https://www.douyin.com`
3. 把**所有** cookie 导出成 JSON（关键是 `sessionid`，它是 HttpOnly，只能用这种方式拿）：

```json
{
  "sessionid": "...",
  "sessionid_ss": "...",
  "sid_guard": "...",
  "uid_tt": "...",
  "ttwid": "...",
  "passport_csrf_token": "..."
}
```

4. 保存为 `cookies/douyin.json`

### 使用

```bash
python run_panel.py            # 面板：http://127.0.0.1:8790
python run_crawl.py            # 命令行直接跑
python run_crawl.py --max-expand 500 --user-pages 3
```

面板功能：实时数量、年龄分布、疾病排行、关键词命中、开始/停止/生成报告、报告每 5 分钟自动刷新。

### 输出

| 文件 | 内容 |
|---|---|
| `data/douyin_users.jsonl` | 原始数据（断点续跑用） |
| `data/state.json` | 已扩展账号，避免重复 |
| `data/report.txt` | 统计报告 |
| `data/report.csv` | 逐人明细（年龄/身高/体重/疾病/简介） |

### 判定口径（可在 `config.py` 改）

- **药娘**：简介含 `药娘 / 木桶饭 / 木桶 / 吃糖 / 含糖 / xyn / yn / hrt / gaht / mtf`
- **昵称标记**：🍥 / 🏳️‍⚧️ / ⚧（只作辅助）
- 年龄支持 `16岁`、`09年的`、`🎂2010/1/11`、`准高三`
- 身高体重支持 `170cm`、`1米7`、`172/55`、`100斤`（自动换算）

### 已知限制

- 只能看**公开**的关注列表（私密账号抓不到）
- 抖音改签名算法后，`abogus/` 需要更新，否则接口返回空
- 简介是自述信息，存在玩笑/单位混用，统计只能看趋势

---

## English

**Douyin "following-list snowball" scraper — pure cookie API, with a web panel.**

Start from your own following list and expand hop by hop; collects public bio info (age / height / weight / mental-health mentions) and keyword stats.

> For personal data organization only. Public information only. Respect platform terms and rate limits.

### How it works

```
your following list
      │  /aweme/v1/web/user/following/list/  (cookie + locally computed a_bogus)
      ▼
  first batch ──► pick accounts with following ≥ 20 that look like mtf
                        │  fetch their following lists
                        ▼
                   new accounts ──► repeat (snowball)
```

- **No browser needed** — signatures are computed locally by the bundled Node signer
- **No captcha** — plain HTTP requests, no headless-browser fingerprints
- **Resumable** — expanded accounts are tracked in `data/state.json`

### Install

Requires **Python 3.9+** and **Node.js 16+**:

```bash
git clone https://github.com/<you>/mtf-finder-dy.git
cd mtf-finder-dy
node -v
```

### Cookies

1. Log in at <https://www.douyin.com> in a desktop browser
2. `F12` → **Application** → **Cookies** → `https://www.douyin.com`
3. Export **all** cookies as JSON (`sessionid` is HttpOnly — this is the only way to get it)
4. Save as `cookies/douyin.json`

### Usage

```bash
python run_panel.py     # panel at http://127.0.0.1:8790
python run_crawl.py     # CLI
python run_crawl.py --max-expand 500 --user-pages 3
```

### Output

`data/douyin_users.jsonl`, `data/state.json`, `data/report.txt`, `data/report.csv`

### Limitations

- Only **public** following lists are visible
- If Douyin changes the signature, `abogus/` must be updated
- Bios are self-reported; treat numbers as trends, not facts

---

MIT License
