from decimal import Decimal

from app.models.product import Product


def seeded_products() -> list[Product]:
    """Return fresh objects so callers cannot mutate shared fallback state."""
    rows = [
        (1, "RUN-TRAIL-001", "TrailBlaze Running Shoes", "Lightweight cushioned shoes for daily runs", "Footwear", "Running", "Stride Sports", "89.99", 4.7, {"weight_g": 255, "drop_mm": 8, "surface": "road", "cushion": "medium"}),
        (2, "RUN-BAG-002", "Urban Commuter Backpack", "Water-resistant 24L laptop and training backpack", "Bags", "Running", "North & Co.", "64.50", 4.5, {"capacity_l": 24, "water_resistant": True, "weight_g": 720}),
        (3, "FIT-WATCH-003", "AeroFit Smartwatch", "GPS multisport watch with heart-rate tracking", "Electronics", "Multisport", "AeroFit", "179.00", 4.6, {"gps": True, "battery_days": 10, "water_rating": "5 ATM", "heart_rate": True}),
        (4, "FIT-HOOD-004", "CloudSoft Hoodie", "Organic cotton warm-up and recovery hoodie", "Clothing", "Fitness", "Common Thread", "52.00", 4.4, {"material": "organic cotton", "fit": "regular", "machine_washable": True}),
        (5, "OUT-BOT-005", "Summit Insulated Bottle", "Stainless steel 750ml sports water bottle", "Outdoors", "Hiking", "Summit Supply", "29.95", 4.8, {"capacity_ml": 750, "insulation_hours": 18, "material": "stainless steel"}),
        (6, "ESP-KEY-006", "QuietKeys Wireless Keyboard", "Compact low-profile Bluetooth esports keyboard", "Electronics", "Esports", "KeyWorks", "74.99", 4.3, {"connection": "Bluetooth", "layout": "75%", "battery_hours": 120}),
        (7, "YOG-MAT-007", "FlexForm Yoga Mat", "Non-slip 6mm exercise and yoga mat", "Fitness", "Yoga", "FlexForm", "38.00", 4.7, {"thickness_mm": 6, "length_cm": 183, "material": "TPE", "non_slip": True}),
        (8, "FIT-DUF-008", "Weekender Canvas Duffel", "Durable gym and travel bag with shoe pocket", "Bags", "Fitness", "Harbor Goods", "79.00", 4.5, {"capacity_l": 38, "shoe_compartment": True, "material": "canvas"}),
        (9, "RUN-RACE-009", "Velocity Carbon Racer", "Carbon-plated lightweight shoe for race day", "Footwear", "Running", "Velocity", "189.00", 4.8, {"weight_g": 198, "drop_mm": 6, "surface": "road", "carbon_plate": True}),
        (10, "FB-BALL-010", "MatchPro Football", "FIFA-quality thermally bonded match football", "Equipment", "Football", "MatchPro", "44.00", 4.6, {"size": 5, "construction": "thermally bonded", "material": "synthetic leather"}),
        (11, "TEN-RKT-011", "ControlSpin Tennis Racket", "Balanced graphite racket for intermediate players", "Equipment", "Tennis", "CourtCraft", "129.00", 4.7, {"weight_g": 285, "head_size_sq_in": 100, "balance": "even", "material": "graphite"}),
        (12, "CYC-HELM-012", "AeroShield Cycling Helmet", "Ventilated road helmet with rotational-impact protection", "Equipment", "Cycling", "AeroShield", "99.00", 4.8, {"weight_g": 270, "vents": 18, "certification": "CPSC", "impact_system": "rotational"}),
    ]
    return [
        Product(
            id=id_,
            sku=sku,
            name=name,
            description=description,
            category=category,
            sport=sport,
            brand=brand,
            specifications=specifications,
            in_stock=True,
            price=Decimal(price),
            currency="USD",
            retailer=brand,
            rating=Decimal(str(rating)),
            image_url=f"https://images.example.com/products/{id_}.jpg",
        )
        for (
            id_,
            sku,
            name,
            description,
            category,
            sport,
            brand,
            price,
            rating,
            specifications,
        ) in rows
    ]
