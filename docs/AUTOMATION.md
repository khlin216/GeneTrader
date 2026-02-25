# GeneTrader 自动化部署指南

本文档介绍如何设置 GeneTrader On-the-Fly 优化系统的自动化运行。

## 概述

On-the-Fly 优化系统可以:
- **自动监控** 实时交易性能
- **智能检测** 策略退化 (使用 SPC/CUSUM 统计方法)
- **自动优化** 当检测到退化时触发重新优化
- **安全部署** 通过影子交易验证和自动回滚机制

## 部署方式

### 方式一: Systemd 服务 (推荐)

适用于 Linux 服务器,提供最稳定的后台运行方式。

#### 安装

```bash
# 基本安装
sudo ./scripts/install_daemon.sh --strategy GeneTrader

# 自定义配置
sudo ./scripts/install_daemon.sh \
    --strategy GeneTrader \
    --config /path/to/ga.json \
    --optimize-interval 72 \
    --check-interval 5
```

#### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--strategy` | GeneTrader | 策略名称 |
| `--config` | ga.json | 配置文件路径 |
| `--optimize-interval` | 72 | 优化间隔 (小时) |
| `--check-interval` | 5 | 性能检查间隔 (分钟) |

#### 管理服务

```bash
# 启动服务
sudo systemctl start genetrader

# 停止服务
sudo systemctl stop genetrader

# 重启服务
sudo systemctl restart genetrader

# 查看状态
sudo systemctl status genetrader

# 设置开机自启
sudo systemctl enable genetrader

# 禁用开机自启
sudo systemctl disable genetrader
```

#### 查看日志

```bash
# 实时查看日志
sudo journalctl -u genetrader -f

# 查看最近100行日志
sudo journalctl -u genetrader -n 100

# 查看今天的日志
sudo journalctl -u genetrader --since today
```

---

### 方式二: Cron 定时任务

适用于不支持 systemd 的系统或者偏好 cron 的用户。

#### 安装

```bash
# 基本安装
./scripts/setup_cron.sh --strategy GeneTrader

# 自定义配置
./scripts/setup_cron.sh \
    --strategy GeneTrader \
    --config /path/to/ga.json \
    --check-interval 5 \
    --optimize-interval 72
```

#### 生成的定时任务

| 任务 | 频率 | 说明 |
|------|------|------|
| 性能检查 | 每5分钟 | 检查策略表现,检测退化 |
| 定期优化 | 每3天 | 触发策略重新优化 |
| 日常维护 | 每天凌晨2点 | 清理旧版本,整理数据库 |

#### 管理 Cron

```bash
# 查看当前用户的 cron 任务
crontab -l

# 编辑 cron 任务
crontab -e

# 查看日志
tail -f ~/genetrader/logs/cron_*.log
```

---

### 方式三: Docker 部署

适用于容器化环境,便于管理和迁移。

#### 前置要求

- Docker 20.10+
- Docker Compose 2.0+

#### 启动服务

```bash
# 启动所有服务 (后台运行)
docker-compose -f docker-compose.adaptive.yml up -d

# 查看运行状态
docker-compose -f docker-compose.adaptive.yml ps

# 查看日志
docker-compose -f docker-compose.adaptive.yml logs -f

# 停止服务
docker-compose -f docker-compose.adaptive.yml down
```

#### 服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| `genetrader-daemon` | - | 主守护进程 |
| `genetrader-api` | 8090 | Agent API 服务 |

#### 环境变量配置

在 `.env` 文件中配置:

```env
STRATEGY_NAME=GeneTrader
CHECK_INTERVAL=300
OPTIMIZE_INTERVAL=259200
FREQTRADE_URL=http://freqtrade:8080
FREQTRADE_USERNAME=freqtrader
FREQTRADE_PASSWORD=your_password
BARK_URL=https://api.day.app/your_key
```

---

### 方式四: 直接运行守护进程

适用于开发测试或临时运行。

```bash
# 基本运行
python scripts/genetrader_daemon.py --strategy GeneTrader

# 完整参数
python scripts/genetrader_daemon.py \
    --config ga.json \
    --strategy GeneTrader \
    --check-interval 300 \
    --optimize-interval 259200 \
    --bark-url "https://api.day.app/your_key"

# 后台运行 (使用 nohup)
nohup python scripts/genetrader_daemon.py \
    --strategy GeneTrader \
    > ~/genetrader.log 2>&1 &

# 后台运行 (使用 screen)
screen -S genetrader
python scripts/genetrader_daemon.py --strategy GeneTrader
# 按 Ctrl+A, D 分离会话
```

#### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--config` | ga.json | 配置文件路径 |
| `--strategy` | GeneTrader | 策略名称 |
| `--check-interval` | 300 | 性能检查间隔 (秒) |
| `--optimize-interval` | 259200 | 优化间隔 (秒, 默认3天) |
| `--bark-url` | - | Bark 推送 URL |
| `--log-level` | INFO | 日志级别 |

---

## 配置文件

在 `ga.json` 中配置自适应优化参数:

```json
{
  "adaptive_optimization_enabled": true,
  "performance_check_interval_minutes": 5,
  "degradation_check_interval_minutes": 60,
  "reoptimization_trigger_threshold": 0.3,
  "minimum_trades_for_evaluation": 20,
  "minimum_days_between_optimizations": 3,
  "recent_data_weight": 0.7,
  "shadow_trading_hours": 24,
  "auto_rollback_enabled": true,
  "rollback_drawdown_threshold": 0.15,
  "agent_api_enabled": true,
  "agent_api_port": 8090,
  "agent_approval_required_for_deployment": true
}
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `adaptive_optimization_enabled` | true | 启用自适应优化 |
| `performance_check_interval_minutes` | 5 | 性能检查间隔 (分钟) |
| `degradation_check_interval_minutes` | 60 | 退化检测间隔 (分钟) |
| `reoptimization_trigger_threshold` | 0.3 | 退化分数阈值 (0-1) |
| `minimum_trades_for_evaluation` | 20 | 评估所需最小交易数 |
| `minimum_days_between_optimizations` | 3 | 两次优化最小间隔 (天) |
| `recent_data_weight` | 0.7 | 近期数据权重 |
| `shadow_trading_hours` | 24 | 影子交易验证时间 (小时) |
| `auto_rollback_enabled` | true | 启用自动回滚 |
| `rollback_drawdown_threshold` | 0.15 | 回滚触发回撤阈值 |

---

## Bark 通知

支持通过 [Bark](https://github.com/Finb/Bark) 发送 iOS 推送通知。

### 配置

1. 在 iPhone 上安装 Bark App
2. 获取推送 URL (格式: `https://api.day.app/YOUR_KEY`)
3. 配置到启动参数中

### 通知类型

| 事件 | 通知内容 |
|------|----------|
| 检测到退化 | 策略名称、退化分数、警报详情 |
| 开始优化 | 策略名称、触发原因 |
| 优化完成 | 新版本号、性能提升百分比 |
| 部署成功 | 新版本号、部署状态 |
| 自动回滚 | 原因、回滚到的版本 |
| 系统错误 | 错误信息 |

---

## 故障排除

### 服务无法启动

```bash
# 检查配置文件
python -c "import json; json.load(open('ga.json'))"

# 检查依赖
pip install -r requirements.txt

# 检查 Freqtrade 连接
curl http://localhost:8080/api/v1/ping
```

### 优化不触发

1. 检查交易数量是否达到 `minimum_trades_for_evaluation`
2. 检查距离上次优化是否超过 `minimum_days_between_optimizations`
3. 检查退化分数是否超过 `reoptimization_trigger_threshold`

```bash
# 手动检查状态
python run_adaptive.py --strategy GeneTrader --check-only
```

### 日志位置

| 部署方式 | 日志位置 |
|----------|----------|
| Systemd | `journalctl -u genetrader` |
| Cron | `~/genetrader/logs/` |
| Docker | `docker-compose logs` |
| 直接运行 | 控制台或指定文件 |

---

## 监控和 API

### Agent API

启动 API 服务后,可通过以下端点监控:

```bash
# 健康检查
curl http://localhost:8090/api/v1/health

# 系统状态
curl -H "X-API-Key: YOUR_KEY" http://localhost:8090/api/v1/status

# 性能指标
curl -H "X-API-Key: YOUR_KEY" "http://localhost:8090/api/v1/metrics?strategy=GeneTrader&hours=168"

# 优化状态
curl -H "X-API-Key: YOUR_KEY" http://localhost:8090/api/v1/optimization/status
```

### WebSocket 实时更新

```javascript
const ws = new WebSocket('ws://localhost:8090/ws?api_key=YOUR_KEY');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data.data);
};
```

---

## 安全建议

1. **API 密钥**: 使用强随机密钥,定期轮换
2. **网络隔离**: API 服务仅在内网开放
3. **权限控制**: 运行用户使用最小权限
4. **日志审计**: 定期检查操作日志
5. **备份策略**: 定期备份策略版本和数据库

---

## 更多资源

- [CLAUDE.md](../CLAUDE.md) - Claude Code 集成指南
- [OpenClaw 技能](../openclaw_skill/SKILL.md) - AI Agent 集成
- [配置示例](../ga.json.example) - 完整配置示例
