"""Build the session notebooks from Daniel Diaz's CLARIPHY notebooks.

    python3 tools/build_notebooks.py

Sources: upstream/*.ipynb, copied unchanged from github.com/nrp-nautilus/nrp-training, branch
materials/clariphy @ c63cb76 (21 Sep 2026). Every lifted cell keeps Daniel's text; the edits below are
the whole diff (model choice, cross-links, renumbering) plus a few new cells, marked NEW. Rerun after
refreshing upstream/ to pick up his changes.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UP = "https://github.com/nrp-nautilus/nrp-training/tree/materials/clariphy"
SITE = "https://training.nrp-nautilus.io/clariphy/"
MODEL, ALT = "deepseek-v4-flash", "glm-5"


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
    keep(c[2]),
    code("%pip install -q openai   # NEW: the workshop's Binder image has no OpenAI client; elsewhere a no-op"),
    md("""
Run the cell below and paste your **LLM API key** (from the training link) into the box that appears, then press
Enter. *NEW in this version:* the key is saved to a private file, `~/.nrp-llm-token`, readable only by you;
notebooks 2 and 3 and opencode read it from there, so you paste it **once per session** and it never sits in a
notebook. A Binder restart wipes the file: just run this cell again.
"""),
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
'''),
    keep(c[5]),
    edit(c[6], ('for model in ["gemma-small", "minimax-m2", "gpt-oss", "qwen3-embedding"]:',
                f'for model in ["{MODEL}", "{ALT}"]:'),
         ('        if model == "qwen3-embedding":\n            client.embeddings.create(model=model, input=["hi"])\n        else:\n            client.chat.completions.create(\n                model=model, max_tokens=1, messages=[{"role": "user", "content": "hi"}])',
          '        client.chat.completions.create(\n            model=model, max_tokens=1, messages=[{"role": "user", "content": "hi"}])')),
    edit(c[7], LESSON1, ("check that you pasted your own token from [nrp.ai/llmtoken](https://nrp.ai/llmtoken) and re-ran both cells",
                         "check that you pasted your own key from the training-link page: delete the saved one with `!rm ~/.nrp-llm-token`, rerun the key cell, then this one")),
    edit(c[8], ("e.g. `minimax-m2`", f"e.g. `{MODEL}`"), (LESSON1[0] + "#step-2", LESSON1[1] + "#step-2"),
         ("../../images/", "../images/")),
    edit(c[9], ("[Section 4](#4-multi-turn-interactive-chat)", "[Section 5](#5-multi-turn-interactive-chat)"),
         ("[model table](1_intro.html#1-managed-llm-service)", f"[model table]({SITE}1_intro.html#1-managed-llm-service)"),
         ("Reasoning models (`minimax-m2`, `qwen3`, `gpt-oss`) spend", f"Reasoning models (`{MODEL}`, `{ALT}`, `gpt-oss`, `qwen3`) spend"),
         ("Reasoning models (`minimax-m2`, `qwen3`, `gpt-oss`) think", f"Reasoning models (`{MODEL}`, `{ALT}`, `gpt-oss`, `qwen3`) think")),
    edit(c[10], ('def chat(prompt, model="gemma-small"', f'def chat(prompt, model="{MODEL}"')),
    keep(c[11]),
    edit(c[12], ("# Code generation — use gpt-oss which is strong at code tasks", f"# Code generation — the same helper, the other model"),
         ('    model="gpt-oss",', f'    model="{ALT}",')),
    code(f'''
# NEW: one question, both models, side by side
QUESTION = ("Explain why the invariant mass of two muons is a useful observable for"
            " searching for new particles decaying to mu+mu-. Three sentences.")
for model in ["{MODEL}", "{ALT}"]:
    print(f"=== {{model}} ===")
    print(chat(QUESTION, model=model, max_tokens=2000), "\\n")
'''),
    md(f"""
## 3. What the model actually receives

*NEW in this version.* A chat model has no memory and no view of your notebook. Each request carries
everything the model will know about the conversation: the `messages` list. The server turns that list
into one long text using the model's **chat template** (role markers, special tokens, sometimes default
instructions), and bills you in **tokens**, roughly ¾ of a word each.

Here is one request exactly as it goes over the wire, and the bill that comes back:
"""),
    code(f'''
import json

request = {{
    "model": "{MODEL}",
    "messages": [
        {{"role": "system", "content": "Answer in one sentence."}},
        {{"role": "user", "content": "What is the CMS detector?"}},
    ],
    "max_tokens": 1200,
}}
print(json.dumps(request, indent=2))     # this JSON is the entire request body

resp = client.chat.completions.create(**request)
print("\\nreply:", resp.choices[0].message.content)
print("tokens in (prompt):", resp.usage.prompt_tokens,
      "| tokens out (completion):", resp.usage.completion_tokens)
'''),
    md("""
Two short messages, yet the prompt is billed at more tokens than the words you wrote. Send the same request
to both models and compare:
"""),
    code(f'''
for model in ["{MODEL}", "{ALT}"]:
    r = client.chat.completions.create(**{{**request, "model": model}})
    print(f"{{model:18s}} prompt tokens: {{r.usage.prompt_tokens:4d}}   completion tokens: {{r.usage.completion_tokens}}")
'''),
    md("""
Where do the extra tokens come from? Send almost nothing — `"hi"` — and then ten of them:
"""),
    code(f'''
for model in ["{MODEL}", "{ALT}"]:
    for text in ["hi", "hi " * 10]:
        r = client.chat.completions.create(model=model, max_tokens=5,
                                           messages=[{{"role": "user", "content": text}}])
        print(f"{{model:18s}} {{text!r:36s}} prompt tokens: {{r.usage.prompt_tokens}}")
'''),
    md("""
Nine more words (ten `"hi"` instead of one) cost ten more tokens on both models. But even a bare `"hi"` cost ~97 prompt tokens on
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
"""),
    code(f'''
history = [{{"role": "system", "content": "You are a concise physics tutor. Two sentences per answer."}}]
for q in ["What is a muon?", "How heavy is it compared with the electron?", "And what does it decay to?"]:
    history.append({{"role": "user", "content": q}})
    r = client.chat.completions.create(model="{MODEL}", messages=history, max_tokens=1500)
    answer = r.choices[0].message.content
    history.append({{"role": "assistant", "content": answer}})
    print(f"Q: {{q}}   [{{r.usage.prompt_tokens}} prompt tokens sent]\\nA: {{answer}}\\n")
'''),
    md("""
The prompt grows every turn. Now ask the last question **without** the history: the model has no idea
what "it" is, because nothing outside the `messages` list exists for it.
"""),
    code(f'''
print(chat("And what does it decay to?", system="You are a concise physics tutor. Two sentences per answer."))
'''),
    edit(c[14], ("## 3. System Prompts & Personas", "## 4. System Prompts & Personas")),
    edit(c[15], ('print(chat(QUESTION, system=system, model="gemma-small"))', 'print(chat(QUESTION, system=system))'),
         ('QUESTION = "How do I apply', 'QUESTION = "How do I apply')),
    edit(c[16], ("## 4. Multi-Turn Interactive Chat", "## 5. Multi-Turn Interactive Chat")),
    edit(c[17], ('MODEL = "gemma-small"      # or minimax-m2, gpt-oss, qwen3', f'MODEL = "{MODEL}"   # or {ALT}, gpt-oss, qwen3'),
         ('    print(f"AI: {reply}\\n")', '    print(f"AI: {reply}\\n   ({r.usage.prompt_tokens} prompt tokens sent this turn)\\n")')),
    md(f"""
## Takeaways

- One request = one `messages` list. The model sees nothing else: no files, no memory, no notebook.
- The **system prompt** is just the first message; it shapes every answer that follows.
- **Context** is the whole history, resent on every turn and billed in tokens; it is finite.
- Models wrap the same messages differently and reason before answering: compare `{MODEL}` and `{ALT}`.

**Next:** [2 · An agent, by hand](2_agent_by_hand.ipynb), where the model starts asking *you* to run things.
"""),
]
save("1_talk_to_a_model", nb1, PY)

# ----------------------------------------------------------------------------------------------- notebook 2
c = load("4_agent")["cells"]
nb2 = [
    edit(c[0], ("# Build a Simple Agent — Tool Calling & the Agent Loop", "# 2 · An agent, by hand — tool calling and the agent loop\n\n" + credit("Build a Simple Agent", "4_agent.html")),
         ("(covered in Lesson 1)", "(covered in [notebook 1](1_talk_to_a_model.ipynb))")),
    md("""
## 1. Setup

Same client as in notebook 1, with the key notebook 1 saved to `~/.nrp-llm-token` (no such file — say, after a
Binder restart? run notebook 1's key cell first). If the cell stops with `PermissionDeniedError: 403`, NRP refused
your key or the model; the [setup check](1_talk_to_a_model.ipynb) in notebook 1 tells you which.
"""),
    code("%pip install -q openai   # NEW: the workshop's Binder image has no OpenAI client; elsewhere a no-op"),
    edit(c[2], ('# Paste your personal token from https://nrp.ai/llmtoken between the quotes.\nTOKEN = "<paste-your-token-here>"\nif TOKEN.startswith("<"):\n    raise ValueError("Paste your token into TOKEN above, then run this cell again.")',
                '# The key notebook 1 saved (missing? run notebook 1\'s key cell first).\nfrom pathlib import Path\nTOKEN = (Path.home() / ".nrp-llm-token").read_text()'),
         ("# Tool calling needs a model that supports it. gpt-oss is reliable at tools;\n# qwen3-small also works well. Small models call tools less consistently.\nMODEL = \"gpt-oss\"",
                f"# Tool calling needs a model that supports it. {MODEL} and {ALT} both do;\n# so does gpt-oss. Small models call tools less consistently.\nMODEL = \"{MODEL}\"")),
    edit(c[3], ("opencode, Claude Code, and Cursor (previous lesson) are exactly this loop —",
                "opencode, Claude Code, and Cursor ([next notebook](3_opencode.ipynb)) are exactly this loop —")),
    *[keep(x) for x in c[4:15]],
    edit(c[15], ("# Reasoning models (gpt-oss, minimax-m2, qwen3) expose private", f"# Reasoning models ({MODEL}, {ALT}, gpt-oss) expose private")),
    *[keep(x) for x in c[16:18]],
    edit(c[18], ("Watch the `[turn N]` trace: the agent looks up the muon mass, feeds it into\n`invariant_mass`, gets ≈ 90.9 GeV, checks the Z with `pdg_lookup`, and only\nthen answers. Nobody told it that plan — it came from the question, the tool\ndescriptions, and the intermediate results.",
                 "Watch the `[turn N]` trace: the agent feeds the muon mass into `invariant_mass`,\ngets ≈ 90.9 GeV, checks the Z with `pdg_lookup`, and only then answers. Nobody\ntold it that plan — it came from the question, the tool descriptions, and the\nintermediate results. Did it *look up* the muon mass, or take it from memory?\nIn our test runs " + MODEL + " did both: sometimes it called `pdg_lookup`, sometimes\nit used its own value despite the system prompt saying \"always use the tools\".\nA system prompt is a request, not a constraint; run it a few times and compare.")),
    keep(c[19]),
    edit(c[20], ("Whether you see much depends on the model: `gpt-oss` may\nnot spend much reasoning budget on a lookup this simple — try\n`model=\"minimax-m2\"` for a more talkative trace.",
                 f"Whether you see much depends on the model — rerun it with\n`model=\"{ALT}\"` and compare the two traces.")),
    keep(c[21]),
    edit(c[22], ("**Challenge (take-home) — a retrieval tool.** Wrap the RAG `retrieve()`\nfunction from the Chat notebook as a `search_docs(query)` tool. Your agent can\nthen *decide* when to search documentation — which is precisely how \"agentic\nRAG\" works in production systems.\n\n", ""),
         ("The agentic tools from the previous lesson (opencode, Claude Code) are this", "The agentic tools of the next notebook (opencode, Claude Code) are this"),
         ("**Next:** [Check In on the Agent](5_analysis.ipynb) — go back to the JFC agent you\nlaunched at the start: the same loop, scaled up to a full research framework, has\nbeen running a H→4ℓ measurement on NRP models while you worked.",
          "**Next:** [3 · opencode](3_opencode.ipynb) — the same loop, with file-editing and shell tools, in a terminal.")),
]
save("2_agent_by_hand", nb2, PY)

# ----------------------------------------------------------------------------------------------- notebook 3
ENV_CELL = r'''
cd ~/opencode-exercise
python3 -m venv .venv
grep -qsxF '.venv/' .gitignore || echo '.venv/' >> .gitignore   # keep it out of git and the agent's searches
.venv/bin/python -m pip install -q 'uproot>=5' tabulate && echo "environment ready"
'''

AFTER_AGENT_CELL = r'''
cd ~/opencode-exercise
[ -f requirements.txt ] && .venv/bin/python -m pip install -q -r requirements.txt
.venv/bin/python cms_nano_summary.py --help
'''

CHECK_CELL = r'''
cd ~/opencode-exercise
# 1) the agent's script on the real file; its output goes to summary.txt
.venv/bin/python cms_nano_summary.py nanoout_1.root > summary.txt 2>&1; echo "the script exited with status $?"

# 2) the check: compare a summary with the file itself (defined once, used again below)
check_summary() {
.venv/bin/python - "$1" <<'PY'
import re, sys, uproot
keys = uproot.open("nanoout_1.root")["Events"].keys()
out = open(sys.argv[1]).read()
missing = [k for k in keys if k not in out]
print(f"{sys.argv[1]}: {len(keys)} columns in the file, {len(missing)} missing from the summary", missing[:5])
for group in ["Muon", "Jet", "Electron", "boostedTau"]:
    has_header = bool(re.search(rf"^\W*{group}\b", out, re.M))   # a line that starts with the group name
    print(f"  {group:11s} has its own group:", "yes" if has_header else "NO - look at the summary")
PY
}
check_summary summary.txt
'''

BREAK_CELL = r'''
cd ~/opencode-exercise
# Prove the check works: remove every line that mentions Muon, check again. It must complain.
grep -v Muon summary.txt > broken.txt
check_summary broken.txt
'''

FALLBACK_CELL = r'''
# No working script by 16:40? Use the reference script, then run the check cell above again.
cp ~/hsf-india-agents/fallback/cms_nano_summary.py ~/opencode-exercise/cms_nano_summary.py && echo "reference script copied"
'''

c = load("3_agentic")["cells"]
nb3 = [
    edit(c[0], ("# Agentic Workflows — opencode & IDE Integration", "# 3 · opencode — a coding agent on NRP"),
         ("**[website version](https://training.nrp-nautilus.io/clariphy/3_agentic.html)** — run cells",
          credit("Agentic Workflows", "3_agentic.html") + "\n\nRun cells")),
    edit(c[1], ("In [Chat with LLMs](2_chat.ipynb) you **called** NRP's managed LLMs from Python. Now you will point an **agentic coding tool** at the same endpoint",
                "In [notebook 1](1_talk_to_a_model.ipynb) you **called** NRP's managed LLMs from Python, and in [notebook 2](2_agent_by_hand.ipynb) you ran the agent loop by hand. Now you will point an **agentic coding tool** — that same loop, with file and shell tools — at the same endpoint")),
    edit(c[2], ("and the VS Code steps happen in an IDE — neither fits", "and the optional VS Code steps happen in an IDE — neither fits")),
    *[keep(x) for x in c[3:7]],
    md("""
### Configure NRP as the provider

opencode needs two things: where NRP's endpoint is, and your key. Notebook 1 already saved the key to
`~/.nrp-llm-token`, a private file in your home directory. Terminals in JupyterLab are **separate processes**
from this notebook, so `export`s here would not reach them; the file is how opencode will find the key (the
config below points at it). It sits outside the project, so it never ends up in the agent's working files or in
git. Check that it is there:
"""),
    code('''
if [ -s ~/.nrp-llm-token ]; then
    echo "Key found in ~/.nrp-llm-token"
    export OPENAI_API_KEY="$(cat ~/.nrp-llm-token)" OPENAI_API_BASE="https://ellm.nrp-nautilus.io/v1"
else
    echo "No key yet: run the key cell at the top of notebook 1 (1_talk_to_a_model.ipynb), then this cell again."
fi
'''),
    keep(c[9]),
    edit(c[10], ('''        "minimax-m2":  { "name": "MiniMax M2"  },
        "gpt-oss":     { "name": "GPT-OSS"     },
        "qwen3":       { "name": "Qwen3 397B"  },
        "gemma-small": { "name": "Gemma 4 12B" },
        "gemma":       { "name": "Gemma 31B"   }''',
                 f'''        "{MODEL}": {{ "name": "DeepSeek V4 Flash" }},
        "{ALT}":             {{ "name": "GLM-5"             }},
        "gpt-oss":           {{ "name": "GPT-OSS"           }},
        "qwen3":             {{ "name": "Qwen3 397B"        }}'''),
         ('"model": "nrp/gpt-oss"', f'"model": "nrp/{MODEL}"')),
    edit(c[11], ("Try the same task with `gpt-oss` (strong at code) vs `qwen3` (largest context, good for understanding large codebases).",
                 f"Try the same task with `{MODEL}` and `{ALT}`: same tools, same files, different model — compare what each one does.")),
    md("""
### Python environment and the data file — before you start opencode (NEW order)

Two things the exercise needs no matter what the agent writes: a private Python environment for the project
(a **virtual environment**, `.venv`, so installs cannot clash with the system Python) with `uproot` and
`tabulate` in it, and a real CMS NanoAOD file to test on — simulated collisions in the CMS NanoAOD format,
~20 MB from NRP's storage. Run both cells now:
"""),
    code(ENV_CELL),
    keep(c[17]),
    edit(c[12], ("Getting `Forbidden` or `401` responses once inside opencode? It couldn't read a valid token — re-run the token cell above (with the placeholder replaced), then restart opencode.",
                 "Getting `Forbidden` or `401` responses once inside opencode? It could not read a valid key: in a notebook cell run `!rm ~/.nrp-llm-token`, rerun notebook 1's key cell, then restart opencode.")),
    keep(c[13]),
    md("""
When the agent says it is done, install anything extra it asked for and check that its script at least starts.
Calling `.venv/bin/python` uses the project's environment directly, so there is nothing to activate:
"""),
    code(AFTER_AGENT_CELL),
    keep(c[18]),
    md("""
### Check the agent's work — a partial check (NEW)

The script ran — but is its output **right**? Here the file itself is the planted truth: we know exactly which
columns it contains. This cell saves the script's output to `summary.txt` and compares it with the file: is every
column named, and do four collections (Muon, Jet, Electron, boostedTau) get a heading of their own? It is a
**partial** check — it does not test that each column appears once or sits in the right group — so look at the
grouping yourself too.
"""),
    code(CHECK_CELL),
    md("""
**Does the check itself work?** A check that never fails proves nothing. Break the summary on purpose and run it
again: it must complain.
"""),
    code(BREAK_CELL),
    md("""
**Fallback.** If your agent has not produced a working script by 16:40, copy in the reference script and do the
check with it: the point of this exercise is the checking.
"""),
    code(FALLBACK_CELL),
    keep(c[19]),
    edit(c[20], ("- Switch to `qwen3` and ask it to add unit tests with `pytest`.", f"- Switch to `{ALT}` and ask it to add unit tests with `pytest`.")),
    md(f"""
## What opencode sends the model (NEW)

opencode is notebook 2's loop with more tools. Every turn it sends the model a `messages` list like the
ones you built by hand: its own long **system prompt** (how to behave, how to edit files), the **schemas
of its tools** (read, edit, bash, search, …), your request, and every tool call and result so far. Your
project files reach the model only through those tool results: it reads what it chooses to read.

That is why the context fills up in a long session (`/compact` summarises it), why the folder matters,
and why the same prompt behaves differently with `{MODEL}` and `{ALT}`.

**Before Wednesday:** `opencode` should start in your JupyterLab terminal and answer with both models.
That is all the setup the hackathon needs.
"""),
]
save("3_opencode", nb3, BASH)
# (KEY_TEXT pairs whose cells were rewritten above simply go unused)
