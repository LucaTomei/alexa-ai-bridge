#!/usr/bin/env python3
"""Consistency checks run by CI (no network, no secrets):

- every relative link in the Markdown files points to an existing file;
- the interaction model is valid and every custom intent it declares is handled by src/app.py;
- every environment variable read by src/ is in .env.example and in the configuration reference (docs/setup.md).
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
errors = []

# ---- Markdown links
for md in ROOT.rglob("*.md"):
    if any(p.startswith(".") for p in md.relative_to(ROOT).parts):
        continue
    text = re.sub(r"```.*?```", "", md.read_text(encoding="utf-8"), flags=re.S)
    for target in re.findall(r"\]\(([^)\s]+)\)", text) + re.findall(r'(?:src|href)="([^"]+)"', text):
        if re.match(r"^(https?:|mailto:|#)", target):
            continue
        path = target.split("#")[0]
        if path and not (md.parent / path).exists():
            errors.append("%s: broken link %s" % (md.relative_to(ROOT), target))

# ---- Alexa interaction model
app = (ROOT / "src" / "app.py").read_text(encoding="utf-8")
for model in (ROOT / "skill").glob("interaction-model.*.json"):
    try:
        lm = json.loads(model.read_text(encoding="utf-8"))["interactionModel"]["languageModel"]
    except (ValueError, KeyError) as e:
        errors.append("%s: invalid (%s)" % (model.name, e))
        continue
    names = [i["name"] for i in lm["intents"]]
    for required in ("AskIntent", "AttesaIntent", "FraseBreveIntent", "AMAZON.YesIntent", "AMAZON.NoIntent",
                     "AMAZON.StopIntent", "AMAZON.HelpIntent", "AMAZON.FallbackIntent"):
        if required not in names:
            errors.append("%s: missing intent %s" % (model.name, required))
    for name in names:
        if not name.startswith("AMAZON.") and '"%s"' % name not in app:
            errors.append("%s: intent %s is not handled in src/app.py" % (model.name, name))
    samples = [s.lower() for i in lm["intents"] for s in i.get("samples", [])]
    dups = sorted({s for s in samples if samples.count(s) > 1})
    if dups:
        errors.append("%s: duplicate samples %s" % (model.name, dups))
    per_intent = {i["name"]: {x.lower() for x in i.get("samples", [])} for i in lm["intents"]}
    brevi = {v["name"]["value"].lower() for t in lm.get("types", []) for v in t["values"]}
    for nome in ("AttesaIntent", "AMAZON.StopIntent"):
        if per_intent.get(nome, set()) & brevi:
            errors.append("%s: %s and FRASE_BREVE share %s" % (model.name, nome, sorted(per_intent[nome] & brevi)))
    if not re.fullmatch(r"[a-zà-ù ]+", lm["invocationName"]):
        errors.append("%s: invocation name must be lowercase words" % model.name)

# ---- environment variables
used = set()
for py in (ROOT / "src").glob("*.py"):
    used |= set(re.findall(r'os\.environ(?:\.get)?[\[(]"([A-Z0-9_]+)"', py.read_text(encoding="utf-8")))
used |= set(re.findall(r'"(LLM_BASE_URL|LLM_MODEL)"', (ROOT / "src" / "llm.py").read_text(encoding="utf-8")))
example = (ROOT / ".env.example").read_text(encoding="utf-8")
reference = (ROOT / "docs" / "setup.md").read_text(encoding="utf-8")
ALIASES = {"LLM_FORMAT"}               # old name of LLM_API, still accepted but no longer documented
INTERNE = {"APP_VERSION", "DATA_DIR"}  # set by the Docker image (Dockerfile), not by the user
for var in sorted(used - ALIASES - INTERNE):
    if not re.search(r"^#?\s*%s=" % var, example, re.M):
        errors.append(".env.example: %s is not listed" % var)
    if "`%s`" % var not in reference:
        errors.append("docs/setup.md: %s is not in the configuration reference" % var)

for e in errors:
    print("ERROR", e)
print("%d problem(s)" % len(errors) if errors else "repository checks: OK")
sys.exit(1 if errors else 0)
