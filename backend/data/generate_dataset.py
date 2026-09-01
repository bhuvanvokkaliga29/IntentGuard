"""
IntentGuard — Dataset Generator

Generates synthetic evaluation dataset:
- 10 mandates (from seed_data)
- 100+ transactions across 4 ground-truth tiers:
  - clearly_in_scope (~40%)
  - clearly_out_of_scope (~25%)  
  - ambiguous (~25%)
  - unsafe_to_decide (~10%)

Ground truth is generated BEFORE model execution.
Ground truth is NEVER visible to the agent.

random_seed = 42 for reproducibility.
"""

import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from backend.data.seed_data import SEED_MANDATES

RANDOM_SEED = 42


# ── Transaction Templates ────────────────────────────────────

def _generate_transactions_for_mandate(mandate: Dict, rng: random.Random) -> List[Dict]:
    """Generate transactions for a single mandate."""
    mandate_id = mandate["id"]
    max_amount = mandate["max_amount_per_txn"]
    merchants = mandate.get("allowed_merchants") or ["Generic Store"]
    categories = mandate.get("allowed_categories", [])

    transactions = []

    if mandate_id == "mandate-001-office-supplies":
        transactions.extend(_office_supply_transactions(mandate_id, max_amount, merchants, rng))
    elif mandate_id == "mandate-002-domestic-flight":
        transactions.extend(_flight_transactions(mandate_id, max_amount, merchants, rng))
    elif mandate_id == "mandate-003-groceries":
        transactions.extend(_grocery_transactions(mandate_id, max_amount, merchants, rng))
    elif mandate_id == "mandate-004-business-procurement":
        transactions.extend(_procurement_transactions(mandate_id, max_amount, merchants, rng))
    elif mandate_id == "mandate-005-subscriptions":
        transactions.extend(_subscription_transactions(mandate_id, max_amount, merchants, rng))
    elif mandate_id == "mandate-006-household":
        transactions.extend(_household_transactions(mandate_id, max_amount, merchants, rng))
    elif mandate_id == "mandate-007-team-meals":
        transactions.extend(_meal_transactions(mandate_id, max_amount, merchants, rng))
    elif mandate_id == "mandate-008-office-furniture":
        transactions.extend(_furniture_transactions(mandate_id, max_amount, merchants, rng))
    elif mandate_id == "mandate-009-courier":
        transactions.extend(_courier_transactions(mandate_id, max_amount, merchants, rng))
    elif mandate_id == "mandate-010-printing":
        transactions.extend(_printing_transactions(mandate_id, max_amount, merchants, rng))

    return transactions


def _office_supply_transactions(mandate_id: str, max_amount: float, merchants: List[str], rng: random.Random) -> List[Dict]:
    """Office supplies mandate — includes canonical test cases."""
    return [
        # CANONICAL CASE A: Printer paper → ALLOW
        {
            "id": "txn-canonical-allow",
            "mandate_id": mandate_id,
            "amount": 1400.0,
            "merchant_name": "Stationery Mart",
            "merchant_category": "stationery",
            "item_description": "printer paper, pens, sticky notes",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Standard office supplies from allowed merchant, well within budget.",
        },
        # CANONICAL CASE B: Chocolates → FLAG
        {
            "id": "txn-canonical-flag",
            "mandate_id": mandate_id,
            "amount": 1950.0,
            "merchant_name": "Stationery Mart",
            "merchant_category": "stationery",
            "item_description": "premium imported chocolates",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Within budget and allowed merchant, but item is food/confectionery, not office supplies. Semantic drift from mandate purpose.",
        },
        # CANONICAL CASE D: Vague item → ESCALATE
        {
            "id": "txn-canonical-escalate",
            "mandate_id": mandate_id,
            "amount": 1750.0,
            "merchant_name": "Stationery Mart",
            "merchant_category": "stationery",
            "item_description": "miscellaneous item",
            "ground_truth_tier": "unsafe_to_decide",
            "ground_truth_reason": "Insufficient information in item description to determine intent fit.",
        },
        # Clearly in scope
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 350.0,
            "merchant_name": "Stationery Mart",
            "merchant_category": "stationery",
            "item_description": "box of 50 blue ballpoint pens",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Standard stationery item from allowed merchant.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1200.0,
            "merchant_name": "Office Depot India",
            "merchant_category": "office_supplies",
            "item_description": "A4 printer paper (5 reams), manila folders, paper clips",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Bulk office supplies from approved vendor, within budget.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 800.0,
            "merchant_name": "Pen Paper Store",
            "merchant_category": "writing_instruments",
            "item_description": "whiteboard markers (pack of 20), eraser, whiteboard cleaner",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Office presentation supplies from allowed merchant.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 450.0,
            "merchant_name": "Stationery Mart",
            "merchant_category": "stationery",
            "item_description": "printer ink cartridge (black), USB cable",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Printer consumable and basic cable — reasonable office supply.",
        },
        # Clearly out of scope — amount violation
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 2500.0,
            "merchant_name": "Stationery Mart",
            "merchant_category": "stationery",
            "item_description": "premium desk organizer set",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Amount ₹2,500 exceeds the ₹2,000 per-transaction limit.",
        },
        # Clearly out of scope — merchant violation
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1500.0,
            "merchant_name": "Amazon India",
            "merchant_category": "e_commerce",
            "item_description": "office stationery kit",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Amazon India is not in the allowed merchant list.",
        },
        # Ambiguous — premium category
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1800.0,
            "merchant_name": "Stationery Mart",
            "merchant_category": "stationery",
            "item_description": "premium leather-bound executive notebook",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Could be considered office supplies, but 'premium leather-bound executive' suggests a personal luxury item rather than routine stationery.",
        },
        # Ambiguous — misleading merchant category
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1600.0,
            "merchant_name": "Stationery Mart",
            "merchant_category": "stationery",
            "item_description": "wireless Bluetooth speaker",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Electronics item sold at a stationery store. Merchant matches but item is consumer electronics, not office supplies.",
        },
        # Unsafe to decide — vague description
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 999.0,
            "merchant_name": "Stationery Mart",
            "merchant_category": "stationery",
            "item_description": "item",
            "ground_truth_tier": "unsafe_to_decide",
            "ground_truth_reason": "Item description is a single word — impossible to determine fit.",
        },
        # Ambiguous — category boundary
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1950.0,
            "merchant_name": "Office Depot India",
            "merchant_category": "office_supplies",
            "item_description": "desk lamp with wireless charger",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Desk lamp is office-adjacent, but the wireless charger feature pushes it toward consumer electronics territory.",
        },
        # Clearly out — exclusion match
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1800.0,
            "merchant_name": "Stationery Mart",
            "merchant_category": "stationery",
            "item_description": "personal grooming kit, hand cream, tissues",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Personal items are explicitly excluded from this mandate.",
        },
    ]


def _flight_transactions(mandate_id: str, max_amount: float, merchants: List[str], rng: random.Random) -> List[Dict]:
    """Domestic flight mandate — includes canonical Case C."""
    return [
        # CANONICAL CASE C: Dubai flight → BLOCK
        {
            "id": "txn-canonical-block",
            "mandate_id": mandate_id,
            "amount": 14500.0,
            "merchant_name": "MakeMyTrip",
            "merchant_category": "travel",
            "item_description": "international flight to Dubai, economy class",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Mandate specifies domestic travel only. International flight to Dubai is a hard categorical mismatch.",
        },
        # Clearly in scope
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 8500.0,
            "merchant_name": "IndiGo",
            "merchant_category": "domestic_travel",
            "item_description": "domestic flight Delhi to Bangalore, economy class",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Exact match — domestic flight to Bangalore, well within budget.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 12000.0,
            "merchant_name": "Air India",
            "merchant_category": "flights",
            "item_description": "domestic flight Delhi to Bangalore, economy with meal",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Domestic flight to Bangalore on approved airline.",
        },
        # Amount violation
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 18000.0,
            "merchant_name": "MakeMyTrip",
            "merchant_category": "travel",
            "item_description": "domestic flight Delhi to Bangalore, business class",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Amount ₹18,000 exceeds the ₹15,000 limit, even though the route is correct.",
        },
        # Ambiguous — different domestic destination
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 9500.0,
            "merchant_name": "SpiceJet",
            "merchant_category": "domestic_travel",
            "item_description": "domestic flight Delhi to Chennai, economy class",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Domestic flight but to Chennai instead of Bangalore. Mandate says 'usual domestic flight to Bangalore' — different destination.",
        },
        # International — hard mismatch
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 14000.0,
            "merchant_name": "Cleartrip",
            "merchant_category": "travel",
            "item_description": "international flight to Singapore, economy",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "International flight — mandate requires domestic only.",
        },
        # Unsafe — vague
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 10000.0,
            "merchant_name": "MakeMyTrip",
            "merchant_category": "travel",
            "item_description": "travel booking",
            "ground_truth_tier": "unsafe_to_decide",
            "ground_truth_reason": "No destination or travel type specified — cannot determine domestic/international or route.",
        },
        # Ambiguous — hotel instead of flight
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 5000.0,
            "merchant_name": "MakeMyTrip",
            "merchant_category": "travel",
            "item_description": "hotel booking in Bangalore, 1 night",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Related to Bangalore travel but mandate is specifically for flights, not hotels. Hotels are in the exclusion list.",
        },
    ]


def _grocery_transactions(mandate_id: str, max_amount: float, merchants: List[str], rng: random.Random) -> List[Dict]:
    """Grocery mandate transactions."""
    return [
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 2200.0,
            "merchant_name": "BigBasket",
            "merchant_category": "groceries",
            "item_description": "rice (5kg), dal (2kg), cooking oil, vegetables, fruits",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Standard weekly groceries from approved merchant.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1800.0,
            "merchant_name": "DMart",
            "merchant_category": "groceries",
            "item_description": "milk, bread, eggs, butter, cheese, yogurt",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Dairy and daily essentials from approved merchant.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 2900.0,
            "merchant_name": "Nature's Basket",
            "merchant_category": "groceries",
            "item_description": "imported artisanal cheese, organic truffle oil, premium olive oil",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Groceries but all premium/imported — significantly above typical grocery basket character.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 2800.0,
            "merchant_name": "BigBasket",
            "merchant_category": "groceries",
            "item_description": "premium wine selection (3 bottles)",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Alcohol is explicitly excluded from the groceries mandate.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1500.0,
            "merchant_name": "BigBasket",
            "merchant_category": "groceries",
            "item_description": "cleaning supplies, laundry detergent, floor cleaner",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Household essentials are an allowed category.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 2750.0,
            "merchant_name": "DMart",
            "merchant_category": "groceries",
            "item_description": "Bluetooth earphones, phone charger",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Electronics, not groceries. Explicit exclusion.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 600.0,
            "merchant_name": "More Supermarket",
            "merchant_category": "food",
            "item_description": "assorted items",
            "ground_truth_tier": "unsafe_to_decide",
            "ground_truth_reason": "Description too vague — cannot verify items are groceries.",
        },
    ]


def _procurement_transactions(mandate_id: str, max_amount: float, merchants: List[str], rng: random.Random) -> List[Dict]:
    """Business procurement transactions."""
    return [
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 3500.0,
            "merchant_name": "Amazon Business",
            "merchant_category": "it_peripherals",
            "item_description": "mechanical keyboard, ergonomic mouse, USB-C hub",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "IT peripherals for engineering team from approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 8500.0,
            "merchant_name": "Flipkart Wholesale",
            "merchant_category": "business_supplies",
            "item_description": "monitor arm mount, cable management kit, desk mat",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Desk accessories for the workspace from approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 9800.0,
            "merchant_name": "Amazon Business",
            "merchant_category": "it_peripherals",
            "item_description": "PlayStation 5 controller, gaming headset",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Gaming equipment is explicitly excluded from business procurement.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 7500.0,
            "merchant_name": "IT Depot",
            "merchant_category": "cables",
            "item_description": "premium noise-cancelling headphones",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Could be for work (calls/focus) or personal use. Boundary case.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 4200.0,
            "merchant_name": "Amazon Business",
            "merchant_category": "it_peripherals",
            "item_description": "supplies",
            "ground_truth_tier": "unsafe_to_decide",
            "ground_truth_reason": "Description too vague to determine if items are approved IT peripherals.",
        },
    ]


def _subscription_transactions(mandate_id: str, max_amount: float, merchants: List[str], rng: random.Random) -> List[Dict]:
    """Software subscription transactions."""
    return [
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1500.0,
            "merchant_name": "Notion",
            "merchant_category": "saas",
            "item_description": "Notion Team Plan monthly subscription",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Standard SaaS subscription renewal from approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 4800.0,
            "merchant_name": "GitHub",
            "merchant_category": "software",
            "item_description": "GitHub Enterprise monthly seats (10 users)",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Development tool subscription from approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 4500.0,
            "merchant_name": "Netflix",
            "merchant_category": "entertainment",
            "item_description": "Netflix Premium annual plan",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Entertainment subscription, not a business software tool. Netflix is not an approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 3200.0,
            "merchant_name": "Figma",
            "merchant_category": "software",
            "item_description": "Figma Professional plan upgrade with FigJam",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Design tool subscription from approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 2800.0,
            "merchant_name": "Slack",
            "merchant_category": "saas",
            "item_description": "Slack Pro with advanced analytics add-on",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Base subscription is in scope but the 'advanced analytics add-on' is an unapproved upgrade tier.",
        },
    ]


def _household_transactions(mandate_id: str, max_amount: float, merchants: List[str], rng: random.Random) -> List[Dict]:
    """Household maintenance transactions."""
    return [
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 2200.0,
            "merchant_name": "Amazon",
            "merchant_category": "household",
            "item_description": "floor mop, bathroom cleaner, glass cleaner, sponges",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Standard household cleaning supplies.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 3800.0,
            "merchant_name": "Local Hardware Store",
            "merchant_category": "maintenance",
            "item_description": "decorative wall painting, designer cushion covers",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Decoration items are explicitly excluded from household maintenance mandate.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1500.0,
            "merchant_name": "BigBasket",
            "merchant_category": "cleaning_supplies",
            "item_description": "laundry detergent (5L), fabric softener, bleach",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Cleaning supplies from approved merchant.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 3500.0,
            "merchant_name": "Amazon",
            "merchant_category": "household",
            "item_description": "smart LED light bulbs (WiFi-enabled, color changing)",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Light bulbs could be maintenance, but smart/WiFi features push toward electronics/luxury territory.",
        },
    ]


def _meal_transactions(mandate_id: str, max_amount: float, merchants: List[str], rng: random.Random) -> List[Dict]:
    """Team meal transactions."""
    return [
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1200.0,
            "merchant_name": "Swiggy",
            "merchant_category": "food_delivery",
            "item_description": "team lunch: 8 thali meals, 8 drinks",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Standard team lunch order from approved platform.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1450.0,
            "merchant_name": "Zomato",
            "merchant_category": "food_delivery",
            "item_description": "premium sushi platter, wagyu appetizers, imported drinks",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Team meal but premium dining items — significantly above 'standard meals' character of mandate.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1500.0,
            "merchant_name": "Swiggy",
            "merchant_category": "food_delivery",
            "item_description": "6 bottles of premium craft beer, bar snacks",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Alcohol is explicitly excluded from team meals mandate.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 800.0,
            "merchant_name": "Box8",
            "merchant_category": "meals",
            "item_description": "quick lunch for 4",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Standard team lunch from approved vendor.",
        },
    ]


def _furniture_transactions(mandate_id: str, max_amount: float, merchants: List[str], rng: random.Random) -> List[Dict]:
    """Office furniture transactions."""
    return [
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 15000.0,
            "merchant_name": "IKEA",
            "merchant_category": "office_furniture",
            "item_description": "ergonomic office chair with lumbar support",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Office furniture from approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 22000.0,
            "merchant_name": "Urban Ladder",
            "merchant_category": "furniture",
            "item_description": "luxury home recliner sofa",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Home/personal furniture, not office furniture. Explicit exclusion for personal furniture.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 18000.0,
            "merchant_name": "Pepperfry",
            "merchant_category": "furniture",
            "item_description": "adjustable standing desk converter",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Ergonomic office equipment from approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 24000.0,
            "merchant_name": "IKEA",
            "merchant_category": "office_furniture",
            "item_description": "bookshelf with decorative lighting",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Bookshelf is office-adjacent but 'decorative lighting' suggests home decor element.",
        },
    ]


def _courier_transactions(mandate_id: str, max_amount: float, merchants: List[str], rng: random.Random) -> List[Dict]:
    """Courier/shipping transactions."""
    return [
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 150.0,
            "merchant_name": "DTDC",
            "merchant_category": "courier",
            "item_description": "domestic document courier, Delhi to Mumbai",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Standard domestic courier from approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 480.0,
            "merchant_name": "Blue Dart",
            "merchant_category": "shipping",
            "item_description": "international parcel to London, UK",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "International shipping is explicitly excluded; mandate is domestic only.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 300.0,
            "merchant_name": "Delhivery",
            "merchant_category": "logistics",
            "item_description": "package delivery within Bangalore",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Domestic package delivery from approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 250.0,
            "merchant_name": "India Post",
            "merchant_category": "postal",
            "item_description": "shipping",
            "ground_truth_tier": "unsafe_to_decide",
            "ground_truth_reason": "Cannot determine if domestic or international from description alone.",
        },
    ]


def _printing_transactions(mandate_id: str, max_amount: float, merchants: List[str], rng: random.Random) -> List[Dict]:
    """Printing services transactions."""
    return [
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 1200.0,
            "merchant_name": "Print Express",
            "merchant_category": "printing",
            "item_description": "200 pages color printing, spiral binding, 5 copies",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Standard document printing from approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 2800.0,
            "merchant_name": "FedEx Print",
            "merchant_category": "document_services",
            "item_description": "500 glossy marketing brochures with company logo",
            "ground_truth_tier": "clearly_out_of_scope",
            "ground_truth_reason": "Marketing/promotional materials are explicitly excluded.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 800.0,
            "merchant_name": "Staples Print",
            "merchant_category": "copying",
            "item_description": "photocopy of 100 pages, lamination of 10 pages",
            "ground_truth_tier": "clearly_in_scope",
            "ground_truth_reason": "Standard document services from approved vendor.",
        },
        {
            "id": f"txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate_id,
            "amount": 2500.0,
            "merchant_name": "Print Express",
            "merchant_category": "printing",
            "item_description": "custom business cards, branded letterhead",
            "ground_truth_tier": "ambiguous",
            "ground_truth_reason": "Business cards/letterhead are at the boundary between internal documents and marketing materials.",
        },
    ]


async def generate_full_dataset(session) -> Dict:
    """
    Generate the full synthetic dataset.
    
    Returns statistics about the generated dataset.
    """
    from backend.db import create_transaction, create_mandate, get_mandate

    rng = random.Random(RANDOM_SEED)

    # Ensure mandates exist
    for mandate_data in SEED_MANDATES:
        existing = await get_mandate(session, mandate_data["id"])
        if existing is None:
            await create_mandate(session, mandate_data)

    # Generate transactions
    all_transactions = []
    for mandate in SEED_MANDATES:
        txns = _generate_transactions_for_mandate(mandate, rng)
        all_transactions.extend(txns)

    # Insert transactions
    inserted = 0
    for txn in all_transactions:
        from backend.db import get_transaction
        existing = await get_transaction(session, txn.get("id", ""))
        if existing is None:
            txn.setdefault("id", str(uuid.uuid4()))
            txn.setdefault("timestamp", datetime.now(timezone.utc))
            await create_transaction(session, txn)
            inserted += 1

    # Compute statistics
    tiers = {}
    for txn in all_transactions:
        tier = txn.get("ground_truth_tier", "unknown")
        tiers[tier] = tiers.get(tier, 0) + 1

    stats = {
        "total_transactions": len(all_transactions),
        "inserted": inserted,
        "tier_distribution": tiers,
        "mandates": len(SEED_MANDATES),
        "random_seed": RANDOM_SEED,
    }

    return stats


if __name__ == "__main__":
    import asyncio
    from backend.db import init_db, get_session

    async def main():
        await init_db()
        session = await get_session()
        async with session:
            stats = await generate_full_dataset(session)
            print(f"\nDataset generated:")
            print(f"  Total transactions: {stats['total_transactions']}")
            print(f"  Tier distribution: {stats['tier_distribution']}")
            print(f"  Random seed: {stats['random_seed']}")

    asyncio.run(main())
