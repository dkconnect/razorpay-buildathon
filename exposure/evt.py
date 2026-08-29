# Extreme Value Theory (EVT) and expected fraud exposure module.

from typing import Any, Dict, List, Optional
import numpy as np
from scipy import stats

class TailExposureEstimator:

    def __init__(self, tail_percentile: float = 90.0, alpha: float = 0.95):
        self.tail_percentile = tail_percentile
        self.alpha = alpha

    def fit_tail_distribution(self, amounts: List[float]) -> Dict[str, float]:

        clean_amounts = [float(a) for a in amounts if a > 0.0]
        if len(clean_amounts) < 5:
            base_mean = float(np.mean(clean_amounts)) if clean_amounts else 0.0
            return {
                "threshold_u": base_mean,
                "var_95": base_mean,
                "cvar_95": base_mean,
                "shape_xi": 0.0,
                "scale_sigma": 1.0,
                "tail_sample_size": float(len(clean_amounts))
            }

        arr = np.array(clean_amounts)
        threshold_u = float(np.percentile(arr, self.tail_percentile))
        excesses = arr[arr > threshold_u] - threshold_u

        if len(excesses) < 3:
            var_empirical = float(np.percentile(arr, self.alpha * 100))
            tail_vals = arr[arr >= var_empirical]
            cvar_empirical = float(np.mean(tail_vals)) if len(tail_vals) > 0 else var_empirical
            return {
                "threshold_u": threshold_u,
                "var_95": var_empirical,
                "cvar_95": cvar_empirical,
                "shape_xi": 0.0,
                "scale_sigma": float(np.std(excesses)) if len(excesses) > 0 else 1.0,
                "tail_sample_size": float(len(excesses))
            }

        # Fit Generalized Pareto Distribution: (c, loc=0, scale) where c = xi (shape)
        try:
            shape_xi, _, scale_sigma = stats.genpareto.fit(excesses, floc=0)
            n_total = len(arr)
            n_excess = len(excesses)
            prob_excess = n_excess / n_total

            # Analytical VaR and CVaR for POT-GPD
            if prob_excess > 0 and (1.0 - self.alpha) > 0:
                p = (1.0 - self.alpha) / prob_excess
                if abs(shape_xi) < 1e-4:
                    var_alpha = threshold_u - scale_sigma * np.log(p)
                    cvar_alpha = var_alpha + scale_sigma
                elif shape_xi < 1.0:  # Finite mean exists when xi < 1
                    var_alpha = threshold_u + (scale_sigma / shape_xi) * (p**(-shape_xi) - 1.0)
                    cvar_alpha = (var_alpha + scale_sigma - shape_xi * threshold_u) / (1.0 - shape_xi)
                else:
                    var_alpha = float(np.percentile(arr, self.alpha * 100))
                    cvar_alpha = float(np.mean(arr[arr >= var_alpha]))
            else:
                var_alpha = float(np.percentile(arr, self.alpha * 100))
                cvar_alpha = float(np.mean(arr[arr >= var_alpha]))

        except Exception:
            var_alpha = float(np.percentile(arr, self.alpha * 100))
            tail_vals = arr[arr >= var_alpha]
            cvar_alpha = float(np.mean(tail_vals)) if len(tail_vals) > 0 else var_alpha
            shape_xi, scale_sigma = 0.0, 1.0

        return {
            "threshold_u": round(float(threshold_u), 2),
            "var_95": round(float(var_alpha), 2),
            "cvar_95": round(float(cvar_alpha), 2),
            "shape_xi": round(float(shape_xi), 4),
            "scale_sigma": round(float(scale_sigma), 2),
            "tail_sample_size": float(len(excesses))
        }

    def compute_exposure_metrics(
        self,
        window_transactions: List[Dict[str, Any]],
        implicated_tx_ids: Optional[List[str]] = None,
        ring_risk_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Quantifies total regime tail exposure and ring-specific expected fraud exposure.
        """
        if not window_transactions:
            return {
                "total_window_volume": 0.0,
                "tail_metrics": {},
                "expected_fraud_exposure": 0.0,
                "implicated_volume": 0.0
            }

        amounts = [t.get("amount", 0.0) for t in window_transactions]
        total_volume = float(sum(amounts))

        tail_metrics = self.fit_tail_distribution(amounts)

        # Calculate expected fraud exposure for implicated transactions
        implicated_set = set(implicated_tx_ids or [])
        implicated_volume = 0.0
        expected_fraud_exposure = 0.0

        for tx in window_transactions:
            tx_id = tx.get("transaction_id")
            amt = float(tx.get("amount", 0.0))
            if tx_id in implicated_set:
                implicated_volume += amt
                # Risk-weighted expected loss
                p_fraud = max(ring_risk_score, 0.50)
                expected_fraud_exposure += p_fraud * amt

        return {
            "total_window_volume": round(total_volume, 2),
            "tail_metrics": tail_metrics,
            "implicated_volume": round(implicated_volume, 2),
            "expected_fraud_exposure": round(expected_fraud_exposure, 2)
        }