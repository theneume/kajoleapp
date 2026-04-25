"""
Kajole Matching Engine — Deepsyke-powered daily match algorithm.
Integrates: Natal Type, LOI, Affinity Zones, practical filters, AI feedback loop.
"""

import json
import random
from datetime import datetime, date, timedelta
from natal_calculator import get_compatibility_dynamic, get_archetype


class MatchingEngine:
    def __init__(self, users_db: dict, matches_db: dict):
        self.users = users_db
        self.matches = matches_db

    def calculate_practical_score(self, user: dict, candidate: dict) -> int:
        """Score based on practical preferences (location, age, lifestyle etc.)"""
        score = 0
        prefs = user.get('preferences', {})

        # Age range
        cand_age = candidate.get('age', 30)
        pref_age_min = prefs.get('age_min', 18)
        pref_age_max = prefs.get('age_max', 60)
        if pref_age_min <= cand_age <= pref_age_max:
            score += 20
        elif abs(cand_age - pref_age_min) <= 3 or abs(cand_age - pref_age_max) <= 3:
            score += 10

        # Gender & orientation match
        user_orient = user.get('orientation', 'straight')
        cand_gender = candidate.get('gender', 'female')
        user_gender = user.get('gender', 'male')

        orient_match = False
        if user_orient == 'straight':
            orient_match = cand_gender != user_gender
        elif user_orient == 'gay':
            orient_match = cand_gender == user_gender
        elif user_orient == 'bisexual':
            orient_match = True
        
        if orient_match:
            score += 25
        else:
            return -999  # Hard filter — skip this candidate

        # Location proximity
        user_city = user.get('city', '').lower()
        cand_city = candidate.get('city', '').lower()
        user_country = user.get('country', '').lower()
        cand_country = candidate.get('country', '').lower()
        
        if user_city and cand_city and user_city == cand_city:
            score += 20
        elif user_country and cand_country and user_country == cand_country:
            score += 10
        
        pref_location = prefs.get('location_preference', 'worldwide')
        if pref_location == 'same_city' and user_city == cand_city:
            score += 15
        elif pref_location == 'same_country' and user_country == cand_country:
            score += 10
        elif pref_location == 'worldwide':
            score += 5

        # Religion
        pref_religion = prefs.get('religion', 'any')
        cand_religion = candidate.get('religion', 'none')
        if pref_religion == 'any' or pref_religion == cand_religion:
            score += 10

        # Lifestyle
        user_lifestyle = user.get('lifestyle', [])
        cand_lifestyle = candidate.get('lifestyle', [])
        if isinstance(user_lifestyle, list) and isinstance(cand_lifestyle, list):
            overlap = len(set(user_lifestyle) & set(cand_lifestyle))
            score += min(10, overlap * 3)

        # Ethnicity preference (open = max points)
        pref_ethnicity = prefs.get('ethnicity', 'any')
        cand_ethnicity = candidate.get('ethnicity', 'any')
        if pref_ethnicity == 'any' or pref_ethnicity == cand_ethnicity:
            score += 5

        # Attractiveness threshold
        user_attract_min = prefs.get('attractiveness_min', 5)
        cand_attract = candidate.get('attractiveness_score', 7)
        if cand_attract >= user_attract_min:
            score += 10
        elif cand_attract >= user_attract_min - 1:
            score += 5

        return score

    def calculate_deepsyke_score(self, user: dict, candidate: dict) -> dict:
        """Calculate psychological compatibility using Deepsyke logic."""
        user_type = user.get('natal_type', 'SD')
        cand_type = candidate.get('natal_type', 'SD')
        user_loi = user.get('loi_score', 50)
        cand_loi = candidate.get('loi_score', 50)

        compat = get_compatibility_dynamic(user_type, cand_type, user_loi, cand_loi)
        return compat

    def apply_ai_feedback(self, user: dict, candidates: list) -> list:
        """
        Re-rank candidates based on user's AI feedback history.
        Feedback adjusts weights for future matches.
        """
        feedback_history = user.get('ai_feedback_adjustments', {})
        
        # Extract learned preferences from feedback
        boost_attractiveness = feedback_history.get('want_more_attractive', False)
        boost_intellect = feedback_history.get('want_more_intellectual', False)
        avoid_traveler = feedback_history.get('avoid_heavy_traveler', False)
        avoid_extrovert = feedback_history.get('avoid_extreme_extrovert', False)
        preferred_types = feedback_history.get('preferred_natal_types', [])
        disliked_types = feedback_history.get('disliked_natal_types', [])

        scored = []
        for candidate in candidates:
            adjustment = 0

            # Attractiveness boost
            if boost_attractiveness:
                attract = candidate.get('attractiveness_score', 7)
                adjustment += (attract - 7) * 3  # ±3 per point above/below 7

            # Intellectual boost
            if boost_intellect:
                intel = candidate.get('intellectual_score', 5)
                adjustment += (intel - 5) * 2

            # Avoid heavy traveler
            if avoid_traveler:
                lifestyle = candidate.get('lifestyle', [])
                if 'travel' in lifestyle or 'adventure' in lifestyle:
                    adjustment -= 15

            # Avoid extreme extrovert
            if avoid_extrovert:
                social_style = candidate.get('social_style', 'balanced')
                if social_style == 'extreme_extrovert':
                    adjustment -= 20

            # Type preference boosts
            cand_type = candidate.get('natal_type', '')
            if cand_type in preferred_types:
                adjustment += 20
            if cand_type in disliked_types:
                adjustment -= 20

            scored.append((adjustment, candidate))

        # Sort by adjustment (highest first), maintain relative order otherwise
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored]

    def get_already_seen_ids(self, user_id: str) -> set:
        """Get IDs of profiles already shown to this user."""
        seen = set()
        user_matches = self.matches.get(user_id, [])
        for match in user_matches:
            seen.add(match.get('candidate_id'))
        return seen

    def has_received_match_today(self, user_id: str) -> bool:
        """Check if user already got their daily match."""
        user_matches = self.matches.get(user_id, [])
        if not user_matches:
            return False
        today = date.today().isoformat()
        last_match = user_matches[-1]
        return last_match.get('match_date', '') == today

    def find_daily_match(self, user_id: str) -> dict | None:
        """
        Core matching algorithm — finds the best single daily match.
        Priority: Practical filters → Deepsyke compatibility → AI feedback loop.
        """
        if user_id not in self.users:
            return None

        user = self.users[user_id]
        already_seen = self.get_already_seen_ids(user_id)

        # Pool: all active users except self and already seen
        candidates = []
        for uid, candidate in self.users.items():
            if uid == user_id:
                continue
            if uid in already_seen:
                continue
            if not candidate.get('profile_complete', False):
                continue
            if not candidate.get('active', True):
                continue
            candidates.append(candidate)

        if not candidates:
            return None

        # Step 1: Practical filters — hard filter (orientation) + soft score
        practical_scored = []
        for candidate in candidates:
            practical = self.calculate_practical_score(user, candidate)
            if practical < 0:  # Hard filter failed
                continue
            practical_scored.append((practical, candidate))

        if not practical_scored:
            return None

        # Step 2: Sort by practical score
        practical_scored.sort(key=lambda x: x[0], reverse=True)

        # Step 3: Take top 20 candidates for deep Deepsyke scoring
        top_pool = [c for _, c in practical_scored[:20]]

        # Step 4: Apply Deepsyke compatibility scoring
        deepsyke_scored = []
        for candidate in top_pool:
            dscore = self.calculate_deepsyke_score(user, candidate)
            combined = dscore['score']
            deepsyke_scored.append((combined, candidate, dscore))

        deepsyke_scored.sort(key=lambda x: x[0], reverse=True)

        # Step 5: Take top 10 and apply AI feedback adjustments
        top_10 = [c for _, c, _ in deepsyke_scored[:10]]
        reranked = self.apply_ai_feedback(user, top_10)

        if not reranked:
            return None

        # Step 6: Select the best match with slight randomness to add serendipity
        # 80% chance top pick, 20% chance pick from top 3
        if len(reranked) >= 3 and random.random() < 0.2:
            chosen = random.choice(reranked[:3])
        else:
            chosen = reranked[0]

        # Build the deepsyke score for the chosen candidate
        chosen_dscore = self.calculate_deepsyke_score(user, chosen)

        return {
            "candidate": chosen,
            "compatibility": chosen_dscore,
            "match_date": date.today().isoformat()
        }

    def record_match(self, user_id: str, candidate_id: str, compatibility: dict):
        """Save a match to the database."""
        if user_id not in self.matches:
            self.matches[user_id] = []
        
        self.matches[user_id].append({
            "candidate_id": candidate_id,
            "match_date": date.today().isoformat(),
            "compatibility": compatibility,
            "status": "pending",  # pending, hi_sent, conversation, archived
            "messages": []
        })

    def process_ai_feedback(self, user_id: str, feedback_text: str, last_candidate_id: str) -> dict:
        """
        Process natural language AI feedback and update user's preference adjustments.
        Returns parsed adjustments to be sent to Gemini for natural language processing.
        """
        if user_id not in self.users:
            return {}

        user = self.users[user_id]
        if 'ai_feedback_adjustments' not in user:
            user['ai_feedback_adjustments'] = {}

        adjustments = user['ai_feedback_adjustments']
        feedback_lower = feedback_text.lower()

        # Simple keyword parsing (Gemini does deeper analysis in app.py)
        if any(w in feedback_lower for w in ['boring', 'dull', 'too quiet', 'no energy']):
            adjustments['want_more_active'] = True
        if any(w in feedback_lower for w in ['too intense', 'overwhelming', 'too much']):
            adjustments['want_calmer'] = True
        if any(w in feedback_lower for w in ['ugly', 'not attractive', 'not my type', 'more attractive', 'more sexy', 'sexier']):
            adjustments['want_more_attractive'] = True
        if any(w in feedback_lower for w in ['antarctica', 'travel', 'always away', 'too much travel']):
            adjustments['avoid_heavy_traveler'] = True
        if any(w in feedback_lower for w in ['shallow', 'not deep', 'superficial']):
            adjustments['want_more_intellectual'] = True

        # Track last candidate's type as disliked if very negative feedback
        negative_words = ['hate', 'awful', 'terrible', 'worst', 'no way', 'absolutely not', 'never again']
        if any(w in feedback_lower for w in negative_words):
            if last_candidate_id and last_candidate_id in self.users:
                disliked_type = self.users[last_candidate_id].get('natal_type', '')
                if disliked_type:
                    disliked = adjustments.get('disliked_natal_types', [])
                    if disliked_type not in disliked:
                        disliked.append(disliked_type)
                    adjustments['disliked_natal_types'] = disliked

        return adjustments


def calculate_attractiveness_score(photos_count: int, self_rating: int, bio_quality: int) -> float:
    """
    Estimate attractiveness score (1-10).
    In production this would use AI photo analysis.
    For demo: weighted average of self-rating, bio quality, and profile completeness.
    """
    # Normalize inputs
    photo_bonus = min(2.0, photos_count * 0.5)
    bio_bonus = (bio_quality / 10) * 1.5
    base = self_rating * 0.7

    score = base + photo_bonus + bio_bonus
    return round(min(10.0, max(1.0, score)), 1)