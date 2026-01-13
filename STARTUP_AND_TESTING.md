# 启动与测试说明（dma-strategy-backend）

本文档用于在本地 Conda 环境中启动后端，并验证两个 MVP 接口（从 `data/` CSV 读取数据并计算均线/信号）。

## 1. 启动

### 1.1 进入 Conda 环境

按你的本地配置初始化 shell 并激活环境（示例环境名：`django-5`）：

```bash
source ~/.bash_profile
conda activate django-5
```

> 如果你的配置在 `~/.bach_profile` / `~/.zshrc` / `~/.zprofile`，请替换为对应文件。

#### 在非交互环境里运行（Codex/脚本更稳）

有些非交互 shell 下 `conda activate` 不会生效（例如工具执行的单条命令）。这时推荐用 `conda run`：

```bash
source ~/.bash_profile
conda run -n django-5 python manage.py runserver
conda run -n django-5 pytest
```

> 如果你的环境名是 `django5` 或其他名字，把 `-n django-5` 改成你的实际环境名即可。

### 1.2 安装依赖

```bash
pip install -r requirements.txt
```

### 1.3 配置 `.env`

项目会在 `config/settings.py` 中自动 `load_dotenv()` 读取 `.env`。

MVP 必需项：

- `DATA_DIR=./data`（默认也是 `./data`，但建议显式写上）

示例：

```dotenv
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATA_DIR=./data
LOG_LEVEL=INFO
```

### 1.4 初始化并启动

```bash
python3 manage.py migrate
python3 manage.py runserver
```

启动后默认地址：`http://127.0.0.1:8000/`

## 2. 手工测试（接口联调）

### 2.0 `GET /api/codes/`（下拉代码）

```bash
curl "http://127.0.0.1:8000/api/codes/"
```

预期：

- HTTP 200
- 返回 JSON 数组：`[{ "code": "AAPL", "label": "AAPL", "file": "AAPL_3y.csv" }, ...]`

### 2.1 数据文件检查

仓库自带样例文件位于 `data/`，例如：

- `data/AAPL_3y.csv`
- `data/MSFT_3y.csv`

接口参数 `code=AAPL` 会自动匹配 `data/AAPL_3y.csv`（也支持 `data/AAPL.csv`）。

### 2.2 `GET /api/stock-data/`（行情 + 均线）

```bash
curl "http://127.0.0.1:8000/api/stock-data/?code=AAPL&short_window=5&long_window=20"
```

预期：

- HTTP 200
- 返回 JSON 数组；每一项包含 `date/open/high/low/close/volume`，并附带 `ma_short/ma_long`（前若干行可能为 `null`，因为均线需要窗口期）

可选参数：

- `start_date=YYYY-MM-DD`
- `end_date=YYYY-MM-DD`
- `short_window`（默认 5）
- `long_window`（默认 20）

### 2.3 `GET /api/signals/`（交易信号）

```bash
curl "http://127.0.0.1:8000/api/signals/?code=AAPL&short_window=5&long_window=20"
```

预期：

- HTTP 200
- 返回 JSON 对象：`{ data: [...], meta: {...} }`
  - `data` 为信号数组，每一项形如：`date/signal_type/price/ma_short/ma_long`
  - `meta` 包含 `generated_count`（生成信号数）与 `returned_count`（过滤后返回数）

可选参数（信号生成 / gen_*）：

- `gen_confirm_bars`：交叉后确认 N 根K线（默认 0；信号日期为确认完成那天）
- `gen_min_cross_gap`：同类型信号之间至少间隔 N 根K线（默认 0）

可选参数（仅影响返回 / filter_*）：

- `filter_signal_type=all|BUY|SELL`（默认 all）
- `filter_sort=asc|desc`（默认 desc）
- `filter_limit=N`（可选）

### 2.4 常见错误用例（用于验证校验/返回码）

- 文件不存在（404）：
  - `curl "http://127.0.0.1:8000/api/stock-data/?code=NOT_EXIST"`
- 参数不合法（400）：
  - `short_window >= long_window`
  - `start_date > end_date`
  - `code` 含非法字符（只允许字母/数字/`.`/`_`/`-`）

## 2.5 离线数据准备（批量下载）

项目提供批量下载命令（yfinance → 标准 CSV），写入 `DATA_DIR`（默认 `./data`）。

为避免同一标的产生多个 CSV 文件导致回测读取歧义，下载命令采用 **canonical 文件命名**：统一写入 `data/<CODE>.csv`（例如 `data/AAPL.csv`），并每次 **全量覆盖**（原子替换）。

```bash
# 下载从 canonical-start（默认 2010-01-01）到最新可得，输出如 data/AAPL.csv
python3 manage.py yfinance_batch_csv --symbols AAPL MSFT

# 指定 canonical-start（例如从 2015-01-01 开始），输出仍为 data/AAPL.csv
python3 manage.py yfinance_batch_csv --symbols AAPL --canonical-start 2015-01-01

# 可选指定结束日期（例如固定到 2025-12-31），输出仍为 data/AAPL.csv
python3 manage.py yfinance_batch_csv --symbols AAPL --canonical-start 2010-01-01 --end-date 2025-12-31
```

## 2.6 离线回测评估（IS/OOS + ablation + grid search）

运行回测评估命令会把产物写到 `results/backtesting/<run_id>/`，核心汇总表为 `summary.csv`：

参数与最佳实践见：`docs/backtesting.md`。
回测指标口径说明见：`docs/backtest-metrics.md`。

```bash
# 默认 IS=2015-01-01..2020-12-31, OOS=2021-01-01..latest
python3 manage.py backtesting --symbols AAPL MSFT

# 启用网格搜索（只用 IS 选参，OOS 锁参评估）
python3 manage.py backtesting --symbols AAPL --grid-search --search-metric sharpe
```

注意：

- 如果你本地 CSV 的覆盖区间不足（例如数据起始日期晚于默认 IS 结束 `2020-12-31`），`backtesting` 会直接失败，并提示 CSV 覆盖区间与下一步操作。
- 解决方式：下载更长历史（推荐）或显式传参调整拆分窗口（`--is-start/--is-end/--oos-start/--oos-end`）。
- 如需只跑 OOS 或只跑 IS，可分别使用 `--allow-empty-is` / `--allow-empty-oos`（默认关闭）。

## 3. 自动化测试（pytest）

### 3.1 运行全部测试

```bash
pytest
```

### 3.2 只跑 services 相关测试

```bash
pytest strategy_engine/tests/test_services.py
```

说明：

- 测试配置在 `pytest.ini`，已设置 `DJANGO_SETTINGS_MODULE=config.settings`
- 当前测试重点覆盖 CSV 读取、均线计算、信号生成的基础行为
