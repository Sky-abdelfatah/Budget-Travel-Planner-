"""Model calls (Gemini REST API) from our own backend.
The key is read from the GEMINI_API_KEY environment variable. It is never written in the code or committed.
If there is no key, or a call fails, the functions return None and the backend uses its rule-based reply."""
import os

ASK_PROMPT = (
    "You are Trip Draft, an AI assistant (not a person) that helps Egyptian university students plan cheap trips "
    "in Egypt. Cities in the sample data: Cairo, Alexandria, Luxor, Aswan, Dahab. All prices are fictional estimates. "
    "Rules: answer in at most 3 short sentences, in the same language as the user (Arabic or English). "
    "Never invent exact prices, opening hours or places. You cannot book or pay for anything. "
    "Do not help with anything illegal, fake tickets or avoiding fees. "
    "If the question is not about budget travel in Egypt, say you can only help with budget trip planning. "
    "If the user needs official or human help (visas, emergencies, disputes), tell them to contact the official source."
)

REWRITE_PROMPT = (
    "You are the voice of Trip Draft, an AI assistant (not a person) that plans cheap trips in Egypt from a small "
    "sample dataset with fictional prices. A backend has already decided what to do and wrote a correct reply. "
    "Rewrite that reply as a friendly, natural message to the user, in at most 4 short sentences. "
    "Rules: write in the language the user used (Arabic if the user wrote Arabic, otherwise English). "
    "Keep every number, city and item name exactly as in the backend reply, written with digits 0-9. "
    "Do not add any price, place, number or fact that is not in the backend reply or the plan facts. "
    "Keep the words Proposed, Accepted, Draft, Confirmed plan, Undo, Redo in English. "
    "Keep the meaning: if the reply says nothing was changed or that something is only a preview, say so. "
    "Do not mention buttons that are not in the list you are given. Plain text only, no markdown."
)

def enabled():
    return bool(os.getenv("GEMINI_API_KEY"))

def _call(system, user, max_tokens=600, timeout=15):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    if "2.5" in model:
        cfg = {"maxOutputTokens": max_tokens, "temperature": 0.3, "thinkingConfig": {"thinkingBudget": 0}}
    else:  # newer models may spend output tokens on thinking, so leave room and keep their default temperature
        cfg = {"maxOutputTokens": max(max_tokens, 2000)}
    body = {"system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": cfg}
    try:
        import httpx
        r = httpx.post(url, json=body, headers={"x-goog-api-key": key, "content-type": "application/json"}, timeout=timeout)
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text[:900] or None
    except Exception:
        return None

def ask(message):
    return _call(ASK_PROMPT, message, 300)

def rewrite(user_message, backend_reply, buttons, plan_facts):
    user = (f"User message: {user_message or '(the user tapped a button)'}\n"
            f"Backend reply: {backend_reply}\n"
            f"Plan facts: {plan_facts or 'no plan yet'}\n"
            f"Buttons shown to the user: {', '.join(buttons) if buttons else 'none'}\n"
            "Write the final reply.")
    return _call(REWRITE_PROMPT, user)
