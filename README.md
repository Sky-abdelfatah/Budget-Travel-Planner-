# Trip Draft

Team: **Just How It Works**

Budget travel planner chatbot for Egypt. Principle: **User Control and Agency**.
Every plan item is a dataset id with a dataset price. Items start as `proposed`; only a user action makes them `accepted`.
The plan panel counts only accepted items as spent: it shows EGP accepted, EGP proposed (not accepted yet) and EGP left.
Undo/Redo move a pointer through saved plan states (event log). Changing budget or days shows a preview first.
If the budget is too low, the chatbot offers three buttons: Raise budget, Shorten trip, Keep my budget.

## Run (Windows PowerShell)
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000/ for the chat page, or http://127.0.0.1:8000/docs for the API.

## Tests
```
pytest -q tests
```
Runs 40 tests: dataset loading (200 rows), grounding (every plan item is a dataset id with its dataset price), accepted-only totals, and the 37 prompts of the test set (`tests/cases_weeks_6_7.py`).

## Files
- `main.py` FastAPI app: `/chat`, `/action`, `/health`, `/`
- `planner.py` request parsing (English and Arabic), budget planner, alternatives
- `data_loader.py` reads `trip_draft_dataset_excel_semicolon.csv` (fixes its messy quoting)
- `static/index.html` simple accessible chat page
- `tests/` pytest tests and the test-set cases

## Notes
- No API key is needed. The LLM is not used in this build; the planner is rule-based on the dataset.
- Never commit API keys. Prices are fictional.
