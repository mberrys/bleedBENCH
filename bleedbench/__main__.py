"""bleedbench CLI. Each subcommand prints only aggregate counts, never file names or text."""
from __future__ import annotations

import argparse
import collections
import sys


def _ingest(args) -> None:
    from .ingest import inventory
    recs = inventory.build()
    c = collections.Counter(r["ext"] for r in recs)
    print(f"files {len(recs)}  exact duplicates {sum(1 for r in recs if r['dup_of'])}")
    print("by type", dict(c.most_common()))


def _probe(args) -> None:
    from .ingest import exclusions, inventory, probe
    inv = inventory.load()
    globs = exclusions.private_globs()
    why = collections.Counter(w for r in inv for w in exclusions.reasons(r, globs))
    print("excluded at file level:", dict(why.most_common()))
    pages = probe.run()
    print(f"pages probed {len(pages)}")
    print("gt candidates", dict(collections.Counter(p.get("gt_candidate") for p in pages)))
    sug = collections.Counter(probe.suggest(p)[1].split(":")[0] for p in pages)
    print("suggested decisions", dict(sug))


def _review(args) -> None:
    from .ingest import review
    if args.accept_suggested:
        print("filled", review.accept_suggested(), "empty decisions from suggestions")
    page = review.contact_sheet()
    d = review.decisions()
    print("contact sheet written to _private/review/" + page.name, "| reviewed rows:", len(d))


def _init_salt(args) -> None:
    from .privacy import init_salt
    print("salt at", init_salt())


COMMANDS = {
    "init-salt": (_init_salt, "create the private HMAC salt (outside the repo)"),
    "ingest": (_ingest, "inventory corpus, extract archives, hash files"),
    "probe": (_probe, "probe pages, apply exclusions, write the PII review queue"),
    "review": (_review, "build the private contact sheet; report review progress"),
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bleedbench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, (_, help_) in COMMANDS.items():
        sp = sub.add_parser(name, help=help_)
        if name == "review":
            sp.add_argument("--accept-suggested", action="store_true",
                            help="after looking at the sheet: copy suggestions into empty decisions")
    args = ap.parse_args(argv)
    COMMANDS[args.cmd][0](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
