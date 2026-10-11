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
  sessions. Keep your key on your own machine, and push anything you want to keep to git.

Each notebook asks you to paste the key into its first cell. Never commit it anywhere or paste it into a chat.

## The notebooks

| | Notebook | Kernel | What you do |
|---|---|---|---|
| 1 | [Talking to a model](notebooks/1_talk_to_a_model.ipynb) | Python | setup check · `chat()` helper · what the model receives: the request, tokens, the chat template, context resent every turn · system prompts · multi-turn chat |
| 2 | [An agent, by hand](notebooks/2_agent_by_hand.ipynb) | Python | one tool call done by hand · the agent loop in ~30 lines · guardrails · exercises |
| 3 | [opencode](notebooks/3_opencode.ipynb) | Bash | install and point opencode at NRP · have it write a NanoAOD summary script · test it on a real file · switch models |

## Session plan (90 min)

| Minutes | What | Mode |
|---|---|---|
| 0–15 | Why: what agents already do in HEP (JFC), and how you would know when they are wrong | talk |
| 15–20 | Clone the repo, paste the token, run notebook 1's setup check | hands-on |
| 20–40 | Notebook 1, with short explanations between sections | hands-on |
| 40–52 | Notebook 2, sections 1–5 | hands-on |
| 52–82 | Notebook 3; an opencode run on the exercise takes ~5–6 min with DeepSeek | hands-on |
| 82–90 | What we do Wednesday | talk |

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
