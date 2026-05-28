# SmartLecture

SmartLecture is a Flask web platform for deaf and hard-of-hearing users. It turns speech into text, shows live captions, saves transcripts and exports materials.

Diploma positioning:

> SmartLecture — веб-платформа для глухих және нашар еститін адамдарға арналған, сөйлеуді мәтінге айналдыратын және тірі субтитр көрсететін жүйе.

## Goal

The project improves access to spoken information in lectures, meetings and everyday communication. SmartLecture is not positioned as a generic student speech-to-text tool; it is an accessibility-focused platform with visual statuses, large readable captions and deaf-friendly workflows.

## Key Features

- Live captions at `/subtitles`: fullscreen mode, large text, caption font size controls, high contrast, caption background color, visual recording indicator, clear/copy/save actions.
- Workspace at `/workspace`: separate blocks for speech recording, audio upload, recognition result, text tools and accessibility actions.
- Dialog mode at `/dialog`: large speaker-separated messages, visible “switch speaker” action, visual status, save to history.
- History and favorites: search, filter, pin, favorite and export saved transcripts.
- Export formats: TXT, PDF and DOCX.
- Accessibility settings: text size, high contrast, dark/light theme, reduced motion, visual notifications and caption background.
- Multilingual UI: Қазақша, Русский, English.
- Admin dashboard and Flask-Admin for diploma demonstration.
- OpenAI audio transcription when `OPENAI_API_KEY` is configured; browser speech recognition remains available without it.

## Pages

- `/` — accessibility-first landing page.
- `/subtitles` — main live captions experience.
- `/workspace` — record, upload, edit, save and process text.
- `/dialog` — conversation mode with speaker separation.
- `/history` — saved transcripts and exports.
- `/favorites` — important saved records.
- `/about` — diploma project description.
- `/accessibility` and `/about-accessibility` — accessibility explanation and usage guide.
- `/contact` — project contact form.
- `/admin-dashboard` — custom admin dashboard.

## Technologies

- Python, Flask, Flask-Login, Flask-WTF, Flask-Migrate, Flask-Bcrypt
- SQLAlchemy and SQLite by default
- Browser SpeechRecognition API
- OpenAI API for optional audio transcription and AI text tools
- ReportLab and python-docx for exports
- HTML, CSS, JavaScript, localStorage
- Pytest

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
flask --app app:create_app db upgrade
flask --app app:create_app run
```

Example environment:

```env
FLASK_ENV=development
SECRET_KEY=change-me
DATABASE_URL=sqlite:///smartlecture.db
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_AUDIO_MODEL=gpt-4o-mini-transcribe
SUPPORT_EMAIL=support@smartlecture.app
```

Never commit `.env` or real API keys. Keep only `.env.example` in the repository.

## Release

```bash
python make_release.py
```

The release archive excludes `.env`, `.git`, `.venv`, caches, local databases, logs and nested zip files.

## Testing

```bash
pytest
```

The test suite covers authentication, transcript CRUD, ownership protection, exports, stats, contact form, admin permissions and audio/AI fallbacks.
