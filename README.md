# Global Hotspot Radar

一个可零服务器运行的“AI 全球热点事件雷达”。项目定时聚合 GDELT 与 BBC、DW、NPR、Al Jazeera 的 RSS，把重复报道整理成事件，给出 0–100 热点评分与中文结构化研判，并将结果发布为 GitHub Pages 静态站点。

> 当前版本：`v0.1.0`。AI 是可选增强项；没有任何 API Key 时，采集、去重、聚类、评分、中文模板分析、DuckDB 存储和网页展示仍可完整运行。

## 能力一览

- GDELT DOC 2.0 全球新闻采集，支持多个主题查询、限流退避与单源容错
- BBC World、DW、NPR World、Al Jazeera RSS 聚合
- URL 规范化与去重：移除 UTM、`fbclid`、fragment 等追踪信息
- 事件级聚类：按标题和摘要的加权词向量、发布时间窗口合并相似报道
- 七类自动分类：国际政治、军事安全、经济金融、科技AI、能源资源、产业供应链、社会突发
- 可解释的 0–100 热点评分：报道量、信源多样性、地区覆盖、时效、可信度、影响等级与传播速度
- 全球热点 TOP 10，以及每个事件的完整中文详情：发生了什么、为什么重要、主要参与方、最新进展、信息来源、对中国可能影响、对金融市场可能影响、后续观察指标
- DuckDB 保存文章、事件关系与每次运行记录
- 响应式静态 Dashboard，可搜索、分类筛选和查看原始信源
- GitHub Actions 每小时自动刷新并提交网页数据与历史数据库

## 工作流程

```text
GDELT + RSS
     │
     ▼
清洗、URL 规范化与去重
     │
     ▼
相似度聚类 → 事件分类 → 热点评分
     │                         │
     ▼                         ▼
可选 AI / 中文规则分析        DuckDB 历史库
     │
     ▼
docs/data/events.json → GitHub Pages Dashboard
```

## 项目结构

```text
.
├── .github/workflows/update-radar.yml  # 每小时运行与提交数据
├── config/
│   ├── settings.json                   # 聚类、时窗、TOP N 等参数
│   └── sources.json                    # RSS 信源配置
├── data/hotspots.duckdb                # 运行后生成的历史库
├── docs/                               # GitHub Pages 静态站点
│   ├── data/events.json
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── src/hotspot_radar/
│   ├── sources/                        # GDELT 与 RSS 采集器
│   ├── analysis.py                     # 可选 AI 与无 Key 回退分析
│   ├── classifier.py                   # 七类分类器
│   ├── clustering.py                   # 相似事件聚类
│   ├── scoring.py                      # 可解释热点评分
│   ├── storage.py                      # DuckDB 持久化
│   └── pipeline.py                     # 端到端编排
└── tests/                              # 单元与集成测试
```

## 本地运行

需要 Python 3.11 或更高版本。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m hotspot_radar.cli run
```

成功后：

- 雷达数据：`docs/data/events.json`
- 历史数据库：`data/hotspots.duckdb`
- 静态页面：执行 `python -m http.server 8000 --directory docs`，访问 `http://localhost:8000`

也可以用离线样例完整验证处理链：

```bash
python -m hotspot_radar.cli run --fixture tests/fixtures/articles.json
```

常用覆盖参数：

```bash
python -m hotspot_radar.cli run \
  --database data/custom.duckdb \
  --docs docs \
  --top-n 10
```

## 可选 AI 分析

不配置 Key 时，系统使用按事件类别设计的中文规则模板，所有必需字段都有输出。模板会保留原文标题和专有名词，不会假装已经翻译或核实报道全文。

如需更丰富的跨信源归纳，在仓库或本地设置：

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4.1-mini"
python -m hotspot_radar.cli run
```

AI 调用失败、超时或返回格式不正确时，系统自动回退到规则模板，不会中断数据更新。发送给模型的内容仅包含当前事件的标题、摘要、信源和时间。

## GitHub Actions

工作流 `.github/workflows/update-radar.yml`：

1. 每小时第 17 分钟自动运行，也支持手动运行；
2. 安装项目并抓取全部信源；
3. 更新静态 JSON 与 DuckDB；
4. 仅在数据变化时由机器人提交到默认分支。

仓库需要允许 Actions 写入：

1. 打开 **Settings → Actions → General**；
2. 在 **Workflow permissions** 选择 **Read and write permissions**；
3. 保存。

可选 AI 配置：

- **Settings → Secrets and variables → Actions → Secrets** 新建 `OPENAI_API_KEY`
- 可在 **Variables** 新建 `OPENAI_MODEL`；不设置时使用 `gpt-4.1-mini`

不要把 `.env`、API Key 或其他凭据提交到仓库。

## GitHub Pages 部署

1. 打开 **Settings → Pages**；
2. **Build and deployment** 选择 **Deploy from a branch**；
3. Branch 选择默认分支（通常为 `main`），目录选择 `/docs`；
4. 保存，等待首次部署完成。

网站地址通常为 `https://cstjb.github.io/global-hotspot-radar/`。

## 配置

`config/settings.json` 主要参数：

| 参数 | 默认值 | 作用 |
|---|---:|---|
| `lookback_hours` | 48 | GDELT 回看范围 |
| `max_articles_per_source` | 50 | 单个查询或 RSS 的最大文章数 |
| `cluster_similarity_threshold` | 0.34 | 越高越不容易合并为同一事件 |
| `cluster_time_window_hours` | 36 | 允许聚类的最大时间间隔 |
| `top_n` | 10 | Dashboard 展示数量 |
| `database_path` | `data/hotspots.duckdb` | 历史库位置 |
| `docs_path` | `docs` | 静态站点位置 |

支持环境变量覆盖：`RADAR_DATABASE`、`RADAR_TOP_N`、`RADAR_LOOKBACK_HOURS`。

添加 RSS 只需在 `config/sources.json` 增加记录：

```json
{
  "name": "Source name",
  "url": "https://example.com/rss.xml",
  "region": "Asia",
  "language": "en",
  "weight": 0.9
}
```

`weight` 建议在 0–1 之间，用于评分中的信源可信度分量。

## 热点评分

每个事件的得分由七个可检查分量构成：

| 分量 | 权重 | 含义 |
|---|---:|---|
| 报道覆盖 | 22 | 事件包含的独立报道量，采用对数缩放 |
| 信源多样性 | 18 | 独立媒体数量 |
| 时效 | 22 | 随最后更新时间指数衰减 |
| 类别影响 | 13 | 军事、安全、宏观等类别的基础影响等级 |
| 地区覆盖 | 10 | 信源所属地区数量 |
| 信源可信度 | 10 | 配置的信源权重均值 |
| 传播速度 | 5 | 单位时间内新增报道速度 |

得分用于同一批次的关注优先级，不代表事实真伪或事件价值判断。页面始终保留原始报道链接，便于交叉核验。

## 数据库

DuckDB 包含四张表：

- `articles`：规范化后的独立文章
- `events`：聚类事件、评分、关键词与分析结果
- `event_articles`：事件与文章的多对多关系
- `run_history`：每次运行的状态、数量与单源错误

快速查看：

```bash
python - <<'PY'
import duckdb
con = duckdb.connect("data/hotspots.duckdb", read_only=True)
print(con.sql("SELECT category, count(*) FROM events GROUP BY category ORDER BY 2 DESC"))
PY
```

## 测试

```bash
python -m unittest discover -s tests -v
```

测试覆盖 URL 规范化、文本清洗、相似事件聚类、分类、评分边界，以及从样例输入到 DuckDB 和 Dashboard JSON 的完整链路。

## 可靠性与限制

- 每个外部信源独立执行；某一来源失败时，其余来源仍会继续，运行状态标记为 `partial`。
- 对 429 和常见 5xx 响应采用指数退避重试。
- 聚类是轻量本地算法，适合免费定时任务，但同义词、跨语言和复杂事件演化仍可能误拆分或误合并。
- 自动分析不是事实核查；重要判断应回到多个原始信源确认。
- 当前事件 ID 以最早报道为稳定锚点。后续版本可加入跨批次事件实体匹配与事件合并审计。

## 后续扩展方向

现有模块边界已为以下能力预留扩展点：

- 全球地图：为文章与事件增加地理实体抽取和坐标表
- 事件时间线：利用文章时间和跨批次实体匹配构建阶段变化
- 趋势变化：基于运行记录和事件评分快照计算升温/降温
- 日报与周报：增加独立渲染器，复用事件分析结构
- 重点预警：在评分后增加规则与通知适配器，不耦合采集层
- 多语种语义聚类：将当前本地词向量替换为可选 embedding 后端

## License

MIT
