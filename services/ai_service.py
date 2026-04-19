import json
import os
import re
from collections import Counter


class AIService:
    DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # =========================
    # INTERNAL HELPERS
    # =========================
    @staticmethod
    def _normalize_text(text: str) -> str:
        return (text or "").strip()

    @staticmethod
    def _get_client():
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None

        try:
            from openai import OpenAI
            return OpenAI(api_key=api_key)
        except Exception:
            return None

    @staticmethod
    def _split_sentences(text: str):
        clean = AIService._normalize_text(text)
        if not clean:
            return []

        parts = re.split(r"(?<=[.!?])\s+|\n+", clean)
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def _extract_words(text: str):
        return re.findall(
            r"[A-Za-zА-Яа-яӘәІіҢңҒғҮүҰұҚқӨөҺһЁё0-9\-]{3,}",
            text or ""
        )

    @staticmethod
    def _fallback_keywords(text: str, limit: int = 8):
        stop_words = {
            "the", "and", "for", "with", "that", "this", "from", "into", "have", "has",
            "you", "your", "about", "what", "when", "where", "which", "there", "their",
            "это", "для", "что", "или", "при", "если", "они", "как", "так", "его", "она",
            "мен", "және", "үшін", "бұл", "сол", "қалай", "болса", "болып", "деген",
            "lecture", "summary", "text", "mode", "demo"
        }

        words = [
            word.lower()
            for word in AIService._extract_words(text)
            if word.lower() not in stop_words
        ]

        if not words:
            return []

        counts = Counter(words)
        return [word for word, _ in counts.most_common(limit)]

    @staticmethod
    def _fallback_summary(text: str, max_sentences: int = 3):
        sentences = AIService._split_sentences(text)
        if not sentences:
            return ""

        if len(sentences) <= max_sentences:
            return " ".join(sentences)

        return " ".join(sentences[:max_sentences])

    @staticmethod
    def _safe_json_parse(text: str):
        raw = (text or "").strip()
        if not raw:
            return None

        try:
            return json.loads(raw)
        except Exception:
            pass

        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            return None

        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    @staticmethod
    def _call_text_model(prompt: str):
        client = AIService._get_client()
        if client is None:
            return None, "AI client is unavailable"

        try:
            response = client.responses.create(
                model=AIService.DEFAULT_MODEL,
                input=prompt
            )

            output_text = getattr(response, "output_text", None)
            if output_text:
                return output_text.strip(), None

            return None, "Empty AI response"
        except Exception as error:
            return None, str(error)

    @staticmethod
    def _build_fallback_structured(text: str, summary_type: str):
        clean = AIService._normalize_text(text)
        sentences = AIService._split_sentences(clean)
        topic = sentences[0][:120] if sentences else "Lecture"
        summary = AIService._fallback_summary(clean, max_sentences=3)
        keywords = AIService._fallback_keywords(clean, limit=8)

        if summary_type == "short":
            structured = (
                "Short summary:\n"
                f"{summary}"
            )

        elif summary_type == "bullets":
            bullet_source = sentences[:5] if sentences else [summary]
            bullets = "\n".join(f"- {item}" for item in bullet_source)
            structured = (
                "Bullet points:\n"
                f"{bullets}"
            )

        elif summary_type == "exam":
            structured = (
                "Exam notes:\n\n"
                f"Topic:\n{topic}\n\n"
                f"Main idea:\n{summary}\n\n"
                "What to review:\n"
                "- Key definitions\n"
                "- Main arguments\n"
                "- Important examples\n"
                "- Important terms\n"
                "- Possible exam questions"
            )

        elif summary_type == "terms":
            terms = keywords or ["No key terms found"]
            terms_block = "\n".join(f"- {term}" for term in terms)
            structured = (
                "Key terms:\n"
                f"{terms_block}"
            )

        else:
            structured = (
                "Topic:\n"
                f"{topic}\n\n"
                "Main idea:\n"
                f"{summary}\n\n"
                "Short notes:\n"
                f"{summary}\n\n"
                "What to review:\n"
                "- Core definitions\n"
                "- Main ideas\n"
                "- Important terms\n"
                "- Examples from the lecture"
            )

        return {
            "summary": summary,
            "structured": structured,
            "keywords": keywords,
            "summary_type": summary_type
        }

    # =========================
    # PUBLIC METHODS
    # =========================
    @staticmethod
    def summarize_text(text: str):
        clean = AIService._normalize_text(text)
        if not clean:
            return None, "Empty text"

        prompt = f"""
You are a precise academic summarizer.
Write a short clear summary of the text below.
Keep the meaning accurate.
Return plain text only.

TEXT:
{clean}
""".strip()

        result, error = AIService._call_text_model(prompt)
        if error or not result:
            return AIService._fallback_summary(clean, max_sentences=3), None

        return result, None

    @staticmethod
    def correct_text(text: str):
        clean = AIService._normalize_text(text)
        if not clean:
            return None, "Empty text"

        prompt = f"""
You are a text correction assistant.
Correct grammar, punctuation and clarity.
Do not change the meaning.
Return only the corrected text.

TEXT:
{clean}
""".strip()

        result, error = AIService._call_text_model(prompt)
        if error or not result:
            corrected = re.sub(r"\s+", " ", clean).strip()
            return corrected, None

        return result, None

    @staticmethod
    def paraphrase_text(text: str):
        clean = AIService._normalize_text(text)
        if not clean:
            return None, "Empty text"

        prompt = f"""
You are a paraphrasing assistant.
Rewrite the text in clearer wording.
Preserve the original meaning.
Return only the paraphrased text.

TEXT:
{clean}
""".strip()

        result, error = AIService._call_text_model(prompt)
        if error or not result:
            return clean, None

        return result, None

    @staticmethod
    def translate_text(text: str, target: str = "ru"):
        clean = AIService._normalize_text(text)
        if not clean:
            return None, "Empty text"

        target = (target or "ru").strip()

        prompt = f"""
Translate the text below into this target language: {target}.
Preserve the meaning accurately.
Return only translated text.

TEXT:
{clean}
""".strip()

        result, error = AIService._call_text_model(prompt)
        if error or not result:
            return clean, None

        return result, None

    @staticmethod
    def lecture_summary_text(text: str, summary_type: str = "lecture"):
        clean = AIService._normalize_text(text)
        if not clean:
            return None, "Empty text"

        allowed_types = {"lecture", "short", "bullets", "exam", "terms"}
        if summary_type not in allowed_types:
            summary_type = "lecture"

        fallback = AIService._build_fallback_structured(clean, summary_type)

        prompt = f"""
You are an academic lecture assistant.

Create a study output using this format: {summary_type}

Available formats:
- lecture: structured lecture notes
- short: very short summary
- bullets: concise bullet points
- exam: exam revision notes
- terms: key terms with short explanations

Return STRICT JSON with this exact schema:
{{
  "topic": "short topic",
  "summary": "concise summary",
  "structured": "formatted study output as plain text",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}

Rules:
- Return JSON only.
- Do not include markdown outside JSON.
- Do not use emojis or decorative icons.
- The structured field must be useful for a student.
- Keep it clear, compact and practical.

TEXT:
{clean}
""".strip()

        raw_result, error = AIService._call_text_model(prompt)
        if error or not raw_result:
            return fallback, None

        parsed = AIService._safe_json_parse(raw_result)
        if not isinstance(parsed, dict):
            return fallback, None

        summary = str(parsed.get("summary") or fallback["summary"]).strip()
        structured = str(parsed.get("structured") or fallback["structured"]).strip()

        raw_keywords = parsed.get("keywords") or fallback["keywords"]
        if not isinstance(raw_keywords, list):
            raw_keywords = fallback["keywords"]

        keywords = [
            str(item).strip()
            for item in raw_keywords
            if str(item).strip()
        ][:8]

        return {
            "summary": summary,
            "structured": structured,
            "keywords": keywords,
            "summary_type": summary_type
        }, None