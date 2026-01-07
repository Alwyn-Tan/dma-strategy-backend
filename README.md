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

- `config/`：Django 项目配置（settings/urls/asgi/wsgi）
- `api/`：HTTP API（DRF views/serializers/urls）
- `domain/`：DB 领域模型（models/migrations/admin）
- `market_data/`：数据来源与落盘（CSV/yfinance/规范化）
- `strategy_engine/`：策略引擎（指标/信号/回测）
- `tooling/`：离线命令（management commands）
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
>
> 在非交互环境（例如脚本/Codex 执行单条命令）中，推荐用 `conda run`：
>
> ```bash
> source ~/.bash_profile
> conda run -n django-5 python manage.py runserver
> ```

### 3) 安装依赖

```bash
pip install -r requirements.txt
```

### 4) 配置环境变量

项目使用 `.env` 作为本地配置来源（`.env.example` 仅作为参考模板）。

建议的关键配置项：

- `SECRET_KEY` / `DEBUG` / `ALLOWED_HOSTS`
- `DATA_DIR`：CSV 数据目录（例如 `./data`，默认建议就是项目根目录下的 `data/`）
- 自动刷新（可选）：
  - `AUTO_REFRESH_ON_REQUEST`：是否按请求自动刷新（默认 true）
  - `AUTO_REFRESH_COOLDOWN_SECONDS`：同一股票自动刷新冷却时间（默认 3600 秒）

### 5) 启动服务

```bash
python3 manage.py migrate
python3 manage.py runserver
```

## API 概览

项目在 `config/urls.py` 中配置了以下路由（默认前缀 `/api`）：

- `GET /api/codes/`：获取可用代码列表（从 `DATA_DIR` 扫描 CSV 文件名）
- `GET /api/stock-data/`：获取行情与均线数据（支持按请求自动刷新）
- `GET /api/signals/`：获取交易信号（返回 `{ data, meta }`）

`/api/signals/` 参数分两类：

- **生成参数（影响生成）**：`gen_confirm_bars`、`gen_min_cross_gap`（同类型信号间隔）
- **过滤参数（仅影响返回）**：`filter_signal_type`、`filter_sort`（默认 `desc`）、`filter_limit`

`/api/stock-data/` 额外参数：

- `include_meta`：返回 `{ data, meta }`，并附带数据范围/刷新状态
- `force_refresh`：忽略冷却时间，强制尝试刷新
- `end_date`：未传时默认今天，用于判断是否需要刷新以及数据过滤
- `include_performance`：返回策略与基准的净值曲线（研究模式：信号在次日开盘成交）

策略增强模块（仅当 `include_performance=true` 时生效，默认都关闭；需要用户显式勾选开关）：

- **Ensemble**：`use_ensemble=true` + `ensemble_pairs`（例如 `5:20,10:50,20:100,50:200`）+ `ensemble_ma_type`（`sma|ema`）
- **Regime Filter**：`use_regime_filter=true` + `regime_ma_window`（默认 `200`）
  - 可选 ADX：`use_adx_filter=true`（需要同时开启 `use_regime_filter=true`）+ `adx_window` + `adx_threshold`
- **Volatility Targeting（年化输入）**：`use_vol_targeting=true` + `target_vol_annual`（例如 `0.15`）+ `trading_days_per_year`（默认 `252`）+ `vol_window` + `max_leverage` + `min_vol_floor`
- **Exits**：`use_chandelier_stop=true` + `chandelier_k`；`use_vol_stop=true` + `vol_stop_atr_mult`

`/api/signals/` 同样支持 `include_meta` / `force_refresh`（`meta.data_meta` 中包含数据状态）

自动刷新规则：**仅当请求的日期区间不被本地 CSV 覆盖时才会触发刷新**。

自动刷新响应头（仅 `include_meta=true` 时添加）：

- `X-Data-Status`：`up_to_date` 或 `stale`
- `X-Data-Range`：`min_date,max_date`
- `X-Data-Last-Updated`：CSV 最后修改时间（UTC ISO）
- `X-Data-Refresh`：`updated` / `failed` / `skipped`
- `X-Data-Refresh-Reason`：刷新原因或失败提示

## CSV 数据约定（MVP）

- 数据目录：`DATA_DIR`（默认 `./data`）
- 文件命名：优先匹配 `data/<CODE>.csv`，其次匹配 `data/<CODE>_3y.csv`（例如 `data/AAPL_3y.csv`）
- 必需字段：`date,open,high,low,close,volume`（列名大小写不敏感）

## 离线数据准备：批量下载（yfinance → CSV）

使用 Django management command 批量下载 **日线 OHLCV（adjusted）** 并写入 `DATA_DIR`（默认 `./data`）：

```bash
# period 模式（默认 3y）：输出如 data/AAPL_3y.csv
python3 manage.py yfinance_batch_csv --symbols AAPL MSFT --period 3y

# date-range 模式：输出如 data/AAPL_2015-01-01_2025-12-31.csv
python3 manage.py yfinance_batch_csv --symbols AAPL --start-date 2015-01-01 --end-date 2025-12-31

# 已存在文件默认跳过；使用 --force 覆盖（原子替换）
python3 manage.py yfinance_batch_csv --symbols AAPL --force
```

### 示例请求

获取行情数据（示例参数）：

```bash
curl "http://127.0.0.1:8000/api/stock-data/?code=AAPL&short_window=5&long_window=20&include_meta=true" \
  -H "Content-Type: application/json"
```

获取带高级模式回测（示例参数）：

```bash
curl "http://127.0.0.1:8000/api/stock-data/?code=AAPL&include_performance=true&use_ensemble=true&ensemble_pairs=5:20,10:50,20:100,50:200&use_regime_filter=true&regime_ma_window=200&use_vol_targeting=true&target_vol_annual=0.15&trading_days_per_year=252&vol_window=14" \
  -H "Content-Type: application/json"
```

## 测试

```bash
pytest
```

> 若你新增了 pytest-django 配置，通常需要设置 `DJANGO_SETTINGS_MODULE=config.settings` 或添加 `pytest.ini`。

更完整的启动与测试步骤见：`STARTUP_AND_TESTING.md`。

## 更多说明

- 更完整的启动与测试步骤见：`STARTUP_AND_TESTING.md`
- 后续扩展（DB/Redis/更多指标）见：`TODO.md`
