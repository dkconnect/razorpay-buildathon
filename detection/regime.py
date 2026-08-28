"""
detection/regime.py
Synthesizes multi-signal CUSUM states into diagnostic regime classifications and scores.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List
import numpy as np

from detection.cusum import CUSUMState


class RegimeType(str, Enum):
    NORMAL = "NORMAL_REGIME"
    FLASH_SALE = "FLASH_SALE_REGIME"
    CARD_TESTING = "CARD_TESTING_REGIME"
    BUSTOUT = "BUSTOUT_REGIME"
    ELEVATED_RISK = "ELEVATED_RISK_REGIME"


@dataclass
class RegimeDiagnosis:
    timestamp: float
    regime: RegimeType
    regime_score: float                # in [0, 1]
    is_suspicious_regime: bool         # True only if malicious shift
    testing_risk: float                # S_v AND S_a interaction
    bustout_risk: float                # S_high independent risk
    reason_codes: List[str]
    cusum_state: CUSUMState


class RegimeClassifier:
    """
    Evaluates temporal CUSUM states using gated non-linear evidence fusion.
    """

    def classify(self, state: CUSUMState) -> RegimeDiagnosis:
        reasons = []

        # 1. Evaluate alert flags for audit logs
        if state.velocity_alert:
            reasons.append(f"TRANSACTION_VELOCITY_SPIKE (S_v+={state.s_velocity_pos:.2f})")
        if state.amount_alert:
            reasons.append(f"MICRO_AMOUNT_CONCENTRATION (S_a-={state.s_amount_neg:.2f})")
        if state.high_val_alert:
            reasons.append(f"HIGH_VALUE_BURST (S_high+={state.s_high_val_pos:.2f})")

        # 2. Conjunctive Phase 1 Risk (Velocity AND Amount-Drop must co-occur)
        testing_risk = float(state.normalized_velocity_score * state.normalized_amount_score)

        # 3. Disjunctive Phase 2 Risk (High-value breakout acts independently)
        bustout_risk = float(state.normalized_high_val_score)

        # 4. Total Unified Regime Score (Probabilistic OR)
        regime_score = float(1.0 - (1.0 - testing_risk) * (1.0 - bustout_risk))

        # 5. Determine Diagnostic Regime Archetype
        if state.velocity_alert and state.amount_alert:
            regime = RegimeType.CARD_TESTING
            is_suspicious = True
        elif state.high_val_alert:
            regime = RegimeType.BUSTOUT
            is_suspicious = True
        elif state.velocity_alert and not state.amount_alert and not state.high_val_alert:
            regime = RegimeType.FLASH_SALE
            is_suspicious = False  # Legitimate merchant volume spike
            reasons.append("LEGITIMATE_VOLUME_SURGE (Healthy Basket Profile)")
        elif testing_risk > 0.35 or bustout_risk > 0.40:
            regime = RegimeType.ELEVATED_RISK
            is_suspicious = True
        else:
            regime = RegimeType.NORMAL
            is_suspicious = False

        if not reasons:
            reasons.append("NOMINAL_TRAFFIC_PROFILE")

        return RegimeDiagnosis(
            timestamp=state.timestamp,
            regime=regime,
            regime_score=regime_score,
            is_suspicious_regime=is_suspicious,
            testing_risk=testing_risk,
            bustout_risk=bustout_risk,
            reason_codes=reasons,
            cusum_state=state,
        )