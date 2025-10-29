# 万智牌锁牌名录

本项目包含《万智牌锁牌名录》的生成工具链以及全新的 Web 前后端，用于在浏览器中检索、筛选并构建锁牌牌本。

## 目录结构概览

- `AllThatStax.cls` / `AllThatStax.tex`：LaTeX 文档类与主文件，用于生成书籍 PDF。
- `Figures/`、`Images/`、`Symbols/`：书籍所需的插图、卡图与法术力符号。
- `card_information_sheet.xlsx`：整理后的卡牌数据源，`Sheet`/`Multiface Sheet` 分别存放单面牌与多面牌。
- `config.json`：配置文件，定义图像、表格、锁类型映射等路径。
- `allthatstax/`：新版的 Python 工具包，封装了配置读取、Excel 数据处理与 LaTeX 文本生成逻辑。
- `get_cards_information.py`、`localization.py`、`run_latex.py`、`main.py`：Python 数据抓取、文本生成与编译脚本，其中 `genarate_latex_text.py` 保留为兼容旧用法的包装器。
- `backend/`：基于 FastAPI 的数据 API，提供卡牌数据与元信息，并托管图片、法术力图标静态资源。
- `frontend/`：基于 Vite + React + TypeScript 的前端项目，包含卡牌表格、筛选器以及可视化牌本构建界面。

## 后端（FastAPI）

后端会从 `card_information_sheet.xlsx` 中读取卡牌数据，统一输出给前端使用，并挂载图片及法术力符号静态目录。

### 快速启动

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

接口默认监听在 `http://127.0.0.1:8000`，关键端点：

- `GET /cards`：返回所有单面牌与多面牌的结构化数据。
- `GET /cards/{card_id}`：按 ID 获取指定卡牌详情。
- `GET /metadata`：返回锁类型映射与牌类型排序信息。
- `GET /health`：健康检查。
- `GET /latex/settings`：读取当前配置中的 LaTeX 生成参数默认值。
- `POST /latex/generate`：根据传入设置生成 `latex_text.txt` 并可选编译 PDF。
- `GET /latex/download`：下载最近一次生成的 PDF 文件。

静态资源：

- `/images/*`：卡图原图。
- `/symbols/*`：法术力符号 SVG。

## 前端（Vite + React）

前端提供卡牌浏览、牌本构建以及 LaTeX/PDF 生成界面，支持按名称/描述搜索、按锁类型和牌类型筛选、展示法术力曲线与锁类型分布等功能。

### 本地开发

```bash
cd frontend
npm install
# 配置后端地址（如需跨域）
cp .env.example .env
npm run dev
```

默认情况下，Vite 会通过代理将 `/cards`、`/metadata`、`/images`、`/symbols` 请求转发到 `.env` 中的 `VITE_API_BASE_URL`（默认为 `http://localhost:8000`）。

### 生产构建

```bash
npm run build
```

构建产物位于 `frontend/dist/`。

## 牌本工作流

1. 使用命令行工具 `python main.py --fetch` 更新 `card_information_sheet.xlsx` 与本地图片资源（可选 `--fetch-from-scratch` 完全重建表格）。
2. 如需补全中文信息，执行 `python main.py --localize` 自动抓取缺失的本地化字段。
3. 默认命令会读取 Excel 并生成最新的 LaTeX 片段，然后调用 `xelatex` 编译 PDF；如只需生成文本可添加 `--skip-compile`。
4. 启动 FastAPI 服务，通过 `/cards` 和 `/metadata` 获取最新数据，配合前端浏览、检索和构建牌本，或使用前端的“PDF 生成”标签直接触发 LaTeX 文本生成与编译。

欢迎根据需要扩展 API、添加导出能力或集成现有 LaTeX 生成流程。

## 命令行工具

新版 `main.py` 将常用流程整合为一个命令行入口，可通过 `python main.py --help` 查看完整参数列表。常用场景示例：

```bash
# 从配置读取路径，抓取卡牌信息并编译 PDF
python main.py --fetch

# 仅生成 LaTeX 文本，跳过编译
python main.py --skip-compile

# 使用自定义 LaTeX 编译命令
python main.py --latex-command xelatex -shell-escape
```

命令会自动解析 `config.json` 中的路径，生成的 LaTeX 片段存放在 `latex_text.txt`（默认配置），并在未禁止的情况下调用 `xelatex` 生成最终 PDF。

## 卡牌列表管理脚本

仓库中新增了 `card_list_manager.py`，用于从指定的 Moxfield 牌表抓取卡牌信息，并整合来自 Scryfall 与 mtgch.com 的数据。执行脚本后会：

- 调用 `https://api.moxfield.com` 获取牌表中的所有卡牌与数量；
- 从 Scryfall 获取卡牌的英文名称、类型、法术力费用、效果文字以及最早印刷的系列与卡图；
- 从 mtgch.com 获取卡牌的中文名称、类型、费用、效果与系列名称（若网站暂缺资料则跳过该部分）；
- 将整合后的数据写入本地 JSON 文件，并把卡图下载至指定目录。

### 环境准备

1. 安装 Python 3.9+（建议使用虚拟环境管理依赖）。
2. 本脚本仅使用标准库，无需额外依赖，但需要能够访问 `moxfield.com`、`api.scryfall.com` 与 `mtgch.com`。
3. 准备一个用于存放输出数据与图片的目录（例如 `data/`）。

### 常用命令

```bash
# 查看脚本自带的帮助信息
python card_list_manager.py --help

# 抓取示例牌表（牌表 ID 可在 moxfield 牌表 URL 中找到）
python card_list_manager.py kBI9w5lzJUijYHVBWddzfg \
  --output data/moxfield_stax_cards.json \
  --image-dir data/moxfield_images
```

主要参数说明：

- `deck_id`：Moxfield 牌表链接中的 ID，例如 `https://moxfield.com/decks/<deck_id>`。
- `--output`：整合后的卡牌数据保存路径（默认为 `data/card_data.json`）。
- `--image-dir`：卡图下载目录（默认 `data/images`）。
- `--pause`：连续请求之间的等待秒数（默认为 `0.2`）。
- `--keep-existing`：若指定则跳过已存在的卡图文件，避免重复下载。

### 运行流程

1. 从 Moxfield 读取牌表中的卡牌与数量。
2. 使用 Scryfall API 获取卡牌的英文资料、最早印刷系列与对应卡图链接。
3. 前往 mtgch.com 搜索对应卡牌，解析中文名称、类别、费用、效果与系列名称（若 mtgch 无数据则该部分字段为空字符串）。
4. 将所有卡牌的中英文资料写入 `--output` 指定的 JSON 文件，并把最早系列的英文卡图下载到 `--image-dir`。

执行过程中，脚本会在终端输出当前处理的卡牌与进度，若遇到网络错误会在重试后抛出提示，可根据需要调整 `--pause` 或稍后重试。
