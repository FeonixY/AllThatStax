# 万智牌锁牌名录

本项目包含《万智牌锁牌名录》的生成工具链以及全新的 Web 前后端，用于在浏览器中检索、筛选并构建锁牌牌本。

## 目录结构概览

- `AllThatStax.cls` / `AllThatStax.tex`：LaTeX 文档类与主文件，用于生成书籍 PDF。
- `Figures/`、`Images/`、`Symbols/`：书籍所需的插图、卡图与法术力符号。
- `card_data.json`：整理后的卡牌数据源，包含单面与多面牌的结构化信息。
- `config.json`：配置文件，定义图像、表格、锁类型映射等路径。
- `allthatstax/`：新版的 Python 工具包，封装了配置读取、JSON 数据处理与 LaTeX 文本生成逻辑。
- `allthatstax/workflow/`：Python 数据抓取与 LaTeX 编译工作流模块，`main.py` 提供命令行入口。
- `backend/`：基于 FastAPI 的数据 API，提供卡牌数据与元信息，并托管图片、法术力图标静态资源。
- `frontend/`：基于 Vite + React + TypeScript 的前端项目，包含卡牌表格、筛选器以及可视化牌本构建界面。

## 后端（FastAPI）

后端会从 `card_data.json` 中读取卡牌数据，统一输出给前端使用，并挂载图片及法术力符号静态目录。

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
- `GET /cards/fetch/settings`：返回卡牌抓取的默认路径与选项。
- `POST /cards/fetch`：根据卡表读取卡牌列表，从 Scryfall 抓取最新英文信息与卡图并写入本地 JSON。
- `GET /latex/download`：下载最近一次生成的 PDF 文件。

静态资源：

- `/images/*`：卡图原图。
- `/symbols/*`：法术力符号 SVG。

## 前端（Vite + React）

前端提供卡牌浏览、牌本构建、LaTeX/PDF 生成以及卡牌信息抓取界面，支持按名称/描述搜索、按锁类型和牌类型筛选、展示法术力曲线与锁类型分布等功能。

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

1. 使用命令行工具 `python main.py --fetch` 或前端“卡牌信息爬取”标签，从 `card_list.json` 读取卡牌列表并调用 Scryfall 获取英文信息、合法性与同系列卡图，结果写入 `card_data.json` 并更新 `Images/`。
2. 如需重置数据，可加上 `--fetch-from-scratch`（或在前端勾选“从空白开始重新生成”），忽略既有 JSON 重新抓取。
3. 默认命令会读取 JSON 并生成最新的 LaTeX 片段，然后调用 `xelatex` 编译 PDF；如只需生成文本可添加 `--skip-compile`，也可在前端“PDF 生成”标签中直接配置并触发。
4. 启动 FastAPI 服务，通过 `/cards` 和 `/metadata` 获取最新数据，配合前端浏览、检索和构建牌本，或使用新增的抓取与生成界面完成全流程。

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

## 卡牌抓取说明

项目默认的卡牌列表保存在 `card_list.json`，结构示例如下：

```
{
  "source": "moxfield",
  "deckId": "kBI9w5lzJUijYHVBWddzfg",
  "cards": [
    {
      "quantity": 1,
      "name": "Aether Barrier",
      "setCode": "NEM",
      "collectorNumber": "27",
      "lockTypes": ["Spell Tax"]
    }
  ]
}
```

若使用 Moxfield 维护牌表，可在 `config.json` 中配置 `moxfield_deck_url`，或在前端“卡牌信息爬取”界面填写 Moxfield 链接并点击“获取牌表”。
后端会通过新的 `/cards/fetch/moxfield` 接口请求 Moxfield API，将主牌列表转换为上述 JSON 结构并写入本地卡表文件，便于随后执行抓取流程。

抓取流程会根据系列代码与收藏编号调用 Scryfall 的 `/cards/{set}/{collector_number}` 接口，若该版本不存在则回退至 `cards/named` 搜索，对应的英文信息、合法性、法术力值与卡图链接都会写入 `card_data.json`。配置中的 `stax_type` 用于将行尾的 `#标签` 映射为中文锁类型。

> 例如示例中的《Aether Barrier》会抓取复仇时代版本，并将“Spell Tax”标记为锁类型。

抓取时会将卡图保存到 `Images/` 目录，文件名包含系列与收藏编号，前端和 LaTeX 生成都会引用这些资源。若仅需更新文字信息，可在前端取消“下载英文卡图”，或在命令行追加 `--no-download-images`。

如需扩展新的标签或自定义存储结构，可修改 `config.json` 中的路径与 `stax_type` 映射，`allthatstax.workflow.fetch.get_cards_information` 会自动读取这些配置。
