"""
IntentGuard — Voice / Natural Language Mandate Interface

Allows a user to declare their spending intent using conversational natural language or voice transcripts.
Extracts and normalizes structured mandate fields:
- intent_text
- max_amount_per_txn
- budget_cap
- allowed_categories
- allowed_merchants
- frequency
- exclusions
- purpose_context
"""

import re
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from backend.models import MandateCreate


class VoiceParseResponse(BaseModel):
    raw_transcript: str
    parsed_mandate: MandateCreate
    extraction_notes: List[str]
    confidence_of_parsing: float


class VoiceMandateAgent:
    @staticmethod
    def parse_natural_language(transcript: str) -> VoiceParseResponse:
        """
        Parse conversational natural language intent into a structured Mandate.
        Includes deterministic heuristic extraction with safe defaults.
        """
        notes = []
        clean_text = transcript.strip()
        lower = clean_text.lower()

        # 1. Amount extraction
        amount_match = re.search(r'(?:₹|rs\.?|inr|under|up to|less than|max|maximum|budget of)\s*([\d,]+(?:\.\d+)?)', lower)
        if not amount_match:
            # Look for number followed by thousand/k
            k_match = re.search(r'(\d+)\s*(?:thousand|k)', lower)
            if k_match:
                extracted_amount = float(k_match.group(1)) * 1000.0
            else:
                word_match = re.search(r'(?:two|three|four|five|ten)\s*thousand', lower)
                word_map = {"two": 2000.0, "three": 3000.0, "four": 4000.0, "five": 5000.0, "ten": 10000.0}
                if word_match:
                    w = word_match.group(0).split()[0]
                    extracted_amount = word_map.get(w, 2000.0)
                else:
                    extracted_amount = 2000.0  # default
        else:
            raw_num = amount_match.group(1).replace(',', '')
            extracted_amount = float(raw_num)

        notes.append(f"Extracted max transaction budget: ₹{extracted_amount:,.2f}")

        # 2. Frequency extraction
        frequency = "on_demand"
        if "every week" in lower or "weekly" in lower or "per week" in lower:
            frequency = "weekly"
        elif "every month" in lower or "monthly" in lower or "per month" in lower:
            frequency = "monthly"
        elif "every day" in lower or "daily" in lower or "per day" in lower:
            frequency = "daily"
        notes.append(f"Extracted frequency: {frequency}")

        # 3. Purpose & Categories
        categories = []
        merchants = []
        exclusions = []

        if any(w in lower for w in ["office", "stationery", "paper", "pen", "supplies"]):
            categories = ["office_supplies", "stationery", "writing_instruments", "paper_products"]
            merchants = ["Stationery Mart", "Office Depot India", "Pen Paper Store"]
            exclusions = ["electronics", "furniture", "food", "beverages", "personal_items"]
            purpose = "Routine restocking of office stationery and desk consumables."
        elif any(w in lower for w in ["flight", "travel", "bangalore", "delhi", "trip", "airline"]):
            categories = ["travel", "flights", "domestic_travel", "air_travel"]
            merchants = ["MakeMyTrip", "Cleartrip", "IndiGo", "Air India"]
            exclusions = ["international_travel", "hotels", "luxury_travel"]
            purpose = "Domestic business travel booking."
        elif any(w in lower for w in ["grocery", "groceries", "food", "supermarket", "kitchen"]):
            categories = ["groceries", "food", "household_essentials", "fresh_produce"]
            merchants = ["BigBasket", "DMart", "More Supermarket"]
            exclusions = ["alcohol", "tobacco", "electronics", "luxury_items"]
            purpose = "Household groceries and staple replenishment."
        else:
            categories = ["general_procurement"]
            merchants = None
            exclusions = ["unauthorized_items"]
            purpose = "General delegated purchasing under declared limits."

        notes.append(f"Assigned {len(categories)} allowed categories and {len(merchants) if merchants else 0} approved vendors.")

        mandate_obj = MandateCreate(
            intent_text=clean_text,
            max_amount_per_txn=extracted_amount,
            budget_cap=extracted_amount * (4.0 if frequency == "weekly" else 1.0),
            allowed_categories=categories,
            allowed_merchants=merchants,
            frequency=frequency,
            exclusions=exclusions,
            location_constraint="domestic" if "domestic" in lower or "flight" in lower else None,
            purpose_context=purpose,
        )

        return VoiceParseResponse(
            raw_transcript=clean_text,
            parsed_mandate=mandate_obj,
            extraction_notes=notes,
            confidence_of_parsing=0.92,
        )
