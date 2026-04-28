# Kajole Dating App

A slow-burn dating app powered by Deepsyke Psychology.

## Deployment to Render

1. Push this code to a GitHub repository
2. Connect the repository to Render
3. Set the following environment variables in Render:
   - `SECRET_KEY` - A random secret key (Render can generate this)
   - `FIREBASE_PROJECT_ID` - Your Firebase project ID
   - `FIREBASE_STORAGE_BUCKET` - Your Firebase storage bucket
   - `FIREBASE_SERVICE_ACCOUNT` - The entire JSON content of your Firebase service account key (as a string)

4. Deploy!

## Environment Variables

| Variable | Description |
|----------|-------------|
| SECRET_KEY | Flask secret key for sessions |
| FIREBASE_PROJECT_ID | Firebase project ID |
| FIREBASE_STORAGE_BUCKET | Firebase storage bucket URL |
| FIREBASE_SERVICE_ACCOUNT | JSON string of service account key |

## Local Development

```bash
pip install -r requirements.txt
python app.py
```

## Firebase Setup

1. Create a Firebase project
2. Enable Firestore Database
3. Enable Storage
4. Create a service account key and save it as `firebase-service-account.json`