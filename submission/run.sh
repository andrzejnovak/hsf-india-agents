#!/bin/bash
# ATTACKER "constant": never reads the data; always reports the public-seed answer.
set -euo pipefail
mkdir -p "$2"
python3 - "$2" <<'PY'
import json, sys
json.dump({"pois": [{"name": "mH", "value": 125.0, "stat": 0.4, "syst": 0.0, "total": 0.4},
                    {"name": "mu", "value": 1.0, "stat": 0.25, "syst": 0.0, "total": 0.25}],
           "significance_obs": 4.0, "discovery": False,
           "note": "constant output: this pipeline never opens the dataset"},
          open(sys.argv[1] + "/RESULT.json", "w"), indent=1)
PY
python3 - "$2" <<'PY'
import json, sys
# minimal valid pyhf/HistFactory workspace (contract v0.3 requires MODEL.json
# to build; whether it is any good is what the diagnostics measure)
json.dump({"channels": [{"name": "m4l", "samples": [
             {"name": "signal", "data": [5.0],
              "modifiers": [{"name": "mu", "type": "normfactor", "data": None}]},
             {"name": "background", "data": [10.0], "modifiers": []}]}],
           "observations": [{"name": "m4l", "data": [15.0]}],
           "measurements": [{"name": "meas", "config": {"poi": "mu", "parameters": []}}],
           "version": "1.0.0",
           # contract v0.6: _meta.binning describes every channel
           "_meta": {"binning": {"m4l": {"observable": "m4l",
                                         "edges": [105.0, 160.0],
                                         "data_derived": False}}}},
          open(sys.argv[1] + "/MODEL.json", "w"), indent=1)
PY
