# 万智牌锁牌名录

本项目包含《万智牌锁牌名录》的生成工具链以及全新的 Web 前后端，用于在浏览器中检索、筛选并构建锁牌牌本。

## 目录结构概览

- `AllThatStax.cls` / `AllThatStax.tex`：LaTeX 文档类与主文件，用于生成书籍 PDF。
- `Figures/`、`Images/`、`Symbols/`：书籍所需的插图、卡图与法术力符号。
- `card_information_sheet.xlsx`：整理后的卡牌数据源，`Sheet`/`Multiface Sheet` 分别存放单面牌与多面牌。
- `config.json`：配置文件，定义图像、表格、锁类型映射等路径。
- `get_cards_information.py`、`localization.py`、`genarate_latex_text.py`、`run_latex.py`、`main.py`：原有的 Python 数据抓取、文本生成与编译脚本。
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

静态资源：

- `/images/*`：卡图原图。
- `/symbols/*`：法术力符号 SVG。

## 前端（Vite + React）

前端提供卡牌浏览与牌本构建界面，支持按名称/描述搜索、按锁类型和牌类型筛选、展示法术力曲线与锁类型分布等功能。

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

1. 使用后端脚本更新 `card_information_sheet.xlsx` 与本地图片资源。
2. 启动 FastAPI 服务，通过 `/cards` 和 `/metadata` 获取最新数据。
3. 启动前端，浏览卡牌表格并将卡牌加入右侧牌本面板。
4. 前端自动按法术力曲线与牌类型分区展示卡牌，便于整理、导出和继续在 LaTeX 流程中使用。

欢迎根据需要扩展 API、添加导出能力或集成现有 LaTeX 生成流程。
