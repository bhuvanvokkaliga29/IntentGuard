"""IntentGuard ML — Training Script"""

import logging
import os
import joblib
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger("intentguard.ml.train")


async def train_model():
    """Train the Random Forest ambiguity model on synthetic data."""
    logger.info("[ML] Generating synthetic training data...")
    
    # Generate synthetic features
    # Features: amount_to_limit_ratio, merchant_known, category_exact_match, 
    # semantic_agreement_rate, mandate_specificity, item_description_length, 
    # hard_constraint_fail_count, evidence_completeness
    
    X = []
    y = []
    
    np.random.seed(42)
    for _ in range(1000):
        # 0 = Safe/Clear, 1 = Ambiguous/High Risk
        is_ambiguous = np.random.choice([0, 1], p=[0.7, 0.3])
        
        if is_ambiguous:
            amount_ratio = np.random.uniform(0.8, 1.2)
            merchant_known = np.random.choice([0.0, 1.0], p=[0.7, 0.3])
            cat_match = np.random.choice([0.0, 1.0], p=[0.6, 0.4])
            agreement = np.random.choice([0.33, 0.67])
            hard_fails = np.random.choice([0, 1], p=[0.8, 0.2])
            completeness = np.random.uniform(0.3, 0.8)
        else:
            amount_ratio = np.random.uniform(0.1, 0.9)
            merchant_known = 1.0
            cat_match = 1.0
            agreement = 1.0
            hard_fails = 0
            completeness = np.random.uniform(0.7, 1.0)
            
        features = [
            amount_ratio,
            merchant_known,
            cat_match,
            agreement,
            np.random.randint(1, 5), # specificity
            np.random.randint(10, 50), # text length
            hard_fails,
            completeness
        ]
        X.append(features)
        y.append(is_ambiguous)
        
    logger.info("[ML] Training Random Forest Classifier...")
    model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    model.fit(X, y)
    
    # Ensure models directory exists
    model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "ambiguity_model.joblib")
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    logger.info(f"[ML] Saving model to {model_path}...")
    joblib.dump(model, model_path)
    
    accuracy = model.score(X, y)
    logger.info(f"[ML] Training complete. Training accuracy: {accuracy:.2f}")
    
    return {"status": "success", "accuracy": accuracy, "path": model_path}

if __name__ == "__main__":
    import asyncio
    asyncio.run(train_model())
