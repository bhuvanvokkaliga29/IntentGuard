"""
IntentGuard — Semantic Drift Matrix

Computes an interactive matrix/heatmap of User Intent vs Proposed Item Types.
Cells classify semantic compatibility into:
- FIT (1.0)
- NEAR_FIT (0.5)
- NO_FIT (0.0)
- UNKNOWN / INSUFFICIENT_EVIDENCE (-1.0)
"""

from typing import Dict, List, Any


def get_semantic_drift_matrix() -> Dict[str, Any]:
    """
    Returns the structured Semantic Drift Matrix data for frontend visualization.
    """
    intents = [
        "Office Supplies",
        "Domestic Flight",
        "Weekly Groceries",
        "IT Hardware",
        "SaaS Subscriptions",
        "Team Meals",
        "Vague/Underspecified Intent"
    ]

    item_categories = [
        "Paper & Pens",
        "Food / Chocolates",
        "Consumer Electronics",
        "Domestic Airline",
        "International Flight",
        "Produce & Staples",
        "Luxury Cosmetics",
        "Executive Furniture",
        "Opaque SKU / Unknown"
    ]

    # Matrix lookup [Intent][Item_Category] = (verdict, count, description)
    matrix_cells = [
        # Office Supplies
        {"intent": "Office Supplies", "item": "Paper & Pens", "verdict": "FIT", "score": 1.0, "status": "ALLOW"},
        {"intent": "Office Supplies", "item": "Food / Chocolates", "verdict": "NO_FIT", "score": 0.0, "status": "FLAG"},
        {"intent": "Office Supplies", "item": "Consumer Electronics", "verdict": "NEAR_FIT", "score": 0.5, "status": "FLAG"},
        {"intent": "Office Supplies", "item": "Domestic Airline", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Office Supplies", "item": "International Flight", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Office Supplies", "item": "Produce & Staples", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Office Supplies", "item": "Luxury Cosmetics", "verdict": "NO_FIT", "score": 0.0, "status": "FLAG"},
        {"intent": "Office Supplies", "item": "Executive Furniture", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Office Supplies", "item": "Opaque SKU / Unknown", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},

        # Domestic Flight
        {"intent": "Domestic Flight", "item": "Paper & Pens", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Domestic Flight", "item": "Food / Chocolates", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Domestic Flight", "item": "Consumer Electronics", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Domestic Flight", "item": "Domestic Airline", "verdict": "FIT", "score": 1.0, "status": "ALLOW"},
        {"intent": "Domestic Flight", "item": "International Flight", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Domestic Flight", "item": "Produce & Staples", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Domestic Flight", "item": "Luxury Cosmetics", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Domestic Flight", "item": "Executive Furniture", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Domestic Flight", "item": "Opaque SKU / Unknown", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},

        # Weekly Groceries
        {"intent": "Weekly Groceries", "item": "Paper & Pens", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Weekly Groceries", "item": "Food / Chocolates", "verdict": "NEAR_FIT", "score": 0.5, "status": "FLAG"},
        {"intent": "Weekly Groceries", "item": "Consumer Electronics", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Weekly Groceries", "item": "Domestic Airline", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Weekly Groceries", "item": "International Flight", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Weekly Groceries", "item": "Produce & Staples", "verdict": "FIT", "score": 1.0, "status": "ALLOW"},
        {"intent": "Weekly Groceries", "item": "Luxury Cosmetics", "verdict": "NO_FIT", "score": 0.0, "status": "FLAG"},
        {"intent": "Weekly Groceries", "item": "Executive Furniture", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Weekly Groceries", "item": "Opaque SKU / Unknown", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},

        # IT Hardware
        {"intent": "IT Hardware", "item": "Paper & Pens", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "IT Hardware", "item": "Food / Chocolates", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "IT Hardware", "item": "Consumer Electronics", "verdict": "FIT", "score": 1.0, "status": "ALLOW"},
        {"intent": "IT Hardware", "item": "Domestic Airline", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "IT Hardware", "item": "International Flight", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "IT Hardware", "item": "Produce & Staples", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "IT Hardware", "item": "Luxury Cosmetics", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "IT Hardware", "item": "Executive Furniture", "verdict": "NEAR_FIT", "score": 0.5, "status": "FLAG"},
        {"intent": "IT Hardware", "item": "Opaque SKU / Unknown", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},

        # SaaS Subscriptions
        {"intent": "SaaS Subscriptions", "item": "Paper & Pens", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "SaaS Subscriptions", "item": "Food / Chocolates", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "SaaS Subscriptions", "item": "Consumer Electronics", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "SaaS Subscriptions", "item": "Domestic Airline", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "SaaS Subscriptions", "item": "International Flight", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "SaaS Subscriptions", "item": "Produce & Staples", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "SaaS Subscriptions", "item": "Luxury Cosmetics", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "SaaS Subscriptions", "item": "Executive Furniture", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "SaaS Subscriptions", "item": "Opaque SKU / Unknown", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},

        # Team Meals
        {"intent": "Team Meals", "item": "Paper & Pens", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Team Meals", "item": "Food / Chocolates", "verdict": "FIT", "score": 1.0, "status": "ALLOW"},
        {"intent": "Team Meals", "item": "Consumer Electronics", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Team Meals", "item": "Domestic Airline", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Team Meals", "item": "International Flight", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Team Meals", "item": "Produce & Staples", "verdict": "NEAR_FIT", "score": 0.5, "status": "FLAG"},
        {"intent": "Team Meals", "item": "Luxury Cosmetics", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Team Meals", "item": "Executive Furniture", "verdict": "NO_FIT", "score": 0.0, "status": "BLOCK"},
        {"intent": "Team Meals", "item": "Opaque SKU / Unknown", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},

        # Vague Intent
        {"intent": "Vague/Underspecified Intent", "item": "Paper & Pens", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},
        {"intent": "Vague/Underspecified Intent", "item": "Food / Chocolates", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},
        {"intent": "Vague/Underspecified Intent", "item": "Consumer Electronics", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},
        {"intent": "Vague/Underspecified Intent", "item": "Domestic Airline", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},
        {"intent": "Vague/Underspecified Intent", "item": "International Flight", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},
        {"intent": "Vague/Underspecified Intent", "item": "Produce & Staples", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},
        {"intent": "Vague/Underspecified Intent", "item": "Luxury Cosmetics", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},
        {"intent": "Vague/Underspecified Intent", "item": "Executive Furniture", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},
        {"intent": "Vague/Underspecified Intent", "item": "Opaque SKU / Unknown", "verdict": "UNKNOWN", "score": -1.0, "status": "ESCALATE"},
    ]

    return {
        "intents": intents,
        "item_categories": item_categories,
        "cells": matrix_cells,
        "legend": {
            "FIT": {"label": "Direct Purpose Entailment", "color": "#10b981", "default_action": "ALLOW"},
            "NEAR_FIT": {"label": "Adjacent / Borderline Category", "color": "#eab308", "default_action": "FLAG"},
            "NO_FIT": {"label": "Categorical Intent Mismatch", "color": "#f43f5e", "default_action": "BLOCK"},
            "UNKNOWN": {"label": "Insufficient Evidence / Ambiguity", "color": "#a855f7", "default_action": "ESCALATE"}
        }
    }
