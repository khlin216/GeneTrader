# GeneTrader 项目战略分析报告

> 日期: 2026-02-26
> 分析范围: 全项目代码审查 + 策略优化建议

---

## 1. 选什么策略优化

### 当前策略: GeneStrategy

项目核心策略文件 `strategies/GeneStrategy.py` 是一个综合性多信号入场策略，包含以下子模块：

| 子策略模块 | 技术指标 | 特点 |
|-----------|---------|------|
| **NFINext44** | EMA offset + EWO + CTI + Williams%R 1h | 趋势回调入场 |
| **NFINext37** | EMA offset + EWO + RSI + CTI | 动量确认入场 |
| **NFINext7** | EMA open mult + CTI | 开盘价偏差入场 |
| **ClucHA** | BB delta + Heikin-Ashi | 波动率收窄入场 |
| **Local Uptrend** | EMA diff + BB factor | 局部上升趋势入场 |
| **SMAOffset** | SMA + low/high offset | 均线偏移入场/出场 |
| **Deadfish** | BB width + volume factor | 低活跃度止损退出 |

### 优化建议

- 可优化参数约 **30+ 个**（IntParameter + DecimalParameter），搜索空间很大
- **建议优先用 Optuna** (`optimizer_type: "optuna"`) — 对 30+ 参数的高维搜索空间，TPE 比 GA 收敛更快
- 不建议从零写新策略，应在 GeneStrategy 基础上优化
- 通过 `fix_pairs: false` 同时优化交易对选择

---

## 2. 选什么代币

### 当前选币机制

`scripts/get_pairs.py` 支持两种模式：
- `--mode all`: 所有 Binance USDT 交易对
- `--mode volume`: 按交易量排名前 N 个（默认 100）

### 推荐选币策略

**初始优化阶段用 30 个高流动性代币：**
```bash
python scripts/get_pairs.py --mode volume --top-n 30
```

**让 GA 自动选择最优子集：**
```json
{
  "fix_pairs": false,
  "num_pairs": 8
}
```

**币种类型建议：**
- 大盘币：BTC, ETH, SOL（稳定性好）
- 中盘高波动：DOGE, PEPE, AVAX, LINK, SUI, NEAR（机会多）
- 避免山寨小币（流动性差，退市风险）

**维护黑名单：**
- 定期更新 `data/delisted_coins.json`
- 运行 `--check-delistings` 检查退市公告

---

## 3. 如何更好的优化

### 推荐配置

```json
{
  "enable_walk_forward": true,
  "walk_forward_method": "rolling",
  "walk_forward_train_weeks": 26,
  "walk_forward_test_weeks": 4,
  "total_data_weeks": 52,
  "max_drawdown_limit": 0.25,
  "min_profit_factor": 1.2,
  "min_win_rate": 0.40,
  "enable_diversity_selection": true,
  "diversity_selection_weight": 0.3
}
```

### Fitness 函数权重调优建议

当前 (`strategy/evaluation.py`):
- 利润 25% + 风险调整 25% + 回撤 15% + 胜率 10% + 频率 10% + 统计 10% + 时间 5%

建议:
- 增大 **风险调整收益** 到 30%（Sharpe/Sortino 对实盘最重要）
- 增大 **回撤惩罚** 到 20%
- 降低 **利润** 到 20%（过分追求利润易过拟合）

### 优化流程

1. Optuna 粗搜索（500 trials）
2. GA 精细搜索（在 Optuna 最优解附近）
3. Walk-Forward 验证
4. Monte Carlo robustness 测试
5. robustness_score >= 0.7 才考虑上线

---

## 4. 如何实盘去跑

### 步骤

1. **准备 Freqtrade** — 配置交易所 API Key
2. **部署策略** — 优化结果在 `bestgenerations/`
3. **启动自适应守护进程**:
   ```bash
   python run_adaptive.py --strategy GeneStrategy --api-port 8090
   ```
4. **配置安全参数**:
   ```json
   {
     "shadow_trading_hours": 24,
     "gradual_rollout_enabled": true,
     "auto_rollback_enabled": true,
     "rollback_drawdown_threshold": 0.15,
     "agent_approval_required_for_deployment": true
   }
   ```

### 安全建议

- 初始资金不超过总资产的 10%
- `max_open_trades` 设为 3-5
- 确保 `auto_rollback_enabled: true`
- 前两周密切监控

---

## 5. 如何更好的和智能体结合

### 推荐架构

```
Claude Agent
    ↓ 定期查询 /api/v1/metrics
    ↓ 分析表现 + 结合市场情报
    ↓ 决定是否优化 /api/v1/optimization/trigger
    ↓ 审核新策略 /api/v1/deployment/approve
    ↓ 监控部署 /api/v1/status
```

### Claude 比纯统计的优势

1. **理解上下文**: 结合市场事件判断退化原因
2. **跨策略分析**: 多策略组合管理
3. **自然语言解释**: 可读的分析报告

### 进一步增强

1. 加入市场情报（恐惧贪婪指数、新闻等）
2. 多策略调度 — 根据市场 regime 动态分配权重
3. 自动化报告 — 通过 Bark 推送每日/每周报告
4. 闭环学习 — 记录决策结果用于改进

---

## 总结

GeneTrader 架构完整、工程质量高。核心竞争力：
- GA + Optuna 双优化引擎
- 完善的防过拟合体系
- 生产级安全部署流水线
- 原生 AI Agent 集成

最大改进空间在实践层面：选好币、调好权重、充分验证、小资金先跑。
