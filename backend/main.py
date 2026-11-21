"""Trip Draft backend (Weeks 6-7). Grounded, rule-based planner + User Control and Agency layer.
Every plan item is a dataset id. Items start as 'proposed'; only a user action makes them 'accepted'.
State is a list of snapshots (event log); Undo/Redo move a pointer."""
import copy, os, re, uuid
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
import planner as P
import llm

app = FastAPI(title="Trip Draft backend - Weeks 6-7")
SESSIONS = {}
GREETING = ("Hi! I'm Trip Draft, an AI assistant (not a person). I plan budget trips inside Egypt from a small sample "
            "dataset, so prices are fictional estimates. I can't book or pay for anything. Nothing is added to your "
            "plan until you accept it, and you can undo any change. Tell me the city, number of days, budget in EGP "
            "and what you like, or tap a button.")
OUT_OF_SCOPE = ["flight", "book ", "essay", "homework", "visa", "weather", "bitcoin", "stock", "hotel in paris", "حجز", "طيران"]
UNSAFE = [
    (["fake id", "fake ticket", "forged", "counterfeit", "تذكرة مزورة", "تذكرة مزوّرة"],
     "I can't help with fake tickets. I can show you the entry prices in my sample data, including free attractions.", ["Free activities only", "Plan a trip"]),
    (["without paying", "avoid paying", "skip the fee", "sneak", "من غير دفع", "بدون دفع"],
     "I can't help with getting in without paying. I can show you free attractions from my sample data instead.", ["Free activities only", "Plan a trip"]),
    (["smuggle", "تهريب"],
     "I can't help with smuggling or carrying banned items. I only plan legal budget trips from my sample data.", ["Plan a trip", "How does this work?"]),
    (["bribe", "رشوة", "hide from police", "illegal"],
     "I can't help with anything illegal or with avoiding the authorities. I only plan legal budget trips from my sample data.", ["Plan a trip", "How does this work?"]),
]
CHIPS = ["Plan a trip", "See an example", "How does this work?"]

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    session_id: Optional[str] = None
    @field_validator("message")
    @classmethod
    def not_blank(cls, v):
        v = v.strip()
        if not v: raise ValueError("message must not be empty")
        return v

class ActionRequest(BaseModel):
    session_id: str
    action: str            # accept | accept_all | remove | swap_options | swap_apply | undo | redo | finalize | set_budget | set_days | apply_pending | keep_old
    item_id: Optional[int] = None
    new_item_id: Optional[int] = None
    value: Optional[int] = None

def new_session():
    sid = uuid.uuid4().hex[:8]
    SESSIONS[sid] = {"c": {"city": None, "days": None, "budget": None, "interests": []},
                     "log": [{"items": [], "label": "Draft", "rejected": []}], "ptr": 0, "pending": None}
    return sid, SESSIONS[sid]

def cur(s): return s["log"][s["ptr"]]
def push(s, state):
    s["log"] = s["log"][: s["ptr"] + 1] + [state]; s["ptr"] += 1

def view(s):
    st = cur(s); items = []
    for x in st["items"]:
        d = P.BY_ID[x["item_id"]]
        items.append({"item_id": d["id"], "day": x["day"], "role": x["role"], "name": d["name"], "area": d["area"],
                      "price_egp": d["price_egp"], "qty": x.get("qty", 1), "line_total": d["price_egp"] * x.get("qty", 1),
                      "status": x["status"], "source_tag": d["source_tag"], "last_verified": d["last_verified"],
                      "confidence": d["confidence"], "safety_notes": d["safety_notes"],
                      "why": "Matches: " + (", ".join(sorted(set(d["interests"]) & set(s["c"]["interests"])) or ["your budget"]))})
    all_total = P.total_of(st["items"]); b = s["c"]["budget"]
    acc = P.total_of([x for x in st["items"] if x["status"] == "accepted"])
    # total_egp / left_egp now count ONLY accepted items; proposed items are shown separately.
    return {"label": st["label"], "constraints": s["c"], "items": items, "total_egp": acc,
            "accepted_egp": acc, "proposed_egp": all_total - acc, "all_items_egp": all_total,
            "budget_egp": b, "left_egp": (b - acc) if b else None,
            "can_undo": s["ptr"] > 0, "can_redo": s["ptr"] < len(s["log"]) - 1,
            "note": "Prices are fictional estimates from the sample dataset. Verify before booking."}

def make_plan(s):
    st = cur(s)
    locked = [x for x in st["items"] if x["status"] == "accepted"]
    fresh = P.build_plan(s["c"], rejected=st["rejected"])
    ids = {x["item_id"] for x in locked}
    items = locked + [dict(x, status="proposed") for x in fresh if x["item_id"] not in ids]
    return items

def reply(s, sid, text, buttons=None, plan=True):
    return {"session_id": sid, "reply": text, "buttons": buttons or [], "plan": view(s) if plan else None,
            "source": "rule_based_planner_on_dataset"}

@app.get("/health")
def health():
    return {"status": "ok", "dataset_items": len(P.ITEMS), "llm_key_configured": bool(os.getenv("GEMINI_API_KEY"))}

FIXED_PREFIXES = ("Hi! I'm Trip Draft", "I can't help", "I can only help draft")  # greeting and safety refusals stay fixed
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def _nums(t):
    return {x.replace(",", "") for x in re.findall(r"\d[\d,]*", (t or "").translate(AR_DIGITS))}

def _facts(plan):
    if not plan: return None
    return (f"label {plan['label']}; budget {plan['budget_egp']} EGP; accepted {plan['accepted_egp']} EGP; "
            f"proposed {plan['proposed_egp']} EGP; left {plan['left_egp']} EGP; items {len(plan['items'])}")

def _with_model(resp, user_msg):
    """The model writes the final reply text. The backend still decides everything else (plan, prices, buttons).
    Safeguards: greeting and refusals stay fixed; the model must not add numbers that are not in the backend data;
    if the model fails or breaks a rule, the rule-based reply is used."""
    if not llm.enabled(): return resp
    base = resp.get("reply") or ""
    if base.startswith(FIXED_PREFIXES): return resp
    facts = _facts(resp.get("plan"))
    new = llm.rewrite(user_msg, base, resp.get("buttons") or [], facts)
    if not new or not _nums(new) <= (_nums(base) | _nums(facts)) or not _nums(base) <= _nums(new):
        return {**resp, "source": "rule_based_fallback"}
    return {**resp, "reply": new, "rule_reply": base, "source": "model"}

@app.post("/chat")
def chat(req: ChatRequest):
    return _with_model(_chat(req), req.message)

@app.post("/action")
def action_http(a: ActionRequest):
    return _with_model(action(a), None)

def _chat(req: ChatRequest):
    sid = req.session_id if req.session_id in SESSIONS else None
    if sid is None: sid, s = new_session()
    else: s = SESSIONS[sid]
    m = req.message.lower()
    if m in ("hi", "hello", "start", "مرحبا", "اهلا") or m.startswith(("hi ", "hello")) and len(m) < 12:
        return reply(s, sid, GREETING, CHIPS, plan=False)
    if m == "how does this work?":
        return reply(s, sid, "I build a draft from my sample dataset. Every item starts as Proposed. You can Accept, Remove, "
                     "Swap, Undo or Redo. Accepted items stay locked until you change them. The label above the plan says if it is a "
                     "Draft, a Proposed change, or a Confirmed plan.", CHIPS, plan=False)
    if m == "see an example":
        return reply(s, sid, "Example (sample data): '3 days in Alexandria, 1800 EGP, food and sea'. Type something like it, or tap Plan a trip.",
                     CHIPS, plan=False)
    if m == "plan a trip":
        return reply(s, sid, "Which city? Cairo, Alexandria, Luxor, Aswan or Dahab. You can also tell me days, budget in EGP and interests in one sentence.",
                     list(dict.fromkeys(P.CITIES.values())), plan=False)
    for keys, text, btns in UNSAFE:
        if any(k in m for k in keys):
            return reply(s, sid, text, btns, plan=False)
    if any(k in m for k in OUT_OF_SCOPE):
        return reply(s, sid, "I can only help draft budget trip plans from my sample data. I can't book or pay for anything or answer other topics. "
                     "Want to keep planning, or see what I can do?", ["Plan a trip", "How does this work?"], plan=False)
    cmds = {"undo": "undo", "undo my last change": "undo", "redo": "redo", "accept all": "accept_all", "finish": "finalize",
            "apply changes": "apply_pending", "keep old plan": "keep_old", "تراجع": "undo"}
    if m in cmds and cur(s)["items"] or m in ("undo", "تراجع") and s["ptr"] > 0:
        return action(ActionRequest(session_id=sid, action=cmds[m]))
    if m in cmds: return reply(s, sid, "There is no plan yet, so there is nothing to change. Tell me a city, days and budget to start.", CHIPS, plan=False)
    k0 = s["c"]; force = False
    if m in ("raise budget", "shorten trip", "keep my budget") and k0["city"] and k0["days"] and k0["budget"]:
        lo0 = P.min_cost(k0["city"], k0["days"])
        if m == "raise budget":
            return reply(s, sid, f"The cheapest {k0['days']}-day plan in {k0['city']} costs about {lo0} EGP. What total budget in EGP would you like? Type a number or tap one.",
                         [f"{x} EGP" for x in (lo0, lo0 + 100, lo0 + 300)], plan=False)
        if m == "shorten trip":
            ok = [d for d in range(k0["days"] - 1, 0, -1) if P.min_cost(k0["city"], d) <= k0["budget"]][:3]
            if not ok:
                return reply(s, sid, f"Even 1 day in {k0['city']} costs more than {k0['budget']} EGP in my data. Please raise the budget.", ["Raise budget"], plan=False)
            return reply(s, sid, f"With {k0['budget']} EGP I can fit up to {ok[0]} day{'s' if ok[0] > 1 else ''} in {k0['city']}. How many days would you like?",
                         [f"{d} day" + ("s" if d > 1 else "") for d in ok], plan=False)
        force = True  # keep my budget: build whatever fits
    c = P.parse_request(req.message)
    if cur(s)["items"] and not c["city"]:
        if c["budget"] and not c["days"]: return action(ActionRequest(session_id=sid, action="set_budget", value=c["budget"]))
        if c["days"] and not c["budget"]: return action(ActionRequest(session_id=sid, action="set_days", value=c["days"]))
    for k in ("city", "days", "budget"):
        if c[k] is not None: s["c"][k] = c[k]
    if c["interests"]: s["c"]["interests"] = c["interests"]
    k = s["c"]
    if not k["city"]:
        return reply(s, sid, "Which city do you mean? I have Cairo, Alexandria, Luxor, Aswan and Dahab.", list(dict.fromkeys(P.CITIES.values())), plan=False)
    if not k["days"]:
        return reply(s, sid, f"How many days in {k['city']}? (1 to 7)", ["2 days", "3 days", "5 days"], plan=False)
    if not 1 <= k["days"] <= 7:
        k["days"] = None
        return reply(s, sid, "I can plan between 1 and 7 days. How many days would you like?", ["2 days", "3 days", "5 days"], plan=False)
    if not k["budget"]:
        return reply(s, sid, "What is your total budget in EGP for the whole trip?", ["1500", "3000", "4000"], plan=False)
    lo = P.min_cost(k["city"], k["days"])
    if k["budget"] < lo and not force:
        return reply(s, sid, f"The cheapest plan I can build in {k['city']} for {k['days']} days costs about {lo} EGP (stay plus two meals a day). "
                     "Nothing was changed. You can raise the budget, shorten the trip, or keep your budget and I will show what fits.",
                     ["Raise budget", "Shorten trip", "Keep my budget"], plan=False)
    items = make_plan(s)
    if not items:
        return reply(s, sid, "Nothing in my sample data fits that budget. Please raise the budget or shorten the trip.", ["Raise budget", "Shorten trip"], plan=False)
    push(s, {"items": [dict(x, status=x.get("status", "proposed")) for x in items], "label": "Draft", "rejected": cur(s)["rejected"]})
    n = len(items)
    thin = " Note: I have fewer items for Aswan, so the plan may be lighter." if k["city"] == "Aswan" else ""
    return reply(s, sid, f"Here is what I understood: {k['city']}, {k['days']} days, {k['budget']} EGP, interests: {', '.join(k['interests']) or 'none given'}. "
                 f"I drafted {n} items. They are Proposed, not accepted. Accept, Remove or Swap each one.{thin}",
                 ["Accept all", "Undo", "Finish"])

def action(a: ActionRequest):
    s = SESSIONS.get(a.session_id)
    if not s: raise HTTPException(404, "Session not found. Start a new chat.")
    st = cur(s); act = a.action
    def fail(msg): return reply(s, a.session_id, msg + " Your plan is unchanged.", ["Undo", "Finish"])
    if act in ("accept", "remove", "swap_options", "swap_apply"):
        x = next((i for i in st["items"] if i["item_id"] == a.item_id), None)
        if not x: return fail("I could not find that item.")
    if act == "accept":
        ns = copy.deepcopy(st); [i.update(status="accepted") for i in ns["items"] if i["item_id"] == a.item_id]
        push(s, ns); return reply(s, a.session_id, f"Accepted: {P.BY_ID[a.item_id]['name']}. It is locked until you change it.", ["Undo"])
    if act == "accept_all":
        ns = copy.deepcopy(st); [i.update(status="accepted") for i in ns["items"]]
        push(s, ns); return reply(s, a.session_id, "All items accepted. You can still Undo.", ["Undo", "Finish"])
    if act == "remove":
        ns = copy.deepcopy(st); ns["items"] = [i for i in ns["items"] if i["item_id"] != a.item_id]; ns["rejected"].append(a.item_id)
        push(s, ns); return reply(s, a.session_id, f"Removed: {P.BY_ID[a.item_id]['name']}. I will not suggest it again in this session. Undo is available.", ["Undo"])
    if act == "swap_options":
        alts = P.alternatives(a.item_id, exclude=[i["item_id"] for i in st["items"]] + st["rejected"])
        s["pending"] = {"type": "swap", "old": a.item_id}
        return {**reply(s, a.session_id, "Choose one of these options from the dataset, or keep your current item.", ["Keep current item"]),
                "alternatives": [{"item_id": i["id"], "name": i["name"], "price_egp": i["price_egp"], "source_tag": i["source_tag"],
                                  "last_verified": i["last_verified"], "price_change_egp": i["price_egp"] - P.BY_ID[a.item_id]["price_egp"]} for i in alts]}
    if act == "swap_apply":
        if a.new_item_id not in P.BY_ID or P.BY_ID[a.new_item_id]["city"] != s["c"]["city"]:
            return fail("That option is not in my dataset for this city, so I did not use it.")
        ns = copy.deepcopy(st)
        for i in ns["items"]:
            if i["item_id"] == a.item_id: i.update(item_id=a.new_item_id, status="proposed")
        ns["label"] = "Draft"; push(s, ns)
        return reply(s, a.session_id, f"Swapped to: {P.BY_ID[a.new_item_id]['name']}. It is Proposed. Undo is available.", ["Undo"])
    if act in ("undo", "redo"):
        if act == "undo" and s["ptr"] > 0: s["ptr"] -= 1
        elif act == "redo" and s["ptr"] < len(s["log"]) - 1: s["ptr"] += 1
        else: return fail(f"There is nothing to {act}.")
        return reply(s, a.session_id, f"Done: {act}. The plan is back to an earlier saved state.", ["Undo", "Redo"])
    if act in ("set_budget", "set_days"):
        new = copy.deepcopy(s["c"]); new["budget" if act == "set_budget" else "days"] = a.value
        if not a.value or a.value <= 0 or (act == "set_days" and a.value > 7): return fail("That value is not valid.")
        old_items = st["items"]; keep = [x for x in old_items if x["status"] == "accepted"]
        saved, s["c"] = s["c"], new
        fresh = P.build_plan(new, rejected=st["rejected"])
        s["c"] = saved
        ids = {x["item_id"] for x in keep}
        proposal = keep + [dict(x, status="proposed") for x in fresh if x["item_id"] not in ids]
        s["pending"] = {"type": "constraint", "c": new, "items": proposal}
        before, after = P.total_of(old_items), P.total_of(proposal)
        removed = [P.BY_ID[x["item_id"]]["name"] for x in old_items if x["item_id"] not in {y["item_id"] for y in proposal}]
        added = [P.BY_ID[x["item_id"]]["name"] for x in proposal if x["item_id"] not in {y["item_id"] for y in old_items}]
        return {**reply(s, a.session_id, f"Preview (Proposed change): total {before} to {after} EGP. {len(removed)} items would be removed and {len(added)} added. "
                        "Accepted items are kept. Nothing changes until you press Apply changes.", ["Apply changes", "Keep old plan"]),
                "preview": {"before_total": before, "after_total": after, "removed": removed, "added": added}}
    if act == "apply_pending" and s["pending"] and s["pending"]["type"] == "constraint":
        p = s["pending"]; s["c"] = p["c"]; push(s, {"items": p["items"], "label": "Draft", "rejected": st["rejected"]}); s["pending"] = None
        return reply(s, a.session_id, "Changes applied. You can Undo.", ["Undo"])
    if act == "keep_old":
        s["pending"] = None; return reply(s, a.session_id, "Kept your previous plan. Nothing changed.", ["Undo"])
    if act == "finalize":
        pend = [i for i in st["items"] if i["status"] != "accepted"]
        ns = copy.deepcopy(st); ns["label"] = "Confirmed plan"; push(s, ns)
        return reply(s, a.session_id, f"Confirmed plan. {len(st['items']) - len(pend)} accepted, {len(pend)} still proposed. Total of accepted items: {P.total_of([i for i in st['items'] if i['status'] == 'accepted'])} EGP. "
                     "Prices are fictional estimates: verify before booking.", ["Undo", "Start new trip"])
    return fail("I do not support that action yet.")

class ModelRequest(BaseModel):
    message: str = Field(..., max_length=500)
    @field_validator("message")
    @classmethod
    def not_blank(cls, v):
        v = v.strip()
        if not v: raise ValueError("message must not be empty")
        return v

MODEL_FALLBACK = ("I could not get an answer from the AI model right now. I can still plan trips from my sample data. "
                  "Tell me a city, number of days and budget in EGP, or tap a button.")

@app.post("/model")
def model_reply(req: ModelRequest):
    """Model call from our own backend. Safeguards run first; the model is only called for safe, on-topic messages.
    If there is no key or the call fails, the rule-based fallback message is returned instead."""
    m = req.message.lower()
    for keys, text, btns in UNSAFE:
        if any(k in m for k in keys):
            return {"reply": text, "buttons": btns, "source": "safeguard_refusal"}
    if any(k in m for k in OUT_OF_SCOPE):
        return {"reply": "I can only help draft budget trip plans from my sample data. I can't book or pay for anything or answer other topics. "
                         "Want to keep planning, or see what I can do?", "buttons": ["Plan a trip", "How does this work?"], "source": "safeguard_out_of_scope"}
    text = llm.ask(req.message)
    if text is None:
        return {"reply": MODEL_FALLBACK, "buttons": CHIPS, "source": "fallback_no_model"}
    return {"reply": text + " (AI-written. Prices are fictional estimates.)", "buttons": CHIPS, "source": "model"}

@app.get("/")
def home(): return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))
