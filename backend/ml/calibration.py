"""IntentGuard ML — Calibration"""


def calibrate_confidence(raw_confidence: float, ml_score: float) -> float:
    """Calibrate confidence with ML signal.
    ml_score is the probability of the transaction being ambiguous/high-risk (0.0 to 1.0).
    We reduce confidence proportionally if ML detects high ambiguity.
    """
    # If ML predicts high risk (ml_score > 0.5), reduce confidence by up to 30%
    if ml_score > 0.5:
        penalty = (ml_score - 0.5) * 0.6  # max penalty 0.3 when ml_score=1.0
        calibrated = raw_confidence * (1.0 - penalty)
        return round(max(0.0, min(1.0, calibrated)), 4)
        
    # If ML predicts very low risk, slight boost
    elif ml_score < 0.2:
        boost = (0.2 - ml_score) * 0.2
        calibrated = raw_confidence * (1.0 + boost)
        return round(max(0.0, min(1.0, calibrated)), 4)
        
    return raw_confidence
