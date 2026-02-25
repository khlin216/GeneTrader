"""
Adaptive optimization module for on-the-fly strategy optimization.

This module provides the core adaptive optimization system that:
- Monitors live trading performance
- Detects strategy degradation
- Triggers re-optimization when needed
- Deploys optimized strategies safely

Components:
- WeightedDataOptimizer: Optimization with recent data weighting
- AdaptiveOptimizer: Main orchestrator for the adaptive system
- OptimizationScheduler: Scheduling and rate limiting for optimizations
"""

from adaptive.weighted_optimizer import WeightedDataOptimizer, OptimizationResult
from adaptive.adaptive_optimizer import AdaptiveOptimizer, AdaptiveState
from adaptive.scheduler import OptimizationScheduler, ScheduleConfig

__all__ = [
    'WeightedDataOptimizer',
    'OptimizationResult',
    'AdaptiveOptimizer',
    'AdaptiveState',
    'OptimizationScheduler',
    'ScheduleConfig',
]
