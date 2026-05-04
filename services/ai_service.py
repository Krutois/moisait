import json
import os
import re
from collections import Counter


class AIService:
    DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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
    def _fallback_flashcards(text: str, keywords: list[str], limit: int = 5):
        sentences = AIService._split_sentences(text)
        cards = []

        for keyword in keywords[:limit]:
            keyword_lower = keyword.lower()
            related_sentence = next(
                (s for s in sentences if keyword_lower in s.lower()),
                None
            )

            back = related_sentence or f"Review how {keyword} appears in the lecture."
            cards.append({
                "front": keyword,
                "back": back
            })

        if not cards and sentences:
            for idx, sentence in enumerate(sentences[:limit], start=1):
                cards.append({
                    "front": f"Main idea {idx}",
                    "back": sentence
                })

        return cards

    @staticmethod
    def _fallback_quiz(text: str, keywords: list[str], limit: int = 5):
        sentences = AIService._split_sentences(text)
        quiz = []

        for idx, sentence in enumerate(sentences[:limit], start=1):
            focus = keywords[idx - 1] if idx - 1 < len(keywords) else f"point {idx}"
            quiz.append({
                "question": f"What is the key idea about {focus}?",
                "answer": sentence,
                "explanation": "This answer comes directly from the lecture text."
            })

        if not quiz and keywords:
            for keyword in keywords[:limit]:
                quiz.append({
                    "question": f"Explain {keyword}.",
                    "answer": f"{keyword} is a key concept from the lecture.",
                    "explanation": "Use the lecture context to expand this answer."
                })

        return quiz

    @staticmethod
    def _fallback_study_pack(text: str):
        clean = AIService._normalize_text(text)
        sentences = AIService._split_sentences(clean)
        topic = sentences[0][:120] if sentences else "Lecture"
        summary = AIService._fallback_summary(clean, max_sentences=3)
        keywords = AIService._fallback_keywords(clean, limit=8)
        flashcards = AIService._fallback_flashcards(clean, keywords, limit=5)
        quiz = AIService._fallback_quiz(clean, keywords, limit=5)

        flashcards_block = "\n".join(
            f"{idx + 1}. {item['front']} — {item['back']}"
            for idx, item in enumerate(flashcards)
        ) or "- No flashcards generated"

        quiz_block = "\n".join(
            f"{idx + 1}. {item['question']}\n   Answer: {item['answer']}"
            for idx, item in enumerate(quiz)
        ) or "- No quiz generated"

        structured = (
            f"Topic:\n{topic}\n\n"
            f"Summary:\n{summary}\n\n"
            f"Key terms:\n"
            f"{chr(10).join('- ' + k for k in keywords) if keywords else '- No key terms found'}\n\n"
            f"Flashcards:\n{flashcards_block}\n\n"
            f"Quiz:\n{quiz_block}"
        )

        return {
            "topic": topic,
            "summary": summary,
            "keywords": keywords,
            "flashcards": flashcards,
            "quiz": quiz,
            "structured": structured,
            "study_type": "study"
        }

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
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None

        return None

    @staticmethod
    def _call_text_model(prompt: str):
        client = AIService._get_client()
        if client is None:
            return None, "AI client is unavailable"

        try:
            response = client.responses.create(
                model=AIService.DEFAULT_MODEL,
                input=prompt,
            )
            output_text = getattr(response, "output_text", None)
            if output_text:
                return output_text.strip(), None
            return None, "Empty AI response"
        except Exception as error:
            return None, str(error)

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

        fallback_summary = AIService._fallback_summary(clean, max_sentences=3)
        keywords = AIService._fallback_keywords(clean, limit=8)
        sentences = AIService._split_sentences(clean)
        topic = sentences[0][:120] if sentences else "Lecture"

        fallback = {
            "summary": fallback_summary,
            "structured": fallback_summary,
            "keywords": keywords,
            "summary_type": summary_type
        }

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
            if summary_type == "short":
                fallback["structured"] = f"Short summary:\n{fallback_summary}"
            elif summary_type == "bullets":
                bullet_lines = sentences[:5] if sentences else [fallback_summary]
                fallback["structured"] = "Bullet points:\n" + "\n".join(f"- {item}" for item in bullet_lines)
            elif summary_type == "exam":
                fallback["structured"] = (
                    f"Exam notes:\n\n"
                    f"Topic:\n{topic}\n\n"
                    f"Main idea:\n{fallback_summary}\n\n"
                    "What to review:\n"
                    "- Key definitions\n"
                    "- Main arguments\n"
                    "- Important examples\n"
                    "- Important terms\n"
                    "- Possible exam questions"
                )
            elif summary_type == "terms":
                terms = keywords or ["No key terms found"]
                fallback["structured"] = "Key terms:\n" + "\n".join(f"- {term}" for term in terms)
            else:
                fallback["structured"] = (
                    f"Topic:\n{topic}\n\n"
                    f"Main idea:\n{fallback_summary}\n\n"
                    f"Short notes:\n{fallback_summary}\n\n"
                    "What to review:\n"
                    "- Core definitions\n"
                    "- Main ideas\n"
                    "- Important terms\n"
                    "- Examples from the lecture"
                )
            return fallback, None

        parsed = AIService._safe_json_parse(raw_result)
        if not isinstance(parsed, dict):
            return fallback, None

        summary = str(parsed.get("summary") or fallback_summary).strip()
        structured = str(parsed.get("structured") or summary).strip()

        raw_keywords = parsed.get("keywords") or keywords
        if not isinstance(raw_keywords, list):
            raw_keywords = keywords

        keywords_clean = [str(item).strip() for item in raw_keywords if str(item).strip()][:8]

        if summary_type == "short":
            if not structured:
                structured = f"Short summary:\n{summary}"
        elif summary_type == "bullets" and not structured:
            structured = "Bullet points:\n" + "\n".join(f"- {item}" for item in sentences[:5] or [summary])
        elif summary_type == "exam" and not structured:
            structured = (
                f"Exam notes:\n\n"
                f"Topic:\n{topic}\n\n"
                f"Main idea:\n{summary}\n\n"
                "What to review:\n"
                "- Key definitions\n"
                "- Main arguments\n"
                "- Important examples\n"
                "- Important terms\n"
                "- Possible exam questions"
            )
        elif summary_type == "terms" and not structured:
            structured = "Key terms:\n" + "\n".join(f"- {term}" for term in keywords_clean or ["No key terms found"])

        return {
            "summary": summary,
            "structured": structured,
            "keywords": keywords_clean,
            "summary_type": summary_type
        }, None

    @staticmethod
    def study_mode_text(text: str):
        clean = AIService._normalize_text(text)
        if not clean:
            return None, "Empty text"

        fallback = AIService._fallback_study_pack(clean)

        prompt = f"""
You are building a study pack from lecture text.

Return STRICT JSON with this exact schema:
{{
  "topic": "short topic",
  "summary": "short study summary",
  "keywords": ["term1", "term2", "term3", "term4", "term5"],
  "flashcards": [
    {{"front": "term or question", "back": "short answer"}},
    {{"front": "term or question", "back": "short answer"}}
  ],
  "quiz": [
    {{"question": "question", "answer": "correct answer", "explanation": "short explanation"}},
    {{"question": "question", "answer": "correct answer", "explanation": "short explanation"}}
  ]
}}

Rules:
- Return JSON only.
- No markdown.
- No emojis.
- Keep it clear and useful for studying.
- Make flashcards short and quiz answers concise.
- If the text is weak or short, still create a usable study pack.

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

        raw_keywords = parsed.get("keywords") or fallback["keywords"]
        if not isinstance(raw_keywords, list):
            raw_keywords = fallback["keywords"]
        keywords = [str(item).strip() for item in raw_keywords if str(item).strip()][:8]

        raw_flashcards = parsed.get("flashcards") or fallback["flashcards"]
        if not isinstance(raw_flashcards, list):
            raw_flashcards = fallback["flashcards"]

        flashcards = []
        for item in raw_flashcards[:6]:
            if isinstance(item, dict):
                front = str(item.get("front") or "").strip()
                back = str(item.get("back") or "").strip()
                if front and back:
                    flashcards.append({"front": front, "back": back})
            elif isinstance(item, str) and "—" in item:
                front, back = item.split("—", 1)
                front = front.strip()
                back = back.strip()
                if front and back:
                    flashcards.append({"front": front, "back": back})

        if not flashcards:
            flashcards = fallback["flashcards"]

        raw_quiz = parsed.get("quiz") or fallback["quiz"]
        if not isinstance(raw_quiz, list):
            raw_quiz = fallback["quiz"]

        quiz = []
        for item in raw_quiz[:6]:
            if isinstance(item, dict):
                question = str(item.get("question") or "").strip()
                answer = str(item.get("answer") or "").strip()
                explanation = str(item.get("explanation") or "").strip()
                if question and answer:
                    quiz.append({
                        "question": question,
                        "answer": answer,
                        "explanation": explanation
                    })

        if not quiz:
            quiz = fallback["quiz"]

        topic = str(parsed.get("topic") or fallback["topic"]).strip()
        flashcards_block = "\n".join(
            f"{idx + 1}. {item['front']} — {item['back']}"
            for idx, item in enumerate(flashcards)
        )
        quiz_block = "\n".join(
            f"{idx + 1}. {item['question']}\n   Answer: {item['answer']}"
            for idx, item in enumerate(quiz)
        )

        structured = (
            f"Topic:\n{topic}\n\n"
            f"Summary:\n{summary}\n\n"
            f"Key terms:\n{chr(10).join('- ' + k for k in keywords) if keywords else '- No key terms found'}\n\n"
            f"Flashcards:\n{flashcards_block}\n\n"
            f"Quiz:\n{quiz_block}"
        )

        return {
            "topic": topic,
            "summary": summary,
            "keywords": keywords,
            "flashcards": flashcards,
            "quiz": quiz,
            "structured": structured,
            "study_type": "study"
        }, None