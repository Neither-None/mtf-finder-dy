# douyin-yaoniang

**抖音「关注列表滚雪球」爬虫**：从你自己的关注列表出发，顺着「谁关注了谁」一层层扩展，
抓取公开简介里的年龄 / 身高 / 体重 / 精神疾病自述，并统计关键词。

自带网页控制面板，跨平台（Windows / macOS / Linux）。

> 仅用于个人数据整理，抓取公开信息，请控制频率、遵守平台条款。

---

## 它是怎么找到人的

```
你自己的关注列表（约几十~几千人）
        │  抓分页接口 /aweme/v1/web/following/list/
        ▼
   第一批账号  ← 存下来
        │  挑出「关注数 ≥ 20 且像药娘（简介有关键词）」的
        ▼
   打开 ta 的关注列表页 → 抓分页 → 又得到一批新账号
        │
        └── 重复，直到队列空或达到上限
```

因为这类社群互关密度很高（简介里常写「同类互fo」），从一个人出发往往能滚到几千上万人。

---

## 安装

需要 Python 3.9+。

```bash
git clone <this-repo>
cd douyin-yaoniang

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium
```

> 如果电脑上已有 Chrome/Chromium，可以跳过最后一步，运行时加
> `--browser-path "C:\Program Files\Google\Chrome\Application\chrome.exe"`
> （macOS: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`）。

---

## 准备 cookie（关键一步）

抖音的登录态在 `sessionid` 里，而它是 **HttpOnly** 的，脚本里读不到，
必须从浏览器开发者工具里导出：

1. Chrome / Edge 打开 <https://www.douyin.com> 并登录
2. 按 `F12` 打开开发者工具
3. 切到 **Application**（应用）→ 左侧 **Cookies** → `https://www.douyin.com`
4. 逐个复制，粘成下面这种 JSON（**必须包含 `sessionid`**，其余越多越好）：

```json
{
  "sessionid": "xxxxx",
  "sessionid_ss": "xxxxx",
  "ttwid": "xxxxx",
  "passport_csrf_token": "xxxxx",
  "odin_tt": "xxxxx",
  "sid_guard": "xxxxx"
}
```

5. 保存为 `cookies/douyin.json`

> Firefox 用户：F12 → 存储 → Cookie，导出方式类似。
> 也可以装 Cookie-Editor 扩展，一键 Export JSON 再取值。

---

## 跑起来

### 方式一：网页面板（推荐）

```bash
python run_panel.py
```

打开 <http://127.0.0.1:8790>

页面上有：
- **状态 / 总账号 / 药娘**：实时数字
- **开始抓取 / 停止 / 生成报告**：三个按钮
- 年龄分布柱状图、精神疾病自述排行、关键词命中表、最近日志
- 报告每 5 分钟自动刷新一次

### 方式二：命令行

```bash
python run_crawl.py                      # 默认：每账号滚 3 屏，最多扩展 200 个
python run_crawl.py --max-expand 500     # 想抓更多
python run_crawl.py --scrolls 5          # 每个账号多滚几屏（抓得更全，也更慢）
python run_crawl.py --no-headless        # 显示浏览器窗口，能看到它在干什么
```

想先小规模试跑：

```bash
python run_crawl.py --max-expand 10 --scrolls 2
```

---

## 输出

| 文件 | 内容 |
|---|---|
| `data/douyin_users.jsonl` | 原始数据（每行一个账号，断点续跑靠它） |
| `data/state.json` | 已扩展过的账号，重启后不会重复爬 |
| `data/report.txt` | 统计报告：年龄/体重/身高、疾病自述、关键词命中、八类分组、名单 |
| `data/report.csv` | 逐人明细：抖音号、昵称、粉丝、年龄、身高、体重、疾病、简介 |
| `data/crawl.log` | 运行日志 |

csv 用 Excel 直接打开（UTF-8 BOM，不会乱码）。

---

## 判定口径

- **药娘**：简介里出现 `药娘 / 木桶饭 / 木桶 / 吃糖 / 含糖 / xyn / yn / hrt / gaht / mtf` 任意一个
- **昵称标记**（🍥 / 🏳️‍⚧️ / ⚧）只作辅助，不单独算药娘
- **年龄**：`16岁`、`09年的`、`🎂2010/1/11`、`准高三` 等写法都能识别
- **身高/体重**：`170cm`、`1米7`、`172/55`、`100斤`（自动换算公斤）
- 想改规则 → 编辑 `config.py`

---

## 常见问题

**抓到 0 个账号**
1. 先加 `--no-headless` 看窗口里是什么页面
2. 如果跳到登录页 → cookie 失效，重新导出
3. 如果能打开关注列表但没有数据 → 抖音改版了，看 `data/crawl.log`

**跑一会儿就停了**
抖音有限流，脚本里每次请求之间会等 2–4 秒。跑太久被限流时，等十几分钟再启动，
会从 `data/state.json` 记录的位置继续。

**能不能抓别人的关注列表？**
能，但只有**公开**的关注列表；对方设置了隐私就抓不到（日志会显示 +0）。

**会被封号吗？**
用的是你自己的账号、正常频率访问，风险等同于手动刷网页。但请自行评估，
不要用主号跑长时间任务。

---

## 免责声明

本项目仅用于个人学习与数据整理，抓取的是用户公开信息。
请勿用于骚扰、人肉或商业用途；使用后果由使用者自行承担。

MIT License
