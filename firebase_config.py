# Firebase Configuration
# Set these environment variables in production
import os

FIREBASE_CONFIG = {
    "type": "service_account",
    "project_id": os.environ.get("FIREBASE_PROJECT_ID", "kajole"),
    "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", ""),
    "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n") if os.environ.get("FIREBASE_PRIVATE_KEY") else "",
    "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL", ""),
    "client_id": os.environ.get("FIREBASE_CLIENT_ID", ""),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.environ.get("FIREBASE_CERT_URL", ""),
}

# For client-side Firebase (used by frontend)
FIREBASE_CLIENT_CONFIG = {
    "apiKey": "AIzaSyCBFiYvBHkiGLaEAbIaC7V1RAYjr3_KbWU",
    "authDomain": "kajole.firebaseapp.com",
    "projectId": "kajole",
    "storageBucket": "kajole.firebasestorage.app",
    "messagingSenderId": "637388268082",
    "appId": "1:637388268082:web:291eb520f17770e60c922b",
    "measurementId": "G-QJQNX01LW5"
}

# Firestore database ID (None = default database)
FIRESTORE_DATABASE_ID = None

# Storage bucket name
STORAGE_BUCKET = "kajole.firebasestorage.app"