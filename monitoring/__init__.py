"""
Monitoring module for on-the-fly optimization.

This module provides real-time performance monitoring, degradation detection,
and integration with live trading systems (Freqtrade).

Components:
- FreqtradeClient: REST API client for Freqtrade
- PerformanceMonitor: Real-time metrics tracking
- PerformanceDB: Time-series data storage
- DegradationDetector: Strategy degradation detection
"""

from monitoring.freqtrade_client import FreqtradeClient
from monitoring.performance_monitor import PerformanceMonitor, PerformanceMetrics
from monitoring.performance_db import PerformanceDB
from monitoring.degradation_detector import DegradationDetector, DegradationAlert

__all__ = [
    'FreqtradeClient',
    'PerformanceMonitor',
    'PerformanceMetrics',
    'PerformanceDB',
    'DegradationDetector',
    'DegradationAlert',
]
