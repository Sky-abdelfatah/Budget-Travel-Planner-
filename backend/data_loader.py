"""Loads the team's semicolon CSV (Excel export with messy quoting) into clean dicts."""
import csv, io, os
FIELDS = ["id","city","area","category","name","price_egp","price_range","interests",
          "diet_tags","open_days","duration_min","safety_notes","confidence",
          "source_tag","last_verified","is_fictional"]

def load_items(path=None):
    path = path or os.path.join(os.path.dirname(__file__), "trip_draft_dataset_excel_semicolon.csv")
    text = open(path, encoding="utf-8-sig").read()
    items = []
    for line in text.splitlines()[1:]:
        line = line.strip().rstrip(",")
        if not line:
            continue
        if line.startswith('"'):
            line = line[1:].replace('", checked by a second member', ' - checked by a second member')
            if line.endswith('"'):
                line = line[:-1]
            line = line.replace('""', '"')
        row = next(csv.reader(io.StringIO(line), delimiter=";"))
        if len(row) != 16:
            continue  # skipped rows are reported by tests
        d = dict(zip(FIELDS, row))
        d["id"] = int(d["id"]); d["price_egp"] = int(d["price_egp"])
        d["interests"] = [x for x in d["interests"].split(";") if x]
        items.append(d)
    return items
