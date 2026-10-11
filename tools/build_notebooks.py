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


def save(name, cells, kernel):
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
    edit(c[3], LESSON1),
    keep(c[4]),
    keep(c[5]),
    edit(c[6], ('for model in ["gemma-small", "minimax-m2", "gpt-oss", "qwen3-embedding"]:',
                f'for model in ["{MODEL}", "{ALT}"]:'),
         ('        if model == "qwen3-embedding":\n            client.embeddings.create(model=model, input=["hi"])\n        else:\n            client.chat.completions.create(\n                model=model, max_tokens=1, messages=[{"role": "user", "content": "hi"}])',
          '        client.chat.completions.create(\n            model=model, max_tokens=1, messages=[{"role": "user", "content": "hi"}])')),
    edit(c[7], LESSON1),
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
Two short messages, yet the prompt is billed at many more tokens than the words you wrote: the
difference is the chat template wrapped around your text. Each model wraps it differently. Send the
same request to both and compare:
"""),
    code(f'''
for model in ["{MODEL}", "{ALT}"]:
    r = client.chat.completions.create(**{{**request, "model": model}})
    print(f"{{model:18s}} prompt tokens: {{r.usage.prompt_tokens:4d}}   completion tokens: {{r.usage.completion_tokens}}")
'''),
    md("""
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
    edit(c[1], LESSON1, ("[Setup Check](2_chat.ipynb) in the Chat\nnotebook", "[setup check](1_talk_to_a_model.ipynb) in notebook 1")),
    edit(c[2], ("# Tool calling needs a model that supports it. gpt-oss is reliable at tools;\n# qwen3-small also works well. Small models call tools less consistently.\nMODEL = \"gpt-oss\"",
                f"# Tool calling needs a model that supports it. {MODEL} and {ALT} both do;\n# so does gpt-oss. Small models call tools less consistently.\nMODEL = \"{MODEL}\"")),
    edit(c[3], ("opencode, Claude Code, and Cursor (previous lesson) are exactly this loop —",
                "opencode, Claude Code, and Cursor ([next notebook](3_opencode.ipynb)) are exactly this loop —")),
    *[keep(x) for x in c[4:15]],
    edit(c[15], ("# Reasoning models (gpt-oss, minimax-m2, qwen3) expose private", f"# Reasoning models ({MODEL}, {ALT}, gpt-oss) expose private")),
    *[keep(x) for x in c[16:18]],
    edit(c[18], ("Watch the `[turn N]` trace: the agent looks up the muon mass, feeds it into\n`invariant_mass`, gets ≈ 90.9 GeV, checks the Z with `pdg_lookup`, and only\nthen answers. Nobody told it that plan — it came from the question, the tool\ndescriptions, and the intermediate results.",
                 "Watch the `[turn N]` trace: the agent feeds the muon mass into `invariant_mass`,\ngets ≈ 90.9 GeV, checks the Z with `pdg_lookup`, and only then answers. Nobody\ntold it that plan — it came from the question, the tool descriptions, and the\nintermediate results. Did it *look up* the muon mass, or take it from memory?\nWhen we tried it, " + MODEL + " used its own value despite the system prompt saying\n\"always use the tools\": a system prompt is a request, not a constraint.")),
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
c = load("3_agentic")["cells"]
nb3 = [
    edit(c[0], ("# Agentic Workflows — opencode & IDE Integration", "# 3 · opencode — a coding agent on NRP"),
         ("**[website version](https://training.nrp-nautilus.io/clariphy/3_agentic.html)** — run cells",
          credit("Agentic Workflows", "3_agentic.html") + "\n\nRun cells")),
    edit(c[1], ("In [Chat with LLMs](2_chat.ipynb) you **called** NRP's managed LLMs from Python. Now you will point an **agentic coding tool** at the same endpoint",
                "In [notebook 1](1_talk_to_a_model.ipynb) you **called** NRP's managed LLMs from Python, and in [notebook 2](2_agent_by_hand.ipynb) you ran the agent loop by hand. Now you will point an **agentic coding tool** — that same loop, with file and shell tools — at the same endpoint")),
    edit(c[2], ("and the VS Code steps happen in an IDE — neither fits", "and the optional VS Code steps happen in an IDE — neither fits")),
    *[keep(x) for x in c[3:10]],
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
    *[keep(x) for x in c[12:20]],
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
