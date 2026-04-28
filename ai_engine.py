"""
Kajole AI Engine — Match Architect
Powered by Gemini 2.5 Flash via Vertex AI REST API.

ARCHITECTURE:
- system_instruction sent as TOP-LEVEL field (not embedded in prompt)
- User context injected fresh per request
- Match Architect persona: focused on matching logic, not life coaching
- Fallback responses are specific and useful, never generic
"""

import os
import json
import traceback
from datetime import datetime
from typing import Optional, Dict, List, Any


# ════════════════════════════════════════════════════════════════════════════
# RAG DATA LOADER
# ════════════════════════════════════════════════════════════════════════════

def _load_rag():
    """Load the Deepsyke core RAG JSON."""
    try:
        rag_path = os.path.join(os.path.dirname(__file__), 'deepsyke_core_rag.json')
        with open(rag_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load deepsyke_core_rag.json: {e}")
        return {}

DEEPSYKE_RAG = _load_rag()


def _get_type_data(natal_type: str) -> dict:
    return DEEPSYKE_RAG.get('affinity_zones', {}).get(natal_type, {})

def _get_compat_data(type_a: str, type_b: str) -> str:
    matrix = DEEPSYKE_RAG.get('compatibility_matrix', {})
    key = f"{type_a}_compatibility"
    pair_key = f"with_{type_b}"
    return matrix.get(key, {}).get(pair_key, "")

def _get_gravitors(natal_type: str) -> list:
    return DEEPSYKE_RAG.get('core_gravitors', {}).get(f"{natal_type}_gravitors", [])

def _get_comm_style(natal_type: str) -> dict:
    return DEEPSYKE_RAG.get('communication_styles', {}).get(natal_type, {})


# ════════════════════════════════════════════════════════════════════════════
# ARCHETYPE MAPS
# ════════════════════════════════════════════════════════════════════════════

ARCHETYPE_MAP = {
    "SS": {"male": "Magician", "female": "Mystic"},
    "SD": {"male": "Knight",   "female": "Maiden"},
    "DS": {"male": "Warrior",  "female": "Queen"},
    "DD": {"male": "King",     "female": "Huntress"},
}

ARCHETYPE_DESCRIPTIONS = {
    "Mystic":   "Soft, spiritual, deeply intuitive. Creates emotional safety through presence.",
    "Maiden":   "Warm, nurturing, genuinely cares about people. The person everyone feels safe around.",
    "Queen":    "Has standards, won't settle. Driven by excellence. Attracted to confidence.",
    "Huntress": "Intense drive, natural leadership. Goes after what she wants directly.",
    "Magician": "Seeks depth and transformation. High emotional intelligence with ambition.",
    "Knight":   "Values honor, wants to protect and provide. Loyal, structured, growth-oriented.",
    "Warrior":  "Confident, bold, approaches everything to win. Creative energy with grounding.",
    "King":     "Natural leader, decisive, results-oriented. Wants control of his life and relationships.",
}

NEUROCHEMISTRY = {
    "SS": "Very High Serotonin + Very High Dopamine — deep emotional stability AND profound drive.",
    "SD": "High Serotonin + Moderate Dopamine — naturally warm, creates emotional safety effortlessly.",
    "DS": "Moderate Serotonin + High Dopamine — creative energy with grounding. Dynamic, inspiring.",
    "DD": "Moderate Serotonin + Very High Dopamine — intense drive and natural leadership.",
}

TYPE_VOICE = {
    "SS": "your deeply soulful, contemplative nature",
    "SD": "your warm, grounded, structure-seeking nature",
    "DS": "your creative, exploratory, dynamic nature",
    "DD": "your driven, high-energy, results-focused nature",
}

NATURE_TRAITS = {
    'SS': 'processes things deeply before speaking, seeks meaning over momentum, high emotional intelligence, can over-idealise',
    'SD': 'naturally warm and creates emotional safety for others, structure-seeking, deeply loyal, risk of over-giving',
    'DS': 'creative, possibility-focused, energised by what could be, dynamic and exploratory, risk of scattered energy',
    'DD': 'action-oriented, natural leadership energy, results-focused, intense drive, risk of burning out those around them',
}

GRAVITOR_CONTEXT = {
    'SS': 'drawn to depth, authenticity, emotional resonance, and meaning',
    'SD': 'drawn to stability, warmth, genuine care, and reliability',
    'DS': 'drawn to possibility, creative tension, freedom, and inspiration',
    'DD': 'drawn to confidence, competence, directness, and momentum',
}

MATCH_NATURE = {
    'SS': 'someone with quiet depth, internal processing, and a preference for meaning over noise',
    'SD': 'someone warm and steady who creates safety and values structure',
    'DS': 'someone with creative energy, possibility-seeking, and dynamic presence',
    'DD': 'someone who leads from confidence, moves with purpose, and values results',
}


# ════════════════════════════════════════════════════════════════════════════
# MATCH ARCHITECT SYSTEM INSTRUCTION
# This replaces the "dating coach" persona entirely.
# Sent as TOP-LEVEL system_instruction to Vertex AI.
# ════════════════════════════════════════════════════════════════════════════

MATCH_ARCHITECT_SYSTEM_INSTRUCTION = """You are the Match Architect for Kajole — a precision tool built for one purpose: helping users get better matches, faster.

## YOUR IDENTITY

You are not a life coach. Not a therapist. Not a cheerleader. You are a specialist — sharp, warm, efficient. Like a high-end concierge who has read the file before you walked in.

Your interface is a tool. Your conversation is the output of that tool. Every exchange moves one of three things forward:
1. Understanding what the user actually wants in a match (not what they say they want)
2. Refining the filter logic based on real feedback about real profiles
3. Giving the user a clear, honest read on today's match

## TONE & ENERGY

Professional, efficient, and supportive. Mix short punchy sentences with longer reflective ones. Natural language — "honestly," "look," "here's the thing," "hmm." These mark genuine thinking. Not decoration.

You sound like someone who has actually read the data. Because you have.

## PRIMARY DIRECTIVES

**1. Feedback Capture**
When a user mentions their match (today's or past), extract the signal. Ask one specific follow-up question about what worked or missed. Never ask vague questions like "what did you think?" — ask precise ones: "Was it the energy level that felt off, or something in the bio?" "What specifically landed for you about how they described their work?"

**2. Affinity Mapping**
Use what you know about the user's neurochemical type to frame observations naturally. Never use jargon — no "Affinity Zones," no "Key 4," no type codes. Use plain language: "It sounds like you value shared intellectual depth over social spontaneity." "You tend to be drawn to people with a certain kind of quiet confidence — not the performative kind."

**3. The Running Record**
Every interaction refines the user's Ideal Profile. If they mention something they liked or disliked about a match, acknowledge it as data: "Got it — noted that the career ambition read as too much. I'm adjusting the filter."

**4. No Coaching**
Do not give advice on how to date, dress, speak, or present yourself. Only suggestions related to filtering and matching logic. If a user asks for personal advice, redirect: "That's a bit outside my lane — I'm better at helping you find someone worth having that conversation with."

**5. Match Cross-Referencing**
Use the current user's affinity data to inform how you describe their compatibility with today's match. Be specific. Not "you seem compatible" — "your pace and theirs are likely similar, which tends to reduce friction in the first few weeks."

## MATCH DESCRIPTION RULES

- Never give a match report in bullets
- Never reveal the match's real name in conversation — describe energy and dynamic
- Never say "soulmate," "perfect match," "sparks fly," or any cliché
- Do not use the word "journey" or generic "connection" — find specific language
- Make the user want to say hi — create intrigue, not hype

## SENTENCE STRUCTURE — NON-NEGOTIABLE

Vary constantly. Short punchy sentences for emphasis. Longer flowing ones for depth. Fragments when natural. Questions that invite rather than demand. If three sentences in a row are the same length — rewrite.

## HARD STOPS — CHECK BEFORE EVERY RESPONSE

- Starting with "I hear you" or "Great question" or "As your [anything]"? DELETE and rewrite.
- Using bullet points or numbered lists? Convert to prose.
- Announcing the framework ("the affinity system says...")? Strip it.
- Giving personal life advice? Redirect to matching logic.
- Repeating an insight already given? Go deeper or change angle.
- Wall of text? Cut it. 3-5 sentences usually. Leave space for them.

## CONVERSATION CRAFT

Length: 3-5 sentences. Occasionally longer for a real moment of insight. Never a list. Never a wall.
Questions: One per response, maximum. Make it precise. Or skip it — a statement that invites response is often stronger.
Tone: Match their energy. Then lead it somewhere more useful."""


# ════════════════════════════════════════════════════════════════════════════
# CONTEXT BUILDER — injected per request
# ════════════════════════════════════════════════════════════════════════════

def _build_match_architect_context(user_profile: dict, match_context: dict = None) -> str:
    """
    Build the background intelligence block injected into each request.
    Gemini reads this silently — never quotes it or references the framework.
    """
    if not user_profile:
        return ""

    name = user_profile.get('name', 'this user')
    natal_type = user_profile.get('natal_type', '')
    loi = user_profile.get('loi_score', 50) or 50
    age = user_profile.get('age', '')
    city = user_profile.get('city', '')
    profession = user_profile.get('profession', '')
    bio = user_profile.get('bio', '')
    match_specs = user_profile.get('match_specs', {}) or {}

    nature_desc = NATURE_TRAITS.get(natal_type, '')
    gravitor_desc = GRAVITOR_CONTEXT.get(natal_type, '')
    gravitors = _get_gravitors(natal_type) if natal_type else []
    comm_style = _get_comm_style(natal_type) if natal_type else {}
    type_data = _get_type_data(natal_type) if natal_type else {}

    int_level = 'high' if loi >= 65 else 'mid' if loi >= 45 else 'low'
    INTEGRATION_CONTEXT = {
        'high': 'well-integrated — drawn to depth-matching energy',
        'mid': 'open to both familiar and contrasting energy — still calibrating',
        'low': 'likely drawn toward contrasting energy — seeking balance through difference',
    }
    integration_desc = INTEGRATION_CONTEXT.get(int_level, '')

    parts = ["## BACKGROUND INTELLIGENCE — Read silently. Never quote or reference this block directly.", ""]

    # User identity
    user_line = f"Person: {name}"
    if age: user_line += f", {age}"
    if city: user_line += f", {city}"
    if profession: user_line += f" | Works as: {profession}"
    parts.append(user_line)

    if nature_desc:
        parts.append(f"Inner nature: {nature_desc}")
    if gravitor_desc:
        parts.append(f"What pulls them: {gravitor_desc}")
    if gravitors:
        parts.append(f"Specific gravitors: {', '.join(gravitors[:5])}")
    if integration_desc:
        parts.append(f"Integration level: {integration_desc}")
    if comm_style.get('tone'):
        parts.append(f"Resonates with: {comm_style['tone']} communication")
    if type_data.get('motivation'):
        parts.append(f"Core motivation: {type_data['motivation']}")
    if type_data.get('stress_response'):
        parts.append(f"Under pressure: {type_data['stress_response']}")
    if bio:
        parts.append(f"Their own words: \"{bio[:140]}{'...' if len(bio) > 140 else ''}\"")

    # Accumulated match preferences from conversation history
    if match_specs:
        prefs = []
        if match_specs.get('prefers_high_emotional_availability'): prefs.append("emotionally available")
        if match_specs.get('prefers_high_drive'): prefs.append("ambitious/driven")
        if match_specs.get('prefers_lower_intensity'): prefs.append("calm/grounded")
        if match_specs.get('prefers_higher_intensity'): prefs.append("passionate/intense")
        if match_specs.get('prefers_intellectual'): prefs.append("intellectually curious")
        if match_specs.get('prefers_adventurous'): prefs.append("adventurous")
        if match_specs.get('prefers_stable'): prefs.append("stable/consistent")
        if match_specs.get('prefers_depth'): prefs.append("depth over surface")
        if prefs:
            parts.append(f"Stated match preferences so far: {', '.join(prefs)}")

    # Today's match context
    if match_context:
        candidate = match_context.get('candidate', {}) or {}
        compat = match_context.get('compatibility', {}) or {}

        c_type = candidate.get('natal_type', '')
        c_profession = candidate.get('profession', '')
        c_bio = (candidate.get('bio', '') or '')[:100]
        c_age = candidate.get('age', '')
        c_city = candidate.get('city', '')

        compat_note = _get_compat_data(natal_type, c_type) if natal_type and c_type else ""
        compat_score = compat.get('score', '') if isinstance(compat, dict) else ''
        dynamic = compat.get('dynamic', '') if isinstance(compat, dict) else ''

        match_nature = MATCH_NATURE.get(c_type, 'someone with their own distinct inner world')

        is_affinity = natal_type == c_type
        is_polarity = bool(natal_type and c_type and natal_type[0] != c_type[0])
        if is_affinity:
            dynamic_frame = "shared inner rhythm — natural understanding, risk of too much similarity"
        elif is_polarity:
            dynamic_frame = "complementary opposites — magnetic tension, mutual growth potential"
        else:
            dynamic_frame = "adjacent energies — familiar enough to connect, different enough to grow"

        parts.append("")
        parts.append("## TODAY'S MATCH — Describe energy and dynamic only. Never use their real name.")
        match_line = f"Match energy: {match_nature}"
        if c_age: match_line += f" | Age: {c_age}"
        if c_city: match_line += f" | {c_city}"
        parts.append(match_line)
        parts.append(f"Connection dynamic: {dynamic_frame}")
        if compat_note:
            parts.append(f"Compatibility read: {compat_note}")
        if dynamic:
            parts.append(f"Named dynamic: {dynamic}")
        if compat_score:
            parts.append(f"Score: {compat_score}%")
        if c_profession:
            parts.append(f"Match's work: {c_profession}")
        if c_bio:
            parts.append(f"Match's own words: \"{c_bio}\"")

        # RAG on match type
        match_type_data = _get_type_data(c_type) if c_type else {}
        if match_type_data:
            c_motiv = match_type_data.get('motivation', '')
            c_gravitors = _get_gravitors(c_type)[:3] if c_type else []
            if c_motiv:
                parts.append(f"What drives the match: {c_motiv}")
            if c_gravitors:
                parts.append(f"What pulls the match: {', '.join(c_gravitors)}")

    parts.append("")
    parts.append("Use this data to inform your response naturally. Respond to their actual message. Make them feel understood, not categorised. Stay in your lane — matching logic, not life coaching.")

    return "\n".join(parts)


def _build_compact_header(user_profile: dict, match_context: dict = None) -> str:
    """Compact per-turn context stamp for conversation history turns."""
    if not user_profile:
        return ""

    name = user_profile.get('name', 'User')
    natal_type = user_profile.get('natal_type', '')
    loi = user_profile.get('loi_score', 50) or 50
    nature = NATURE_TRAITS.get(natal_type, '')
    gravitors = _get_gravitors(natal_type)[:3] if natal_type else []
    comm = _get_comm_style(natal_type) if natal_type else {}

    loi_trait = (
        "well-integrated, drawn to depth-matching"
        if loi >= 65
        else "still calibrating, open to contrasting energy"
        if loi >= 45
        else "early growth phase, drawn to contrasting energy"
    )

    parts = [f"[CONTEXT — {name}"]
    if nature:
        parts.append(f" | {nature}")
    parts.append(f" | {loi_trait}")
    if gravitors:
        parts.append(f" | drawn to: {', '.join(gravitors)}")
    if comm.get('tone'):
        parts.append(f" | resonates with: {comm['tone']} communication")

    if match_context:
        candidate = match_context.get('candidate', {}) or {}
        c_type = candidate.get('natal_type', '')
        match_nature = MATCH_NATURE.get(c_type, '')
        compat_note = _get_compat_data(natal_type, c_type) if natal_type and c_type else ""
        if match_nature:
            parts.append(f" | today's match: {match_nature}")
        if compat_note:
            short = compat_note.split('.')[0]
            if short:
                parts.append(f" | dynamic: {short}")

    parts.append("] — silent background only. Never quote.")
    return "".join(parts)


# ════════════════════════════════════════════════════════════════════════════
# VERTEX AI REST CALL
# system_instruction at ROOT LEVEL — this is the critical architecture fix
# ════════════════════════════════════════════════════════════════════════════

def get_gemini_via_rest(
    prompt: str,
    history: list = None,
    user_context: str = None,
    system_override: str = None,
    profile_header: str = None
) -> Optional[str]:
    """
    Call Gemini via Vertex AI REST API using service account OAuth2.

    3-layer context injection:
    1. system_instruction at TOP LEVEL — persona enforcement
    2. profile_header prepended to every historical user turn — stateful identity
    3. Full user_context block on current turn — rich per-turn detail
    """
    import urllib.request
    import urllib.error

    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        cred_json = (
            os.environ.get('FIREBASE_CREDENTIALS_JSON') or
            os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON') or
            os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        )
        if not cred_json:
            print("No service account credentials found for Vertex AI")
            return None

        cred_dict = json.loads(cred_json)
        if 'private_key' in cred_dict:
            cred_dict['private_key'] = cred_dict['private_key'].replace('\\n', '\n')

        project_id = cred_dict.get('project_id') or os.environ.get('FIREBASE_PROJECT_ID', 'kajole')

        credentials = service_account.Credentials.from_service_account_info(
            cred_dict,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        credentials.refresh(Request())
        token = credentials.token
        print(f'KAJOLE AI: Auth OK — project={project_id}, token_len={len(token)}', flush=True)

        # Build contents with stateful header on every user turn
        contents = []

        if history:
            for msg in history[-10:]:  # last 5 exchanges
                role = 'user' if msg.get('role') == 'user' else 'model'
                content_text = msg.get('content', '')
                if not content_text:
                    continue
                if role == 'user' and profile_header:
                    stamped = f"{profile_header}\n{content_text}"
                else:
                    stamped = content_text
                contents.append({
                    'role': role,
                    'parts': [{'text': stamped}]
                })

        # Current turn — inject full context block
        if user_context:
            full_prompt = f"{user_context}\n\n---\n\nUser message: {prompt}"
        elif profile_header:
            full_prompt = f"{profile_header}\n{prompt}"
        else:
            full_prompt = prompt

        contents.append({
            'role': 'user',
            'parts': [{'text': full_prompt}]
        })

        system_text = system_override or MATCH_ARCHITECT_SYSTEM_INSTRUCTION

        payload = {
            'system_instruction': {
                'parts': [{'text': system_text}]
            },
            'contents': contents,
            'generationConfig': {
                'temperature': 0.85,
                'topP': 0.95,
                'maxOutputTokens': 512,
                'frequencyPenalty': 0.4,
                'presencePenalty': 0.3,
            },
        }

        url = (
            f"https://australia-southeast1-aiplatform.googleapis.com/v1/projects/{project_id}"
            f"/locations/australia-southeast1/publishers/google/models/gemini-2.5-flash:generateContent"
        )

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'Authorization': f'Bearer {token}',
                'x-goog-api-client': 'genai-python',
                'Content-Type': 'application/json',
            },
            method='POST'
        )

        print(f'KAJOLE AI: Calling Vertex AI -> {url}', flush=True)
        print(f'KAJOLE AI: turns={len(contents)}, payload={len(json.dumps(payload))} bytes', flush=True)

        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.loads(response.read().decode('utf-8'))

        candidates = result.get('candidates', [])
        if candidates:
            content = candidates[0].get('content', {})
            parts = content.get('parts', [])
            if parts:
                text = parts[0].get('text', '').strip()
                if text:
                    print(f"Vertex AI response: {len(text)} chars", flush=True)
                    return text

        finish = candidates[0].get('finishReason', 'unknown') if candidates else 'no candidates'
        print(f"Vertex AI returned no text. Finish reason: {finish}")
        return None

    except ImportError:
        print('KAJOLE AI ERROR: google-auth not installed — Vertex AI unavailable')
        return None
    except json.JSONDecodeError as e:
        print(f'KAJOLE AI ERROR: Credential JSON parse error: {e}')
        return None
    except Exception as e:
        import urllib.error as _ue
        if isinstance(e, _ue.HTTPError):
            try:
                body = e.read().decode('utf-8')
                print(f'KAJOLE AI HTTP {e.code} ERROR: {body[:800]}', flush=True)
            except Exception:
                print(f'KAJOLE AI HTTP {e.code} ERROR (body unreadable)', flush=True)
        else:
            print(f'KAJOLE AI REST ERROR: {type(e).__name__}: {e}', flush=True)
            traceback.print_exc()
        return None


# ════════════════════════════════════════════════════════════════════════════
# MAIN CHAT FUNCTION
# ════════════════════════════════════════════════════════════════════════════

def chat_with_kajole(
    user_message: str,
    conversation_history: list = None,
    user_profile: dict = None,
    match_context: dict = None
) -> str:
    """
    Main Kajole chat function. Builds Match Architect context and calls Vertex AI.
    Data is expected to be passed in fresh from the calling endpoint (stateless pattern).
    """
    context_block = _build_match_architect_context(user_profile, match_context)
    profile_header = _build_compact_header(user_profile, match_context)

    response = get_gemini_via_rest(
        prompt=user_message,
        history=conversation_history,
        user_context=context_block if context_block else None,
        profile_header=profile_header if profile_header else None
    )

    if response:
        return response

    return _get_fallback_response(user_message, user_profile, match_context)


# ════════════════════════════════════════════════════════════════════════════
# MATCH INSIGHT GENERATOR (for Today's Match card)
# ════════════════════════════════════════════════════════════════════════════

def get_match_insight(user_profile: dict, candidate_profile: dict) -> str:
    """
    Generate a Deepsyke insight for the Today's Match card.
    Uses RAG compatibility data to ground the AI insight.
    """
    user_type = user_profile.get('natal_type', 'SD')
    cand_type = candidate_profile.get('natal_type', 'DS')

    user_gender = user_profile.get('gender', '').lower()
    cand_gender = candidate_profile.get('gender', '').lower()
    u_key = 'female' if ('female' in user_gender or 'woman' in user_gender) else 'male'
    c_key = 'female' if ('female' in cand_gender or 'woman' in cand_gender) else 'male'

    user_arch = (
        (user_profile.get('archetype') or {}).get('title')
        or ARCHETYPE_MAP.get(user_type, {}).get(u_key, 'your archetype')
    )
    cand_arch = (
        (candidate_profile.get('archetype') or {}).get('title')
        or ARCHETYPE_MAP.get(cand_type, {}).get(c_key, 'their archetype')
    )

    user_loi = user_profile.get('loi_score', 50) or 50
    cand_profession = candidate_profile.get('profession', '')
    cand_bio = (candidate_profile.get('bio', '') or '')[:100]

    compat_note = _get_compat_data(user_type, cand_type)
    user_gravitors = _get_gravitors(user_type)[:4]
    cand_gravitors = _get_gravitors(cand_type)[:4]

    is_affinity = user_type == cand_type
    is_polarity = bool(user_type and cand_type and user_type[0] != cand_type[0])
    match_type = "Affinity Zone" if is_affinity else ("Polarity" if is_polarity else "Complementary")

    insight_system = """You are Kajole's match insight generator. Write a brief, magnetic, psychologically rich insight (2-3 sentences max) about a specific pairing.

Rules:
- No bullet points, no lists, no formatting
- No generic "soulmate" language or clichés
- Reference the energetic dynamic subtly and naturally
- Make the user WANT to say hi — create intrigue, not hype
- Under 75 words total
- Flowing narrative prose only
- Be specific to this pairing
- Do not use "journey" or generic "connection\""""

    prompt = (
        f"Write a Kajole match insight for this pairing:\n\n"
        f"User: {user_arch} (LOI: {user_loi}) — drawn to {', '.join(user_gravitors)}\n"
        f"Match: {cand_arch} — driven by {', '.join(cand_gravitors)}\n"
        f"Match type: {match_type}\n"
        f"RAG dynamic: {compat_note}\n"
        f"Match's profession: {cand_profession}\n"
        f"Match's bio snippet: {cand_bio}\n\n"
        f"Write 2-3 sentences that are grounded, intriguing, and specific to this pairing."
    )

    response = get_gemini_via_rest(
        prompt=prompt,
        history=None,
        user_context=None,
        system_override=insight_system
    )

    if response:
        return response.strip()

    return _generate_fallback_insight(user_type, cand_type, user_loi)


# ════════════════════════════════════════════════════════════════════════════
# INTELLIGENT FALLBACK RESPONSES
# ════════════════════════════════════════════════════════════════════════════

def _get_fallback_response(
    user_message: str,
    user_profile: dict = None,
    match_context: dict = None
) -> str:
    """Utility fallback when Vertex AI is unavailable — specific, never generic."""
    print(f'KAJOLE AI FALLBACK: using local fallback for: {user_message[:60]!r}', flush=True)
    msg_lower = user_message.lower()

    natal_type = ""
    if user_profile:
        natal_type = user_profile.get('natal_type', '')

    # Match-related
    if any(w in msg_lower for w in ['match', 'today', 'who', 'profile', 'compatible', 'them']):
        if match_context and match_context.get('candidate'):
            cand = match_context['candidate']
            c_type = cand.get('natal_type', '')
            compat_note = _get_compat_data(natal_type, c_type) if natal_type and c_type else ""
            if compat_note:
                return (
                    f"Here's the honest read — {compat_note.lower()} "
                    f"That dynamic tends to produce something real when both people show up honestly. "
                    f"What's your gut read on the profile?"
                )
        return (
            "I'm having trouble pulling your latest match data. "
            "Let me refresh the connection — try again in a moment."
        )

    # Feedback about a match
    if any(w in msg_lower for w in ['boring', 'too much', 'not my type', 'off', 'didn\'t']):
        return (
            "Noted — that's useful signal for the filter. "
            "Was it something specific in the profile that missed, or more of a general energy mismatch? "
            "The more precise you can be, the better the next match."
        )

    if any(w in msg_lower for w in ['liked', 'loved', 'yes', 'interesting', 'good match']):
        return (
            "Good signal — I've got that. "
            "What specifically worked? The bio, the profession, the energy they described? "
            "Each answer sharpens the next selection."
        )

    # How the app works
    if any(w in msg_lower for w in ['why', 'how', 'work', 'system', 'different', 'app', 'kajole']):
        return (
            "One match per day, chosen with actual intelligence behind it. "
            "Not an algorithm optimizing for your anxiety — a selection based on neurochemical compatibility and your evolving preferences. "
            "The daily constraint is intentional. It breaks the slot machine pattern."
        )

    # Greetings
    if any(w in msg_lower for w in ['hi', 'hello', 'hey', 'start', 'help']):
        return (
            "Hey — I'm your Match Architect. "
            "I'm here to help you get better matches, not to chat about dating in general. "
            "Tell me about today's match, or what you're looking for — and I'll work with that."
        )

    # Default utility message
    return (
        "I'm having trouble pulling your latest match data right now. "
        "Let me refresh the connection — try sending that again in a moment."
    )


def _generate_fallback_insight(user_type: str, candidate_type: str, user_loi: float) -> str:
    """Generate fallback match insight using RAG compatibility data."""
    compat_note = _get_compat_data(user_type, candidate_type)
    if compat_note:
        return f"{compat_note} With both people showing up honestly, that's the kind of dynamic that tends to surprise you."

    insights = {
        ('DS', 'SD'): "There's a real tension in this pairing — exploratory energy meeting depth-seeking soul. They'll pull you into feeling what you usually only observe.",
        ('SD', 'DS'): "Your emotional depth will both fascinate and ground them. They move fast but feel deeply — and they need someone who can keep up.",
        ('DD', 'SS'): "Your drive and their stillness create a dynamic where both get what they're actually missing. Don't mistake their calm for lack of depth.",
        ('SS', 'DD'): "They'll bring the momentum you sometimes hesitate to start yourself. You'll bring the anchor. Together there's something worth building.",
        ('DS', 'DS'): "Two explorers mapping the same territory. The conversation won't get boring — the real risk is depth. Let yourself go there.",
        ('DD', 'DD'): "Everything becomes possible and intense. The chemistry isn't in question — whether both people can build with it is.",
        ('SS', 'SS'): "Two people who understand depth in a world that rarely rewards it. The risk is too much stillness. The possibility is genuine understanding.",
        ('SD', 'SD'): "Shared values, mutual loyalty, a foundation that builds. Steadier than magnetic — which might be exactly what's needed.",
    }

    key = (user_type, candidate_type)
    reverse_key = (candidate_type, user_type)
    return (
        insights.get(key) or
        insights.get(reverse_key) or
        "There's something real here worth a closer look. Not every match announces itself loudly — some reveal layer after layer."
    )


# ════════════════════════════════════════════════════════════════════════════
# MATCH SPEC EXTRACTOR (silent preference extraction from conversation)
# ════════════════════════════════════════════════════════════════════════════

def extract_match_specs_from_message(user_message: str, user_profile: dict) -> dict:
    """
    Silently extract match preferences from user messages.
    Returns a dict of adjustments to store on the user profile.
    """
    specs = {}
    msg_lower = user_message.lower()

    if any(p in msg_lower for p in ['emotionally available', 'can communicate', 'actually present', 'shows up']):
        specs['prefers_high_emotional_availability'] = True
    if any(p in msg_lower for p in ['ambitious', 'has their life together', 'driven', 'successful', 'career']):
        specs['prefers_high_drive'] = True
    if any(p in msg_lower for p in ['not too intense', 'calm', 'stable', 'grounded', 'steady', 'peaceful']):
        specs['prefers_lower_intensity'] = True
    if any(p in msg_lower for p in ['intense', 'passionate', 'fire', 'exciting', 'electric']):
        specs['prefers_higher_intensity'] = True
    if any(p in msg_lower for p in ['intelligent', 'intellectual', 'smart', 'curious', 'deep thinker']):
        specs['prefers_intellectual'] = True
    if any(p in msg_lower for p in ['adventurous', 'spontaneous', 'travel', 'explorer']):
        specs['prefers_adventurous'] = True
    if any(p in msg_lower for p in ['stable', 'consistent', 'reliable', 'settled', 'routine']):
        specs['prefers_stable'] = True
    if any(p in msg_lower for p in ['deep', 'meaningful', 'substance', 'real conversations', 'depth']):
        specs['prefers_depth'] = True
    if any(p in msg_lower for p in ['fun', 'light', 'easy-going', 'chill', 'carefree']):
        specs['prefers_lightness'] = True

    return specs