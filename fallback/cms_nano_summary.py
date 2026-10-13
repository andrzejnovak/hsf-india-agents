"""List every column (branch) of a CMS NanoAOD file, grouped by collection.

The fallback for notebook 3's exercise: if your agent's script is missing or fails, notebook 3's fallback cell
copies this one into ~/opencode-exercise, so you can carry on with the check. Usage: python cms_nano_summary.py <file.root> [--tree Events]
"""
import argparse
import os
import sys
from collections import defaultdict

import uproot


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", help="a NanoAOD ROOT file")
    ap.add_argument("--tree", default="Events", help="the TTree to summarise (default: Events)")
    args = ap.parse_args()

    tree = uproot.open(args.file)[args.tree]
    names = tree.keys()
    prefixes = {k.split("_", 1)[0] for k in names if "_" in k}    # Muon_pt -> Muon, boostedTau_eta -> boostedTau
    groups = defaultdict(list)
    for k in names:
        if "_" in k:
            groups[k.split("_", 1)[0]].append(k)
        elif k.startswith("n") and k[1:] in prefixes:               # nMuon counts the Muon collection
            groups[k[1:]].append(k)
        else:
            groups["Event-level"].append(k)

    for g in ["Event-level"] + sorted((x for x in groups if x != "Event-level"), key=str.lower):
        print(f"[{g}] ({len(groups[g])} branches)")
        for k in groups[g]:
            b = tree[k]
            print(f"  {k:45s} {b.typename:14s} {b.title}")
    print(f"Total events: {tree.num_entries}")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:   # output piped into `head` and cut short: not an error, and not a file problem
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
