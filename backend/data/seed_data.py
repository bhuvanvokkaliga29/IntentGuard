"""
IntentGuard — Seed Data

10 mandates covering the required categories:
1. Office supplies (canonical)
2. Domestic travel (canonical)
3. Groceries
4. Business procurement
5. Software subscriptions
6. Household recurring
7. Team meals
8. Office furniture
9. Courier/shipping
10. Printing services

Each mandate includes: intent_text, max_amount_per_txn, budget_cap,
allowed_categories, allowed_merchants, frequency, optional exclusions,
optional location, optional purpose context.
"""

SEED_MANDATES = [
    {
        "id": "mandate-001-office-supplies",
        "intent_text": "Buy my regular office supplies up to ₹2,000 per week from our usual stationery suppliers.",
        "max_amount_per_txn": 2000.0,
        "budget_cap": 8000.0,
        "allowed_categories": ["office_supplies", "stationery", "writing_instruments", "paper_products"],
        "allowed_merchants": ["Stationery Mart", "Office Depot India", "Pen Paper Store"],
        "frequency": "weekly",
        "exclusions": ["electronics", "furniture", "food", "beverages", "personal_items"],
        "location_constraint": None,
        "purpose_context": "Routine restocking of office consumables — paper, pens, folders, sticky notes, printer cartridges.",
    },
    {
        "id": "mandate-002-domestic-flight",
        "intent_text": "Book my usual domestic flight to Bangalore under ₹15,000.",
        "max_amount_per_txn": 15000.0,
        "budget_cap": 15000.0,
        "allowed_categories": ["travel", "flights", "domestic_travel", "air_travel"],
        "allowed_merchants": ["MakeMyTrip", "Cleartrip", "IndiGo", "Air India", "SpiceJet"],
        "frequency": "on_demand",
        "exclusions": ["international_travel", "hotels", "car_rental"],
        "location_constraint": "domestic",
        "purpose_context": "Regular business travel from Delhi to Bangalore. Domestic economy class only.",
    },
    {
        "id": "mandate-003-groceries",
        "intent_text": "Purchase weekly household groceries up to ₹3,000 from our regular supermarket.",
        "max_amount_per_txn": 3000.0,
        "budget_cap": 12000.0,
        "allowed_categories": ["groceries", "food", "household_essentials", "fresh_produce", "dairy"],
        "allowed_merchants": ["BigBasket", "DMart", "More Supermarket", "Nature's Basket"],
        "frequency": "weekly",
        "exclusions": ["alcohol", "tobacco", "luxury_items", "electronics"],
        "location_constraint": None,
        "purpose_context": "Regular weekly grocery shopping — fruits, vegetables, staples, dairy, cleaning supplies.",
    },
    {
        "id": "mandate-004-business-procurement",
        "intent_text": "Procure approved business supplies and equipment for the engineering team, up to ₹10,000 per month from approved vendors.",
        "max_amount_per_txn": 10000.0,
        "budget_cap": 10000.0,
        "allowed_categories": ["business_supplies", "it_peripherals", "cables", "adapters", "desk_accessories"],
        "allowed_merchants": ["Amazon Business", "Flipkart Wholesale", "IT Depot"],
        "frequency": "monthly",
        "exclusions": ["personal_electronics", "gaming", "luxury_items"],
        "location_constraint": None,
        "purpose_context": "Engineering team procurement — keyboards, mice, cables, USB hubs, monitor stands, and similar desk peripherals.",
    },
    {
        "id": "mandate-005-subscriptions",
        "intent_text": "Manage and renew our regular software subscriptions, each under ₹5,000 per month.",
        "max_amount_per_txn": 5000.0,
        "budget_cap": 25000.0,
        "allowed_categories": ["software", "saas", "subscriptions", "cloud_services"],
        "allowed_merchants": ["Google Workspace", "Slack", "Notion", "Figma", "GitHub", "AWS"],
        "frequency": "monthly",
        "exclusions": ["hardware", "physical_goods"],
        "location_constraint": None,
        "purpose_context": "Routine SaaS subscription renewals for the team's productivity and development tools.",
    },
    {
        "id": "mandate-006-household",
        "intent_text": "Handle recurring household maintenance and cleaning purchases up to ₹4,000 per month.",
        "max_amount_per_txn": 4000.0,
        "budget_cap": 4000.0,
        "allowed_categories": ["household", "cleaning_supplies", "maintenance", "home_care"],
        "allowed_merchants": ["BigBasket", "Amazon", "Local Hardware Store"],
        "frequency": "monthly",
        "exclusions": ["furniture", "electronics", "decoration", "luxury_items"],
        "location_constraint": None,
        "purpose_context": "Monthly household cleaning and maintenance supplies — detergent, mops, light bulbs, minor repair items.",
    },
    {
        "id": "mandate-007-team-meals",
        "intent_text": "Order team lunch for up to 8 people, maximum ₹1,500 per day from approved restaurants.",
        "max_amount_per_txn": 1500.0,
        "budget_cap": 30000.0,
        "allowed_categories": ["food_delivery", "restaurant", "catering", "meals"],
        "allowed_merchants": ["Swiggy", "Zomato", "Box8", "FreshMenu"],
        "frequency": "daily",
        "exclusions": ["alcohol", "tobacco", "personal_meals"],
        "location_constraint": None,
        "purpose_context": "Daily team lunch orders for the office. Standard meals, no premium dining.",
    },
    {
        "id": "mandate-008-office-furniture",
        "intent_text": "Purchase approved office furniture items up to ₹25,000 from designated furniture suppliers.",
        "max_amount_per_txn": 25000.0,
        "budget_cap": 100000.0,
        "allowed_categories": ["furniture", "office_furniture", "ergonomic_equipment"],
        "allowed_merchants": ["IKEA", "Urban Ladder", "Pepperfry", "Nilkamal"],
        "frequency": "on_demand",
        "exclusions": ["home_decor", "personal_furniture", "luxury_furniture"],
        "location_constraint": None,
        "purpose_context": "Office furniture procurement — desks, chairs, storage units, monitor arms for the workspace.",
    },
    {
        "id": "mandate-009-courier",
        "intent_text": "Send office courier and shipping packages, each under ₹500 per shipment.",
        "max_amount_per_txn": 500.0,
        "budget_cap": 5000.0,
        "allowed_categories": ["courier", "shipping", "logistics", "postal"],
        "allowed_merchants": ["DTDC", "Blue Dart", "Delhivery", "India Post"],
        "frequency": "on_demand",
        "exclusions": ["international_shipping"],
        "location_constraint": "domestic",
        "purpose_context": "Domestic courier services for sending documents and small packages within India.",
    },
    {
        "id": "mandate-010-printing",
        "intent_text": "Order printing and document services up to ₹3,000 per month from our regular print shop.",
        "max_amount_per_txn": 3000.0,
        "budget_cap": 3000.0,
        "allowed_categories": ["printing", "document_services", "copying", "binding"],
        "allowed_merchants": ["Print Express", "Staples Print", "FedEx Print"],
        "frequency": "monthly",
        "exclusions": ["promotional_materials", "marketing_collateral"],
        "location_constraint": None,
        "purpose_context": "Document printing, binding, and photocopying for internal office use.",
    },
    {
        "id": "mandate-008-vague",
        "intent_text": "Buy something useful for the office.",
        "max_amount_per_txn": 2000.0,
        "budget_cap": 8000.0,
        "allowed_categories": ["office_supplies", "stationery", "general"],
        "allowed_merchants": ["Stationery Mart", "Office Depot India", "Pen Paper Store"],
        "frequency": "weekly",
        "exclusions": [],
        "location_constraint": None,
        "purpose_context": "Buy something useful for the office.",
    },
]


async def seed_mandates():
    """Insert all seed mandates into the database."""
    from backend.db import get_session, create_mandate, get_mandate

    async with await get_session() as session:
        for mandate_data in SEED_MANDATES:
            existing = await get_mandate(session, mandate_data["id"])
            if existing is None:
                await create_mandate(session, mandate_data)
                print(f"  OK Seeded mandate: {mandate_data['id']}")
            else:
                print(f"  - Mandate already exists: {mandate_data['id']}")


if __name__ == "__main__":
    import asyncio
    from backend.db import init_db

    async def main():
        await init_db()
        await seed_mandates()
        print("\nDone — 10 mandates seeded.")

    asyncio.run(main())
