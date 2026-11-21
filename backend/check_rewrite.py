import llm, main
from main import ChatRequest
msg = "3 days in Alexandria 1800 EGP food and sea"
resp = main._chat(ChatRequest(message=msg))
base = resp["reply"]; facts = main._facts(resp["plan"])
new = llm.rewrite(msg, base, resp["buttons"], facts)
print("MODEL REPLY:", new)
print("base nums:", sorted(main._nums(base)))
print("facts nums:", sorted(main._nums(facts)))
if new:
    print("model nums:", sorted(main._nums(new)))
    print("missing from model:", sorted(main._nums(base) - main._nums(new)))
    print("extra in model:", sorted(main._nums(new) - (main._nums(base) | main._nums(facts))))