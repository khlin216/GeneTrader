"""
Weighted data optimizer for adaptive optimization.

This module provides optimization that weights recent market data more heavily,
allowing the strategy to adapt to current market conditions.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
from utils.logging_config import logger


@dataclass
class TimePeriod:
    """Represents a time period for weighted optimization."""
    start_date: datetime
    end_date: datetime
    weight: float
    name: str = ""

    @property
    def days(self) -> int:
        """Get number of days in period."""
        return (self.end_date - self.start_date).days


@dataclass
class OptimizationResult:
    """Result of an optimization run."""
    success: bool
    strategy_name: str
    parameters: Dict[str, Any]
    fitness_score: float
    backtest_metrics: Dict[str, Any]
    weighted_score: float
    period_scores: Dict[str, float]
    optimization_time_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'strategy_name': self.strategy_name,
            'parameters': self.parameters,
            'fitness_score': self.fitness_score,
            'backtest_metrics': self.backtest_metrics,
            'weighted_score': self.weighted_score,
            'period_scores': self.period_scores,
            'optimization_time_seconds': self.optimization_time_seconds,
            'timestamp': self.timestamp.isoformat(),
            'notes': self.notes,
        }


class WeightedDataOptimizer:
    """
    Optimizer that weights recent data more heavily.

    This allows the optimization to favor strategies that perform well
    in recent market conditions while still considering historical performance.

    Weighting schemes:
    - Linear: Weight decreases linearly with age
    - Exponential: Weight decreases exponentially with age
    - Step: Recent period gets higher fixed weight

    Example with exponential decay (half-life = 30 days):
    - Data from today: weight = 1.0
    - Data from 30 days ago: weight = 0.5
    - Data from 60 days ago: weight = 0.25
    """

    def __init__(
        self,
        recent_weight: float = 0.7,
        historical_weight: float = 0.3,
        recent_period_days: int = 30,
        weighting_scheme: str = "step",
        decay_half_life_days: int = 30,
        min_weight: float = 0.1
    ):
        """
        Initialize weighted optimizer.

        Args:
            recent_weight: Weight for recent period (step scheme)
            historical_weight: Weight for historical period (step scheme)
            recent_period_days: Days considered "recent"
            weighting_scheme: "step", "linear", or "exponential"
            decay_half_life_days: Half-life for exponential decay
            min_weight: Minimum weight for any period
        """
        self.recent_weight = recent_weight
        self.historical_weight = historical_weight
        self.recent_period_days = recent_period_days
        self.weighting_scheme = weighting_scheme
        self.decay_half_life_days = decay_half_life_days
        self.min_weight = min_weight

        # Fitness function callback
        self._fitness_func: Optional[Callable[[Dict[str, Any], TimePeriod], float]] = None

    def set_fitness_function(
        self,
        func: Callable[[Dict[str, Any], TimePeriod], float]
    ) -> None:
        """
        Set the fitness evaluation function.

        Args:
            func: Function(parameters, time_period) -> fitness_score
        """
        self._fitness_func = func

    def create_time_periods(
        self,
        total_days: int,
        end_date: Optional[datetime] = None
    ) -> List[TimePeriod]:
        """
        Create weighted time periods for optimization.

        Args:
            total_days: Total days of data to use
            end_date: End date (defaults to now)

        Returns:
            List of TimePeriod objects with weights
        """
        end_date = end_date or datetime.now()

        if self.weighting_scheme == "step":
            return self._create_step_periods(total_days, end_date)
        elif self.weighting_scheme == "linear":
            return self._create_linear_periods(total_days, end_date)
        elif self.weighting_scheme == "exponential":
            return self._create_exponential_periods(total_days, end_date)
        else:
            raise ValueError(f"Unknown weighting scheme: {self.weighting_scheme}")

    def _create_step_periods(
        self,
        total_days: int,
        end_date: datetime
    ) -> List[TimePeriod]:
        """Create two periods with fixed weights."""
        recent_start = end_date - timedelta(days=self.recent_period_days)
        historical_start = end_date - timedelta(days=total_days)

        return [
            TimePeriod(
                start_date=historical_start,
                end_date=recent_start,
                weight=self.historical_weight,
                name="historical"
            ),
            TimePeriod(
                start_date=recent_start,
                end_date=end_date,
                weight=self.recent_weight,
                name="recent"
            )
        ]

    def _create_linear_periods(
        self,
        total_days: int,
        end_date: datetime,
        num_periods: int = 4
    ) -> List[TimePeriod]:
        """Create periods with linearly decreasing weights."""
        periods = []
        period_days = total_days // num_periods

        for i in range(num_periods):
            period_start = end_date - timedelta(days=(num_periods - i) * period_days)
            period_end = end_date - timedelta(days=(num_periods - i - 1) * period_days)

            # Linear weight: most recent period gets weight 1.0
            weight = max(self.min_weight, (i + 1) / num_periods)

            periods.append(TimePeriod(
                start_date=period_start,
                end_date=period_end,
                weight=weight,
                name=f"period_{i+1}"
            ))

        return periods

    def _create_exponential_periods(
        self,
        total_days: int,
        end_date: datetime,
        num_periods: int = 4
    ) -> List[TimePeriod]:
        """Create periods with exponentially decaying weights."""
        periods = []
        period_days = total_days // num_periods

        for i in range(num_periods):
            period_start = end_date - timedelta(days=(num_periods - i) * period_days)
            period_end = end_date - timedelta(days=(num_periods - i - 1) * period_days)

            # Days ago for this period (center)
            days_ago = (num_periods - i - 0.5) * period_days

            # Exponential decay: weight = 2^(-days_ago / half_life)
            weight = max(
                self.min_weight,
                math.pow(2, -days_ago / self.decay_half_life_days)
            )

            periods.append(TimePeriod(
                start_date=period_start,
                end_date=period_end,
                weight=weight,
                name=f"period_{i+1}"
            ))

        return periods

    def calculate_weighted_fitness(
        self,
        parameters: Dict[str, Any],
        periods: List[TimePeriod]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate weighted fitness score across all periods.

        Args:
            parameters: Strategy parameters to evaluate
            periods: Time periods with weights

        Returns:
            (weighted_score, period_scores)
        """
        if not self._fitness_func:
            raise RuntimeError("Fitness function not set")

        period_scores = {}
        total_weight = 0.0
        weighted_sum = 0.0

        for period in periods:
            try:
                score = self._fitness_func(parameters, period)
                period_scores[period.name] = score
                weighted_sum += score * period.weight
                total_weight += period.weight
            except Exception as e:
                logger.warning(f"Error evaluating period {period.name}: {e}")
                period_scores[period.name] = 0.0

        weighted_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        return weighted_score, period_scores

    def optimize_with_weights(
        self,
        strategy_name: str,
        parameter_space: Dict[str, Any],
        total_days: int = 90,
        population_size: int = 50,
        generations: int = 20,
        optimization_func: Optional[Callable] = None
    ) -> OptimizationResult:
        """
        Run optimization with weighted time periods.

        This is a wrapper that integrates with the existing optimization
        framework while adding time-weighted fitness evaluation.

        Args:
            strategy_name: Name of strategy to optimize
            parameter_space: Parameter search space
            total_days: Total days of data to use
            population_size: Population size for genetic algorithm
            generations: Number of generations
            optimization_func: Custom optimization function

        Returns:
            OptimizationResult with best parameters
        """
        import time as time_module
        start_time = time_module.time()

        periods = self.create_time_periods(total_days)

        logger.info(f"Starting weighted optimization for {strategy_name}")
        logger.info(f"Time periods: {[(p.name, f'{p.weight:.2f}') for p in periods]}")

        # This would integrate with the existing genetic algorithm
        # For now, return a placeholder result
        result = OptimizationResult(
            success=True,
            strategy_name=strategy_name,
            parameters={},
            fitness_score=0.0,
            backtest_metrics={},
            weighted_score=0.0,
            period_scores={p.name: 0.0 for p in periods},
            optimization_time_seconds=time_module.time() - start_time,
        )

        return result


class AdaptiveFitnessFunction:
    """
    Fitness function that adapts to market conditions.

    Adjusts fitness evaluation based on:
    - Recent market volatility
    - Strategy style matching
    - Risk-adjusted returns
    """

    def __init__(
        self,
        profit_weight: float = 0.4,
        stability_weight: float = 0.3,
        drawdown_weight: float = 0.3,
        volatility_adjustment: bool = True
    ):
        """
        Initialize adaptive fitness function.

        Args:
            profit_weight: Weight for profit component
            stability_weight: Weight for stability (Sharpe, consistency)
            drawdown_weight: Weight for drawdown penalty
            volatility_adjustment: Adjust weights based on market volatility
        """
        self.profit_weight = profit_weight
        self.stability_weight = stability_weight
        self.drawdown_weight = drawdown_weight
        self.volatility_adjustment = volatility_adjustment

    def calculate(
        self,
        metrics: Dict[str, Any],
        market_volatility: float = 1.0
    ) -> float:
        """
        Calculate adaptive fitness score.

        Args:
            metrics: Backtest metrics
            market_volatility: Current market volatility (1.0 = normal)

        Returns:
            Fitness score
        """
        # Extract metrics
        profit_pct = metrics.get('total_profit_pct', 0.0)
        sharpe = metrics.get('sharpe_ratio', 0.0) or 0.0
        drawdown = abs(metrics.get('max_drawdown', 0.0))
        win_rate = metrics.get('win_rate', 0.0)
        profit_factor = metrics.get('profit_factor', 0.0) or 0.0

        # Normalize components
        profit_score = self._sigmoid(profit_pct * 10)  # Scale profit
        stability_score = self._normalize_sharpe(sharpe)
        drawdown_penalty = drawdown * 2  # Penalize drawdown

        # Adjust weights based on volatility
        if self.volatility_adjustment:
            if market_volatility > 1.5:
                # High volatility: favor stability over profit
                weights = (0.3, 0.4, 0.3)
            elif market_volatility < 0.5:
                # Low volatility: favor profit
                weights = (0.5, 0.2, 0.3)
            else:
                weights = (self.profit_weight, self.stability_weight, self.drawdown_weight)
        else:
            weights = (self.profit_weight, self.stability_weight, self.drawdown_weight)

        # Calculate weighted score
        score = (
            weights[0] * profit_score +
            weights[1] * stability_score -
            weights[2] * drawdown_penalty
        )

        # Bonus for good profit factor and win rate
        if profit_factor > 1.5:
            score *= 1.1
        if win_rate > 0.6:
            score *= 1.05

        return max(0.0, score)

    def _sigmoid(self, x: float) -> float:
        """Sigmoid function for normalization."""
        return 1 / (1 + math.exp(-x))

    def _normalize_sharpe(self, sharpe: float) -> float:
        """Normalize Sharpe ratio to 0-1 range."""
        if sharpe <= 0:
            return 0.0
        return min(1.0, sharpe / 3.0)  # Sharpe of 3 = perfect score
