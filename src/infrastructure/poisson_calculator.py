import numpy as np
from scipy.stats import poisson
from typing import Dict, Tuple, List
from domain.interfaces import ProbabilityCalculator
from domain.models import ExpectedGoals

class ScipyPoissonCalculator(ProbabilityCalculator):
    """Calculador matricial Poisson de 8x8 corregido mediante Dixon-Coles."""
    def __init__(self, max_goals: int = 8):
        self.max_goals = max_goals

    def calculate_distribution(self, expected_goals: ExpectedGoals, top_n: int = 5) -> Tuple[Dict[str, float], List[Dict[str, float]]]:
        matrix = np.zeros((self.max_goals, self.max_goals))
        mu_x = expected_goals.home
        mu_y = expected_goals.away
        
        for i in range(self.max_goals):
            for j in range(self.max_goals):
                matrix[i, j] = poisson.pmf(i, mu_x) * poisson.pmf(j, mu_y)
                
        tau = 0.08 
        if mu_x > 0 and mu_y > 0:
            matrix[0, 0] *= (1 - mu_x * mu_y * tau)
            matrix[1, 1] *= (1 - tau)
            matrix[1, 0] *= (1 + mu_y * tau)
            matrix[0, 1] *= (1 + mu_x * tau)
            
        matrix = matrix / np.sum(matrix)
                
        outcomes = {
            "home_win": float(np.sum(np.tril(matrix, -1))),
            "draw": float(np.sum(np.diag(matrix))),
            "away_win": float(np.sum(np.triu(matrix, 1)))
        }
        
        exact_scores = []
        for i in range(self.max_goals):
            for j in range(self.max_goals):
                exact_scores.append({"score": f"{i}-{j}", "prob": float(matrix[i, j])})
                
        top_scores = sorted(exact_scores, key=lambda x: x["prob"], reverse=True)[:top_n]
        return outcomes, top_scores