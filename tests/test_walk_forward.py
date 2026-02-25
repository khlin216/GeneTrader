"""Unit tests for strategy/walk_forward.py."""
import unittest
from datetime import datetime, timedelta

from strategy.walk_forward import (
    WalkForwardValidator,
    ValidationPeriod,
)


class TestValidationPeriod(unittest.TestCase):
    """Tests for ValidationPeriod dataclass."""

    def setUp(self):
        """Set up test fixtures."""
        self.now = datetime(2024, 12, 1)
        self.train_start = self.now - timedelta(weeks=30)
        self.train_end = self.now - timedelta(weeks=4)
        self.test_start = self.train_end
        self.test_end = self.now

        self.period = ValidationPeriod(
            train_start=self.train_start,
            train_end=self.train_end,
            test_start=self.test_start,
            test_end=self.test_end,
            fold_number=0
        )

    def test_train_timerange_format(self):
        """Test train_timerange returns correct format."""
        timerange = self.period.train_timerange
        self.assertIn('-', timerange)
        parts = timerange.split('-')
        self.assertEqual(len(parts), 2)

    def test_test_timerange_format(self):
        """Test test_timerange returns correct format."""
        timerange = self.period.test_timerange
        self.assertIn('-', timerange)
        parts = timerange.split('-')
        self.assertEqual(len(parts), 2)

    def test_train_weeks_calculation(self):
        """Test train_weeks property."""
        self.assertEqual(self.period.train_weeks, 26)

    def test_test_weeks_calculation(self):
        """Test test_weeks property."""
        self.assertEqual(self.period.test_weeks, 4)


class TestWalkForwardValidatorInit(unittest.TestCase):
    """Tests for WalkForwardValidator initialization."""

    def test_valid_initialization(self):
        """Test valid initialization."""
        validator = WalkForwardValidator(
            total_weeks=52,
            train_weeks=26,
            test_weeks=4
        )
        self.assertEqual(validator.total_weeks, 52)
        self.assertEqual(validator.train_weeks, 26)
        self.assertEqual(validator.test_weeks, 4)

    def test_invalid_method_raises(self):
        """Test invalid method raises ValueError."""
        with self.assertRaises(ValueError):
            WalkForwardValidator(method='invalid')

    def test_train_weeks_below_min_raises(self):
        """Test train_weeks below min raises ValueError."""
        with self.assertRaises(ValueError):
            WalkForwardValidator(
                train_weeks=8,
                min_train_weeks=12
            )

    def test_weeks_exceed_total_raises(self):
        """Test train + test exceeding total raises ValueError."""
        with self.assertRaises(ValueError):
            WalkForwardValidator(
                total_weeks=30,
                train_weeks=26,
                test_weeks=10
            )


class TestRollingWindow(unittest.TestCase):
    """Tests for rolling window validation."""

    def setUp(self):
        """Set up validator with rolling method."""
        self.validator = WalkForwardValidator(
            total_weeks=52,
            train_weeks=26,
            test_weeks=4,
            method='rolling'
        )

    def test_generates_multiple_periods(self):
        """Test that multiple periods are generated."""
        periods = self.validator.generate_periods()
        self.assertGreater(len(periods), 1)

    def test_periods_are_sequential(self):
        """Test that periods don't overlap incorrectly."""
        periods = self.validator.generate_periods()
        for i in range(len(periods) - 1):
            # Test end should be before or equal to next train start
            self.assertLessEqual(
                periods[i].test_end,
                periods[i + 1].train_end
            )

    def test_train_weeks_are_constant(self):
        """Test that all training periods have same length."""
        periods = self.validator.generate_periods()
        train_weeks = [p.train_weeks for p in periods]
        self.assertEqual(len(set(train_weeks)), 1)

    def test_test_weeks_are_constant(self):
        """Test that all test periods have same length."""
        periods = self.validator.generate_periods()
        test_weeks = [p.test_weeks for p in periods]
        self.assertEqual(len(set(test_weeks)), 1)


class TestExpandingWindow(unittest.TestCase):
    """Tests for expanding window validation."""

    def setUp(self):
        """Set up validator with expanding method."""
        self.validator = WalkForwardValidator(
            total_weeks=52,
            train_weeks=26,
            test_weeks=4,
            min_train_weeks=12,
            method='expanding'
        )

    def test_generates_multiple_periods(self):
        """Test that multiple periods are generated."""
        periods = self.validator.generate_periods()
        self.assertGreater(len(periods), 1)

    def test_train_weeks_expand(self):
        """Test that training period expands."""
        periods = self.validator.generate_periods()
        if len(periods) > 1:
            # Training should expand
            self.assertLessEqual(periods[0].train_weeks, periods[-1].train_weeks)


class TestAnchoredWindow(unittest.TestCase):
    """Tests for anchored validation."""

    def setUp(self):
        """Set up validator with anchored method."""
        self.validator = WalkForwardValidator(
            total_weeks=52,
            train_weeks=26,
            test_weeks=4,
            min_train_weeks=12,
            method='anchored'
        )

    def test_generates_periods(self):
        """Test that periods are generated."""
        periods = self.validator.generate_periods()
        self.assertGreater(len(periods), 0)

    def test_same_test_period(self):
        """Test that all periods have same test period."""
        periods = self.validator.generate_periods()
        if len(periods) > 1:
            test_ends = [p.test_end for p in periods]
            self.assertEqual(len(set(test_ends)), 1)


class TestCompositeFitness(unittest.TestCase):
    """Tests for composite fitness calculation."""

    def setUp(self):
        """Set up validator."""
        self.validator = WalkForwardValidator(
            total_weeks=52,
            train_weeks=26,
            test_weeks=4
        )

    def test_empty_results_returns_negative_inf(self):
        """Test that empty results return negative infinity."""
        result = self.validator.calculate_composite_fitness([])
        self.assertEqual(result, float('-inf'))

    def test_valid_results_return_positive(self):
        """Test that valid results return positive value."""
        fold_results = [
            {'train_fitness': 0.8, 'test_fitness': 0.6},
            {'train_fitness': 0.7, 'test_fitness': 0.5},
        ]
        result = self.validator.calculate_composite_fitness(fold_results)
        self.assertGreater(result, 0)

    def test_overfitting_penalized(self):
        """Test that overfitting (train >> test) is penalized."""
        # Low overfitting (train slightly better)
        low_overfit = [
            {'train_fitness': 0.6, 'test_fitness': 0.5},
            {'train_fitness': 0.7, 'test_fitness': 0.6},
        ]
        # High overfitting (train much better)
        high_overfit = [
            {'train_fitness': 0.9, 'test_fitness': 0.3},
            {'train_fitness': 0.95, 'test_fitness': 0.25},
        ]

        low_score = self.validator.calculate_composite_fitness(low_overfit)
        high_score = self.validator.calculate_composite_fitness(high_overfit)

        # Low overfitting should score better
        self.assertGreater(low_score, high_score)

    def test_consistency_rewarded(self):
        """Test that consistent results score better."""
        # Consistent results
        consistent = [
            {'train_fitness': 0.6, 'test_fitness': 0.5},
            {'train_fitness': 0.6, 'test_fitness': 0.5},
            {'train_fitness': 0.6, 'test_fitness': 0.5},
        ]
        # Inconsistent results (same average but high variance)
        inconsistent = [
            {'train_fitness': 0.6, 'test_fitness': 0.8},
            {'train_fitness': 0.6, 'test_fitness': 0.2},
            {'train_fitness': 0.6, 'test_fitness': 0.5},
        ]

        consistent_score = self.validator.calculate_composite_fitness(consistent)
        inconsistent_score = self.validator.calculate_composite_fitness(inconsistent)

        # Consistent results should score better
        self.assertGreater(consistent_score, inconsistent_score)


class TestDiversityFunctions(unittest.TestCase):
    """Tests for diversity-related functions in operators.py."""

    def setUp(self):
        """Set up test individuals."""
        from genetic_algorithm.individual import Individual

        self.param_types = [
            {'type': 'Int', 'start': 0, 'end': 100},
            {'type': 'Decimal', 'start': 0.0, 'end': 1.0},
        ]

        self.ind1 = Individual([50, 0.5], ['BTC/USDT'], self.param_types)
        self.ind2 = Individual([75, 0.75], ['ETH/USDT'], self.param_types)
        self.ind3 = Individual([50, 0.5], ['BTC/USDT'], self.param_types)

    def test_genetic_distance_identical(self):
        """Test that identical individuals have zero distance."""
        from genetic_algorithm.operators import calculate_genetic_distance

        distance = calculate_genetic_distance(self.ind1, self.ind3)
        self.assertEqual(distance, 0.0)

    def test_genetic_distance_different(self):
        """Test that different individuals have positive distance."""
        from genetic_algorithm.operators import calculate_genetic_distance

        distance = calculate_genetic_distance(self.ind1, self.ind2)
        self.assertGreater(distance, 0.0)
        self.assertLessEqual(distance, 1.0)

    def test_population_diversity(self):
        """Test population diversity calculation."""
        from genetic_algorithm.operators import calculate_population_diversity

        population = [self.ind1, self.ind2, self.ind3]
        diversity = calculate_population_diversity(population)

        self.assertGreaterEqual(diversity, 0.0)
        self.assertLessEqual(diversity, 1.0)


if __name__ == '__main__':
    unittest.main()
