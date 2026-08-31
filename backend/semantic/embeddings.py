"""
IntentGuard — Embeddings (Optional, Disabled by Default)

Embeddings may be used as:
- Supporting feature
- Retrieval/context similarity
- Diagnostic metric

They MUST NOT be the main decision mechanism.

This module is a stub. Enable only if embeddings materially improve
the system during evaluation.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger("intentguard.semantic.embeddings")


# Feature flag
EMBEDDINGS_ENABLED = False


async def compute_similarity(
    text_a: str,
    text_b: str,
) -> Optional[Dict]:
    """
    Compute semantic similarity between two texts.
    
    Returns None if embeddings are disabled.
    This is NOT used for decision-making — only as a diagnostic metric.
    """
    if not EMBEDDINGS_ENABLED:
        return None

    logger.info("[EMBEDDINGS] Embeddings are disabled in this build.")
    return None


def get_embedding_info() -> Dict:
    """Get info about the embedding configuration."""
    return {
        "enabled": EMBEDDINGS_ENABLED,
        "model": None,
        "version": None,
        "note": "Embeddings are disabled. They are not the primary decision mechanism.",
    }
