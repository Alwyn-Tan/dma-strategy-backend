# `backtesting` 参数说明与最佳实践

本文档用于说明 Django management command：`python manage.py backtesting ...` 的所有参数含义、默认值、以及推荐用法。

另见：

- 指标口径说明：`docs/backtest-metrics.md`

## 1. 作用与产物

`backtesting` 会对一组标的（`--symbols`）按 **IS/OOS 固定拆分**（可通过参数调整）跑回测，并输出产物到：

- `results/backtesting/<run_id>/config.json`：本次运行配置（拆分、网格、成本等）
- `results/backtesting/<run_id>/summary.csv`：每个 symbol × variant 的 IS/OOS 指标汇总
- `results/backtesting/<run_id>/series/*.csv`：逐日净值/权益曲线等（来自回测 `details["daily"]`）
- `results/backtesting/<run_id>/fills/*.csv`：成交明细（来自回测 `details["fills"]`）
- `results/backtesting/<run_id>/trades/*.csv`：已平仓交易（来自回测 `details["closed_trades"]`）
- `results/backtesting/<run_id>/grid/*.csv`：网格搜索明细（仅 `--grid-search` 时输出）

说明：

- 为提升可读性，`summary.csv` 与 `grid/*.csv` 中的数值会在写出前按字段做统一 round（仍以数值写出，不会转成字符串）。
- 这不会影响策略计算与网格搜索选参（内部计算使用全精度）。

## 2. 数据准备（强烈推荐）

本项目数据下载采用 **canonical 单文件命名**：同一标的统一写入 `data/<CODE>.csv`，避免多个 CSV 造成回测读取歧义。

```bash
# 默认从 2010-01-01 下载到最新，写入 data/AAPL.csv（每次覆盖）
python manage.py yfinance_batch_csv --symbols AAPL

# 自定义起始日期（仍写入 data/AAPL.csv）
python manage.py yfinance_batch_csv --symbols AAPL --canonical-start 2015-01-01
```

如果本地 CSV 覆盖区间不足，`backtesting` 默认会 **直接失败（fail-fast）**，并在错误信息里提示 CSV 覆盖区间与下一步操作。

## 3. 快速开始

```bash
# 最小运行（默认 IS=2015-01-01..2020-12-31，OOS=2021-01-01..latest）
python manage.py backtesting --symbols AAPL

# 多标的
python manage.py backtesting --symbols AAPL MSFT SPY

# 指定输出目录与 run_id
python manage.py backtesting --symbols AAPL --run-id my-run --output-dir results/backtesting
```

## 4. 参数说明（按类别）

### 4.1 必填

#### `--symbols`

- 含义：标的列表（空格分隔）
- 示例：`--symbols AAPL MSFT 00700.HK`

### 4.2 输出与数据目录

#### `--run-id`

- 含义：本次运行标识
- 默认：UTC 时间戳（如 `20260112-084153Z`）

#### `--output-dir`

- 含义：结果输出根目录
- 默认：`results/backtesting`

#### `--data-dir`

- 含义：本地 CSV 数据目录（覆盖 `settings.DATA_DIR`）
- 默认：`settings.DATA_DIR`（通常是 `./data`）

### 4.3 IS/OOS 拆分（日期）

#### `--is-start` / `--is-end`

- 含义：样本内（IS）区间
- 默认：`2015-01-01` .. `2020-12-31`

#### `--oos-start` / `--oos-end`

- 含义：样本外（OOS）区间
- 默认：`2021-01-01` .. `None`（表示一直跑到 CSV 最晚日期）

约束：

- 必须满足 `is_start <= is_end`
- 若提供 `oos_end`，必须满足 `oos_start <= oos_end`
- **IS/OOS 必须不重叠**：要求 `is_end < oos_start`

#### `--allow-empty-is` / `--allow-empty-oos`

默认情况下，IS 或 OOS 任一分段若没有 bars（例如数据覆盖不足），命令会直接失败。

- `--allow-empty-is`：允许 IS 段为空（用于“只跑 OOS”）；IS 指标会是 `bars=0`、其余大多为 `NaN`
- `--allow-empty-oos`：允许 OOS 段为空（用于“只跑 IS”）

注意：

- 启用 `--grid-search` 时 **必须** 有 IS bars（即使传了 `--allow-empty-is` 也会报错）

### 4.4 Variants（策略变体）

#### `--variants`

- 含义：逗号分隔的 variant id 列表
- 默认：`dma_baseline,advanced_full,advanced_no_vol_targeting`
- 示例：`--variants dma_baseline,advanced_full`

### 4.5 网格搜索（IS 选参）

当启用网格搜索时，会在 IS 区间上搜索最优参数，并将选出的参数锁定用于 OOS 评估（符合“只用 IS 选参”的隔离规则）。

工作流程（按 symbol × variant）：

1) 对每组候选窗口 `(short_window, long_window)`（仅评估 `short < long`）运行一次完整回测
2) 对回测产物按日期切片，仅用 IS 分段计算指标（见 `docs/backtest-metrics.md`）
3) 使用 `--search-metric` 指定的指标作为目标函数，选择得分最高的参数组合
4) 用该参数组合对应的回测产物写入 `series/`、`fills/`、`trades/`，并输出 IS/OOS 汇总到 `summary.csv`

目标函数规则：

- `--search-metric` 支持 `sharpe` / `calmar` / `cagr`
- 若该指标为 `NaN`（例如 IS bars 太少导致无法计算），该组合视为无效（记为 `-inf`）
- 同分（完全相等）时不会替换当前最优（实现是严格 `>` 比较），通常等价于“保留先出现的组合”

输出文件：

- `results/backtesting/<run_id>/grid/<CODE>__<variant>__grid.csv`：每个候选组合一行，包含 `bars/cagr/mdd/sharpe/calmar`
- `results/backtesting/<run_id>/summary.csv`：只记录最终选中的 `(short_window,long_window)` 对应的一行汇总（每个 variant 一行）

重要说明：

- **未启用** `--grid-search` 时，默认参数为 `short_window=5`、`long_window=20`
- 启用 `--grid-search` 时，若所有候选组合都无有效目标分数（例如全部为 `NaN`），会回退到默认参数

规模与耗时粗估：

- 每个 symbol × variant 的回测次数约为：`len(short_grid) * len(long_grid) - invalid_pairs`
- 总回测次数约为：`symbols * variants * combos`

#### `--grid-search`

- 含义：启用网格搜索
- 默认：关闭

#### `--short-grid` / `--long-grid`

- 含义：短/长均线窗口候选（逗号分隔整数）
- 默认：`--short-grid 5,10,20`；`--long-grid 20,50,100,200`
- 约束：仅评估 `short < long`

#### `--search-metric`

- 含义：网格搜索在 IS 上的目标指标
- 可选：`sharpe` / `calmar` / `cagr`
- 默认：`sharpe`

示例：

```bash
# 用 IS Sharpe 选参（默认）
python manage.py backtesting --symbols AAPL --grid-search

# 自定义网格与目标指标
python manage.py backtesting --symbols AAPL --grid-search \
  --short-grid 5,10,20,50 --long-grid 50,100,200 \
  --search-metric calmar
```

### 4.6 成本与交易假设

#### `--fee-rate`

- 含义：手续费率（小数）
- 默认：`0.001`（即 0.1%）

#### `--slippage-rate`

- 含义：滑点率（小数）
- 默认：`0.0005`（即 0.05%）

#### `--confirm-bars`

- 含义：信号确认 bars（用于减少噪声的确认延迟）
- 默认：`0`

#### `--min-cross-gap`

- 含义：同方向信号的最小间隔 bars
- 默认：`0`

### 4.7 年化与波动率目标（advanced variants）

#### `--trading-days-per-year`

- 含义：年化基准（Sharpe/CAGR/Calmar 年化使用）
- 默认：`252`

#### `--vol-window`

- 含义：波动率/ATR 等窗口（用于波动率目标/止损模块）
- 默认：`14`

#### `--target-vol-annual` / `--target-vol`

- 含义：目标波动率
- 默认：`--target-vol-annual 0.15`
- 说明：
  - `target-vol-annual` 为年化目标波动率（推荐）
  - `target-vol` 为日频目标波动率（legacy）
  - 两者同时提供时，以 `target-vol-annual` 为主

#### `--max-leverage`

- 含义：最大杠杆上限
- 默认：`1.0`

#### `--min-vol-floor`

- 含义：波动率下限（避免除以 0）
- 默认：`1e-6`

### 4.8 Regime / ADX 过滤（advanced variants）

#### `--regime-ma-window`

- 含义：regime filter 的均线窗口（如 MA200）
- 默认：`200`

#### `--adx-window` / `--adx-threshold`

- 含义：ADX 过滤参数
- 默认：`14` / `20.0`

### 4.9 Ensemble 参数（advanced variants）

#### `--ensemble-pairs`

- 含义：多组均线对（短:长），逗号分隔
- 默认：`5:20,10:50,20:100,50:200`
- 约束：每对都需满足 `short < long`

#### `--ensemble-ma-type`

- 含义：ensemble 使用的 MA 类型
- 可选：`sma` / `ema`
- 默认：`sma`

### 4.10 出场模块（exits）

#### `--use-exits`

- 含义：在 advanced variants 中启用出场模块（如 chandelier stop / vol stop）
- 默认：关闭

#### `--chandelier-k`

- 含义：Chandelier stop 的倍数参数
- 默认：`3.0`

#### `--vol-stop-atr-mult`

- 含义：波动止损的 ATR 倍数
- 默认：`2.0`

## 5. 最佳实践（推荐流程）

1) **先保证数据覆盖**：对要跑的标的先执行 `yfinance_batch_csv --canonical-start 2010-01-01`，确保能覆盖默认 IS/OOS。

```bash
python manage.py yfinance_batch_csv --symbols AAPL --canonical-start 2010-01-01
```

2) **从单标的开始**：先跑下面这组命令，确认 `summary.csv`、`series/`、`trades/` 都正常，再扩展到多标的。

```bash
python manage.py backtesting --symbols AAPL
```

3) **默认保持严格 fail-fast**：除非你明确要“只跑 IS”或“只跑 OOS”，不要使用 `--allow-empty-is/--allow-empty-oos`。

4) **网格搜索循序渐进**：先用小网格验证正确性与速度，再扩大网格范围与目标指标。

```bash
python manage.py backtesting --symbols AAPL --grid-search \
  --short-grid 5,10,20,50 --long-grid 50,100,200 \
  --search-metric calmar
```

5) **成本先从 0 调试**：如果你在验证信号/逻辑，建议先用 `--fee-rate 0 --slippage-rate 0`，确认策略行为后再恢复真实成本。

6) **指标解释以文档为准**：`summary.csv` 中各指标的定义/NaN 规则见 `docs/backtest-metrics.md`。

## 6. 常见报错与排查

- `IS segment has zero bars ... (CSV range ...)`：
  - 你的 CSV 起始日期晚于 IS 结束日期；先下载更长历史或调整 `--is-start/--is-end`
- `IS and OOS must be disjoint`：
  - 需要满足 `is_end < oos_start`
- `grid search requires IS data`：
  - 网格搜索必须有 IS bars；请补齐 IS 覆盖或关闭 `--grid-search`
