# dma-strategy-backend

基于 **Django + DRF** 的策略服务后端，当前目标是快速做出一个可用的 MVP：**直接从项目内 `data/` 的 CSV 读取数据**，在接口层计算均线与信号并返回给前端使用。

> 代码中仍保留了 PostgreSQL/Redis/JWT 等“可扩展方向”的依赖与配置，但 MVP 阶段不要求启用它们；以 `TODO.md` 为准逐步收敛实现。

## Demo

![Demo](demo.png)

## 技术栈

- Python / Django 5.x
- Django REST framework（DRF）
- 数据来源（MVP）：`data/` 下 CSV
- 可选（后续再做）：PostgreSQL、Redis、Celery、JWT、第三方行情源

## 目录结构

- `dma_strategy/`：Django 项目配置（settings/urls/asgi/wsgi）
- `stocks/`：核心业务 App（models/services/views/migrations）
- `data/`：MVP 数据目录（CSV 数据源）
- `results/`、`*.ipynb`：本地结果/实验文件（非服务必需）

## 本地开发启动

### 1) 环境准备

- Python 3.10+（建议使用虚拟环境）
- MVP 阶段不需要 Redis/数据库（仅需读取 `data/` CSV）

### 2) 进入开发环境

本项目在本地使用 Conda 环境（例如 `django-5`）开发时，建议先初始化 shell 环境再激活：

```bash
source ~/.bash_profile
conda activate django-5
```

> 如果你使用 zsh 且 conda 初始化写在 `~/.zshrc` / `~/.zprofile`，则按你的实际配置 `source` 对应文件即可。

### 3) 安装依赖

```bash
pip install -r requirements.txt
```

### 4) 配置环境变量

项目使用 `.env` 作为本地配置来源（`.env.example` 仅作为参考模板）。

建议的关键配置项：

- `SECRET_KEY` / `DEBUG` / `ALLOWED_HOSTS`
- `DATA_DIR`：CSV 数据目录（例如 `./data`，默认建议就是项目根目录下的 `data/`）

### 5) 启动服务

```bash
python manage.py migrate
python manage.py runserver
```

## API 概览

项目在 `dma_strategy/urls.py` 中配置了以下路由（默认前缀 `/api`）：

- `GET /api/codes/`：获取可用代码列表（从 `DATA_DIR` 扫描 CSV 文件名）
- `GET /api/stock-data/`：获取行情与均线数据
- `GET /api/signals/`：获取交易信号（返回 `{ data, meta }`）

`/api/signals/` 参数分两类：

- **生成参数（影响生成）**：`gen_confirm_bars`、`gen_min_cross_gap`（同类型信号间隔）
- **过滤参数（仅影响返回）**：`filter_signal_type`、`filter_sort`（默认 `desc`）、`filter_limit`

## CSV 数据约定（MVP）

- 数据目录：`DATA_DIR`（默认 `./data`）
- 文件命名：优先匹配 `data/<CODE>.csv`，其次匹配 `data/<CODE>_3y.csv`（例如 `data/AAPL_3y.csv`）
- 必需字段：`date,open,high,low,close,volume`（列名大小写不敏感）

### 示例请求

获取行情数据（示例参数）：

```bash
curl "http://127.0.0.1:8000/api/stock-data/?code=AAPL&short_window=5&long_window=20" \
  -H "Content-Type: application/json"
```

## 测试

```bash
pytest
```

> 若你新增了 pytest-django 配置，通常需要设置 `DJANGO_SETTINGS_MODULE=dma_strategy.settings` 或添加 `pytest.ini`。

更完整的启动与测试步骤见：`STARTUP_AND_TESTING.md`。

## 更多说明

- 更完整的启动与测试步骤见：`STARTUP_AND_TESTING.md`
- 后续扩展（DB/Redis/更多指标）见：`TODO.md`
