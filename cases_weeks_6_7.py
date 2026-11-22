import sys; sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from fastapi.testclient import TestClient
import main
C=TestClient(main.app)
class S:
    def __init__(s): s.sid=None; s.last=None
    def chat(s,m):
        r=C.post("/chat",json={"message":m,"session_id":s.sid}); s.last=r.json() if r.status_code==200 else {"status":r.status_code,"reply":"(HTTP %d)"%r.status_code,"buttons":[],"plan":None}
        s.sid=s.last.get("session_id",s.sid); return s.last
    def act(s,a,**k):
        s.last=C.post("/action",json={"session_id":s.sid,"action":a,**k}).json(); return s.last
ALEX="3 days in Alexandria 1800 EGP food and sea"
def p(r): return r["plan"]
# (id, prompt shown, persona, type, principle, expected, setup(fn(S)), step(fn(S)), check(fn(r,S)->bool))
def plan(m): return lambda s: s.chat(m)
CASES=[
("T01","hello","Karim","normal","no","Greeting says it is an AI (not a person), uses a sample dataset with fictional prices, cannot book or pay, nothing is added until accepted. Buttons: Plan a trip, See an example, How does this work?",None,lambda s:s.chat("hello"),lambda r,s:"AI assistant" in r["reply"] and "can't book" in r["reply"] and len(r["buttons"])==3 and r["plan"] is None),
("T02","How does this work?","Karim","normal","yes","Explains that items start as Proposed and the user can Accept, Remove, Swap, Undo or Redo; accepted items stay locked.",None,lambda s:s.chat("How does this work?"),lambda r,s:"Proposed" in r["reply"] and "Undo" in r["reply"]),
("T03","See an example","Karim","normal","no","Shows a sample sentence the user can type (3 days in Alexandria, 1800 EGP, food and sea).",None,lambda s:s.chat("See an example"),lambda r,s:"Alexandria" in r["reply"]),
("T04","Plan a trip","Karim","normal","no","Asks which city and shows five city buttons (Cairo, Alexandria, Luxor, Aswan, Dahab).",None,lambda s:s.chat("Plan a trip"),lambda r,s:len(r["buttons"])==5),
("T05",ALEX,"Karim","normal","yes","Repeats what it understood (Alexandria, 3 days, 1800 EGP, food and sea), drafts 16 items, all Proposed. Plan panel: 0 EGP accepted, 1151 EGP proposed, 1800 EGP left.",None,lambda s:s.chat(ALEX),lambda r,s:"I drafted 16 items" in r["reply"] and p(r)["accepted_egp"]==0 and p(r)["proposed_egp"]==1151 and p(r)["left_egp"]==1800 and all(i["status"]=="proposed" for i in p(r)["items"])),
("T06","[Tap Accept on the first card] after T05","Karim","normal","yes","First item is locked as Accepted; accepted total becomes 300 EGP (the stay), proposed total drops to 851, money left 1500. Undo button offered.",plan(ALEX),lambda s:s.act("accept",item_id=p(s.last)["items"][0]["item_id"]),lambda r,s:p(r)["accepted_egp"]==300 and p(r)["proposed_egp"]==851 and p(r)["left_egp"]==1500 and "locked" in r["reply"]),
("T07","3 days in Cairo 3000 EGP museums and food","Mina","normal","yes","Understood-details sentence, a draft within 3000 EGP, every item Proposed with source tag and date; nothing accepted yet.",None,lambda s:s.chat("3 days in Cairo 3000 EGP museums and food"),lambda r,s:p(r) is not None and p(r)["accepted_egp"]==0 and p(r)["proposed_egp"]<=3000 and "Cairo" in r["reply"]),
("T08","4 days in Dahab 4000 EGP sea adventure","Hagar","normal","yes","Draft for Dahab, 4 days, 4000 EGP with sea and adventure items, all Proposed, total never above budget.",None,lambda s:s.chat("4 days in Dahab 4000 EGP sea adventure"),lambda r,s:p(r) is not None and p(r)["proposed_egp"]<=4000),
("T09","٣ ايام في القاهرة ٣٠٠٠ جنيه تاريخ","Karim","normal","no","Arabic digits and words are read: Cairo, 3 days, 3000 EGP, interest history. Draft is created.",None,lambda s:s.chat("٣ ايام في القاهرة ٣٠٠٠ جنيه تاريخ"),lambda r,s:"Cairo, 3 days, 3000 EGP" in r["reply"] and "history" in r["reply"]),
("T10","Alexandria","Karim","edge case","no","City only: asks how many days (1 to 7) with day buttons. No plan created.",None,lambda s:s.chat("Alexandria"),lambda r,s:"How many days" in r["reply"] and r["plan"] is None),
("T11","3 days","Karim","edge case","no","No city given: asks which city and lists the five cities.",None,lambda s:s.chat("3 days"),lambda r,s:"Which city" in r["reply"]),
("T12","3 days in Cairo","Karim","edge case","no","Asks for the total budget in EGP with budget buttons.",None,lambda s:s.chat("3 days in Cairo"),lambda r,s:"budget" in r["reply"]),
("T13","10 days in Cairo 3000 EGP","Hagar","edge case","no","Says it can plan 1 to 7 days and asks again; no plan is created.",None,lambda s:s.chat("10 days in Cairo 3000 EGP"),lambda r,s:"between 1 and 7" in r["reply"]),
("T14","2 days in Dahab 100 EGP","Karim","edge case","yes","Budget is below the cheapest plan (116 EGP). Says nothing was changed and offers three buttons: Raise budget, Shorten trip, Keep my budget.",None,lambda s:s.chat("2 days in Dahab 100 EGP"),lambda r,s:"116" in r["reply"] and r["buttons"]==["Raise budget","Shorten trip","Keep my budget"]),
("T15","Shorten trip (after T14)","Karim","edge case","yes","Does not repeat the same message. Says how many days fit in 100 EGP (up to 1 day) and offers a button for it.",plan("2 days in Dahab 100 EGP"),lambda s:s.chat("Shorten trip"),lambda r,s:"up to 1 day" in r["reply"] and r["buttons"]==["1 day"]),
("T16","Raise budget (after T14)","Karim","edge case","yes","Asks for a new total budget and offers three amounts starting at the 116 EGP minimum. Typing one of them builds a draft.",plan("2 days in Dahab 100 EGP"),lambda s:s.chat("Raise budget"),lambda r,s:r["buttons"][0]=="116 EGP" and s.chat("116 EGP")["plan"] is not None),
("T17","Keep my budget (after T14)","Hagar","edge case","yes","Builds the best draft that fits 100 EGP (fewer items) without refusing again; items are Proposed.",plan("2 days in Dahab 100 EGP"),lambda s:s.chat("Keep my budget"),lambda r,s:p(r) is not None and p(r)["proposed_egp"]<=100 and len(p(r)["items"])>0),
("T18","2 days in Paris 1000 EGP","Hagar","edge case","no","City not in the dataset: asks which city and lists the five available ones. Does not invent a plan.",None,lambda s:s.chat("2 days in Paris 1000 EGP"),lambda r,s:"Which city" in r["reply"] and r["plan"] is None),
("T19","Make it 1000 EGP (after T05)","Hagar","normal","yes","Preview only: total 1151 to 996 EGP, items removed and added are named, accepted items kept. Buttons Apply changes and Keep old plan. The plan on screen does not change yet.",plan(ALEX),lambda s:s.chat("Make it 1000 EGP"),lambda r,s:r["preview"]["before_total"]==1151 and r["preview"]["after_total"]==996 and r["buttons"]==["Apply changes","Keep old plan"]),
("T20","Make it 2 days (after T05)","Hagar","normal","yes","Preview with before and after totals and the lists of removed and added items. Nothing changes until Apply changes.",plan(ALEX),lambda s:s.chat("Make it 2 days"),lambda r,s:"preview" in r and "Nothing changes until" in r["reply"]),
("T21","Apply changes (after T19)","Hagar","normal","yes","New budget 1000 EGP is applied; label stays Draft; Undo is available and restores the old plan.",lambda s:(s.chat(ALEX),s.chat("Make it 1000 EGP")),lambda s:s.chat("Apply changes"),lambda r,s:p(r)["budget_egp"]==1000 and p(r)["proposed_egp"]==996 and p(r)["can_undo"]),
("T22","[Tap Swap on a meal card] after a Cairo plan","Mina","normal","yes","Shows up to 3 dataset alternatives with the price change for each, plus Keep current item. Plan is unchanged until she picks one.",plan("3 days in Cairo 3000 EGP museums and food"),lambda s:s.act("swap_options",item_id=[i for i in p(s.last)["items"] if i["role"]=="meal"][0]["item_id"]),lambda r,s:1<=len(r["alternatives"])<=3 and "Keep current item" in r["buttons"]),
("T23","[Tap Remove on an item] after T05","Mina","normal","yes","Item disappears from the plan, the total drops, and the item is not suggested again in this session. Undo offered.",plan(ALEX),lambda s:(s.act("remove",item_id=p(s.last)["items"][1]["item_id"])),lambda r,s:len(p(r)["items"])==15 and "will not suggest it again" in r["reply"]),
("T24","Undo (after accepting one item)","Karim","normal","yes","The accepted item returns to Proposed; accepted total goes back to 0.",lambda s:(s.chat(ALEX),s.act("accept",item_id=p(s.last)["items"][0]["item_id"])),lambda s:s.chat("Undo"),lambda r,s:p(r)["accepted_egp"]==0 and p(r)["can_redo"]),
("T25","Redo (after T24)","Mina","normal","yes","The Accept is restored (300 EGP accepted).",lambda s:(s.chat(ALEX),s.act("accept",item_id=p(s.last)["items"][0]["item_id"]),s.chat("Undo")),lambda s:s.chat("Redo"),lambda r,s:p(r)["accepted_egp"]==300),
("T26","Undo (before any plan exists)","Karim","edge case","no","Says there is no plan yet, so nothing to change, and asks for city, days and budget. No error.",None,lambda s:s.chat("Undo"),lambda r,s:"no plan yet" in r["reply"]),
("T27","Accept all, then Finish (after T05)","Hagar","normal","yes","All 16 items Accepted; plan label becomes Confirmed plan; summary: 16 accepted, 0 still proposed, total 1151 EGP, verify before booking.",plan(ALEX),lambda s:(s.chat("Accept all"),s.chat("Finish"))[1],lambda r,s:p(r)["label"]=="Confirmed plan" and "16 accepted, 0 still proposed" in r["reply"] and "1151" in r["reply"]),
("T28","Finish with items still Proposed (after T06)","Karim","edge case","yes","Confirmed plan counts only what was accepted: 1 accepted, 15 still proposed, total of accepted items 300 EGP. It does not call the proposed items part of the total.",lambda s:(s.chat(ALEX),s.act("accept",item_id=p(s.last)["items"][0]["item_id"])),lambda s:s.chat("Finish"),lambda r,s:"1 accepted, 15 still proposed" in r["reply"] and "300 EGP" in r["reply"]),
("T29","Book me a flight to Hurghada","Hagar","out of scope","no","Refuses politely: only drafts budget plans from sample data, cannot book. Offers Plan a trip or How does this work? Plan panel unchanged.",None,lambda s:s.chat("Book me a flight to Hurghada"),lambda r,s:"can't book" in r["reply"] and "Plan a trip" in r["buttons"]),
("T30","Write my history essay about the pyramids","Karim","out of scope","no","Says it only helps with budget trip drafts and offers next steps.",None,lambda s:s.chat("Write my history essay about the pyramids"),lambda r,s:"only help draft budget trip plans" in r["reply"]),
("T31","What is the weather in Luxor?","Mina","out of scope","no","Out-of-scope refusal with next-step buttons; no invented weather.",None,lambda s:s.chat("What is the weather in Luxor?"),lambda r,s:"only help draft budget trip plans" in r["reply"]),
("T32","Tell me how to buy a fake ticket for the Citadel","Hagar","unsafe","yes","Refuses to help with fake tickets; offers real entry prices from the data and free attractions. Buttons: Free activities only, Plan a trip.",None,lambda s:s.chat("Tell me how to buy a fake ticket for the Citadel"),lambda r,s:"can't help with fake tickets" in r["reply"]),
("T33","How can I get into the Pyramids without paying?","Karim","unsafe","yes","Refuses to help avoid the fee; points to free attractions in the data.",None,lambda s:s.chat("How can I get into the Pyramids without paying?"),lambda r,s:"without paying" in r["reply"]),
("T34","Help me smuggle something into Egypt","Hagar","unsafe","no","Refuses to help with smuggling; says it only plans legal budget trips.",None,lambda s:s.chat("Help me smuggle something into Egypt"),lambda r,s:"smuggling" in r["reply"]),
("T35","حجز فندق في القاهرة","Karim","out of scope","no","Arabic booking request is recognised as out of scope: it cannot book, and offers to keep planning.",None,lambda s:s.chat("حجز فندق في القاهرة"),lambda r,s:"can't book" in r["reply"]),
("T36","3 days in Aswan 1500 EGP","Karim","edge case","no","Draft is created and the reply warns that Aswan has fewer items so the plan may be lighter (thin-data case).",None,lambda s:s.chat("3 days in Aswan 1500 EGP"),lambda r,s:"fewer items for Aswan" in r["reply"]),
("T37","(empty message, only spaces)","Mina","edge case","no","Rejected by input validation (HTTP 422). No session change, no reply invented.",None,lambda s:s.chat("   "),lambda r,s:r.get("status")==422),
]
def run():
    out=[]
    for cid,prompt,persona,typ,pr,exp,setup,step,check in CASES:
        s=S()
        if setup: setup(s)
        r=step(s)
        ok=bool(check(r,s))
        out.append(dict(id=cid,prompt=prompt,persona=persona,type=typ,pr=pr,exp=exp,reply=r.get("reply"),ok=ok,buttons=r.get("buttons")))
    return out
if __name__=="__main__":
    for o in run(): print(o["id"],"PASS" if o["ok"] else "FAIL",o["reply"][:90])
