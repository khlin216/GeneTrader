"""
Deployment module for safe strategy deployment.

This module provides tools for safely deploying optimized strategies
to live trading, including version control, shadow trading validation,
gradual rollout, and automatic rollback.

Components:
- StrategyVersionControl: Version management for strategies
- StrategyDeployer: Safe deployment with validation
- ShadowTrader: Paper trading validation before live deployment
- RollbackManager: Automatic rollback on performance degradation
"""

from deployment.version_control import StrategyVersionControl, StrategyVersion
from deployment.strategy_deployer import StrategyDeployer, DeploymentStatus
from deployment.shadow_trader import ShadowTrader, ShadowTradeResult
from deployment.rollback_manager import RollbackManager, RollbackEvent

__all__ = [
    'StrategyVersionControl',
    'StrategyVersion',
    'StrategyDeployer',
    'DeploymentStatus',
    'ShadowTrader',
    'ShadowTradeResult',
    'RollbackManager',
    'RollbackEvent',
]
