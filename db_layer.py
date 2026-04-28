"""
Database Abstraction Layer for Kajole
Switches between Firebase and in-memory storage based on availability
"""
import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# Try to import Firebase
try:
    from firebase_db import (
        is_firebase_available,
        create_user as fb_create_user,
        get_user as fb_get_user,
        get_user_by_email as fb_get_user_by_email,
        update_user as fb_update_user,
        get_all_users as fb_get_all_users,
        create_match as fb_create_match,
        get_user_matches as fb_get_user_matches,
        get_today_match as fb_get_today_match,
        create_conversation as fb_create_conversation,
        get_user_conversations as fb_get_user_conversations,
        send_message as fb_send_message,
        get_conversation_messages as fb_get_conversation_messages,
        create_session as fb_create_session,
        get_session as fb_get_session,
        delete_session as fb_delete_session,
        upload_photo as fb_upload_photo,
        seed_demo_profiles as fb_seed_demo_profiles,
        seed_initial_matches as fb_seed_initial_matches,
    )
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

# In-memory fallback storage
IN_MEMORY_DB = {
    'users': {},
    'matches': {},
    'messages': {},
    'sessions': {},
    'conversations': {},
}

# ============================================================================
# USER OPERATIONS
# ============================================================================

def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_create_user(user_data)
    
    # In-memory fallback
    user_id = user_data.get('id', f"user_{uuid.uuid4().hex[:12]}")
    user_data['id'] = user_id
    user_data['created_at'] = datetime.utcnow().isoformat()
    user_data['updated_at'] = datetime.utcnow().isoformat()
    IN_MEMORY_DB['users'][user_id] = user_data
    return user_data

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_get_user(user_id)
    return IN_MEMORY_DB['users'].get(user_id)

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_get_user_by_email(email)
    
    for user in IN_MEMORY_DB['users'].values():
        if user.get('email') == email:
            return user
    return None

def update_user(user_id: str, updates: Dict[str, Any]) -> bool:
    """Update user fields"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_update_user(user_id, updates)
    
    if user_id in IN_MEMORY_DB['users']:
        IN_MEMORY_DB['users'][user_id].update(updates)
        IN_MEMORY_DB['users'][user_id]['updated_at'] = datetime.utcnow().isoformat()
        return True
    return False

def get_all_users() -> List[Dict[str, Any]]:
    """Get all users"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_get_all_users()
    return list(IN_MEMORY_DB['users'].values())

def delete_user(user_id: str) -> bool:
    """Delete a user"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        from firebase_db import delete_user as fb_delete
        return fb_delete(user_id)
    
    if user_id in IN_MEMORY_DB['users']:
        del IN_MEMORY_DB['users'][user_id]
        return True
    return False


# ============================================================================
# MATCH OPERATIONS
# ============================================================================

def create_match(match_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a match record"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_create_match(match_data)
    
    match_id = match_data.get('id', f"match_{uuid.uuid4().hex[:12]}")
    match_data['id'] = match_id
    match_data['created_at'] = datetime.utcnow().isoformat()
    
    user_id = match_data.get('user_id')
    if user_id not in IN_MEMORY_DB['matches']:
        IN_MEMORY_DB['matches'][user_id] = []
    IN_MEMORY_DB['matches'][user_id].append(match_data)
    return match_data

def get_user_matches(user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Get all matches for a user"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_get_user_matches(user_id, limit)
    return IN_MEMORY_DB['matches'].get(user_id, [])[-limit:]

def get_today_match(user_id: str) -> Optional[Dict[str, Any]]:
    """Get today's match for user"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_get_today_match(user_id)
    
    today = datetime.utcnow().strftime('%Y-%m-%d')
    for match in IN_MEMORY_DB['matches'].get(user_id, []):
        if match.get('match_date') == today:
            return match
    return None

def update_match(match_id: str, updates: Dict[str, Any]) -> bool:
    """Update a match"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        from firebase_db import update_match as fb_update_match
        return fb_update_match(match_id, updates)
    
    # In-memory: find and update
    for user_matches in IN_MEMORY_DB['matches'].values():
        for match in user_matches:
            if match.get('id') == match_id:
                match.update(updates)
                return True
    return False


# ============================================================================
# CONVERSATION & MESSAGE OPERATIONS
# ============================================================================

def create_conversation(convo_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a conversation"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_create_conversation(convo_data)
    
    participants = sorted([convo_data.get('user_id'), convo_data.get('candidate_id')])
    convo_id = f"convo_{participants[0]}_{participants[1]}"
    
    convo = {
        'id': convo_id,
        'participants': participants,
        'user_id': convo_data.get('user_id'),
        'candidate_id': convo_data.get('candidate_id'),
        'created_at': datetime.utcnow().isoformat(),
        'last_message_at': datetime.utcnow().isoformat(),
        'last_message': '',
    }
    IN_MEMORY_DB['conversations'][convo_id] = convo
    return convo

def get_user_conversations(user_id: str) -> List[Dict[str, Any]]:
    """Get all conversations for a user"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_get_user_conversations(user_id)
    
    convos = []
    for convo in IN_MEMORY_DB['conversations'].values():
        if user_id in convo.get('participants', []):
            convos.append(convo)
    return sorted(convos, key=lambda x: x.get('last_message_at', ''), reverse=True)

def get_conversation(convo_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific conversation"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        from firebase_db import get_conversation as fb_get_convo
        return fb_get_convo(convo_id)
    return IN_MEMORY_DB['conversations'].get(convo_id)

def send_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send a message"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_send_message(message_data)
    
    convo_id = message_data.get('conversation_id')
    message = {
        'id': f"msg_{uuid.uuid4().hex[:12]}",
        'conversation_id': convo_id,
        'sender_id': message_data.get('sender_id'),
        'text': message_data.get('text', ''),
        'created_at': datetime.utcnow().isoformat(),
        'read': False,
    }
    
    if convo_id not in IN_MEMORY_DB['messages']:
        IN_MEMORY_DB['messages'][convo_id] = []
    IN_MEMORY_DB['messages'][convo_id].append(message)
    
    # Update conversation
    if convo_id in IN_MEMORY_DB['conversations']:
        IN_MEMORY_DB['conversations'][convo_id]['last_message'] = message['text']
        IN_MEMORY_DB['conversations'][convo_id]['last_message_at'] = message['created_at']
    
    return message

def get_conversation_messages(convo_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get messages in a conversation"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_get_conversation_messages(convo_id, limit)
    return IN_MEMORY_DB['messages'].get(convo_id, [])[-limit:]


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def create_session(user_id: str) -> str:
    """Create a login session"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_create_session(user_id)
    
    token = uuid.uuid4().hex
    IN_MEMORY_DB['sessions'][token] = {
        'token': token,
        'user_id': user_id,
        'created_at': datetime.utcnow().isoformat(),
        'expires_at': (datetime.utcnow() + timedelta(days=30)).isoformat(),
    }
    return token

def get_session(token: str) -> Optional[Dict[str, Any]]:
    """Get session by token"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_get_session(token)
    
    session = IN_MEMORY_DB['sessions'].get(token)
    if session:
        expires = datetime.fromisoformat(session.get('expires_at', '2000-01-01'))
        if expires > datetime.utcnow():
            return session
    return None

def delete_session(token: str) -> bool:
    """Delete a session"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_delete_session(token)
    
    if token in IN_MEMORY_DB['sessions']:
        del IN_MEMORY_DB['sessions'][token]
        return True
    return False


# ============================================================================
# PHOTO UPLOAD
# ============================================================================

def upload_photo(user_id: str, file_data: bytes, filename: str) -> str:
    """Upload a photo"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_upload_photo(user_id, file_data, filename)
    
    # In-memory: return a placeholder URL
    # In production, you'd use Firebase Storage
    return f"/static/uploads/{user_id}/{filename}"


# ============================================================================
# DEMO DATA
# ============================================================================

def seed_demo_profiles():
    """Seed demo profiles"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_seed_demo_profiles()
    
    # In-memory seed
    from natal_calculator import get_archetype
    
    demo_profiles = [
        {
            'id': 'demo_001',
            'email': 'sophia.demo@kajole.com',
            'name': 'Sophia Chen',
            'age': 26,
            'gender': 'female',
            'city': 'San Francisco',
            'country': 'United States',
            'orientation': 'straight',
            'profession': 'UX Designer',
            'education': "Master's Degree",
            'bio': "Designing delightful experiences by day, hunting for the best dumplings by night.",
            'lifestyle': ['Art', 'Food & Wine', 'Travel', 'Mindfulness'],
            'social_style': 'ambivert',
            'natal_type': 'SS',
            'archetype': get_archetype('SS', 'female'),
            'loi_score': 55,
            'onboarded': True,
        },
        {
            'id': 'demo_002',
            'email': 'marcus.demo@kajole.com',
            'name': 'Marcus Williams',
            'age': 32,
            'gender': 'male',
            'city': 'Los Angeles',
            'country': 'United States',
            'orientation': 'straight',
            'profession': 'Film Producer',
            'education': "Bachelor's Degree",
            'bio': "Stories are my life — whether I'm producing them or living them.",
            'lifestyle': ['Travel', 'Business', 'Art', 'Music'],
            'social_style': 'extrovert',
            'natal_type': 'DD',
            'archetype': get_archetype('DD', 'male'),
            'loi_score': 71,
            'onboarded': True,
        },
        {
            'id': 'demo_003',
            'email': 'isabelle.demo@kajole.com',
            'name': 'Isabelle Moreau',
            'age': 27,
            'gender': 'female',
            'city': 'Paris',
            'country': 'France',
            'orientation': 'straight',
            'profession': 'Art Curator',
            'education': "Master's Degree",
            'bio': "Passionate about art, culture, and meaningful connections.",
            'lifestyle': ['Art', 'Travel', 'Reading', 'Fashion'],
            'social_style': 'introvert',
            'natal_type': 'SD',
            'archetype': get_archetype('SD', 'female'),
            'loi_score': 62,
            'onboarded': True,
        },
        {
            'id': 'demo_004',
            'email': 'jordan.demo@kajole.com',
            'name': 'Jordan Taylor',
            'age': 29,
            'gender': 'male',
            'city': 'London',
            'country': 'United Kingdom',
            'orientation': 'straight',
            'profession': 'Investment Banker',
            'education': "Master's Degree",
            'bio': "Driven professional with a hidden creative side.",
            'lifestyle': ['Business', 'Music', 'Fitness', 'Travel'],
            'social_style': 'ambivert',
            'natal_type': 'DS',
            'archetype': get_archetype('DS', 'male'),
            'loi_score': 48,
            'onboarded': True,
        },
        {
            'id': 'demo_005',
            'email': 'amara.demo@kajole.com',
            'name': 'Amara Okonkwo',
            'age': 25,
            'gender': 'female',
            'city': 'Berlin',
            'country': 'Germany',
            'orientation': 'straight',
            'profession': 'Software Engineer',
            'education': "Bachelor's Degree",
            'bio': "Coding by day, dancing by night.",
            'lifestyle': ['Tech', 'Travel', 'Music', 'Fitness'],
            'social_style': 'extrovert',
            'natal_type': 'DS',
            'archetype': get_archetype('DS', 'female'),
            'loi_score': 67,
            'onboarded': True,
        },
        {
            'id': 'demo_006',
            'email': 'rafael.demo@kajole.com',
            'name': 'Rafael Costa',
            'age': 31,
            'gender': 'male',
            'city': 'São Paulo',
            'country': 'Brazil',
            'orientation': 'straight',
            'profession': 'Architect',
            'education': "Master's Degree",
            'bio': "I design spaces that bring people together.",
            'lifestyle': ['Art', 'Travel', 'Nature', 'Sport'],
            'social_style': 'ambivert',
            'natal_type': 'SS',
            'archetype': get_archetype('SS', 'male'),
            'loi_score': 58,
            'onboarded': True,
        },
        {
            'id': 'demo_007',
            'email': 'nadia.demo@kajole.com',
            'name': 'Nadia Rahman',
            'age': 28,
            'gender': 'female',
            'city': 'Dubai',
            'country': 'UAE',
            'orientation': 'straight',
            'profession': 'Marketing Director',
            'education': "MBA",
            'bio': "Ambitious, cultured, and deeply curious about the world.",
            'lifestyle': ['Business', 'Fashion', 'Travel', 'Reading'],
            'social_style': 'extrovert',
            'natal_type': 'DD',
            'archetype': get_archetype('DD', 'female'),
            'loi_score': 73,
            'onboarded': True,
        },
    ]
    
    for profile in demo_profiles:
        if profile['id'] not in IN_MEMORY_DB['users']:
            IN_MEMORY_DB['users'][profile['id']] = profile
            print(f"   Seeded: {profile['name']}")


def seed_initial_matches(user_id: str, num_matches: int = 3) -> int:
    """Seed initial matches for a new user"""
    if FIREBASE_AVAILABLE and is_firebase_available():
        return fb_seed_initial_matches(user_id, num_matches)
    
    # In-memory fallback - simplified version
    import random
    from natal_calculator import get_compatibility_dynamic
    
    user = get_user(user_id)
    if not user:
        return 0
    
    demo_ids = ['demo_001', 'demo_002', 'demo_003', 'demo_004', 'demo_005', 'demo_006', 'demo_007']
    
    # Filter by orientation
    user_gender = user.get('gender', 'male')
    user_orient = user.get('orientation', 'straight')
    
    compatible_demos = []
    for demo_id in demo_ids:
        demo = get_user(demo_id)
        if not demo:
            continue
        demo_gender = demo.get('gender', 'female')
        if user_orient == 'straight' and demo_gender != user_gender:
            compatible_demos.append(demo)
        elif user_orient == 'gay' and demo_gender == user_gender:
            compatible_demos.append(demo)
        elif user_orient == 'bisexual':
            compatible_demos.append(demo)
    
    if not compatible_demos:
        return 0
    
    random.shuffle(compatible_demos)
    selected = compatible_demos[:num_matches]
    
    matches_created = 0
    today = datetime.utcnow().date()
    
    for i, demo in enumerate(selected):
        user_type = user.get('natal_type', 'SD')
        demo_type = demo.get('natal_type', 'SD')
        user_loi = user.get('loi_score', 50)
        demo_loi = demo.get('loi_score', 50)
        
        compat = get_compatibility_dynamic(user_type, demo_type, user_loi, demo_loi)
        match_date = (today - timedelta(days=i+1)).isoformat()
        
        match_data = {
            'id': f"match_{uuid.uuid4().hex[:12]}",
            'user_id': user_id,
            'candidate_id': demo['id'],
            'match_date': match_date,
            'compatibility': compat,
            'compatibility_score': compat.get('score', 50),
            'dynamic': compat.get('dynamic', 'Unknown'),
            'status': 'pending'
        }
        
        if user_id not in IN_MEMORY_DB['matches']:
            IN_MEMORY_DB['matches'][user_id] = []
        IN_MEMORY_DB['matches'][user_id].append(match_data)
        matches_created += 1
    
    return matches_created


# ============================================================================
# STATUS CHECK
# ============================================================================

def get_db_status() -> Dict[str, Any]:
    """Get database status"""
    return {
        'firebase_available': FIREBASE_AVAILABLE and is_firebase_available() if FIREBASE_AVAILABLE else False,
        'storage_type': 'Firebase Firestore' if (FIREBASE_AVAILABLE and is_firebase_available()) else 'In-Memory',
        'user_count': len(get_all_users()),
    }

# Export IN_MEMORY_DB for backward compatibility with app.py
IN_MEMORY_DB = {
    'users': {},
    'matches': {},
    'messages': {},
    'sessions': {},
    'conversations': {},
}