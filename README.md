# LLMs and coding agents on NRP — HSF-India workshop, Delhi, 13 Oct 2026

Hands-on material for the agents session of the
[HSF-India Scientific Computing Workshop](https://indico.cern.ch/event/1714663/) (Tue 13 Oct, 15:30–17:00 IST),
and the setup every student needs for the hackathon that follows (Wed–Fri).

By the end of the session each student can call NRP's open models from Python, knows what a model
actually receives (messages, system prompt, context, tokens), has run an agent loop by hand, and has
[opencode](https://opencode.ai) working in their JupyterLab terminal with **DeepSeek** (`deepseek-v4-flash`)
and **GLM** (`glm-5`).

## Before you start

- Open the **training link** from the organisers and log in to NRP. It adds you to the workshop's namespace
  for the week and shows your **LLM API key** once: copy it somewhere safe straight away. If you lose it,
  open the training link again; you get a new key, which replaces the old one. The base URL for every
  client is `https://ellm.nrp-nautilus.io/v1`.
- JupyterLab on the workshop's BinderHub, which runs on NRP:
  [launch it](https://binderhub.ssl-hep.org/v2/gh/research-software-collaborations/courses-hsf-india-October2026/binder?gpuModel=&gpuCount=0&cudaMajor=undefined&cudaMinor=undefined&site=nrp&memory=4.0&cpu=1&qos=Guaranteed)
  (first time: ask at [connect.tempest.uchicago.edu](https://connect.tempest.uchicago.edu) to join the
  *hsf-india* workshop). opencode is preinstalled there. Any other JupyterLab with Python 3 and git works too
  (`pip install -r requirements.txt`). Get the notebooks from a JupyterLab terminal (**File → New → Terminal**):

  ```bash
  git clone https://github.com/andrzejnovak/hsf-india-agents.git
  ```

- **A Binder session is temporary.** When it ends, everything in it is gone: files, the saved key, opencode's
  sessions. Keep your key on your own machine, and copy what you want to keep to `/data/<your-name>` (shared:
  everyone can read it, so never the key). A new session: Binder → `git clone` → notebook 1's key cell →
  notebook 3's setup cells → your files from `/data/<your-name>`. opencode on your own laptop stays set up:
  [three commands](#on-your-own-laptop-optional).

Notebook 1's key cell asks for the key once and saves it privately (`~/.nrp-llm-token`); notebooks 2 and 3 and
opencode read it from there. Never commit it anywhere or paste it into a chat. Key not accepted? In a notebook
cell `!rm ~/.nrp-llm-token`, rerun the key cell and the setup check, then restart opencode: `/exit`, then
`opencode service stop` in the terminal, then `opencode` (the Binder's opencode keeps a background service that
remembers the old key until it stops).

## On your own laptop (optional)

opencode also runs on your own machine with the same key, which is handy for the hackathon, and unlike a Binder
session it stays set up. macOS, Linux, or Windows inside WSL (`wsl --install` in an administrator PowerShell,
then open Ubuntu). In a terminal:

```bash
curl -fsSL https://opencode.ai/install | bash        # 1. install opencode, then open a NEW terminal
read -rs K && printf %s "$K" > ~/.nrp-llm-token && chmod 600 ~/.nrp-llm-token
                                                     # 2. paste your key, press Enter (nothing shows)
mkdir -p ~/.config/opencode && curl -fsSL https://raw.githubusercontent.com/andrzejnovak/hsf-india-agents/main/laptop/opencode.json -o ~/.config/opencode/opencode.json
                                                     # 3. tell opencode where NRP is
opencode models nrp                                  # check: lists nrp/deepseek-v4-flash, nrp/glm-5, …
```

Then `cd` into a project folder and run `opencode`; `/models` switches between DeepSeek and GLM.
[`laptop/opencode.json`](laptop/opencode.json) holds exactly the settings notebook 3 writes, and the key sits in the
same private file the notebooks use.

- Step 3 **replaces** opencode settings you already have. Already an opencode user? Copy the `"provider"` block
  from `laptop/opencode.json` into your own config instead.
- `opencode: command not found` → the installer could not put it on your PATH: run `~/.opencode/bin/opencode`, or
  add `export PATH=$HOME/.opencode/bin:$PATH` to your shell's startup file. With Node.js, `npm i -g opencode-ai`
  also installs it.
- `bad file reference … .nrp-llm-token does not exist` → step 2 did not run: repeat it. 401/403 → the key was not
  accepted: repeat step 2 with the key from the training link.
- Native Windows without WSL should work with `npm i -g opencode-ai`, but we have not tested it.

Tested on 12 Oct 2026 in a fresh home directory with opencode 1.19.0 from the installer (bash; step 2 also in zsh):
both models answer from any folder.

## The notebooks

| | Notebook | Kernel | What you do |
|---|---|---|---|
| 1 | [Talking to a model](notebooks/1_talk_to_a_model.ipynb) | Python | setup check · `chat()` helper · what the model receives: the request, tokens, the chat template, context resent every turn · system prompts · multi-turn chat |
| 2 | [An agent, by hand](notebooks/2_agent_by_hand.ipynb) | Python | one tool call done by hand · the agent loop in ~30 lines · guardrails · exercises |
| 3 | [opencode](notebooks/3_opencode.ipynb) | Bash | point opencode at NRP · have it write a NanoAOD summary script · check its output against the file · prove the check works · switch models |

`fallback/cms_nano_summary.py` is a reference solution for notebook 3: if the agent has not produced a working
script by 16:40, copy it in and do the check with it.

## Session plan (90 min, Tue 13 Oct 2026, IST)

| Clock | What | Mode |
|---|---|---|
| 15:30 | Start your session: training link (key), Binder link | hands-on, while it boots |
| 15:33 | Why: an agent that did physics; how would you know it was wrong? | talk |
| 15:39 | Setup: clone, notebook 1's key cell, two green ticks | hands-on |
| 15:49 | Notebook 1: one API call, text you never wrote, no memory → your turn until 16:04 | talk + hands-on |
| 16:04 | Notebook 2: one tool call, the loop → your turn until 16:18 | talk + hands-on |
| 16:19 | Notebook 3: opencode on a CMS file, the partial check → your turn until 16:50 | talk + hands-on |
| 16:50 | What we found, the exit check, saving your work | talk |

Tested end to end on 11 Oct 2026 against NRP (`deepseek-v4-flash`, `glm-5`; opencode 1.18.30), and notebook 3's
config against opencode 2.0.26 with the Binder's global config: DeepSeek, GLM and qwen3 all answer, the key read
from `~/.nrp-llm-token`. On 11 Oct all three notebooks also ran inside the workshop Binder session itself
(opencode 2.0.21, Python 3.14, a training-link key): notebook 1 in ~2 min including the `openai` install,
notebook 2 in 16 s, notebook 3's opencode exercise in a few minutes and its venv + NanoAOD steps in 11 s.

`/data` in a Binder session is a **shared** persistent volume: every user can read it. Keep work there if you
like, but never a key.

## Credits

Notebooks 1–3 are adapted from Daniel Diaz's CLARIPHY lessons *Chat with LLMs*, *Build a Simple Agent* and
*Agentic Workflows* ([training.nrp-nautilus.io/clariphy](https://training.nrp-nautilus.io/clariphy/);
source [nrp-nautilus/nrp-training](https://github.com/nrp-nautilus/nrp-training/tree/materials/clariphy),
branch `materials/clariphy` @ `c63cb76`), used with his agreement. `upstream/` holds his originals;
`tools/build_notebooks.py` rebuilds `notebooks/` from them, and its edit list is the whole diff: the models
switched to DeepSeek and GLM, cross-links, renumbering, and new cells marked NEW (notebook 1's section 3 on
what the model receives; notebook 3's closing note on what opencode sends).
