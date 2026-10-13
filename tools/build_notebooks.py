"""Build the session notebooks from Daniel Diaz's CLARIPHY notebooks.

    python3 tools/build_notebooks.py

Sources: upstream/*.ipynb, copied unchanged from github.com/nrp-nautilus/nrp-training, branch
materials/clariphy @ c63cb76 (21 Sep 2026). Every lifted cell keeps Daniel's text; the edits below are
the whole diff (model choice, cross-links, renumbering, fixes) plus a few new cells, marked "# NEW" here
(the notebooks themselves carry no NEW markers). Rerun after refreshing upstream/ to pick up his changes.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UP = "https://github.com/nrp-nautilus/nrp-training/tree/materials/clariphy"
SITE = "https://training.nrp-nautilus.io/clariphy/"
MODEL, ALT = "deepseek-v4-flash", "glm-5"
# opencode 2 (the workshop Binder's) runs a background service that keeps the settings and key it started with:
# a fixed key or a new opencode.json is ignored until it stops. No version test: on 13 Oct `opencode service stop`
# exited 0 on 2.0.26 (stopping a running service, or none) and 1 on 1.19.0 (usage only, no TUI started).
SERVICE_STOP = '''
# opencode 2 keeps a background service that remembers old settings and keys: stop it, so the next
# `opencode` start reads this file and your current key (opencode 1.x has no such service: nothing happens)
if opencode service stop > /dev/null 2>&1; then
    echo "opencode: background service stopped (the next start reads these settings)"
fi'''


def load(name):
    return json.load(open(ROOT / "upstream" / f"{name}.ipynb"))


def src(cell):
    return "".join(cell["source"])


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}


def edit(cell, *pairs):
    """Copy a cell with exact replacements (every occurrence); each `old` must occur."""
    c = copy.deepcopy(cell)
    s = src(c)
    for old, new in pairs:
        assert old in s, f"not found: {old[:70]!r}"
        s = s.replace(old, new)
    c["source"] = s.splitlines(keepends=True)
    if c["cell_type"] == "code":
        c["outputs"], c["execution_count"] = [], None
    return c


def keep(cell):
    return edit(cell)


# Students get their key from the organisers' NRP training link (it also adds them to the workshop namespace),
# not from nrp.ai/llmtoken: applied to every cell of every notebook; each pair must be used at least once.
KEY_TEXT = [
    ("# Paste your personal token from https://nrp.ai/llmtoken between the quotes.",
     "# Paste your LLM API key (shown when you opened the training link) between the quotes."),
    ("your own token from [nrp.ai/llmtoken](https://nrp.ai/llmtoken)", "your own key from the training-link page"),
    ("([Lesson 1](https://training.nrp-nautilus.io/clariphy/1_intro.html#step-1-nrp-account))",
     "(opening the training link adds you to it)"),
    ("[Lesson 1](https://training.nrp-nautilus.io/clariphy/1_intro.html#step-2-get-an-api-token)",
     "[the training link](../README.md#before-you-start)"),
    ("your personal token from [https://nrp.ai/llmtoken](https://nrp.ai/llmtoken)", "your LLM API key from the training link"),
    ("personal token", "LLM API key"),
]
KEY_USED = set()


def key_text(cell):
    s = src(cell)
    for i, (old, new) in enumerate(KEY_TEXT):
        if old in s:
            s = s.replace(old, new)
            KEY_USED.add(i)
    cell["source"] = s.splitlines(keepends=True)


def save(name, cells, kernel):
    for cell in cells:
        key_text(cell)
    for i, cell in enumerate(cells):
        cell["id"] = f"{name[:1]}-{i:02d}"
    nb = {"cells": cells, "nbformat": 4, "nbformat_minor": 5, "metadata": {"kernelspec": kernel}}
    (ROOT / "notebooks" / f"{name}.ipynb").write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    print("wrote notebooks/%s.ipynb (%d cells)" % (name, len(cells)))


PY = {"display_name": "Python 3", "language": "python", "name": "python3"}
BASH = {"display_name": "Bash", "language": "bash", "name": "bash"}
LESSON1 = (f"(1_intro.html", f"({SITE}1_intro.html")


def credit(lesson, page):
    return (f"*Adapted from Daniel Diaz's CLARIPHY lesson [{lesson}]({SITE}{page}) "
            f"([nrp-nautilus/nrp-training]({UP})).*")


# ----------------------------------------------------------------------------------------------- notebook 1
c = load("2_chat")["cells"]
PIP = "%pip install -q openai   # the Binder image lacks it; ignore any note about restarting the kernel"
nb1 = [
    md(f"""
# 1 · Talking to a model on NRP

{credit("Chat with LLMs on NRP", "2_chat.html")}

This notebook calls NRP's managed LLMs from Python, through the OpenAI-compatible endpoint at
`https://ellm.nrp-nautilus.io/v1`. The models run on NRP's shared inference cluster, so no GPU is
needed here. We use the two models of the hackathon, **`{MODEL}`** and **`{ALT}`**.

**Run cells with Shift+Enter, top to bottom.**

| Step | Topic |
|---|---|
| 1 | Setup check |
| 2 | Basic chat & the `chat()` helper |
| 3 | What the model actually receives |
| 4 | System prompts |
| 5 | Multi-turn chat |
"""),  # NEW title (Daniel's covered sections 5-7 too: embeddings, images, RAG)
    edit(c[1], ("[Lesson 1](1_intro.html#1-managed-llm-service)", f"[Lesson 1]({SITE}1_intro.html#1-managed-llm-service)"),
         ("This notebook defaults to `gemma-small` and `minimax-m2`, both good general-purpose choices.",
          f"This notebook uses `{MODEL}` and `{ALT}`, the models of the hackathon; any other row works the same way.")),
    edit(c[2], ("Verify your token", "Verify your key")),
    code(PIP),  # NEW
    md("""
Run the cell below and paste your **LLM API key** (from the training link) into the box that appears, then press
Enter. The key is saved to a private file, `~/.nrp-llm-token`, readable only by you;
notebooks 2 and 3 and opencode read it from there, so you paste it **once per session** and it never sits in a
notebook. A Binder restart wipes the file: just run this cell again.
"""),  # NEW
    code('''
import os, getpass
from pathlib import Path

KEY_FILE = Path.home() / ".nrp-llm-token"          # private: readable only by you
while not KEY_FILE.exists() or len(KEY_FILE.read_text().strip()) < 10:   # missing, or nothing pasted
    key = getpass.getpass("Paste your NRP LLM API key, then press Enter: ").strip()
    if len(key) < 10:
        print("That does not look like a key — paste it again.")
        continue
    KEY_FILE.write_text(key)
    KEY_FILE.chmod(0o600)
    print("Saved to", KEY_FILE)

# Set both explicitly, replacing anything already in the environment.
os.environ["OPENAI_API_KEY"] = KEY_FILE.read_text().strip()
os.environ["OPENAI_API_BASE"] = "https://ellm.nrp-nautilus.io/v1"
print("Key loaded from", KEY_FILE)
'''),  # NEW
    edit(c[5], ("without a valid token", "without a valid key")),
    # The models live in MODEL and ALT from here on, so one model down does not break the notebook: the setup
    # check switches both to the one that answered. The key is no longer printed, not even its first characters
    # (notebooks are copied, outputs included, to the world-readable /data at the end of the session).
    edit(c[6], ('print("OPENAI_API_KEY  =", key[:8] + "..." if key else "NOT SET")',
                'print("OPENAI_API_KEY  =", f"set ({len(key)} characters)" if key else "NOT SET")\n'
                'assert key, "No key loaded: run the key cell above first (it re-reads ~/.nrp-llm-token)."'),
         ("# Listing models doesn't check your token, so send one tiny request per model we use.\nprint()\n"
          'for model in ["gemma-small", "minimax-m2", "gpt-oss", "qwen3-embedding"]:',
          "# Listing models doesn't check your key, so send one tiny request per model we use.\n"
          f'MODEL, ALT = "{MODEL}", "{ALT}"     # the two models this notebook uses\n'
          "working = []\nprint()\nfor model in [MODEL, ALT]:"),
         ('        if model == "qwen3-embedding":\n            client.embeddings.create(model=model, input=["hi"])\n        else:\n            client.chat.completions.create(\n                model=model, max_tokens=1, messages=[{"role": "user", "content": "hi"}])\n        print(f"  ✅ {model}")',
          '        client.chat.completions.create(\n            model=model, max_tokens=1, messages=[{"role": "user", "content": "hi"}])\n        print(f"  ✅ {model}")\n        working.append(model)'),
         ("""        print(f"  ❌ {model}: {type(e).__name__} {getattr(e, 'status_code', '')}")""",
          """        print(f"  ❌ {model}: {type(e).__name__} {getattr(e, 'status_code', '')}")\n"""
          """if len(working) == 1:          # one model down: the rest of the notebook uses the other one for both\n"""
          """    MODEL = ALT = working[0]\n"""
          """    print(f"\\nOnly {MODEL} answered: the rest of this notebook uses it for both models. Carry on.")""")),
    md("""
**❌ on both models** (`PermissionDeniedError 403` or `AuthenticationError 401`): NRP refused your key. Run
`!rm ~/.nrp-llm-token` in a cell, rerun the key cell with the key from the training link, then rerun this check.
Opening the training link also adds your account to the workshop's namespace, which LLM access needs.

**❌ on one model:** that model is unavailable right now. The check has already switched the rest of this notebook
to the model that answered, so carry on.
"""),  # NEW, replaces Daniel's c[7]
    edit(c[9], (" (see [Section 4](#4-multi-turn-interactive-chat))", " (see Section 5 below)"),
         ("[model table](1_intro.html#1-managed-llm-service)", f"[model table]({SITE}1_intro.html#1-managed-llm-service)"),
         ("Reasoning models (`minimax-m2`, `qwen3`, `gpt-oss`) spend", f"Reasoning models (`{MODEL}`, `{ALT}`, `gpt-oss`, `qwen3`) spend"),
         ("Reasoning models (`minimax-m2`, `qwen3`, `gpt-oss`) think", f"Reasoning models (`{MODEL}`, `{ALT}`, `gpt-oss`, `qwen3`) think")),
    edit(c[10], ('def chat(prompt, model="gemma-small", system=None, max_tokens=1200):\n    msgs = []',
                 'def chat(prompt, model=None, system=None, max_tokens=1200):\n'
                 '    model = model or MODEL                 # default: the model the setup check chose\n    msgs = []')),
    keep(c[11]),
    edit(c[12], ("# Code generation — use gpt-oss which is strong at code tasks", "# Code generation — the same helper, the other model"),
         ('    model="gpt-oss",', '    model=ALT,')),
    code('''
# One question, both models, side by side
QUESTION = ("Explain why the invariant mass of two muons is a useful observable for"
            " searching for new particles decaying to mu+mu-. Three sentences.")
for model in [MODEL, ALT]:
    print(f"=== {model} ===")
    print(chat(QUESTION, model=model, max_tokens=2000), "\\n")
'''),  # NEW
    md("""
## 3. What the model actually receives

A chat model has no memory and no view of your notebook. Each request carries
everything the model will know about the conversation: the `messages` list. The server turns that list
into one long text using the model's **chat template** (role markers, special tokens, sometimes default
instructions), and bills you in **tokens**, roughly ¾ of a word each.

Here is one request exactly as it goes over the wire, and the bill that comes back:
"""),  # NEW section
    code('''
import json

request = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "Answer in one sentence."},
        {"role": "user", "content": "What is the CMS detector?"},
    ],
    "max_tokens": 1200,
}
print(json.dumps(request, indent=2))     # this JSON is the entire request body

resp = client.chat.completions.create(**request)
print("\\nreply:", resp.choices[0].message.content)
print("tokens in (prompt):", resp.usage.prompt_tokens,
      "| tokens out (completion):", resp.usage.completion_tokens)
'''),  # NEW
    md("""
Two short messages, yet the prompt is billed at more tokens than the words you wrote. Send the same request
to both models and compare:
"""),  # NEW
    code('''
for model in [MODEL, ALT]:
    r = client.chat.completions.create(**{**request, "model": model})
    print(f"{model:18s} prompt tokens: {r.usage.prompt_tokens:4d}   completion tokens: {r.usage.completion_tokens}")
'''),  # NEW
    md("""
Where do the extra tokens come from? Send almost nothing — `"hi"` — and then ten of them:
"""),  # NEW
    code('''
for model in [MODEL, ALT]:
    for text in ["hi", "hi " * 10]:
        r = client.chat.completions.create(model=model, max_tokens=5,
                                           messages=[{"role": "user", "content": text}])
        print(f"{model:18s} {text!r:36s} prompt tokens: {r.usage.prompt_tokens}")
'''),  # NEW
    # +10 checked on 13 Oct with both models' own tokenizers (Hugging Face tokenizer.json): "hi" is 1 token,
    # "hi " * 10 is 11, nine " hi" and the trailing space.
    md("""
Nine more words (ten `"hi"` instead of one) cost ten more tokens on both models: nine for the words, one for the
space after the last `hi`. But even a bare `"hi"` cost ~97 prompt tokens on
DeepSeek and ~13 on GLM when we tried (11 Oct 2026): every request carries text you never wrote, added around
your messages by the server (the **chat template**: role markers, special tokens, and for some models a default
preamble). You never see it, but the model reads it and you pay for it.

The completion count includes the model's private **reasoning**: both models think before they answer,
and that thinking is billed and counted against `max_tokens` too (`msg.reasoning_content` holds it).

### The conversation is resent every turn

To continue a conversation you send the **whole history again**: the model re-reads everything on every
turn. That history is the model's **context**, and each model has a maximum, its context window. An agent's
context is its system prompt, its tool descriptions and every tool call and result so far; that is what
fills up during a long run.
"""),  # NEW
    code('''
history = [{"role": "system", "content": "You are a concise physics tutor. Two sentences per answer."}]
for q in ["What is a muon?", "How heavy is it compared with the electron?", "And what does it decay to?"]:
    history.append({"role": "user", "content": q})
    r = client.chat.completions.create(model=MODEL, messages=history, max_tokens=1500)
    answer = r.choices[0].message.content or "(no reply)"    # a reply that is all reasoning has no content
    history.append({"role": "assistant", "content": answer})
    print(f"Q: {q}   [{r.usage.prompt_tokens} prompt tokens sent]\\nA: {answer}\\n")
'''),  # NEW
    md("""
The prompt grows every turn. Now ask the last question **without** the history: the model has no idea
what "it" is, because nothing outside the `messages` list exists for it.
"""),  # NEW
    code('''
print(chat("And what does it decay to?", system="You are a concise physics tutor. Two sentences per answer."))
'''),  # NEW
    edit(c[14], ("## 3. System Prompts & Personas", "## 4. System Prompts & Personas")),
    edit(c[15], ('print(chat(QUESTION, system=system, model="gemma-small"))', 'print(chat(QUESTION, system=system))'),
         ('QUESTION = "How do I apply', 'QUESTION = "How do I apply')),
    edit(c[16], ("## 4. Multi-Turn Interactive Chat", "## 5. Multi-Turn Interactive Chat")),
    edit(c[17], ('ROLE  = "Teaching assistant"   # change to any key in ROLES above\nMODEL = "gemma-small"      # or minimax-m2, gpt-oss, qwen3',
                 'ROLE  = "Teaching assistant"   # or "CMS expert" or "Technical coder" (the keys of SYSTEMS below)\n'
                 'CHAT_MODEL = MODEL            # the setup check\'s model; or ALT, "gpt-oss", "qwen3"'),
         ('print(f"Chatting as: {ROLE} ({MODEL}).', 'print(f"Chatting as: {ROLE} ({CHAT_MODEL}).'),
         # 1000 tokens: on 13 Oct deepseek-v4-flash spent them all thinking and the first reply came back empty
         ("        model=MODEL, max_tokens=1000,", "        model=CHAT_MODEL, max_tokens=2000,"),
         ('    print(f"AI: {reply}\\n")', '    print(f"AI: {reply}\\n   ({r.usage.prompt_tokens} prompt tokens sent this turn)\\n")')),
    md(f"""
## Takeaways

- One request = one `messages` list. The model sees nothing else: no files, no memory, no notebook.
- The **system prompt** is just the first message; it shapes every answer that follows.
- **Context** is the whole history, resent on every turn and billed in tokens; it is finite.
- Models wrap the same messages differently and reason before answering: compare `{MODEL}` and `{ALT}`.

**Next:** [2 · An agent, by hand](2_agent_by_hand.ipynb), where the model starts asking *you* to run things.
"""),  # NEW
    # Daniel's optional Jupyter AI section, moved from after the setup check to the end: it sat inside the
    # 10-minute hands-on block of the session.
    edit(c[8], ("## Optional: Set Up Jupyter AI in JupyterLab\n\nEverything below can also be done",
                "## Optional extra: Jupyter AI in JupyterLab\n\nEverything in this notebook can also be done"),
         ("e.g. `minimax-m2`", f"e.g. `{MODEL}`"), (LESSON1[0] + "#step-2", LESSON1[1] + "#step-2"),
         ("../../images/", "../images/"), ("paste your token into", "paste your key into")),
]
save("1_talk_to_a_model", nb1, PY)

# ----------------------------------------------------------------------------------------------- notebook 2
c = load("4_agent")["cells"]
nb2 = [
    edit(c[0], ("# Build a Simple Agent — Tool Calling & the Agent Loop", "# 2 · An agent, by hand — tool calling and the agent loop\n\n" + credit("Build a Simple Agent", "4_agent.html")),
         ("**Requirements:** `OPENAI_API_BASE` and `OPENAI_API_KEY` must be set — export\nyour personal token from [https://nrp.ai/llmtoken](https://nrp.ai/llmtoken)\n(covered in Lesson 1). CPU-only is fine.",
          "**Requirements:** notebook 1's key cell saved your key to `~/.nrp-llm-token`; run it first\nif you have not. CPU-only is fine.")),
    md("""
## 1. Setup

Same client as in notebook 1, with the key notebook 1 saved to `~/.nrp-llm-token` (no such file — say, after a
Binder restart? run notebook 1's key cell first). If one of the two models is down, the cell uses the other one. If it
stops with `No model answered`, NRP refused your key: the [setup check](1_talk_to_a_model.ipynb) in notebook 1 says
what to do.
"""),  # NEW
    code(PIP),  # NEW
    edit(c[2], ('# Paste your personal token from https://nrp.ai/llmtoken between the quotes.\nTOKEN = "<paste-your-token-here>"\nif TOKEN.startswith("<"):\n    raise ValueError("Paste your token into TOKEN above, then run this cell again.")',
                '# The key notebook 1 saved (missing? run notebook 1\'s key cell first).\nfrom pathlib import Path\nTOKEN = (Path.home() / ".nrp-llm-token").read_text()'),
         # One model down does not stop the notebook: the setup request picks the first model that answers.
         ("# Tool calling needs a model that supports it. gpt-oss is reliable at tools;\n# qwen3-small also works well. Small models call tools less consistently.\nMODEL = \"gpt-oss\"\n\n"
          "# One tiny request, so a token problem shows up here rather than halfway through.\nclient.chat.completions.create(\n"
          "    model=MODEL, max_tokens=1, messages=[{\"role\": \"user\", \"content\": \"hi\"}])\n"
          "print(\"Client ready, token accepted, using model:\", MODEL)",
          f"# Tool calling needs a model that supports it. {MODEL} and {ALT} both do;\n# so does gpt-oss. Small models call tools less consistently.\n\n"
          f"# One tiny request per model, so a key problem shows up here rather than halfway through;\n"
          f"# the first model that answers is the one this notebook uses.\nMODEL = None\n"
          f"for m in [\"{MODEL}\", \"{ALT}\"]:\n    try:\n        client.chat.completions.create(\n"
          f"            model=m, max_tokens=1, messages=[{{\"role\": \"user\", \"content\": \"hi\"}}])\n"
          f"        MODEL = m\n        break\n    except Exception as e:\n"
          f"        print(f\"{{m}} did not answer: {{type(e).__name__}} {{getattr(e, 'status_code', '')}}\")\n"
          f"assert MODEL, \"No model answered: NRP refused your key. Rerun notebook 1's key cell and its setup check.\"\n"
          f"print(\"Client ready, key accepted, using model:\", MODEL)")),
    edit(c[3], ("opencode, Claude Code, and Cursor (previous lesson) are exactly this loop —",
                "opencode, Claude Code, and Cursor ([next notebook](3_opencode.ipynb)) are exactly this loop —"),
         ("Everything you did in the Chat notebook", "Everything you did in notebook 1")),
    *[keep(x) for x in c[4:11]],
    # A model that answers in words leaves tool_calls empty: say so, rather than a TypeError on None[0].
    edit(c[11], ("tc = msg.tool_calls[0]\n",
                 'if not msg.tool_calls:\n'
                 '    raise RuntimeError("The model answered in words instead of calling the tool. "\n'
                 '                       "That is normal variance: run the cell above again, then this one.")\n'
                 "tc = msg.tool_calls[0]\n")),
    *[keep(x) for x in c[12:15]],
    edit(c[15], ("# Reasoning models (gpt-oss, minimax-m2, qwen3) expose private", f"# Reasoning models ({MODEL}, {ALT}, gpt-oss) expose private")),
    *[keep(x) for x in c[16:18]],
    edit(c[18], ("Watch the `[turn N]` trace: the agent looks up the muon mass, feeds it into\n`invariant_mass`, gets ≈ 90.9 GeV, checks the Z with `pdg_lookup`, and only\nthen answers. Nobody told it that plan — it came from the question, the tool\ndescriptions, and the intermediate results.",
                 "Watch the `[turn N]` trace: the agent feeds the muon mass into `invariant_mass`,\ngets ≈ 90.9 GeV, checks the Z with `pdg_lookup`, and only then answers. Nobody\ntold it that plan — it came from the question, the tool descriptions, and the\nintermediate results. Did it *look up* the muon mass, or take it from memory?\nIn our test runs " + MODEL + " did both: sometimes it called `pdg_lookup`, sometimes\nit used its own value despite the system prompt saying \"always use the tools\".\nA system prompt is a request, not a constraint; run it a few times and compare.")),
    # On 13 Oct deepseek-v4-flash asked for "tauon" and "tau" in the same first turn in 4 of 5 runs, so the
    # error never got to teach it anything; "on its own" gave "tauon" alone in 6 of 6 (glm-5: 3 of 3 either way).
    edit(c[19], ("\"Try looking up 'tauon' first.\"", "\"Look up 'tauon' first, on its own, and wait for the result.\"")),
    edit(c[20], ('lookup trick.\n', 'lookup trick. (Without "on its own" in the question, the model often asks for `tauon` and\n'
                 '`tau` at once, in the same turn: try it, and look at turn 0 of the trace.)\n'),
         ("Whether you see much depends on the model: `gpt-oss` may\nnot spend much reasoning budget on a lookup this simple — try\n`model=\"minimax-m2\"` for a more talkative trace.",
                 f"Whether you see much depends on the model: run it again as\n"
                 f"`run_agent(\"…\", model=\"{ALT}\", show_reasoning=True)` and compare the two traces.")),
    keep(c[21]),
    edit(c[22], ("**Challenge (take-home) — a retrieval tool.** Wrap the RAG `retrieve()`\nfunction from the Chat notebook as a `search_docs(query)` tool. Your agent can\nthen *decide* when to search documentation — which is precisely how \"agentic\nRAG\" works in production systems.\n\n", ""),
         ("The agentic tools from the previous lesson (opencode, Claude Code) are this", "The agentic tools of the next notebook (opencode, Claude Code) are this"),
         ("**Next:** [Check In on the Agent](5_analysis.ipynb) — go back to the JFC agent you\nlaunched at the start: the same loop, scaled up to a full research framework, has\nbeen running a H→4ℓ measurement on NRP models while you worked.",
          "**Next:** [3 · opencode](3_opencode.ipynb) — the same loop, with file-editing and shell tools, in a terminal.")),
]
save("2_agent_by_hand", nb2, PY)

# ----------------------------------------------------------------------------------------------- notebook 3
ENV_CELL = r"""
cd ~/opencode-exercise
python3 -m venv .venv
for f in '.venv/' '*.root'; do grep -qsxF "$f" .gitignore || echo "$f" >> .gitignore; done   # out of git and the agent's searches
.venv/bin/python -m pip install -q 'uproot>=5' tabulate && echo "environment ready"
"""

AFTER_AGENT_CELL = r"""
cd ~/opencode-exercise
[ -f requirements.txt ] && .venv/bin/python -m pip install -q -r requirements.txt
.venv/bin/python cms_nano_summary.py --help
"""

# Item order after the run (review of 13 Oct): run → "the real test" → fallback → check → break. The fallback is
# safe to run top to bottom: it only replaces a script that is missing or fails on the file, and keeps the agent's.
FALLBACK_CELL = r"""
cd ~/opencode-exercise
if [ -f cms_nano_summary.py ] && timeout 120 .venv/bin/python cms_nano_summary.py nanoout_1.root > /dev/null 2>&1; then
    echo "Your agent's script runs on the file: keep it, and go on to the check."
else
    [ -f cms_nano_summary.py ] && cp cms_nano_summary.py cms_nano_summary.agent.py && echo "the agent's script is kept as cms_nano_summary.agent.py"
    { cp ~/hsf-india-agents/fallback/cms_nano_summary.py . 2>/dev/null \
      || curl -fsSL https://raw.githubusercontent.com/andrzejnovak/hsf-india-agents/main/fallback/cms_nano_summary.py -o cms_nano_summary.py; } \
      && echo "reference script copied: go on to the check" || echo "could not copy the reference script"
fi
"""

# The check matches whole names (a substring test passed nMuon because nMuon_x was listed) and accepts the usual
# headings: "[Muon]", "Muon (78 branches)", "Muon_*", "Collection: Muon"; never a branch line such as "Muon_pt".
CHECK_CELL = r"""
cd ~/opencode-exercise
# 1) the agent's script on the real file; its output goes to summary.txt
.venv/bin/python cms_nano_summary.py nanoout_1.root > summary.txt 2>&1; echo "the script exited with status $?"

# 2) the check: compare a summary with the file itself (defined once, used again below)
check_summary() {
.venv/bin/python - "$1" <<'PY'
import re, sys, uproot
keys = uproot.open("nanoout_1.root")["Events"].keys()
out = open(sys.argv[1]).read()
words = set(re.findall(r"\w+", out))        # whole names: nMuon is not found inside nMuon_whatever
missing = [k for k in keys if k not in words]
print(f"{sys.argv[1]}: {len(keys)} columns in the file, {len(missing)} missing from the summary", missing[:5])
for group in ["Muon", "Jet", "Electron", "boostedTau"]:
    # a heading line: "[Muon]", "Muon (78 branches)", "Muon_*", "Collection: Muon"; not a column like "Muon_pt"
    has_header = bool(re.search(rf"^\W*(?:[Cc]ollection\W*)?{group}(?:_\*)?(?!\w)", out, re.M))
    print(f"  {group:11s} has its own group:", "yes" if has_header else "NO - look at the summary")
PY
}
check_summary summary.txt
"""

BREAK_CELL = r"""
cd ~/opencode-exercise
# Prove the check works: remove every line that mentions Muon, check again. It must complain.
grep -v Muon summary.txt > broken.txt
if type check_summary > /dev/null 2>&1; then check_summary broken.txt
else echo "Run the check cell above first: it defines check_summary (a kernel restart forgets it)."; fi
"""

c = load("3_agentic")["cells"]
nb3 = [
    edit(c[0], ("# Agentic Workflows — opencode & IDE Integration", "# 3 · opencode — a coding agent on NRP"),
         ("**[website version](https://training.nrp-nautilus.io/clariphy/3_agentic.html)** — run cells",
          credit("Agentic Workflows", "3_agentic.html") + "\n\n**The goal for today:** `opencode` starts in your "
          "JupyterLab terminal and answers you with both models. That is all the setup the hackathon needs. Then "
          "you have it write a script, and you check its work.\n\nRun cells")),
    edit(c[1], ("In [Chat with LLMs](2_chat.ipynb) you **called** NRP's managed LLMs from Python. Now you will point an **agentic coding tool** at the same endpoint",
                "In [notebook 1](1_talk_to_a_model.ipynb) you **called** NRP's managed LLMs from Python, and in [notebook 2](2_agent_by_hand.ipynb) you ran the agent loop by hand. Now you will point an **agentic coding tool** — that same loop, with file and shell tools — at the same endpoint")),
    md("""
> **Where to run what:** the setup steps below are notebook cells (Shift+Enter). `opencode` itself is an interactive
> program, so it runs in a JupyterLab terminal: those steps are marked 🖥️ **Terminal step**.
>
> Nothing here edits your shell startup files or any opencode configuration you already have: the exercise lives in
> a new `~/opencode-exercise` folder, and your key stays in the private file notebook 1 saved.
"""),  # NEW, replaces Daniel's c[2] (it also covered his VS Code steps, which this session skips)
    edit(c[3], ("## Part 1: opencode", "## Set up opencode")),
    edit(c[4], ("curl -fsSL https://opencode.ai/install | bash", "curl -fsSL https://opencode.ai/install | bash -s -- --no-modify-path")),
    *[keep(x) for x in c[5:7]],
    md("""
### Configure NRP as the provider

opencode needs two things: where NRP's endpoint is, and your key. Notebook 1 already saved the key to
`~/.nrp-llm-token`, a private file in your home directory. Terminals in JupyterLab are **separate processes**
from this notebook, so `export`s here would not reach them; the file is how opencode will find the key (the
config below points at it). It sits outside the project, so it never ends up in the agent's working files or in
git. Check that it is there:
"""),  # NEW
    code("""
if [ -s ~/.nrp-llm-token ]; then
    echo "Key found in ~/.nrp-llm-token"
else
    echo "No key yet: run the key cell at the top of notebook 1 (1_talk_to_a_model.ipynb), then this cell again."
fi
"""),  # NEW
    keep(c[9]),
    edit(c[10], ("""        "minimax-m2":  { "name": "MiniMax M2"  },
        "gpt-oss":     { "name": "GPT-OSS"     },
        "qwen3":       { "name": "Qwen3 397B"  },
        "gemma-small": { "name": "Gemma 4 12B" },
        "gemma":       { "name": "Gemma 31B"   }""",
                 f"""        "{MODEL}": {{ "name": "DeepSeek V4 Flash" }},
        "{ALT}":             {{ "name": "GLM-5"             }},
        "gpt-oss":           {{ "name": "GPT-OSS"           }},
        "qwen3":             {{ "name": "Qwen3 397B"        }}"""),
         ('"model": "nrp/gpt-oss"', f'"model": "nrp/{MODEL}"'),
         ("\ncat opencode.json", "\ncat opencode.json\n" + SERVICE_STOP)),
    edit(c[11], ("read your token from that file", "read your key from that file"), ("with *your* token", "with *your* key"),
         ("press **Ctrl+P** and select *Switch models* to change the active model mid-session.",
          "type `/models`, then pick one, to change the active model mid-session."),
         ("Try the same task with `gpt-oss` (strong at code) vs `qwen3` (largest context, good for understanding large codebases).",
          f"Try the same task with `{MODEL}` and `{ALT}`: same tools, same files, different model — compare what each one does.")),
    md("""
### Python environment and the data file — before you start opencode

Two things the exercise needs no matter what the agent writes: a private Python environment for the project
(a **virtual environment**, `.venv`, so installs cannot clash with the system Python) with `uproot` and
`tabulate` in it, and a real CMS NanoAOD file to test on — simulated collisions in the CMS NanoAOD format,
~20 MB from NRP's storage. Run both cells now:
"""),  # NEW
    code(ENV_CELL),  # NEW
    edit(c[17], ("# Pull the same NanoAOD file from NRP S3 — no proxy, no credentials (~20 MB).",
                 "# A CMS NanoAOD file from NRP's S3 storage — no proxy, no credentials (~20 MB)."),
         ("curl -fL -o nanoout_1.root", "curl -fsSL -o nanoout_1.root")),
    md(f"""
### What opencode sends the model

opencode is notebook 2's loop with more tools. Every turn it sends the model a `messages` list like the
ones you built by hand: its own long **system prompt** (how to behave, how to edit files), the **schemas
of its tools** (read, edit, bash, search, …), your request, and every tool call and result so far. Your
project files reach the model only through those tool results: it reads what it chooses to read.

That is why the context fills up in a long session (`/compact` summarises it), why the folder matters,
and why the same prompt behaves differently with `{MODEL}` and `{ALT}`. Watch for those tool calls while it works.
"""),  # NEW, before the launch: it explains what students watch while opencode runs
    edit(c[12], ("Getting `Forbidden` or `401` responses once inside opencode? It couldn't read a valid token — re-run the token cell above (with the placeholder replaced), then restart opencode.",
                 "Getting `Forbidden` or `401` responses once inside opencode? It could not use your key. Quit opencode "
                 "(`/exit`), then in the terminal run `rm ~/.nrp-llm-token` (no `!` here: that is only for notebook cells), "
                 "rerun notebook 1's key cell, run `opencode service stop`, and start `opencode` again: its background "
                 "service remembers the old key until it stops."),
         ("The prompt is active as soon as opencode opens — just type your task and press Enter. (`/` opens the slash-command menu for things like `/models` or `/clear`, not the prompt itself.) Paste the following task:",
          f"The prompt is active as soon as opencode opens. First type `hi` and press Enter: you should get a reply. "
          f"Then type `/models`, pick `{ALT}`, and say `hi` again. A reply from both models is the setup the hackathon "
          f"needs. (`/` opens the command menu for things like `/models` or `/clear`, not the prompt itself.)\n\n"
          f"Now paste the following task:")),
    # An agent that wrote `--input FILE` made every later cell fail: say how the script is run.
    edit(c[13], ('given as a command-line\nargument. It has an',
                 'given as a command-line\nargument, positional rather than an option:\n'
                 '  python cms_nano_summary.py nanoout_1.root\nIt has an')),
    md("""
> **Important:** if opencode generates a file named `uproot.py`, rename it — it would shadow the `uproot` package on import.
"""),  # Daniel's warning from c[20], moved up to the task
    md("""
When the agent says it is done, install anything extra it asked for and check that its script at least starts.
Calling `.venv/bin/python` uses the project's environment directly, so there is nothing to activate. (Agent not
done after ~20 min? The fallback cell is a little further down.)
"""),  # NEW
    code(AFTER_AGENT_CELL),  # NEW
    edit(c[18], ("cd ~/opencode-exercise\n",
                 "cd ~/opencode-exercise\n# The first 40 lines. A \"Broken pipe\" error after them is head stopping early, "
                 "not a problem with the file.\n")),
    keep(c[19]),
    md("""
### Agent not done after ~20 min, or its script still fails? Run this instead of waiting

The point of this exercise is the checking. This cell puts the reference script in place of a script that is
missing or fails on the file, and keeps the agent's as `cms_nano_summary.agent.py`. If the agent's script runs, the
cell leaves it alone.
"""),  # NEW
    code(FALLBACK_CELL),  # NEW
    md("""
### Check the agent's work — a partial check

The script ran — but is its output **right**? Here the file itself is the planted truth: we know exactly which
columns it contains. This cell saves the script's output to `summary.txt` and compares it with the file: is every
column named, and do four collections (Muon, Jet, Electron, boostedTau) get a heading of their own? It is a
**partial** check — it does not test that each column appears once or sits in the right group — so look at the
grouping yourself too.
"""),  # NEW
    code(CHECK_CELL),  # NEW
    md("""
**Does the check itself work?** A check that never fails proves nothing. Break the summary on purpose and run it
again: it must complain. (This uses `check_summary` from the cell above: after a kernel restart, run that cell first.)
"""),  # NEW
    code(BREAK_CELL),  # NEW
    edit(c[20], ("> **Important:** if opencode generates a file named `uproot.py`, rename it — it would shadow the `uproot` package on import.\n\n", ""),
         ("- Switch to `qwen3` and ask it to add unit tests with `pytest`.", f"- Switch to `{ALT}` and ask it to add unit tests with `pytest`.")),
    md("""
## Before Wednesday

`opencode` should start in your JupyterLab terminal and answer with both models: that is all the setup the hackathon
needs. The NRP settings are in `~/opencode-exercise/opencode.json` and apply inside that folder. For a project in
another folder, copy them there and make it a git project:

```bash
mkdir -p ~/my-project && cp ~/opencode-exercise/opencode.json ~/my-project/ && cd ~/my-project && git init -q
```
"""),  # NEW
]
save("3_opencode", nb3, BASH)

# laptop/opencode.json: exactly the settings notebook 3 writes, for opencode on a student's own machine
# (README, "On your own laptop"): one source, so the two cannot drift apart.
cfg = next(src(x) for x in nb3 if x["cell_type"] == "code" and "cat > opencode.json" in src(x))
cfg = cfg.split("<<'JSON'\n", 1)[1].split("\nJSON", 1)[0] + "\n"
json.loads(cfg)
(ROOT / "laptop").mkdir(exist_ok=True)
(ROOT / "laptop" / "opencode.json").write_text(cfg)
# (KEY_TEXT pairs whose cells were rewritten above simply go unused)
