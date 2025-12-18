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

### 1.2 安装依赖

```bash
pip install -r requirements.txt
```

### 1.3 配置 `.env`

项目会在 `dma_strategy/settings.py` 中自动 `load_dotenv()` 读取 `.env`。

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
python manage.py migrate
python manage.py runserver
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

## 3. 自动化测试（pytest）

### 3.1 运行全部测试

```bash
pytest
```

### 3.2 只跑 services 相关测试

```bash
pytest stocks/tests/test_services.py
```

说明：

- 测试配置在 `pytest.ini`，已设置 `DJANGO_SETTINGS_MODULE=dma_strategy.settings`
- 当前测试重点覆盖 CSV 读取、均线计算、信号生成的基础行为
