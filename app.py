"""
Kajole — The Slow Burn Dating App
Powered by Deepsyke Psychology & Gemini AI
"""

import json
import os
import random
import uuid
import bcrypt
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, session
from natal_calculator import calculate_natal_type_from_dob, get_archetype, get_loi_score
from matching_engine import MatchingEngine, calculate_attractiveness_score
from natal_calculator import get_compatibility_dynamic
import requests

# Database layer (Firebase + in-memory fallback)
from db_layer import (
    create_user, get_user, get_user_by_email, update_user, get_all_users, delete_user,
    create_match, get_user_matches, get_today_match, update_match,
    create_conversation, get_user_conversations, get_conversation, send_message, get_conversation_messages,
    create_session, get_session, delete_session,
    upload_photo, seed_demo_profiles, seed_initial_matches, get_db_status, IN_MEMORY_DB
)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'kajole-demo-secret-2024')

# Session configuration for better auth persistence
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('RENDER', False)  # True in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Session version - increment this to invalidate ALL old sessions across all users
# This forces everyone to re-login when deployed
SESSION_VERSION = '3'

@app.before_request
def validate_session():
    """Validate session version - clears stale sessions from old deployments"""
    # Skip for static files and OPTIONS
    if request.endpoint and request.endpoint.startswith('static'):
        return
    if request.method == 'OPTIONS':
        return
    # Check session version - if it doesn't match, clear the stale session
    if session.get('user_id') and session.get('session_version') != SESSION_VERSION:
        print(f"🔄 Clearing stale session (old version) for user: {session.get('user_id')}")
        session.clear()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ─────────────────────────────────────────────
# IN-MEMORY DATABASES (Firebase-ready structure)
# ─────────────────────────────────────────────
# Database is handled by db_layer (Firebase or in-memory)
USERS_DB = IN_MEMORY_DB['users']  # Reference to in-memory users
MATCHES_DB = IN_MEMORY_DB['matches']  # Reference to in-memory matches
MESSAGES_DB = IN_MEMORY_DB['messages']  # Reference to in-memory messages
SESSIONS_DB = IN_MEMORY_DB['sessions']  # Reference to in-memory sessions

# Load Deepsyke core RAG
try:
    with open('deepsyke_core_rag.json', 'r') as f:
        DEEPSYKE_CORE = json.load(f)
except FileNotFoundError:
    DEEPSYKE_CORE = {}

# Initialize matching engine
engine = MatchingEngine(USERS_DB, MATCHES_DB)

# ─────────────────────────────────────────────
# DEMO DATA — seed with some profiles for demo
# ─────────────────────────────────────────────
# seed_demo_profiles is now imported from db_layer
# ─────────────────────────────────────────────
# GEMINI AI HELPER
# ─────────────────────────────────────────────
def call_gemini(system_prompt: str, user_message: str, history: list = None) -> str:
    """Call Gemini API with system prompt and message."""
    if not GEMINI_API_KEY:
        return _fallback_response(user_message)

    headers = {"Content-Type": "application/json"}
    
    contents = []
    if history:
        for msg in history[-6:]:  # last 6 messages for context
            contents.append({
                "role": msg['role'],
                "parts": [{"text": msg['content']}]
            })
    
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 600,
            "topP": 0.9
        }
    }

    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=15
        )
        data = resp.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini error: {e}")
        return _fallback_response(user_message)


def _fallback_response(message: str) -> str:
    """Fallback when Gemini is unavailable."""
    return "Your match is being carefully selected. Our Deepsyke engine is analysing deep compatibility patterns for you. Check back soon for your daily reveal."


def build_ai_coach_prompt(user: dict, last_match: dict = None) -> str:
    """Build the Deepsyke AI coach system prompt for a user."""
    natal_type = user.get('natal_type', 'SD')
    archetype = user.get('archetype', {})
    archetype_name = archetype.get('name', 'Guide') if isinstance(archetype, dict) else 'Guide'
    loi = user.get('loi_score', 50)
    loi_state = "highly aligned with your true nature" if loi >= 50 else "in a growth and seeking phase"
    
    match_context = ""
    if last_match:
        match_candidate = last_match.get('candidate', {})
        match_type = match_candidate.get('natal_type', '')
        match_name = match_candidate.get('name', 'your recent match')
        compat = last_match.get('compatibility', {})
        match_context = f"""
Last Match Context:
- Their name: {match_name}
- Their neurochemical blueprint: {match_type}
- Compatibility dynamic: {compat.get('dynamic', 'Resonance')} ({compat.get('score', 75)}% alignment)
"""

    return f"""You are Kajole's AI Companion — a witty, warm, psychologically sophisticated dating coach powered by Deepsyke neurochemical intelligence.

ABOUT THE USER:
- Their neurochemical blueprint: {natal_type} type
- Their archetype: The {archetype_name}
- Current alignment state: {loi_state} (LOI: {loi}/100)
- Name: {user.get('name', 'User')}

{match_context}

YOUR ROLE:
- You are their personal "slow burn" dating companion
- Help them process their feelings about matches, refine what they want, and build self-awareness
- When they give feedback about matches, extract their preferences to improve future matching
- Use warm, intelligent, slightly witty language — never clinical or robotic
- NEVER use the raw type labels (SS/SD/DS/DD) directly — translate into poetic language:
  * SS = "deep thinker / soulful" energy
  * SD = "grounded visionary / steady flame" energy  
  * DS = "creative spark / the connoisseur" energy
  * DD = "dynamic initiator / bold force" energy
- Keep responses under 150 words — punchy, memorable, insightful

FEEDBACK PROCESSING:
When they say things like "too boring", "too intense", "I didn't like X about them" — acknowledge with empathy, extract the preference signal, and confirm how it will inform their next match.

Remember: This is a SLOW BURN app. No swiping. One match per day. The mystery and reflection are features, not bugs.
"""


def build_bio_helper_prompt(partial_info: dict) -> str:
    """Prompt to help write a compelling dating bio."""
    return f"""You are a dating profile copywriter with a gift for capturing authentic human essence in a few sentences.

The person has shared this about themselves:
- Name: {partial_info.get('name', '')}
- Age: {partial_info.get('age', '')}
- Profession: {partial_info.get('profession', '')}
- Interests/Hobbies: {partial_info.get('interests', '')}
- What they're looking for: {partial_info.get('looking_for', '')}
- One thing they want people to know: {partial_info.get('personality_note', '')}
- Neurochemical archetype hint: {partial_info.get('archetype_hint', '')}

Write 3 different short bios (2-3 sentences each), each with a distinct voice:
1. Poetic & evocative
2. Witty & confident
3. Warm & direct

Format as:
BIO_1: [text]
BIO_2: [text]  
BIO_3: [text]

Make them REAL, not clichéd. No "I love long walks" or "looking for my partner in crime." Capture their actual essence."""


# ─────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────
def get_current_user_id():
    return session.get('user_id')

def get_current_user():
    uid = get_current_user_id()
    if uid:
        return get_user(uid)  # Use db_layer
    return None


# ─────────────────────────────────────────────
# ROUTES — PAGES
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/onboard')
def onboard():
    return render_template('index.html')


# ─────────────────────────────────────────────
# ROUTES — AUTH
# ─────────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').lower().strip()
    name = data.get('name', '').strip()
    password = data.get('password', '')

    if not email or not name or not password:
        return jsonify({"error": "All fields required"}), 400

    # Check if email exists using db_layer
    existing_user = get_user_by_email(email)
    if existing_user:
        print(f"⚠️ Registration failed - email already exists: {email}")
        return jsonify({"error": "Email already registered"}), 409

    user_id = str(uuid.uuid4())[:12]
    user_data = {
        "id": user_id,
        "email": email,
        "name": name,
        "password_hash": password,  # In prod: bcrypt hash
        "profile_complete": False,
        "onboarding_step": 1,
        "active": True,
        "created_at": datetime.now().isoformat(),
        "ai_feedback_adjustments": {},
        "ai_conversation": []
    }
    
    # Create user via db_layer (persists to Firebase if available)
    create_user(user_data)
    print(f"✅ New user registered: {user_id} - {name} ({email})")

    # Clear any existing session before setting new user
    session.clear()
    session['user_id'] = user_id
    session['session_version'] = SESSION_VERSION
    session.permanent = True  # Make session last 7 days
    print(f"✅ Session cleared and set for new user: {user_id}")
    return jsonify({"success": True, "user_id": user_id, "name": name})


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')

    # Use db_layer to find user by email (checks Firebase first)
    user = get_user_by_email(email)
    
    # Verify password (supports bcrypt and plain text)
    password_hash = user.get('password_hash', '')
    password_valid = False
    if password_hash:
        if password_hash.startswith('$2'):
            # Bcrypt hash
            try:
                password_valid = bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            except:
                password_valid = False
        else:
            # Plain text (legacy)
            password_valid = password == password_hash
    
    if user and password_valid:
        uid = user.get('id')
        # Clear any existing session before setting new user
        session.clear()
        session['user_id'] = uid
        session['session_version'] = SESSION_VERSION
        session.permanent = True  # Make session last 7 days
        print(f"✅ User logged in: {uid} - {user.get('name', 'User')}")
        return jsonify({
            "success": True,
            "user_id": uid,
            "name": user.get('name', 'User'),
            "profile_complete": user.get('profile_complete', False),
            "onboarding_step": user.get('onboarding_step', 1)
        })

    # Demo login for testing
    if email == 'demo@kajole.com' and password == 'demo':
        demo_uid = 'demo_user_main'
        # Check if demo user exists in database
        demo_user = get_user(demo_uid)
        if not demo_user:
            # Create demo user in database
            demo_data = {
                "id": demo_uid,
                "email": email,
                "password_hash": "demo",
                "name": "Alex",
                "gender": "male",
                "age": 30,
                "dob": "1994-07-15",
                "city": "London",
                "country": "UK",
                "orientation": "straight",
                "natal_type": "DS",
                "archetype": get_archetype("DS", "male"),
                "loi_score": 62,
                "bio": "A soul at the crossroads of creativity and ambition. Building things, breaking patterns, always looking for the next beautiful conversation.",
                "profession": "Product Designer",
                "education": "University of Arts London",
                "religion": "none",
                "ethnicity": "mixed",
                "lifestyle": ["design", "music", "fitness", "travel"],
                "social_style": "ambivert",
                "attractiveness_score": 8.0,
                "intellectual_score": 8,
                "photos": [],
                "profile_complete": True,
                "active": True,
                "onboarding_step": 4,
                "created_at": "2024-01-01",
                "ai_feedback_adjustments": {},
                "ai_conversation": [],
                "preferences": {
                    "age_min": 24,
                    "age_max": 36,
                    "location_preference": "worldwide",
                    "religion": "any",
                    "ethnicity": "any",
                    "attractiveness_min": 7
                }
            }
            create_user(demo_data)
        session['user_id'] = demo_uid
        return jsonify({
            "success": True,
            "user_id": demo_uid,
            "name": "Alex",
            "profile_complete": True,
            "onboarding_step": 4
        })

    return jsonify({"error": "Invalid credentials"}), 401


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route('/api/auth/me', methods=['GET'])
def me():
    user_id = get_current_user_id()
    print(f"🔍 /api/auth/me called - session user_id: {user_id}")
    
    if not user_id:
        print("❌ No user_id in session")
        return jsonify({"authenticated": False}), 401
    
    user = get_user(user_id)
    if not user:
        print(f"❌ User not found in database: {user_id}")
        return jsonify({"authenticated": False}), 401
        
    safe_user = {k: v for k, v in user.items() if k != 'password_hash'}
    print(f"✅ User authenticated: {user_id} - {safe_user.get('name', 'Unknown')}")
    return jsonify({"authenticated": True, "user": safe_user})


# ─────────────────────────────────────────────
# ROUTES — PROFILE CREATION (3-step onboarding)
# ─────────────────────────────────────────────
@app.route('/api/profile/step1', methods=['POST'])
def profile_step1():
    """Basic profile — who you are."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.json
    required = ['name', 'age', 'gender', 'dob', 'city', 'country', 'orientation', 'profession', 'bio']

    # Update user via db_layer
    updates = {
        'name': data.get('name', ''),
        'age': int(data.get('age', 25)),
        'gender': data.get('gender', 'female'),
        'dob': data.get('dob', ''),
        'city': data.get('city', ''),
        'country': data.get('country', ''),
        'orientation': data.get('orientation', 'straight'),
        'profession': data.get('profession', ''),
        'education': data.get('education', ''),
        'bio': data.get('bio', ''),
        'religion': data.get('religion', 'none'),
        'ethnicity': data.get('ethnicity', 'any'),
        'lifestyle': data.get('lifestyle', []),
        'social_style': data.get('social_style', 'ambivert'),
        'attractiveness_score': float(data.get('attractiveness_self', 7)),
        'intellectual_score': int(data.get('intellectual_self', 7)),
        'onboarding_step': 2
    }
    update_user(user_id, updates)

    return jsonify({"success": True, "step": 2})


@app.route('/api/profile/step2', methods=['POST'])
def profile_step2():
    """What you're looking for — preferences."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.json
    # Update user via db_layer
    updates = {
        'preferences': {
            'age_min': int(data.get('age_min', 22)),
            'age_max': int(data.get('age_max', 45)),
            'location_preference': data.get('location_preference', 'worldwide'),
            'religion': data.get('religion', 'any'),
            'ethnicity': data.get('ethnicity', 'any'),
            'attractiveness_min': int(data.get('attractiveness_min', 6)),
            'lifestyle_must': data.get('lifestyle_must', []),
            'dealbreakers': data.get('dealbreakers', []),
            'partner_description': data.get('partner_description', '')
        },
        'onboarding_step': 3
    }
    update_user(user_id, updates)
    return jsonify({"success": True, "step": 3})


@app.route('/api/profile/step3', methods=['POST'])
def profile_step3():
    """Deepsyke test — calculates natal type from DOB + LOI questions."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.json
    user = get_user(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404

    dob = user.get('dob') or data.get('dob', '')
    gender = user.get('gender', 'female')

    # Calculate natal type from DOB
    try:
        natal_type = calculate_natal_type_from_dob(dob, gender)
    except Exception as e:
        natal_type = 'SD'  # fallback

    # Calculate LOI score from questionnaire answers
    loi_answers = {
        'loi_indicators': {
            'peace_with_self': int(data.get('peace_with_self', 3)),
            'authenticity': int(data.get('authenticity', 3)),
            'internal_validation': int(data.get('internal_validation', 3)),
            'relationship_stability': int(data.get('relationship_stability', 3)),
            'decision_comfort': int(data.get('decision_comfort', 3))
        }
    }
    loi_score = get_loi_score(loi_answers)

    archetype = get_archetype(natal_type, gender)

    # Calculate final attractiveness score
    # Get existing photos from user profile (uploaded via /api/photos/upload)
    existing_photos = user.get('photos', [])
    photos_list = data.get('photos') if data.get('photos') else existing_photos
    
    attractiveness_score = calculate_attractiveness_score(
        photos_count=len(photos_list) or 1,
        self_rating=int(data.get('attractiveness_self', 7)),
        bio_quality=min(10, len(user.get('bio', '')) // 20)
    )

    # Update user via db_layer
    updates = {
        'natal_type': natal_type,
        'loi_score': loi_score,
        'archetype': archetype,
        'deepsyke_answers': data,
        'profile_complete': True,
        'onboarding_step': 4,
        'attractiveness_score': attractiveness_score
    }
    # Only update photos if we have new ones, otherwise preserve existing
    if photos_list:
        updates['photos'] = photos_list
        
    update_user(user_id, updates)
    
    # Seed initial matches for new user (3 matches in history)
    import traceback
    try:
        print(f"DEBUG: About to seed matches for {user_id}")
        matches_created = seed_initial_matches(user_id, num_matches=3)
        print(f"DEBUG: Seeded {matches_created} initial matches for {user_id}")
    except Exception as e:
        print(f"ERROR: Could not seed initial matches: {e}")
        traceback.print_exc()
    
    return jsonify({
        "success": True,
        "natal_type": natal_type,
        "loi_score": loi_score,
        "archetype": archetype,
        "step": 4
    })


# ─────────────────────────────────────────────
# ROUTES — AI BIO HELPER
# ─────────────────────────────────────────────
@app.route('/api/bio/generate', methods=['POST'])
def generate_bio():
    data = request.json
    prompt = build_bio_helper_prompt(data)
    response = call_gemini(prompt, "Please write the three bio options now.")

    # Parse bios from response
    bios = []
    for i in range(1, 4):
        marker = f"BIO_{i}:"
        if marker in response:
            start = response.index(marker) + len(marker)
            end = response.index(f"BIO_{i+1}:") if f"BIO_{i+1}:" in response else len(response)
            bio_text = response[start:end].strip()
            bios.append(bio_text)

    if not bios:
        bios = [response[:300]]

    return jsonify({"bios": bios})


# ─────────────────────────────────────────────
# ROUTES — DAILY MATCH
# ─────────────────────────────────────────────
@app.route('/api/match/today', methods=['GET'])
def api_get_today_match():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = get_current_user()
    if not user or not user.get('profile_complete'):
        return jsonify({"error": "Profile incomplete"}), 400

    today = date.today().isoformat()

    # Check if today's match already exists using db_layer
    today_match_record = get_today_match(user_id)  # from db_layer
    if today_match_record:
        candidate_id = today_match_record.get('candidate_id')
        candidate = get_user(candidate_id) or {}
        safe_candidate = _safe_profile(candidate)
        return jsonify({
            "has_match": True,
            "match": today_match_record,
            "candidate": safe_candidate,
            "already_sent_hi": today_match_record.get('status') in ['hi_sent', 'conversation']
        })

    # Generate new match
    result = engine.find_daily_match(user_id)

    if not result:
        return jsonify({
            "has_match": False,
            "message": "We're searching the universe for your perfect match. Check back soon.",
            "next_match_at": (datetime.now() + timedelta(hours=2)).isoformat()
        })

    candidate = result['candidate']
    candidate_id = candidate['id']
    compatibility = result['compatibility']

    # Record the match via db_layer
    match_data = {
        "user_id": user_id,
        "candidate_id": candidate_id,
        "match_date": today,
        "compatibility": compatibility,
        "status": "pending"
    }
    create_match(match_data)

    # Get the saved match
    today_match_record = get_today_match(user_id)  # from db_layer

    safe_candidate = _safe_profile(candidate)

    return jsonify({
        "has_match": True,
        "match": today_match_record,
        "candidate": safe_candidate,
        "already_sent_hi": False
    })


def _safe_profile(profile: dict) -> dict:
    """Return profile safe for frontend (no sensitive data)."""
    if not profile:
        return {}
    return {
        "id": profile.get('id'),
        "name": profile.get('name'),
        "age": profile.get('age'),
        "city": profile.get('city'),
        "country": profile.get('country'),
        "profession": profile.get('profession'),
        "bio": profile.get('bio'),
        "lifestyle": profile.get('lifestyle', []),
        "archetype": profile.get('archetype', {}),
        "natal_type": profile.get('natal_type'),
        "social_style": profile.get('social_style'),
        "religion": profile.get('religion'),
        "education": profile.get('education'),
        "attractiveness_score": profile.get('attractiveness_score'),
        "photos": profile.get('photos', [])
    }


@app.route('/api/match/next_time', methods=['GET'])
def next_match_time():
    """When will the next match be available?"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    # Next match is tomorrow at 9am
    now = datetime.now()
    tomorrow_9am = datetime(now.year, now.month, now.day, 9, 0, 0)
    if now.hour >= 9:
        tomorrow_9am = tomorrow_9am + timedelta(days=1)

    hours_left = max(0, (tomorrow_9am - now).seconds // 3600)
    minutes_left = max(0, ((tomorrow_9am - now).seconds % 3600) // 60)

    return jsonify({
        "next_match_at": tomorrow_9am.isoformat(),
        "hours_left": hours_left,
        "minutes_left": minutes_left
    })


# ─────────────────────────────────────────────
# ROUTES — MESSAGING
# ─────────────────────────────────────────────
@app.route('/api/match/send_hi', methods=['POST'])
def send_hi():
    """Send a Hi to today's match."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.json
    candidate_id = data.get('candidate_id')
    message_text = data.get('message', 'Hi 👋')

    user_matches = get_user_matches(user_id)
    today = date.today().isoformat()

    for match in user_matches:
        if match.get('candidate_id') == candidate_id and match.get('match_date') == today:
            # Update match status
            update_match(match.get('id'), {'status': 'hi_sent'})
            
            # Get user info for message
            user = get_user(user_id)
            candidate = get_user(candidate_id)
            
            # Send message via db_layer
            conv_id = f"{user_id}_{candidate_id}"
            send_message(conv_id, user_id, user.get('name', 'User'), message_text)

            return jsonify({
                "success": True,
                "conversation_id": conv_id,
                "message": f"Your Hi has been sent to {candidate.get('name', 'your match') if candidate else 'your match'}. The conversation begins."
            })

    return jsonify({"error": "Match not found for today"}), 404


@app.route('/api/messages/<conv_id>', methods=['GET'])
def get_messages(conv_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    # Verify user is part of this conversation
    if user_id not in conv_id:
        return jsonify({"error": "Unauthorized"}), 403

    messages = get_conversation_messages(conv_id)  # from db_layer
    return jsonify({"messages": messages})


@app.route('/api/messages/<conv_id>/send', methods=['POST'])
def api_send_message(conv_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    if user_id not in conv_id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    text = data.get('text', '').strip()
    if not text:
        return jsonify({"error": "Message cannot be empty"}), 400

    user = get_user(user_id) or {}
    # Use db_layer send_message
    message_data = {
        "conversation_id": conv_id,
        "sender_id": user_id,
        "sender_name": user.get('name', 'Unknown'),
        "text": text
    }
    send_message(message_data)  # from db_layer

    return jsonify({"success": True})


# ─────────────────────────────────────────────
# ROUTES — AI COMPANION
# ─────────────────────────────────────────────
@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """AI companion chat — processes feedback and gives coaching."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json
    user_message = data.get('message', '')
    last_candidate_id = data.get('last_candidate_id', '')

    if not user_message:
        return jsonify({"error": "Message required"}), 400

    # Process feedback if it mentions a match
    feedback_keywords = ['boring', 'exciting', 'liked', 'didn\'t like', 'too', 'not enough',
                         'attractive', 'ugly', 'interesting', 'dull', 'next', 'more', 'less']
    is_feedback = any(kw in user_message.lower() for kw in feedback_keywords)

    if is_feedback and last_candidate_id:
        adjustments = engine.process_ai_feedback(user_id, user_message, last_candidate_id)
        if adjustments:
            update_user(user_id, {'ai_feedback_adjustments': adjustments})

    # Get last match for context
    user_matches = get_user_matches(user_id)
    last_match_record = user_matches[-1] if user_matches else None
    last_match_with_candidate = None
    if last_match_record:
        cand_id = last_match_record.get('candidate_id')
        candidate = get_user(cand_id) or {}
        last_match_with_candidate = {
            "candidate": candidate,
            "compatibility": last_match_record.get('compatibility', {})
        }

    # Build system prompt
    system_prompt = build_ai_coach_prompt(user, last_match_with_candidate)

    # Get conversation history
    history = user.get('ai_conversation', [])

    # Call Gemini
    response = call_gemini(system_prompt, user_message, history)

    # Save conversation via db_layer
    new_conversation = (user.get('ai_conversation', []) or []) + [
        {"role": "user", "content": user_message},
        {"role": "model", "content": response}
    ]
    # Keep only last 20 messages
    update_user(user_id, {'ai_conversation': new_conversation[-20:]})

    return jsonify({
        "response": response,
        "feedback_processed": is_feedback,
        "adjustments_applied": bool(is_feedback and last_candidate_id)
    })


@app.route('/api/ai/match_insight', methods=['POST'])
def match_insight():
    """Get AI insight about today's match."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = get_current_user()
    data = request.json
    candidate_id = data.get('candidate_id')
    candidate = USERS_DB.get(candidate_id, {})

    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404

    user_type = user.get('natal_type', 'SD')
    cand_type = candidate.get('natal_type', 'SD')
    user_loi = user.get('loi_score', 50)
    cand_loi = candidate.get('loi_score', 50)

    compat = get_compatibility_dynamic(user_type, cand_type, user_loi, cand_loi)

    # Type translations (hidden hand principle)
    type_translations = {
        "SS": "soulful depth",
        "SD": "grounded warmth",
        "DS": "creative spark",
        "DD": "bold fire"
    }

    user_essence = type_translations.get(user_type, "unique energy")
    cand_essence = type_translations.get(cand_type, "distinctive rhythm")

    system_prompt = f"""You are Kajole's AI match insight generator. Write a poetic, intriguing, psychologically rich insight about why these two people have been matched today.

User energy: {user_essence} | Candidate energy: {cand_essence}
Compatibility dynamic: {compat['dynamic']} ({compat['score']}% alignment)
Is this an affinity match (same energy): {compat['affinity']}
Is this a polarity match (opposite energies): {compat['is_opposite']}

Write 2-3 sentences that:
1. Describe the energetic dynamic between them in poetic, non-clinical language
2. Hint at what they might learn from each other or offer each other
3. Create intrigue and curiosity — make the user WANT to say Hi

Keep it under 80 words. No clichés. No "soulmate" language. Sophisticated, magnetic, real."""

    insight_prompt = f"Generate the match insight for {user.get('name', 'our user')} meeting {candidate.get('name', 'their match')} today."
    insight = call_gemini(system_prompt, insight_prompt)

    return jsonify({
        "insight": insight,
        "compatibility": compat,
        "dynamic_name": compat['dynamic'],
        "score": compat['score']
    })


# ─────────────────────────────────────────────
# ROUTES — MATCH HISTORY & INBOX
# ─────────────────────────────────────────────
@app.route('/api/matches/history', methods=['GET'])
def match_history():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user_matches = get_user_matches(user_id)  # from db_layer
    result = []

    for match in reversed(user_matches):
        cand_id = match.get('candidate_id')
        candidate = get_user(cand_id) or {}
        result.append({
            "match_date": match.get('match_date'),
            "status": match.get('status', 'pending'),
            "compatibility": match.get('compatibility', {}),
            "candidate": _safe_profile(candidate)
        })

    return jsonify({"matches": result})


@app.route('/api/matches/inbox', methods=['GET'])
def inbox():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user_matches = get_user_matches(user_id)  # from db_layer
    active_convos = []

    for match in user_matches:
        # Include matches with any active status (not just pending)
        if match.get('status') in ['hi_sent', 'conversation', 'active']:
            cand_id = match.get('candidate_id')
            candidate = get_user(cand_id) or {}
            # Use the conversation_id from the match, or build it
            conv_id = match.get('conversation_id') or f"conv_{user_id}_{cand_id}"
            messages = get_conversation_messages(conv_id)  # from db_layer
            last_msg = messages[-1] if messages else None

            active_convos.append({
                "conversation_id": conv_id,
                "candidate": _safe_profile(candidate),
                "match_date": match.get('match_date'),
                "last_message": last_msg,
                "message_count": len(messages)
            })

    return jsonify({"conversations": active_convos})


# ─────────────────────────────────────────────
# ROUTES — USER PROFILE
# ─────────────────────────────────────────────
@app.route('/api/profile/me', methods=['GET'])
def get_my_profile():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    user = get_user(user_id)  # Fetch fresh user data from database
    if not user:
        return jsonify({"error": "User not found"}), 404
    safe = {k: v for k, v in user.items() if k not in ['password_hash', 'ai_conversation']}
    print(f"Profile data for {user_id}: photos = {safe.get('photos', [])}")
    return jsonify(safe)


@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.json
    safe_fields = ['bio', 'profession', 'education', 'lifestyle', 'social_style',
                   'religion', 'city', 'country', 'photos']
    updates = {}
    for field in safe_fields:
        if field in data:
            updates[field] = data[field]
    if updates:
        update_user(user_id, updates)
    return jsonify({"success": True})


# ============================================================================
# PHOTO UPLOAD
# ============================================================================

@app.route('/api/photos/upload', methods=['POST'])
def upload_photo():
    """Upload a photo for the current user."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    if 'photo' not in request.files:
        return jsonify({"error": "No photo provided"}), 400
    
    file = request.files['photo']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Check file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        return jsonify({"error": "Invalid file type. Use JPEG, PNG, or WebP"}), 400
    
    # Check file size (max 5MB)
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    if size > 5 * 1024 * 1024:
        return jsonify({"error": "File too large. Max 5MB"}), 400
    
    # Read file data
    photo_data = file.read()
    
    # Upload to Firebase Storage
    from firebase_db import upload_photo as fb_upload_photo
    result = fb_upload_photo(user_id, photo_data, file.filename)
    
    if result.get('success'):
        return jsonify({
            "success": True,
            "url": result.get('url'),
            "photos": get_user(user_id).get('photos', [])
        })
    else:
        return jsonify({"error": result.get('error', 'Upload failed')}), 500


@app.route('/api/photos/delete', methods=['POST'])
def delete_photo():
    """Delete a photo for the current user."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    photo_url = data.get('url')
    if not photo_url:
        return jsonify({"error": "No photo URL provided"}), 400
    
    from firebase_db import delete_photo as fb_delete_photo
    result = fb_delete_photo(user_id, photo_url)
    
    if result.get('success'):
        return jsonify({
            "success": True,
            "photos": get_user(user_id).get('photos', [])
        })
    else:
        return jsonify({"error": result.get('error', 'Delete failed')}), 500


@app.route('/api/photos', methods=['GET'])
def get_photos():
    """Get all photos for the current user."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    from firebase_db import get_user_photos
    photos = get_user_photos(user_id)
    return jsonify({"photos": photos})


if __name__ == '__main__':
    seed_demo_profiles()
    print("🔥 Kajole is running at http://0.0.0.0:5002")
    app.run(host='0.0.0.0', port=5002, debug=True)