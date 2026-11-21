import os, time, httpx, llm, main
from main import ChatRequest

msg = "3 days in Alexandria 1800 EGP food and sea"
resp = main._chat(ChatRequest(message=msg))
user = (f"User message: {msg}\nBackend reply: {resp['reply']}\n"
        f"Plan facts: {main._facts(resp['plan'])}\n"
        f"Buttons shown to the user: {', '.join(resp['buttons'])}\nWrite the final reply.")
model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
print("model:", model)
body = {"system_instruction": {"parts": [{"text": llm.REWRITE_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": 2000}}
t = time.time()
try:
    r = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                   json=body, headers={"x-goog-api-key": os.getenv("GEMINI_API_KEY", ""), "content-type": "application/json"}, timeout=60)
    print("status:", r.status_code, "| seconds:", round(time.time() - t, 1))
    print(r.text[:900])
except Exception as e:
    print("ERROR:", type(e).__name__, e, "| seconds:", round(time.time() - t, 1))