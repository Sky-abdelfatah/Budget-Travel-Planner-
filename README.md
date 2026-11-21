# Trip Draft

**Team: Just How It Works**

Trip Draft is a budget travel planner chatbot for Egyptian university students. The user tells the chatbot a city, number of days, budget in EGP and interests, and gets a draft plan built from a small synthetic dataset. All prices are fictional estimates.

**HAI principle: User Control and Agency.** The AI only proposes. The user decides what to accept, remove, swap, preview or undo.

## What it does

- Every plan item is a dataset id with its dataset price. Nothing is invented.
- Items start as **Proposed**. Only a user action makes them **Accepted** (locked).
- The plan panel shows three separate numbers: EGP accepted, EGP proposed (not accepted yet) and EGP left. Only accepted items count as spent.
- **Accept, Remove, Swap** (up to 3 dataset alternatives), **Undo and Redo** (a pointer through saved plan states).
- Changing the budget or the number of days shows a **preview** first. Nothing changes until the user presses Apply changes.
- If the budget is too low, the chatbot changes nothing and offers three buttons: Raise budget, Shorten trip, Keep my budget. Each button leads to its own next step.
- Unsafe requests (fake tickets, avoiding fees, smuggling) and out-of-scope requests (booking, essays, weather) get a polite refusal with a next step.
- Every card shows a source tag, last-verified date and confidence.

## How it works

| Part | What it does |
|---|---|
| `static/index.html` | Chat page and plan panel. Status is written in words, not only colour. Works with keyboard and screen readers. |
| `main.py` | FastAPI backend: `/chat`, `/action`, `/model`, `/health`, `/`. Holds the session state and the undo log. |
| `planner.py` | Rule-based request parsing (English and Arabic) and the budget planner. Every item comes from the dataset. |
| `data_loader.py` | Reads `trip_draft_dataset_excel_semicolon.csv` (200 items, 5 cities) and fixes its messy quoting. |
| `llm.py` | Model call to the Gemini API from our own backend. |

**The model writes the final reply text. The backend decides everything else:** the plan, the prices, the totals and the buttons.

Safeguards around the model:

- The greeting and the safety refusals are fixed texts and never go to the model.
- The model must keep the numbers from the backend and may not add any number that is not in the backend data.
- If the model fails, there is no key, or it breaks a rule, the rule-based reply is sent instead.
- Each reply has a `source` field: `model`, `rule_based_fallback` or `rule_based_planner_on_dataset`.
- `POST /model` is an extra endpoint that sends a free question to the model, with the unsafe and out-of-scope checks running first.

## Run (Windows PowerShell)

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/ for the chat page, or http://127.0.0.1:8000/docs for the API.

### Turn on the model (optional)

Without a key the chatbot works fully with rule-based replies. To let the model write the replies, create a key in [Google AI Studio](https://aistudio.google.com/apikey) and set it in the **same PowerShell window**, before starting the server:

```
$env:GEMINI_API_KEY="your-key"
uvicorn main:app --reload
```

The default model is `gemini-3.7-flash`. To use another one:

```
$env:GEMINI_MODEL="model-name"
```

Check http://127.0.0.1:8000/health: `llm_key_configured` should be `true`.

**Never commit an API key.** The key is only read from the environment variable and is not stored in any file.

## Tests

```
pytest -q tests
```

Runs 40 tests: dataset loading (200 rows), grounding (every plan item is a dataset id with its dataset price), accepted-only totals, and the 37 prompts of the test set (`tests/cases_weeks_6_7.py`). `tests/conftest.py` removes the API key while the tests run, because they check the fixed rule-based replies.

## Project layout

```
main.py
planner.py
data_loader.py
llm.py
requirements.txt
trip_draft_dataset_excel_semicolon.csv
README.md
static/
  index.html
tests/
  conftest.py
  cases_weeks_6_7.py
  test_weeks_6_7.py
```

## Notes

- All data is synthetic. Prices are fictional. The chatbot cannot book or pay for anything.
- The chatbot tells the user at the start that it is an AI assistant and not a person.
