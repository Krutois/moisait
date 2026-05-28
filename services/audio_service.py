import logging
import os


logger = logging.getLogger(__name__)


class AudioService:
    ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "webm"}

    @staticmethod
    def is_allowed(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in AudioService.ALLOWED_EXTENSIONS

    @staticmethod
    def transcribe(file_storage, model=None):
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None, "OPENAI_API_KEY is not configured. Use browser speech recognition fallback."

        try:
            from openai import OpenAI
        except Exception:
            return None, "OpenAI package is not installed"

        client = OpenAI(api_key=api_key)
        audio_model = model or os.getenv("OPENAI_AUDIO_MODEL", "gpt-4o-mini-transcribe")
        try:
            file_storage.stream.seek(0)
            result = client.audio.transcriptions.create(
                model=audio_model,
                file=(file_storage.filename, file_storage.stream, file_storage.mimetype),
            )
            text = getattr(result, "text", None)
            if not text and isinstance(result, dict):
                text = result.get("text")
            return (text or "").strip(), None
        except Exception as error:
            logger.exception("Audio transcription failed")
            status_code = getattr(error, "status_code", None)
            error_code = getattr(error, "code", None)
            error_body = getattr(error, "body", None)

            if isinstance(error_body, dict):
                nested_error = error_body.get("error")
                if isinstance(nested_error, dict):
                    error_code = error_code or nested_error.get("code")

            if error_code == "insufficient_quota":
                return None, "OpenAI quota exceeded"
            if status_code == 401:
                return None, "OpenAI API key is invalid"
            if status_code == 429:
                return None, "OpenAI rate limit reached"
            if status_code == 400:
                return None, "OpenAI rejected the audio request"

            return None, "Audio transcription failed"
