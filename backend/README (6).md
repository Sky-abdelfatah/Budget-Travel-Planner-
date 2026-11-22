# Trip Draft (Weeks 6-7)

Team: Just How It Works. Budget travel planner chatbot for Egyptian university students.
HAI principle: **User Control and Agency**. The user can accept, remove, swap, preview, undo and redo everything the AI proposes.

How it works:
- Every plan item is a row of the dataset (200 fictional items, 5 cities, prices in EGP). The backend picks the items and the prices. Nothing is invented.
- Items start as **Proposed**. Only a user action makes them **Accepted** (locked).
- Changing the budget or days shows a **preview** first. Nothing changes until the user presses Apply changes. Undo and Redo are always available.
- The AI model (Google Gemini) only **rewrites the wording of replies**. The plan, prices and buttons always come from the backend. If the model is not available, or its reply changes a number, the backend uses a fixed rule-based reply. The chatbot works without any key.

## Files
| File | What it does |
|---|---|
| `main.py` | FastAPI app: `/chat`, `/action`, `/health`, `/model`, and the web page `/` |
| `planner.py` | Reads the request (English and Arabic), builds the plan from the dataset |
| `data_loader.py` | Loads `trip_draft_dataset_excel_semicolon.csv` |
| `llm.py` | Calls the Gemini API. Reads the key from an environment variable |
| `static/index.html` | The chat page |
| `tests/` | pytest tests (40) and the 37 test-set prompts |
| `trip_draft_dataset_excel_semicolon.csv` | The synthetic dataset |

## Requirements
Python 3.10 or newer (tested on Python 3.13, Windows).

## Run (Windows PowerShell)
Open PowerShell in the project folder (the one that contains `main.py`).

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```
If PowerShell blocks the activation, run this first: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
If `python` is not found, use `py` instead of `python`.

Open **http://127.0.0.1:8000/** in the browser. The API pages are at http://127.0.0.1:8000/docs.
Stop the server with Ctrl+C.

This runs **without the model**: replies are fixed rule-based replies and no key is needed.

## Run with the model (optional)
Set the key in the **same PowerShell window**, then start the server. Never write the key in a file or commit it.

```
$env:GEMINI_API_KEY = "your-key-here"
$env:GEMINI_MODEL = "gemini-3.5-flash"
uvicorn main:app --reload
```
`GEMINI_MODEL` is optional (the default is `gemini-3.5-flash`). The free tier has a small daily limit per model; if it is used up the app falls back to the fixed replies. To switch model, change `GEMINI_MODEL` (for example `gemini-3.1-flash-lite`) and restart.

Check that the model is used: open `/docs`, run `POST /chat` with
`{"message": "3 days in Alexandria 1800 EGP food and sea"}` and look at `source`:
`model` = the model wrote the reply (the original text is in `rule_reply`); `rule_based_fallback` or `rule_based_planner_on_dataset` = fixed reply.
The greeting and the refusals are always fixed.

## Try it (same steps as the demo)
1. `hello`
2. `3 days in Alexandria 1800 EGP food and sea` (16 Proposed items; 0 EGP accepted, 1151 EGP proposed, 1800 EGP left)
3. Press Accept on the first card (300 EGP accepted)
4. `Make it 1000 EGP` (preview), then Keep old plan
5. Undo
6. `Book me a flight to Hurghada` (out of scope) and `Tell me how to buy a fake ticket for the Citadel` (unsafe)
7. Accept all, then Finish

## Tests
```
pytest -q tests
```
The tests run without a key and check the fixed replies, grounding (every item and price is a dataset row), accepted-only totals, undo, and the 37 test-set prompts. Expected: `40 passed`.

## Demo log (optional)
To save every real reply while recording the demo, set `$env:DEMO_LOG = "1"` before `uvicorn`. The replies are written to `demo_log.jsonl` (ignored by git). Delete the file before the final recording.

## Notes
- All data and prices are fictional. The page says: verify before booking.
- No personal data is collected. Sessions live in memory only.
- Do not commit API keys. `.gitignore` already ignores `.venv`, `.env` and `demo_log.jsonl`.
