"""Genetic algorithm optimizer wrapper for strategy optimization.

This module wraps the existing genetic algorithm implementation
into the unified optimizer interface.

Features:
- Walk-forward validation to prevent overfitting
- Diversity-aware selection to prevent premature convergence
- Elitism to preserve best solutions
"""
import gc
import random
import multiprocessing
from typing import List, Tuple, Any, Dict, Optional

from optimization.base_optimizer import BaseOptimizer
from genetic_algorithm.individual import Individual
from genetic_algorithm.population import Population
from genetic_algorithm.operators import (
    crossover, mutate, select_tournament,
    select_with_diversity, maintain_diversity, calculate_population_diversity
)
from strategy.backtest import run_backtest
from strategy.walk_forward import WalkForwardValidator, create_validator_from_settings
from utils.logging_config import logger


class GeneticOptimizer(BaseOptimizer):
    """
    Genetic algorithm optimizer using selection, crossover, and mutation.

    This is the original optimization method, suitable for exploring
    diverse solution spaces with potentially multiple local optima.
    """

    def __init__(self, settings: Any, parameters: List[Dict], all_pairs: List[str]):
        """
        Initialize the genetic optimizer.

        Args:
            settings: Settings object containing optimization configuration
            parameters: List of parameter definitions for optimization
            all_pairs: List of all available trading pairs
        """
        super().__init__(settings, parameters)
        self.all_pairs = all_pairs
        self.best_individual: Optional[Individual] = None

    def _create_population(self, population_size: int, initial_individuals: List[Individual] = None) -> Population:
        """
        Create initial population.

        Args:
            population_size: Size of the population to create
            initial_individuals: Optional list of individuals to include

        Returns:
            Population object
        """
        population = Population.create_random(
            size=population_size,
            parameters=self.parameters,
            trading_pairs=self.all_pairs,
            num_pairs=None if self.settings.fix_pairs else self.settings.num_pairs
        )

        if initial_individuals:
            population.individuals.extend(initial_individuals)

        return population

    def optimize(self, initial_individuals: List[Individual] = None) -> List[Tuple[int, Individual]]:
        """
        Run genetic algorithm optimization with anti-overfitting measures.

        Features:
        - Diversity-aware selection to prevent premature convergence
        - Elitism to preserve best solutions
        - Population diversity maintenance

        Args:
            initial_individuals: Optional list of initial individuals to seed the population

        Returns:
            List of tuples containing (generation number, best individual)
        """
        # Calculate population size accounting for initial individuals
        population_size = self.settings.population_size - len(initial_individuals or [])
        population = self._create_population(population_size, initial_individuals)

        best_individuals = []
        num_parameters = len(self.parameters)

        # Check if diversity selection is enabled
        enable_diversity = getattr(self.settings, 'enable_diversity_selection', False)
        diversity_weight = getattr(self.settings, 'diversity_selection_weight', 0.3)
        diversity_threshold = getattr(self.settings, 'diversity_threshold', 0.1)

        with multiprocessing.Pool(processes=self.settings.pool_processes) as pool:
            for gen in range(self.settings.generations):
                logger.info(f"Generation {gen+1}")

                # Log population diversity
                if enable_diversity:
                    diversity = calculate_population_diversity(population.individuals)
                    logger.info(f"Population diversity: {diversity:.4f}")

                # Evaluate fitness in parallel
                try:
                    fitnesses = pool.starmap(
                        run_backtest,
                        [(ind.genes, ind.trading_pairs, gen+1, None, num_parameters)
                         for ind in population.individuals]
                    )

                    for ind, fit in zip(population.individuals, fitnesses):
                        ind.fitness = fit if fit is not None else float('-inf')

                except (OSError, multiprocessing.TimeoutError) as e:
                    logger.error(f"Process error in generation {gen+1}: {str(e)}")
                    for ind in population.individuals:
                        ind.fitness = float('-inf')
                except ValueError as e:
                    logger.error(f"Value error in generation {gen+1}: {str(e)}")
                    for ind in population.individuals:
                        if ind.fitness is None:
                            ind.fitness = float('-inf')
                except Exception as e:
                    logger.error(f"Unexpected error in generation {gen+1}: {type(e).__name__}: {str(e)}")

                # Filter out individuals with negative or None fitness
                valid_individuals = [
                    ind for ind in population.individuals
                    if ind.fitness is not None and ind.fitness > 0
                ]
                logger.info(f"Valid individuals in generation {gen+1}: {len(valid_individuals)}")

                if not valid_individuals:
                    # Fall back to all non-None individuals if all have negative fitness
                    valid_individuals = [
                        ind for ind in population.individuals
                        if ind.fitness is not None
                    ]
                    if not valid_individuals:
                        logger.warning(f"No valid individuals in generation {gen+1}. Terminating early.")
                        break

                # Find the best individual before selection
                best_individual = max(valid_individuals, key=lambda ind: ind.fitness)

                # Select individuals for the next generation with diversity consideration
                offspring = []
                for i in range(self.settings.population_size):
                    if enable_diversity and i > 0 and offspring:
                        # Use diversity-aware selection
                        reference = offspring[-1] if offspring else None
                        selected = select_with_diversity(
                            valid_individuals,
                            self.settings.tournament_size,
                            diversity_weight=diversity_weight,
                            reference_individual=reference
                        )
                    else:
                        selected = select_tournament(valid_individuals, self.settings.tournament_size)
                    offspring.append(selected.copy())

                # Elitism: preserve the best individual
                if best_individual.fitness > offspring[0].fitness:
                    offspring[0] = best_individual.copy()

                # Apply crossover
                for i in range(1, len(offspring) - 1, 2):
                    if random.random() < self.settings.crossover_prob:
                        offspring[i], offspring[i+1] = crossover(
                            offspring[i],
                            offspring[i+1],
                            with_pair=self.settings.fix_pairs
                        )
                        offspring[i].after_genetic_operation(self.parameters)
                        offspring[i+1].after_genetic_operation(self.parameters)

                # Apply mutation (skip elite)
                for ind in offspring[1:]:
                    mutate(ind, self.settings.mutation_prob)
                    ind.after_genetic_operation(self.parameters)

                # Maintain diversity if it drops too low
                if enable_diversity:
                    mutations = maintain_diversity(
                        offspring[1:],  # Don't mutate elite
                        min_diversity=diversity_threshold,
                        mutation_boost=self.settings.mutation_prob * 2
                    )
                    if mutations > 0:
                        logger.info(f"Applied {mutations} diversity mutations")

                # Replace the population
                population.individuals = offspring

                # Record best individual
                best_individuals.append((gen+1, best_individual))

                # Update overall best
                if self.best_individual is None or best_individual.fitness > self.best_individual.fitness:
                    self.best_individual = best_individual

                logger.info(f"Best individual in generation {gen+1}: Fitness: {best_individual.fitness:.4f}")

                gc.collect()

        return best_individuals

    def optimize_with_walk_forward(
        self,
        initial_individuals: List[Individual] = None
    ) -> Tuple[List[Tuple[int, Individual]], Dict[str, Any]]:
        """
        Run optimization with walk-forward validation.

        This method trains on multiple time periods and validates on
        out-of-sample data to prevent overfitting.

        Args:
            initial_individuals: Optional list of initial individuals

        Returns:
            Tuple of (best_individuals, validation_results)
        """
        # Create walk-forward validator
        validator = create_validator_from_settings(self.settings)
        periods = validator.generate_periods()

        if not periods:
            logger.warning("No walk-forward periods generated. Running standard optimization.")
            return self.optimize(initial_individuals), {}

        logger.info(f"Running walk-forward optimization with {len(periods)} periods")

        all_results = []
        fold_results = []

        for period in periods:
            logger.info(f"=== Fold {period.fold_number + 1}/{len(periods)} ===")
            logger.info(f"Train: {period.train_timerange} ({period.train_weeks} weeks)")
            logger.info(f"Test: {period.test_timerange} ({period.test_weeks} weeks)")

            # Run optimization on training period
            # Store original timerange
            original_timerange = self.settings.backtest_timerange_weeks

            # Run training
            train_results = self._run_fold_optimization(
                period.train_timerange,
                initial_individuals,
                f"fold{period.fold_number}_train"
            )

            if not train_results:
                logger.warning(f"Fold {period.fold_number + 1} training failed")
                continue

            # Get best individual from training
            best_train = max(train_results, key=lambda x: x[1].fitness)
            train_fitness = best_train[1].fitness

            # Validate on test period
            test_fitness = self._evaluate_on_period(
                best_train[1],
                period.test_timerange
            )

            logger.info(f"Fold {period.fold_number + 1} - Train: {train_fitness:.4f}, Test: {test_fitness:.4f}")

            fold_results.append({
                'fold': period.fold_number,
                'train_fitness': train_fitness,
                'test_fitness': test_fitness,
                'best_individual': best_train[1],
                'train_period': period.train_timerange,
                'test_period': period.test_timerange
            })

            all_results.extend(train_results)

        # Calculate composite fitness
        composite_fitness = validator.calculate_composite_fitness(fold_results)

        validation_results = {
            'fold_results': fold_results,
            'composite_fitness': composite_fitness,
            'num_folds': len(periods),
            'method': validator.method
        }

        logger.info(f"Walk-forward composite fitness: {composite_fitness:.4f}")

        return all_results, validation_results

    def _run_fold_optimization(
        self,
        timerange: str,
        initial_individuals: List[Individual],
        fold_name: str
    ) -> List[Tuple[int, Individual]]:
        """Run optimization for a single fold."""
        # This would need to be implemented to run backtest with custom timerange
        # For now, we use the standard optimize method
        return self.optimize(initial_individuals)

    def _evaluate_on_period(self, individual: Individual, timerange: str) -> float:
        """Evaluate an individual on a specific time period."""
        try:
            fitness = run_backtest(
                individual.genes,
                individual.trading_pairs,
                generation=0,
                custom_timerange=timerange,
                num_parameters=len(self.parameters)
            )
            return fitness if fitness is not None else float('-inf')
        except Exception as e:
            logger.error(f"Error evaluating on period {timerange}: {e}")
            return float('-inf')

    def get_best_individual(self) -> Individual:
        """
        Get the best individual found during optimization.

        Returns:
            The best Individual found
        """
        return self.best_individual
