# 回测指标说明文档 (Backtesting Metrics)

本文档旨在定义 `backtesting` 命令产出物（尤其是 `results/backtesting/<run_id>/summary.csv`）中核心指标的计算逻辑、数学公式及业务含义。

所有计算逻辑均与 `strategy_engine/backtest_metrics.py` 的代码实现保持一致。

## 1. 数据源与预处理

指标计算主要基于策略引擎产出的三类核心数据结构：

| 数据源 | 关键字段 | 用途 |
| :--- | :--- | :--- |
| **Daily Records** | `date`, `value` (净值), `equity`, `exposure` | 计算 CAGR, Sharpe, MDD, Avg Exposure |
| **Fills** | `date`, `notional` (成交额) | 计算 Turnover (换手率) |
| **Closed Trades** | `exit_date`, `pnl` (盈亏额) | 计算 Win Rate, P/L Ratio |

### 分段 (Segmentation) 规则
* **IS (样本内) / OOS (样本外)**：严格基于日期进行切片。
* **闭区间原则**：`start <= date <= end`。若 `end` 为 `None`，则包含 `start` 之后所有数据。
* **年化基准**：默认 `trading_days_per_year = 252` (可通过命令行参数覆盖)。

---

## 2. 核心绩效指标 (Performance Metrics)

### CAGR (年化复合增长率)

* **含义**：描述策略资产在特定时间跨度内的几何平均增长率。它平滑了期间的波动，只关注起点和终点。
* **公式**：
  $$
  \text{CAGR} = \left( \frac{\text{End Value}}{\text{Start Value}} \right)^{\frac{1}{\text{Years}}} - 1
  $$
  其中，年数的计算采用交易日近似法：
  $$
  \text{Years} = \frac{\text{Total Bars} - 1}{\text{Trading Days Per Year}}
  $$
* **解读**：衡量策略的**长期盈利能力**。
* **异常处理**：若数据不足 2 条 (`bars < 2`) 或起止净值为负，结果为 `NaN`。

### MDD (最大回撤, Max Drawdown)

* **含义**：在历史上任何时点买入策略，可能遭受的最大本金损失比例。这是衡量**极端风险**的核心指标。
* **公式**：
  首先计算历史最高水位线 (Running Max)：
  $$
  \text{RunningMax}_t = \max(\text{Value}_0, \text{Value}_1, ..., \text{Value}_t)
  $$
  计算当前回撤：
  $$
  \text{Drawdown}_t = \frac{\text{Value}_t}{\text{RunningMax}_t} - 1
  $$
  最终取最大值（取绝对值）：
  $$
  \text{MDD} = \max(0, -\min(\text{Drawdown}_t))
  $$
* **解读**：**数值越小越好**。MDD > 20% 通常被视为高风险策略。
* **注意**：结果为正数（如 `0.20` 代表回撤 20%）。

### Sharpe Ratio (夏普比率)

* **含义**：衡量策略的**性价比**——每承担一单位总风险（波动率），能获得多少超额收益。
* **公式**：
  $$
  \text{Sharpe} = \frac{\bar{R}_p}{\sigma_p} \times \sqrt{252}
  $$
  * $\bar{R}_p$: 周期（如日）收益率的均值
  * $\sigma_p$: 周期收益率的**样本标准差** (Sample Std Dev, `ddof=1`)
  * $\sqrt{252}$: 年化系数
* **解读**：**数值越高越好**。
  * `> 1.0`: 合格
  * `> 2.0`: 优秀
  * `> 3.0`: 需警惕（可能是过拟合或统计幻觉）

### Calmar Ratio (卡玛比率)

* **含义**：年化收益与最大回撤之比。相比夏普比率，它更侧重于**防御属性下的盈利能力**。
* **公式**：
  $$
  \text{Calmar} = \frac{\text{CAGR}}{\text{MDD}}
  $$
* **解读**：**数值越高越好**。对于 CTA/趋势策略，`Calmar > 2.0` 是稳健的分水岭。
* **异常处理**：若 MDD 为 0 或 CAGR/MDD 为 NaN，返回 `NaN`。

### Turnover (换手率 - Proxy)

* **含义**：资金的周转强度。侧面反映**交易成本**消耗和**策略活跃度**。
* **公式**：
  $$
  \text{Turnover} = \frac{\sum |\text{Fill Notional}|}{\text{Mean Equity}}
  $$
* **解读**：
  * **数值**：`20.0` 代表一年内资金被彻底轮换了 20 遍。
  * **警示**：换手率越高，滑点和手续费对净值的侵蚀越严重。
* **注意**：采用**双边计算**（买入+卖出均取绝对值累加）。

### Avg Exposure (平均仓位)

* **含义**：策略在市场中的平均风险暴露程度。
* **计算**：`daily.exposure` 字段的算术平均值。
* **解读**：`1.0` 代表满仓，`0.0` 代表空仓。该指标低说明资金利用率不高。

---

## 3. 交易统计指标 (Trade Metrics)

此类指标仅基于 **已平仓 (Closed)** 的完整交易计算。

### Win Rate (胜率)

* **含义**：盈利交易次数占总交易次数的比例。
* **公式**：
  $$
  \text{Win Rate} = \frac{\text{Count}(\text{PnL} > 0)}{\text{Total Trades}}
  $$
* **解读**：趋势跟踪策略通常胜率较低 (30%-45%)，需结合盈亏比观看。

### P/L Ratio (盈亏比)

* **含义**：平均赚一次的钱，够亏几次。也称为赔率。
* **公式**：
  $$
  \text{P/L Ratio} = \frac{\text{Avg Win}}{\text{Avg Loss}} = \frac{\text{Mean}(\text{PnL} > 0)}{|\text{Mean}(\text{PnL} < 0)|}
  $$
* **解读**：
  * 低胜率策略必须拥有高盈亏比（通常 > 2.0）才能盈利。
  * 若分段内没有盈利单或没有亏损单，返回 `NaN`。

---

## 4. 常见异常值 (NaN) 说明

在 `summary.csv` 中遇到 `NaN` 通常由以下原因导致，属于正常的数据清洗结果：

1.  **数据不足 (Insufficient Data)**：
    * 分段内 `bars < 2`：无法计算标准差，导致 `Sharpe` 为 NaN。
    * 起始或结束净值 <= 0：导致 `CAGR` 无法计算。
2.  **无交易 (No Trades)**：
    * 分段内无平仓记录：`win_rate` 和 `pl_ratio` 为 NaN。
    * 分段内无成交记录：`turnover` 为 0.0。
3.  **全胜或全负 (All Wins/Losses)**：
    * 只有盈利单或只有亏损单：导致 `pl_ratio` 的分子或分母缺失。
4.  **账户异常 (Invalid Equity)**：
    * 平均净值 <= 0（爆仓）：导致 `turnover` 为 NaN。
