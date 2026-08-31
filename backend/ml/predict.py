"""IntentGuard ML — Prediction"""

import os
import joblib
import logging

logger = logging.getLogger("intentguard.ml.predict")

# Cache model in memory
_model = None

def get_model():
    global _model
    if _model is None:
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "ambiguity_model.joblib")
        if os.path.exists(model_path):
            _model = joblib.load(model_path)
        else:
            logger.warning(f"ML model not found at {model_path}. Returning default.")
    return _model

async def predict_ambiguity(features: dict) -> float:
    """Predict ambiguity/risk probability using trained ML model."""
    model = get_model()
    if not model:
        return 0.0
        
    # Extract features in same order as training
    feature_vector = [[
        features.get("amount_to_limit_ratio", 0.0),
        features.get("merchant_known", 1.0),
        features.get("category_exact_match", 1.0),
        features.get("semantic_agreement_rate", 1.0),
        features.get("mandate_specificity", 1),
        features.get("item_description_length", 20),
        features.get("hard_constraint_fail_count", 0),
        features.get("evidence_completeness", 1.0)
    ]]
    
    # Predict probability of class 1 (Ambiguous)
    prob = model.predict_proba(feature_vector)[0][1]
    return float(prob)
