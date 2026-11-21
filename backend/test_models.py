import os, httpx
key = os.getenv("GEMINI_API_KEY", "")
H = {"x-goog-api-key": key, "content-type": "application/json"}
r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=100", headers=H, timeout=30)
names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
         if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m["name"]
         and not any(x in m["name"] for x in ("image", "tts", "live", "audio", "embedding", "preview-"))]
for n in names[:8]:
    body = {"contents": [{"role": "user", "parts": [{"text": "Say hi"}]}], "generationConfig": {"maxOutputTokens": 50}}
    try:
        x = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{n}:generateContent", json=body, headers=H, timeout=30)
        print(n, "->", x.status_code)
    except Exception as e:
        print(n, "-> ERROR", type(e).__name__)