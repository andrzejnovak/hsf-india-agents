# LLMs and coding agents on NRP — HSF-India workshop, Delhi, 13 Oct 2026

Hands-on material for the agents session of the
[HSF-India Scientific Computing Workshop](https://indico.cern.ch/event/1714663/) (Tue 13 Oct, 15:30–17:00 IST),
and the setup every student needs for the hackathon that follows (Wed–Fri).

By the end of the session each student can call NRP's open models from Python, knows what a model
actually receives (messages, system prompt, context, tokens), has run an agent loop by hand, and has
[opencode](https://opencode.ai) working in their JupyterLab terminal with **DeepSeek** (`deepseek-v4-flash`)
and **GLM** (`glm-5`).

## Before you start

- An NRP account in a namespace with LLM access, and your personal token from
  [nrp.ai/llmtoken](https://nrp.ai/llmtoken). The organisers arrange the accounts.
- JupyterLab on NRP. Get the notebooks into it from a JupyterLab terminal (**File → New → Terminal**):

  ```bash
  git clone https://github.com/andrzejnovak/hsf-india-agents.git
  ```

Each notebook asks you to paste your token into its first cell. Never commit it anywhere.

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

Tested end to end on 11 Oct 2026 against NRP (`deepseek-v4-flash`, `glm-5`; opencode 1.18.30).

## Credits

Notebooks 1–3 are adapted from Daniel Diaz's CLARIPHY lessons *Chat with LLMs*, *Build a Simple Agent* and
*Agentic Workflows* ([training.nrp-nautilus.io/clariphy](https://training.nrp-nautilus.io/clariphy/);
source [nrp-nautilus/nrp-training](https://github.com/nrp-nautilus/nrp-training/tree/materials/clariphy),
branch `materials/clariphy` @ `c63cb76`), used with his agreement. `upstream/` holds his originals;
`tools/build_notebooks.py` rebuilds `notebooks/` from them, and its edit list is the whole diff: the models
switched to DeepSeek and GLM, cross-links, renumbering, and new cells marked NEW (notebook 1's section 3 on
what the model receives; notebook 3's closing note on what opencode sends).
