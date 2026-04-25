"""
Firebase Database Integration for Kajole
Replaces in-memory storage with Firestore
"""
import os
import json
import uuid
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import firebase_admin
from firebase_admin import credentials, firestore, storage, auth as firebase_auth
from google.cloud.firestore_v1.base_client import BaseClient

# Initialize Firebase (singleton pattern)
_firebase_app = None
_db = None
_bucket = None

def init_firebase():
    """Initialize Firebase Admin SDK"""
    global _firebase_app, _db, _bucket
    
    if _firebase_app is not None:
        return _firebase_app
    
    try:
        # Try to get credentials from multiple sources
        cred_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        
        # Get storage bucket from env or use default
        storage_bucket = os.environ.get("FIREBASE_STORAGE_BUCKET", "kajole.firebasestorage.app")
        
        # Also check for local service account file
        local_cred_path = os.path.join(os.path.dirname(__file__), 'firebase-service-account.json')
        
        if cred_json:
            # Credentials provided as JSON string
            print("📦 Found FIREBASE_CREDENTIALS_JSON environment variable")
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        elif cred_path and os.path.exists(cred_path):
            # Credentials from environment path
            print(f"📁 Found credentials file at: {cred_path}")
            cred = credentials.Certificate(cred_path)
        elif os.path.exists(local_cred_path):
            # Credentials from local file
            print(f"📁 Found local credentials file")
            cred = credentials.Certificate(local_cred_path)
        else:
            # Use Application Default Credentials (for Cloud Run/GKE/etc)
            print("⚠️ No credentials found, trying Application Default Credentials")
            cred = credentials.ApplicationDefault()
        
        _firebase_app = firebase_admin.initialize_app(cred, {
            'storageBucket': storage_bucket
        })
        
        _db = firestore.client()
        _bucket = storage.bucket()
        
        print(f"✅ Firebase initialized successfully - Bucket: {storage_bucket}")
        return _firebase_app
        
    except Exception as e:
        print(f"⚠️ Firebase initialization failed: {e}")
        print("   Falling back to in-memory storage")
        return None

def get_db():
    """Get Firestore database client"""
    global _db
    if _db is None:
        init_firebase()
    return _db

def get_bucket():
    """Get Firebase Storage bucket"""
    global _bucket
    if _bucket is None:
        init_firebase()
    return _bucket

def is_firebase_available() -> bool:
    """Check if Firebase is available"""
    return get_db() is not None


# ============================================================================
# USER OPERATIONS
# ============================================================================

def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user in Firestore"""
    db = get_db()
    if not db:
        return None
    
    user_id = user_data.get('id', f"user_{uuid.uuid4().hex[:12]}")
    
    user_doc = {
        'id': user_id,
        'email': user_data.get('email', ''),
        'name': user_data.get('name', ''),
        'password_hash': user_data.get('password_hash', ''),  # Needed for login
        'age': user_data.get('age'),
        'dob': user_data.get('dob', ''),
        'gender': user_data.get('gender', ''),
        'city': user_data.get('city', ''),
        'country': user_data.get('country', ''),
        'orientation': user_data.get('orientation', 'straight'),
        'profession': user_data.get('profession', ''),
        'education': user_data.get('education', ''),
        'bio': user_data.get('bio', ''),
        'religion': user_data.get('religion', ''),
        'ethnicity': user_data.get('ethnicity', ''),
        'lifestyle': user_data.get('lifestyle', []),
        'social_style': user_data.get('social_style', 'ambivert'),
        'attractiveness_score': user_data.get('attractiveness_score', 5),
        'intellectual_score': user_data.get('intellectual_score', 5),
        'photos': user_data.get('photos', []),
        'photo_urls': user_data.get('photo_urls', []),
        'archetype': user_data.get('archetype', {}),
        'loi_score': user_data.get('loi_score', 50),
        'natal_type': user_data.get('natal_type', ''),
        'preferences': user_data.get('preferences', {}),
        'dealbreakers': user_data.get('dealbreakers', []),
        'ideal_partner_desc': user_data.get('ideal_partner_desc', ''),
        'onboarded': user_data.get('onboarded', False),
        'onboarding_step': user_data.get('onboarding_step', 1),
        'profile_complete': user_data.get('profile_complete', False),
        'active': user_data.get('active', True),
        'onboarded_at': user_data.get('onboarded_at'),
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP,
        'last_match_date': None,
        'daily_match_id': None,
        'ai_feedback_adjustments': user_data.get('ai_feedback_adjustments', {}),
        'ai_conversation': user_data.get('ai_conversation', []),
    }
    
    db.collection('users').document(user_id).set(user_doc)
    
    # Return the user without server timestamps
    result = user_doc.copy()
    result['created_at'] = datetime.utcnow().isoformat()
    result['updated_at'] = datetime.utcnow().isoformat()
    return result

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    db = get_db()
    if not db:
        return None
    
    doc = db.collection('users').document(user_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    db = get_db()
    if not db:
        return None
    
    users = db.collection('users').where('email', '==', email).limit(1).get()
    for doc in users:
        return doc.to_dict()
    return None

def update_user(user_id: str, updates: Dict[str, Any]) -> bool:
    """Update user fields"""
    db = get_db()
    if not db:
        return False
    
    updates['updated_at'] = firestore.SERVER_TIMESTAMP
    db.collection('users').document(user_id).update(updates)
    return True

def delete_user(user_id: str) -> bool:
    """Delete a user"""
    db = get_db()
    if not db:
        return False
    
    db.collection('users').document(user_id).delete()
    return True

def get_all_users() -> List[Dict[str, Any]]:
    """Get all users (for matching)"""
    db = get_db()
    if not db:
        return []
    
    users = []
    for doc in db.collection('users').get():
        users.append(doc.to_dict())
    return users


# ============================================================================
# MATCH OPERATIONS
# ============================================================================

def create_match(match_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a match record"""
    db = get_db()
    if not db:
        return None
    
    match_id = match_data.get('id', f"match_{uuid.uuid4().hex[:12]}")
    
    match_doc = {
        'id': match_id,
        'user_id': match_data.get('user_id'),
        'candidate_id': match_data.get('candidate_id'),
        'compatibility_score': match_data.get('compatibility_score', 0),
        'dynamic': match_data.get('dynamic', ''),
        'match_date': match_data.get('match_date', datetime.utcnow().strftime('%Y-%m-%d')),
        'status': match_data.get('status', 'pending'),  # pending, accepted, passed
        'created_at': firestore.SERVER_TIMESTAMP,
    }
    
    db.collection('matches').document(match_id).set(match_doc)
    
    result = match_doc.copy()
    result['created_at'] = datetime.utcnow().isoformat()
    return result

def get_user_matches(user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Get all matches for a user"""
    db = get_db()
    if not db:
        return []
    
    matches = []
    # Simple query without orderBy to avoid needing composite index
    docs = db.collection('matches').where('user_id', '==', user_id).limit(limit).get()
    for doc in docs:
        matches.append(doc.to_dict())
    # Sort in Python instead
    matches.sort(key=lambda x: x.get('match_date', ''), reverse=True)
    return matches

def get_today_match(user_id: str) -> Optional[Dict[str, Any]]:
    """Get today's match for user"""
    db = get_db()
    if not db:
        return None
    
    today = datetime.utcnow().strftime('%Y-%m-%d')
    # Get all matches for user and filter by date in Python (avoids index requirement)
    docs = db.collection('matches').where('user_id', '==', user_id).limit(10).get()
    for doc in docs:
        match = doc.to_dict()
        match_date = match.get('match_date', '')
        # Check if match_date starts with today's date
        if match_date.startswith(today):
            return match
    return None

def update_match(match_id: str, updates: Dict[str, Any]) -> bool:
    """Update a match"""
    db = get_db()
    if not db:
        return False
    
    db.collection('matches').document(match_id).update(updates)
    return True


# ============================================================================
# MESSAGE OPERATIONS
# ============================================================================

def create_conversation(convo_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a conversation between two users"""
    db = get_db()
    if not db:
        return None
    
    participants = sorted([convo_data.get('user_id'), convo_data.get('candidate_id')])
    convo_id = f"convo_{participants[0]}_{participants[1]}"
    
    convo_doc = {
        'id': convo_id,
        'participants': participants,
        'user_id': convo_data.get('user_id'),
        'candidate_id': convo_data.get('candidate_id'),
        'created_at': firestore.SERVER_TIMESTAMP,
        'last_message_at': firestore.SERVER_TIMESTAMP,
        'last_message': '',
    }
    
    db.collection('conversations').document(convo_id).set(convo_doc)
    
    result = convo_doc.copy()
    result['created_at'] = datetime.utcnow().isoformat()
    result['last_message_at'] = datetime.utcnow().isoformat()
    return result

def get_user_conversations(user_id: str) -> List[Dict[str, Any]]:
    """Get all conversations for a user"""
    db = get_db()
    if not db:
        return []
    
    conversations = []
    docs = db.collection('conversations').where('participants', 'array_contains', user_id).order_by('last_message_at', direction=firestore.Query.DESCENDING).get()
    for doc in docs:
        conversations.append(doc.to_dict())
    return conversations

def get_conversation(convo_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific conversation"""
    db = get_db()
    if not db:
        return None
    
    doc = db.collection('conversations').document(convo_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

def send_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send a message in a conversation"""
    db = get_db()
    if not db:
        return None
    
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    
    message_doc = {
        'id': message_id,
        'conversation_id': message_data.get('conversation_id'),
        'sender_id': message_data.get('sender_id'),
        'sender_name': message_data.get('sender_name', 'Unknown'),
        'text': message_data.get('text', ''),
        'timestamp': datetime.utcnow().isoformat(),
        'type': message_data.get('type', 'text'),
        'read': False,
    }
    
    # Add message to messages collection
    db.collection('messages').document(message_id).set(message_doc)
    
    return message_doc
    
    result = message_doc.copy()
    result['created_at'] = datetime.utcnow().isoformat()
    return result

def get_conversation_messages(convo_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get messages in a conversation"""
    db = get_db()
    if not db:
        return []
    
    messages = []
    # Simple query without orderBy to avoid needing composite index
    docs = db.collection('messages').where('conversation_id', '==', convo_id).limit(limit).get()
    for doc in docs:
        messages.append(doc.to_dict())
    # Sort in Python instead
    messages.sort(key=lambda x: x.get('timestamp', ''))
    return messages


# ============================================================================
# PHOTO UPLOAD
# ============================================================================

def upload_photo(user_id: str, file_data: bytes, filename: str) -> str:
    """Upload a photo to Firebase Storage"""
    bucket = get_bucket()
    if not bucket:
        return None
    
    # Generate unique filename
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg'
    blob_path = f"photos/{user_id}/{uuid.uuid4().hex[:8]}.{ext}"
    
    blob = bucket.blob(blob_path)
    blob.upload_from_string(file_data, content_type=f'image/{ext}')
    
    # Make publicly accessible
    blob.make_public()
    
    return blob.public_url

def delete_photo(photo_url: str) -> bool:
    """Delete a photo from Firebase Storage"""
    bucket = get_bucket()
    if not bucket:
        return False
    
    try:
        # Extract blob path from URL
        # URL format: https://storage.googleapis.com/{bucket}/{path}
        path = photo_url.split(f"{bucket.name}/")[-1]
        blob = bucket.blob(path)
        blob.delete()
        return True
    except:
        return False


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def create_session(user_id: str) -> str:
    """Create a login session"""
    db = get_db()
    if not db:
        return None
    
    session_token = uuid.uuid4().hex
    
    session_doc = {
        'token': session_token,
        'user_id': user_id,
        'created_at': firestore.SERVER_TIMESTAMP,
        'expires_at': datetime.utcnow() + timedelta(days=30),
    }
    
    db.collection('sessions').document(session_token).set(session_doc)
    return session_token

def get_session(token: str) -> Optional[Dict[str, Any]]:
    """Get session by token"""
    db = get_db()
    if not db:
        return None
    
    doc = db.collection('sessions').document(token).get()
    if doc.exists:
        session = doc.to_dict()
        # Check expiry
        if session.get('expires_at') and session['expires_at'] > datetime.utcnow():
            return session
    return None

def delete_session(token: str) -> bool:
    """Delete a session (logout)"""
    db = get_db()
    if not db:
        return False
    
    db.collection('sessions').document(token).delete()
    return True


# ============================================================================
# DEMO DATA SEEDING
# ============================================================================

def seed_demo_profiles():
    """Seed demo profiles for testing with photos and complete profiles."""
    # Demo password hash for "DemoPass123!" (bcrypt)
    import bcrypt
    demo_password_hash = bcrypt.hashpw('DemoPass123!'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    demo_profiles = [
        {
            'id': 'demo_001',
            'email': 'sophia.demo@kajole.com',
            'password_hash': demo_password_hash,
            'name': 'Sophia Chen',
            'age': 26,
            'dob': '1998-07-15',
            'gender': 'female',
            'city': 'San Francisco',
            'country': 'United States',
            'orientation': 'straight',
            'profession': 'UX Designer',
            'education': "Master's Degree",
            'bio': "Designing delightful experiences by day, hunting for the best dumplings by night. Looking for someone who appreciates both the aesthetic and the authentic.",
            'lifestyle': ['Art', 'Food & Wine', 'Travel', 'Mindfulness'],
            'social_style': 'ambivert',
            'natal_type': 'SS',
            'archetype': {'name': 'Maiden', 'element': 'Water', 'energy': 'Yin-Yin'},
            'loi_score': 55,
            'attractiveness_score': 8,
            'intellectual_score': 7,
            'photos': [
                'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400&h=400&fit=crop'
            ],
            'photo_urls': [],
            'preferences': {
                'age_min': 25, 'age_max': 35, 'location_preference': 'same_country',
                'religion': 'any', 'ethnicity': 'any', 'attractiveness_min': 6
            },
            'profile_complete': True,
            'active': True,
            'onboarded': True,
        },
        {
            'id': 'demo_002',
            'email': 'marcus.demo@kajole.com',
            'password_hash': demo_password_hash,
            'name': 'Marcus Williams',
            'age': 32,
            'dob': '1992-03-22',
            'gender': 'male',
            'city': 'Los Angeles',
            'country': 'United States',
            'orientation': 'straight',
            'profession': 'Film Producer',
            'education': "Bachelor's Degree",
            'bio': "Stories are my life — whether I'm producing them or living them. Always seeking the next adventure and someone to share it with.",
            'lifestyle': ['Travel', 'Business', 'Art', 'Music'],
            'social_style': 'extrovert',
            'natal_type': 'DD',
            'archetype': {'name': 'King', 'element': 'Lightning', 'energy': 'Yang-Yang'},
            'loi_score': 71,
            'attractiveness_score': 7,
            'intellectual_score': 6,
            'photos': [
                'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=400&fit=crop'
            ],
            'photo_urls': [],
            'preferences': {
                'age_min': 24, 'age_max': 32, 'location_preference': 'worldwide',
                'religion': 'any', 'ethnicity': 'any', 'attractiveness_min': 5
            },
            'profile_complete': True,
            'active': True,
            'onboarded': True,
        },
        {
            'id': 'demo_003',
            'email': 'isabelle.demo@kajole.com',
            'password_hash': demo_password_hash,
            'name': 'Isabelle Moreau',
            'age': 27,
            'dob': '1997-11-08',
            'gender': 'female',
            'city': 'Paris',
            'country': 'France',
            'orientation': 'straight',
            'profession': 'Art Curator',
            'education': "Master's Degree",
            'bio': "Passionate about art, culture, and meaningful connections. I believe the right relationship is like a masterpiece — it takes time to appreciate.",
            'lifestyle': ['Art', 'Travel', 'Reading', 'Fashion'],
            'social_style': 'introvert',
            'natal_type': 'SD',
            'archetype': {'name': 'Maiden', 'element': 'Water', 'energy': 'Yin-Yang'},
            'loi_score': 62,
            'attractiveness_score': 8,
            'intellectual_score': 8,
            'photos': [
                'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=400&fit=crop'
            ],
            'photo_urls': [],
            'preferences': {
                'age_min': 26, 'age_max': 36, 'location_preference': 'worldwide',
                'religion': 'any', 'ethnicity': 'any', 'attractiveness_min': 6
            },
            'profile_complete': True,
            'active': True,
            'onboarded': True,
        },
        {
            'id': 'demo_004',
            'email': 'jordan.demo@kajole.com',
            'password_hash': demo_password_hash,
            'name': 'Jordan Taylor',
            'age': 29,
            'dob': '1995-06-14',
            'gender': 'male',
            'city': 'London',
            'country': 'United Kingdom',
            'orientation': 'straight',
            'profession': 'Investment Banker',
            'education': "Master's Degree",
            'bio': "Driven professional with a hidden creative side. I play jazz piano on weekends and believe balance is everything.",
            'lifestyle': ['Business', 'Music', 'Fitness', 'Travel'],
            'social_style': 'ambivert',
            'natal_type': 'DS',
            'archetype': {'name': 'Warrior', 'element': 'Fire', 'energy': 'Yang-Yin'},
            'loi_score': 48,
            'attractiveness_score': 7,
            'intellectual_score': 7,
            'photos': [
                'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&h=400&fit=crop'
            ],
            'photo_urls': [],
            'preferences': {
                'age_min': 23, 'age_max': 30, 'location_preference': 'same_country',
                'religion': 'any', 'ethnicity': 'any', 'attractiveness_min': 5
            },
            'profile_complete': True,
            'active': True,
            'onboarded': True,
        },
        {
            'id': 'demo_005',
            'email': 'amara.demo@kajole.com',
            'password_hash': demo_password_hash,
            'name': 'Amara Okonkwo',
            'age': 25,
            'dob': '1999-02-28',
            'gender': 'female',
            'city': 'Berlin',
            'country': 'Germany',
            'orientation': 'straight',
            'profession': 'Software Engineer',
            'education': "Bachelor's Degree",
            'bio': "Coding by day, dancing by night. I love exploring new cultures, trying exotic foods, and finding beauty in unexpected places.",
            'lifestyle': ['Tech', 'Travel', 'Music', 'Fitness'],
            'social_style': 'extrovert',
            'natal_type': 'DS',
            'archetype': {'name': 'Huntress', 'element': 'Fire', 'energy': 'Yang-Yin'},
            'loi_score': 67,
            'attractiveness_score': 8,
            'intellectual_score': 8,
            'photos': [
                'https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=400&h=400&fit=crop'
            ],
            'photo_urls': [],
            'preferences': {
                'age_min': 25, 'age_max': 35, 'location_preference': 'worldwide',
                'religion': 'any', 'ethnicity': 'any', 'attractiveness_min': 6
            },
            'profile_complete': True,
            'active': True,
            'onboarded': True,
        },
        {
            'id': 'demo_006',
            'email': 'rafael.demo@kajole.com',
            'password_hash': demo_password_hash,
            'name': 'Rafael Costa',
            'age': 31,
            'dob': '1993-09-10',
            'gender': 'male',
            'city': 'São Paulo',
            'country': 'Brazil',
            'orientation': 'straight',
            'profession': 'Architect',
            'education': "Master's Degree",
            'bio': "I design spaces that bring people together. Looking for someone to build a life with — one beautiful moment at a time.",
            'lifestyle': ['Art', 'Travel', 'Nature', 'Sport'],
            'social_style': 'ambivert',
            'natal_type': 'SS',
            'archetype': {'name': 'Magician', 'element': 'Earth', 'energy': 'Yin-Yin'},
            'loi_score': 58,
            'attractiveness_score': 7,
            'intellectual_score': 6,
            'photos': [
                'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1463453091185-6158ff44f6be?w=400&h=400&fit=crop'
            ],
            'photo_urls': [],
            'preferences': {
                'age_min': 24, 'age_max': 32, 'location_preference': 'worldwide',
                'religion': 'any', 'ethnicity': 'any', 'attractiveness_min': 5
            },
            'profile_complete': True,
            'active': True,
            'onboarded': True,
        },
        {
            'id': 'demo_007',
            'email': 'nadia.demo@kajole.com',
            'password_hash': demo_password_hash,
            'name': 'Nadia Rahman',
            'age': 28,
            'dob': '1996-04-05',
            'gender': 'female',
            'city': 'Dubai',
            'country': 'UAE',
            'orientation': 'straight',
            'profession': 'Marketing Director',
            'education': "MBA",
            'bio': "Ambitious, cultured, and deeply curious about the world. I believe in living life boldly and loving even bolder.",
            'lifestyle': ['Business', 'Fashion', 'Travel', 'Reading'],
            'social_style': 'extrovert',
            'natal_type': 'DD',
            'archetype': {'name': 'Queen', 'element': 'Lightning', 'energy': 'Yang-Yang'},
            'loi_score': 73,
            'attractiveness_score': 9,
            'intellectual_score': 7,
            'photos': [
                'https://images.unsplash.com/photo-1544005313-94ddf02805df?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1488426862026-3ee343758e0e?w=400&h=400&fit=crop'
            ],
            'photo_urls': [],
            'preferences': {
                'age_min': 27, 'age_max': 38, 'location_preference': 'worldwide',
                'religion': 'any', 'ethnicity': 'any', 'attractiveness_min': 7
            },
            'profile_complete': True,
            'active': True,
            'onboarded': True,
        },
    ]
    
    seeded_count = 0
    for profile in demo_profiles:
        existing = get_user(profile['id'])
        if not existing:
            profile['onboarded_at'] = datetime.utcnow().isoformat()
            create_user(profile)
            print(f"   ✅ Seeded: {profile['name']}")
            seeded_count += 1
        else:
            print(f"   ⏭️ Already exists: {profile['name']}")
    
    return seeded_count

# ============================================================================
# STORAGE OPERATIONS - Photo Upload
# ============================================================================

def upload_photo(user_id: str, photo_data: bytes, filename: str = None) -> Dict[str, Any]:
    """
    Upload a photo for a user.
    First tries Firebase Storage, falls back to local file storage if unavailable.
    
    Args:
        user_id: The user's ID
        photo_data: Raw bytes of the photo
        filename: Optional filename (will be generated if not provided)
    
    Returns:
        Dict with 'success', 'url', and 'error' keys
    """
    import base64
    import os
    
    # Determine file extension and content type
    ext = 'jpg'
    content_type = 'image/jpeg'
    if filename:
        ext = filename.lower().split('.')[-1] if '.' in filename else 'jpg'
        if ext == 'png':
            content_type = 'image/png'
        elif ext == 'webp':
            content_type = 'image/webp'
    
    # Generate unique filename
    photo_filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    
    # Try Firebase Storage first
    bucket = get_bucket()
    
    if bucket:
        try:
            storage_path = f"photos/{user_id}/{photo_filename}"
            
            # Create blob and upload
            blob = bucket.blob(storage_path)
            blob.upload_from_string(photo_data, content_type=content_type)
            
            # Generate a Firebase Storage download token (permanent public URL)
            # Using REST API approach with a download token
            import uuid as _uuid
            download_token = _uuid.uuid4().hex
            
            # Set the download token as metadata so it works as a public URL
            blob.metadata = {'firebaseStorageDownloadTokens': download_token}
            blob.patch()
            
            # Construct the permanent Firebase Storage URL with the download token
            bucket_name = bucket.name
            encoded_path = storage_path.replace('/', '%2F')
            public_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{encoded_path}?alt=media&token={download_token}"
            print(f"✅ Photo uploaded with permanent Firebase download URL")
            
            # Update user's photos array in Firestore
            db = get_db()
            if db:
                user_ref = db.collection('users').document(user_id)
                user_doc = user_ref.get()
                if user_doc.exists:
                    current_photos = user_doc.to_dict().get('photos', [])
                    if not isinstance(current_photos, list):
                        current_photos = []
                    current_photos.append(public_url)
                    user_ref.update({'photos': current_photos})
                    print(f"✅ Updated user {user_id} photos array, now has {len(current_photos)} photos")
            
            return {
                'success': True,
                'url': public_url,
                'path': storage_path
            }
        except Exception as e:
            print(f"⚠️ Firebase Storage upload failed: {e}")
            import traceback
            traceback.print_exc()
            print("   Falling back to local file storage...")
    
    # Fallback: Store locally in static/uploads/photos
    try:
        # Create uploads directory if it doesn't exist
        uploads_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'photos')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Create user-specific directory
        user_dir = os.path.join(uploads_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(user_dir, photo_filename)
        with open(file_path, 'wb') as f:
            f.write(photo_data)
        
        # Generate URL (relative to static folder)
        photo_url = f"/static/uploads/photos/{user_id}/{photo_filename}"
        
        # Store URL in user's photos array in Firestore
        db = get_db()
        if db:
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            if user_doc.exists:
                current_photos = user_doc.to_dict().get('photos', [])
                if not isinstance(current_photos, list):
                    current_photos = []
                current_photos.append(photo_url)
                user_ref.update({'photos': current_photos})
                
                return {
                    'success': True,
                    'url': photo_url,
                    'storage_type': 'local'
                }
        
        return {'success': False, 'error': 'Database not available'}
    except Exception as e:
        print(f"❌ Photo upload failed: {e}")
        return {'success': False, 'error': str(e)}

def delete_photo(user_id: str, photo_url: str) -> Dict[str, Any]:
    """
    Delete a photo for a user.
    Handles Firebase Storage URLs, local file URLs, and base64 data URLs.
    
    Args:
        user_id: The user's ID
        photo_url: The URL of the photo to delete
    
    Returns:
        Dict with 'success' and 'error' keys
    """
    import os
    
    bucket = get_bucket()
    
    # Try to delete from Firebase Storage if it's a storage URL
    if bucket and photo_url.startswith('https://storage.googleapis.com'):
        try:
            # Extract path from URL
            path = photo_url.split(f"{bucket.name}/")[-1].split('?')[0]
            
            # Delete from storage
            blob = bucket.blob(path)
            if blob.exists():
                blob.delete()
        except Exception as e:
            print(f"⚠️ Could not delete from Firebase Storage: {e}")
    
    # Delete local file if it's a local URL
    if photo_url.startswith('/static/uploads/photos/'):
        try:
            # Extract file path
            local_path = photo_url.replace('/static/uploads/photos/', '')
            file_path = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'photos', local_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"⚠️ Could not delete local file: {e}")
    
    # Remove from user's photos array (works for all URL types)
    try:
        db = get_db()
        if db:
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            if user_doc.exists:
                current_photos = user_doc.to_dict().get('photos', [])
                if photo_url in current_photos:
                    current_photos.remove(photo_url)
                    user_ref.update({'photos': current_photos})
        
        return {'success': True}
    except Exception as e:
        print(f"❌ Photo delete failed: {e}")
        return {'success': False, 'error': str(e)}

def get_user_photos(user_id: str) -> List[str]:
    """
    Get all photo URLs for a user.
    """
    user = get_user(user_id)
    if user:
        return user.get('photos', [])
    return []

def seed_initial_matches(user_id: str, num_matches: int = 3) -> int:
    """
    Seed initial matches for a new user - SELF-CONTAINED.
    Creates match records with embedded demo profile data - no DB dependencies.
    """
    import random
    from natal_calculator import get_compatibility_dynamic
    
    user = get_user(user_id)
    if not user:
        return 0
    
    user_gender = user.get('gender', 'male')
    user_orient = user.get('orientation', 'straight')
    user_type = user.get('natal_type', 'SD')
    user_loi = user.get('loi_score', 50)
    
    # Hardcoded attractive demo profiles (NO DB DEPENDENCY)
    demo_profiles = [
        {'id': 'demo_sophia', 'name': 'Sophia Chen', 'natal_type': 'SS', 'loi_score': 55, 'gender': 'female', 'age': 26, 'city': 'San Francisco', 'profession': 'UX Designer', 'bio': 'Designing delightful experiences by day, hunting for the best dumplings by night.'},
        {'id': 'demo_marcus', 'name': 'Marcus Williams', 'natal_type': 'DD', 'loi_score': 71, 'gender': 'male', 'age': 32, 'city': 'Los Angeles', 'profession': 'Film Producer', 'bio': 'Stories are my life - whether producing them or living them.'},
        {'id': 'demo_isabelle', 'name': 'Isabelle Moreau', 'natal_type': 'SD', 'loi_score': 58, 'gender': 'female', 'age': 27, 'city': 'Paris', 'profession': 'Art Curator', 'bio': 'Passionate about art, culture, and meaningful connections.'},
        {'id': 'demo_jordan', 'name': 'Jordan Taylor', 'natal_type': 'DS', 'loi_score': 62, 'gender': 'male', 'age': 29, 'city': 'New York', 'profession': 'Architect', 'bio': 'Building spaces that inspire connection and wonder.'},
        {'id': 'demo_amara', 'name': 'Amara Okonkwo', 'natal_type': 'DD', 'loi_score': 68, 'gender': 'female', 'age': 25, 'city': 'London', 'profession': 'Data Scientist', 'bio': 'Finding patterns in chaos, seeking meaning in moments.'},
        {'id': 'demo_rafael', 'name': 'Rafael Santos', 'natal_type': 'SS', 'loi_score': 60, 'gender': 'male', 'age': 31, 'city': 'Miami', 'profession': 'Chef', 'bio': 'Creating flavors that tell stories and spark memories.'},
        {'id': 'demo_nadia', 'name': 'Nadia Al-Hassan', 'natal_type': 'DD', 'loi_score': 73, 'gender': 'female', 'age': 28, 'city': 'Dubai', 'profession': 'Marketing Director', 'bio': 'Ambitious, cultured, and deeply curious about the world.'},
    ]
    
    # Filter by gender/orientation
    if user_gender == 'male' and user_orient == 'straight':
        targets = [p for p in demo_profiles if p['gender'] == 'female']
    elif user_gender == 'female' and user_orient == 'straight':
        targets = [p for p in demo_profiles if p['gender'] == 'male']
    elif user_orient == 'gay':
        targets = [p for p in demo_profiles if p['gender'] == user_gender]
    else:
        targets = demo_profiles
    
    random.shuffle(targets)
    targets = targets[:num_matches]
    
    today = datetime.utcnow().date()
    matches_created = 0
    
    for i, demo in enumerate(targets):
        try:
            compat = get_compatibility_dynamic(user_type, demo['natal_type'], user_loi, demo['loi_score'])
        except:
            compat = {'score': random.randint(65, 85), 'dynamic': 'Compatible'}
        
        match_data = {
            'id': f"match_{uuid.uuid4().hex[:12]}",
            'user_id': user_id,
            'candidate_id': demo['id'],
            'candidate': demo,  # EMBED the profile data so it displays correctly
            'match_date': (today - timedelta(days=i+1)).isoformat(),
            'compatibility': compat,
            'compatibility_score': compat.get('score', 70),
            'dynamic': compat.get('dynamic', 'Compatible'),
            'status': 'pending'
        }
        
        create_match(match_data)
        matches_created += 1
    
    return matches_created
