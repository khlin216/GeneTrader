---
name: genetrader
description: Monitor and control GeneTrader adaptive trading strategy optimization
user-invocable: true
metadata: { "requires": { "bins": ["python3"], "env": ["GENETRADER_PATH"] } }
---

# GeneTrader Skill

This skill allows you to monitor and control the GeneTrader adaptive optimization system.

## Capabilities

- Check live trading strategy performance
- Detect strategy degradation
- Trigger re-optimization when needed
- Approve or reject strategy deployments
- Rollback to previous strategy versions

## Commands

### Check Strategy Performance
```
/genetrader check [strategy_name]
```
Returns current performance metrics, degradation status, and recommendations.

### Get System Status
```
/genetrader status
```
Returns optimization system status, scheduler queue, and recent history.

### Force Optimization
```
/genetrader optimize [strategy_name]
```
Triggers an immediate re-optimization of the specified strategy.

### List Pending Approvals
```
/genetrader approvals
```
Shows pending deployment approvals waiting for your decision.

### Approve Deployment
```
/genetrader approve [request_id]
```
Approves a pending strategy deployment.

### Reject Deployment
```
/genetrader reject [request_id] [reason]
```
Rejects a pending strategy deployment with a reason.

### Rollback Strategy
```
/genetrader rollback [strategy_name] [version_id]
```
Rolls back to a previous strategy version.

## Configuration

Set these environment variables:
- `GENETRADER_PATH`: Path to GeneTrader installation (e.g., `/home/user/GeneTrader`)
- `GENETRADER_STRATEGY`: Default strategy name (optional)
- `GENETRADER_API_KEY`: API key for Agent API (if using API mode)
- `GENETRADER_API_URL`: Agent API URL (default: `http://localhost:8090`)

## Example Usage

User: "检查我的交易策略表现如何"
Agent: Runs `/genetrader check` and reports the results

User: "策略退化了，帮我重新优化"
Agent: Runs `/genetrader optimize` to trigger re-optimization

User: "有等待审批的新策略吗"
Agent: Runs `/genetrader approvals` to list pending deployments
