"""
Deepsyke Natal Type Calculator - 9-year cycle with 108 month blocks.
Derived from the LOHA/Deepsyke core logic.
"""

from datetime import datetime


def get_year_order(year: int) -> int:
    """Calculates the unique year order (1-9 cycle) based on the provided year."""
    years = {}
    year_order_counter = 1
    for y in range(1919, 2031):
        years[y] = year_order_counter
        if year_order_counter == 9:
            year_order_counter = 0
        year_order_counter += 1
    return years.get(year, -1)


def get_month_row(day: int, month: int, year: int) -> int:
    """Determines the 'row' index based on the specific date within the 13-range table."""
    table_ranges = [
        {"row": 0, "from": (1, 1), "to": (1, 5)},
        {"row": 1, "from": (1, 6), "to": (2, 3)},
        {"row": 2, "from": (2, 4), "to": (3, 5)},
        {"row": 3, "from": (3, 6), "to": (4, 4)},
        {"row": 4, "from": (4, 5), "to": (5, 5)},
        {"row": 5, "from": (5, 6), "to": (6, 5)},
        {"row": 6, "from": (6, 6), "to": (7, 7)},
        {"row": 7, "from": (7, 8), "to": (8, 7)},
        {"row": 8, "from": (8, 8), "to": (9, 7)},
        {"row": 9, "from": (9, 8), "to": (10, 8)},
        {"row": 10, "from": (10, 9), "to": (11, 7)},
        {"row": 11, "from": (11, 8), "to": (12, 7)},
        {"row": 12, "from": (12, 8), "to": (12, 31)}
    ]

    user_date = datetime(year, month, day)

    for item in table_ranges:
        from_month, from_day = item["from"]
        to_month, to_day = item["to"]
        date_from = datetime(year, from_month, from_day)
        date_to = datetime(year, to_month, to_day)

        if item["row"] == 0:
            if date_from <= user_date <= date_to:
                return 12
        else:
            if date_from <= user_date <= date_to:
                return item["row"]

    return -1


def calculate_natal_type_from_dob(dob: str, gender: str) -> str:
    """Convenience function. Accepts YYYY-MM-DD."""
    try:
        parts = dob.split('-')
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
    except Exception:
        raise ValueError(f"Invalid date format: {dob}. Expected YYYY-MM-DD")
    return calculate_natal_type(day, month, year, gender)


def calculate_natal_type(day: int, month: int, year: int, gender: str) -> str:
    """
    Calculates the natal Affinity Zone (SS, SD, DS, DD) based on birth date and gender.
    """
    if not (1 <= month <= 12 and 1 <= day <= 31):
        raise ValueError("Invalid month or day.")
    if not (1919 <= year <= 2030):
        raise ValueError("Year out of supported range (1919-2030).")
    if gender not in ["male", "female"]:
        raise ValueError("Gender must be 'male' or 'female'.")

    male_lookup = {
        1:  {"1": "G", "2": "A", "3": "D", "4": "A", "5": "A", "6": "D", "7": "A", "8": "G", "9": "B"},
        2:  {"1": "G", "2": "B", "3": "G", "4": "A", "5": "B", "6": "G", "7": "A", "8": "D", "9": "A"},
        3:  {"1": "D", "2": "A", "3": "D", "4": "B", "5": "A", "6": "D", "7": "B", "8": "G", "9": "B"},
        4:  {"1": "G", "2": "B", "3": "G", "4": "A", "5": "B", "6": "G", "7": "A", "8": "D", "9": "A"},
        5:  {"1": "D", "2": "A", "3": "G", "4": "B", "5": "A", "6": "G", "7": "B", "8": "G", "9": "A"},
        6:  {"1": "G", "2": "B", "3": "D", "4": "A", "5": "B", "6": "D", "7": "A", "8": "D", "9": "B"},
        7:  {"1": "D", "2": "A", "3": "G", "4": "B", "5": "A", "6": "G", "7": "B", "8": "G", "9": "A"},
        8:  {"1": "G", "2": "A", "3": "D", "4": "A", "5": "A", "6": "D", "7": "A", "8": "G", "9": "B"},
        9:  {"1": "D", "2": "B", "3": "G", "4": "B", "5": "B", "6": "G", "7": "B", "8": "D", "9": "A"},
        10: {"1": "G", "2": "A", "3": "D", "4": "A", "5": "A", "6": "D", "7": "A", "8": "G", "9": "B"},
        11: {"1": "G", "2": "B", "3": "G", "4": "A", "5": "B", "6": "G", "7": "A", "8": "D", "9": "A"},
        12: {"1": "D", "2": "A", "3": "D", "4": "B", "5": "A", "6": "D", "7": "B", "8": "G", "9": "B"}
    }

    female_lookup = {
        1:  {"1": "G", "2": "A", "3": "D", "4": "A", "5": "G", "6": "D", "7": "A", "8": "G", "9": "B"},
        2:  {"1": "D", "2": "B", "3": "G", "4": "B", "5": "D", "6": "G", "7": "B", "8": "D", "9": "A"},
        3:  {"1": "D", "2": "A", "3": "D", "4": "B", "5": "G", "6": "D", "7": "B", "8": "G", "9": "B"},
        4:  {"1": "G", "2": "B", "3": "G", "4": "A", "5": "D", "6": "G", "7": "A", "8": "D", "9": "A"},
        5:  {"1": "D", "2": "A", "3": "D", "4": "B", "5": "G", "6": "D", "7": "B", "8": "G", "9": "B"},
        6:  {"1": "G", "2": "B", "3": "D", "4": "A", "5": "D", "6": "D", "7": "A", "8": "D", "9": "B"},
        7:  {"1": "D", "2": "A", "3": "G", "4": "B", "5": "G", "6": "G", "7": "B", "8": "G", "9": "A"},
        8:  {"1": "G", "2": "B", "3": "D", "4": "A", "5": "D", "6": "D", "7": "A", "8": "D", "9": "B"},
        9:  {"1": "D", "2": "B", "3": "G", "4": "B", "5": "D", "6": "G", "7": "B", "8": "D", "9": "A"},
        10: {"1": "G", "2": "A", "3": "D", "4": "A", "5": "G", "6": "D", "7": "A", "8": "G", "9": "B"},
        11: {"1": "D", "2": "B", "3": "G", "4": "B", "5": "D", "6": "G", "7": "B", "8": "D", "9": "A"},
        12: {"1": "D", "2": "A", "3": "D", "4": "B", "5": "G", "6": "D", "7": "B", "8": "G", "9": "B"}
    }

    affinity_map = {
        "D": "SS",
        "B": "DS",
        "A": "DD",
        "G": "SD"
    }

    current_year = year
    month_row_index = get_month_row(day, month, current_year)

    if month_row_index == 12 and month == 1 and day <= 5:
        current_year -= 1

    year_order = get_year_order(current_year)

    if year_order == -1:
        raise ValueError("Year order could not be determined.")

    if gender == "male":
        letter_code = male_lookup[month_row_index][str(year_order)]
    else:
        letter_code = female_lookup[month_row_index][str(year_order)]

    return affinity_map.get(letter_code, "UNKNOWN_TYPE")


def get_archetype(natal_type: str, gender: str) -> dict:
    """Returns full archetype info for a natal type + gender combo."""
    archetypes = {
        "SS": {
            "male": {
                "name": "Magician",
                "title": "The Magician",
                "essence": "Intuitive, creative, seeing depths others miss",
                "energy": "Yin-Yin",
                "element": "Water",
                "color": "#6B7FD4",
                "description": "You see what others miss. Your depth is your superpower — mysterious, perceptive, and quietly magnetic."
            },
            "female": {
                "name": "Mystic",
                "title": "The Mystic",
                "essence": "Soft, spiritual, deeply feminine, and more powerful than she knows",
                "energy": "Yin-Yin",
                "element": "Water",
                "color": "#9B6BD4",
                "description": "You feel everything deeply. Your intuition and emotional depth create connections that others can only dream of."
            }
        },
        "SD": {
            "male": {
                "name": "Knight",
                "title": "The Knight",
                "essence": "Loyal, structured, the protector with a gentle heart",
                "energy": "Yin-Yang",
                "element": "Earth",
                "color": "#4A9B6F",
                "description": "You are the rare balance — driven but grounded, ambitious but loyal. People naturally trust you."
            },
            "female": {
                "name": "Maiden",
                "title": "The Maiden",
                "essence": "Balanced, supportive, quietly ambitious and deeply caring",
                "energy": "Yin-Yang",
                "element": "Earth",
                "color": "#6FB87A",
                "description": "You bring harmony wherever you go. Your grace under pressure and genuine warmth make you unforgettable."
            }
        },
        "DS": {
            "male": {
                "name": "Warrior",
                "title": "The Warrior",
                "essence": "Bold, creative, a force of nature with a soulful core",
                "energy": "Yang-Yin",
                "element": "Fire",
                "color": "#D4844A",
                "description": "You move fast but feel deeply. Your creative energy and bold presence are impossible to ignore."
            },
            "female": {
                "name": "Queen",
                "title": "The Queen",
                "essence": "Powerful, visionary, commanding with grace and wisdom",
                "energy": "Yang-Yin",
                "element": "Fire",
                "color": "#D4A84A",
                "description": "You don't enter rooms — you change them. Your vision and presence are your crown."
            }
        },
        "DD": {
            "male": {
                "name": "King",
                "title": "The King",
                "essence": "Decisive, powerful, built for conquest and legacy",
                "energy": "Yang-Yang",
                "element": "Lightning",
                "color": "#D44A4A",
                "description": "You are built for impact. Your drive, decisiveness, and magnetic confidence draw people into your orbit."
            },
            "female": {
                "name": "Huntress",
                "title": "The Huntress",
                "essence": "Fierce, independent, a force of nature who knows exactly what she wants",
                "energy": "Yang-Yang",
                "element": "Lightning",
                "color": "#C44A7A",
                "description": "You pursue life on your own terms. Your independence, fire, and focus are irresistible."
            }
        }
    }
    return archetypes.get(natal_type, {}).get(gender, archetypes["SS"]["female"])


def get_loi_score(answers: dict) -> int:
    """
    Calculate LOI (Level of Identification) score from Deepsyke questionnaire answers.
    Returns 0-100 score. Higher = more aligned with natal type.
    """
    score = 50  # baseline

    # Each answer contributes to LOI adjustment
    loi_indicators = answers.get('loi_indicators', {})

    # Q1: Do you feel at peace with who you are? (alignment indicator)
    peace = loi_indicators.get('peace_with_self', 3)  # 1-5 scale
    score += (peace - 3) * 5

    # Q2: How often do you act against your true nature?
    authenticity = loi_indicators.get('authenticity', 3)
    score += (authenticity - 3) * 4

    # Q3: External vs internal validation seeking
    validation = loi_indicators.get('internal_validation', 3)
    score += (validation - 3) * 4

    # Q4: Stability in relationships
    stability = loi_indicators.get('relationship_stability', 3)
    score += (stability - 3) * 3

    # Q5: Decision making comfort
    decisions = loi_indicators.get('decision_comfort', 3)
    score += (decisions - 3) * 4

    return max(0, min(100, score))


def get_compatibility_dynamic(type_a: str, type_b: str, loi_a: int, loi_b: int) -> dict:
    """
    Returns the compatibility dynamic between two types based on their LOI scores.
    """
    # Affinity zones (same type)
    affinity = type_a == type_b

    # Wholeness (opposite types)
    opposites = {
        "SS": "DD",
        "DD": "SS",
        "SD": "DS",
        "DS": "SD"
    }

    is_opposite = opposites.get(type_a) == type_b

    # Cross-chemical dynamics
    cross_dynamics = {
        ("SS", "DS"): "Depth & Design",
        ("DS", "SS"): "Depth & Design",
        ("SD", "DD"): "Nurturer & Thrill-Seeker",
        ("DD", "SD"): "Nurturer & Thrill-Seeker",
        ("SS", "SD"): "The Still Lake & The River",
        ("SD", "SS"): "The Still Lake & The River",
        ("DS", "DD"): "The Creative & The Conqueror",
        ("DD", "DS"): "The Creative & The Conqueror",
    }

    # Compatibility scores
    base_scores = {
        # Affinity zones
        ("SS", "SS"): 85, ("SD", "SD"): 82, ("DS", "DS"): 80, ("DD", "DD"): 78,
        # Wholeness pairings
        ("SS", "DD"): 88, ("DD", "SS"): 88,
        ("SD", "DS"): 86, ("DS", "SD"): 86,
        # Cross-chemical
        ("SS", "SD"): 75, ("SD", "SS"): 75,
        ("SS", "DS"): 70, ("DS", "SS"): 70,
        ("SD", "DD"): 72, ("DD", "SD"): 72,
        ("DS", "DD"): 74, ("DD", "DS"): 74,
    }

    base_score = base_scores.get((type_a, type_b), 65)

    # LOI adjustments
    # High LOI + Affinity = Harmony bonus
    if affinity and loi_a >= 50 and loi_b >= 50:
        base_score += 8
        dynamic_type = "Affinity Zone — Same Gear"
    # Low LOI + Opposite = Wholeness bonus
    elif is_opposite and loi_a < 50 and loi_b < 50:
        base_score += 10
        dynamic_type = "Wholeness Protocol — Seeking Integration"
    elif is_opposite:
        base_score += 5
        dynamic_type = "Polarity Dynamic — Growth Laboratory"
    elif affinity:
        dynamic_type = "Affinity Resonance"
    else:
        dynamic_type = cross_dynamics.get((type_a, type_b), "Cross-Chemical Spark")

    return {
        "score": min(99, base_score),
        "dynamic": dynamic_type,
        "affinity": affinity,
        "is_opposite": is_opposite
    }