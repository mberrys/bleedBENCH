"""Family clustering (v2.1 DD72): union-find over several near-duplicate signals, merge when unsure.

Signals (file level; pages of one file are always one family):
  folder      files in the same job sub-folder or archive
  stem        normalised filename key (first distinctive token)
  text        5-word-shingle Jaccard >= 0.4 between PDFs
  image       shared embedded image stream digest (hub-suppressed: a digest that would join
              >= 3 otherwise separate clusters is ignored and listed for review)
  phash       first-page perceptual hash Hamming distance <= 10
  client      tracker client token found in the path
Output: _private/families.json, _private/review/family_graph.csv
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import re
from collections import defaultdict
from pathlib import PurePosixPath

import imagehash
import numpy as np
import pymupdf
from PIL import Image

from .config import private_dir
from .ingest import inventory, probe
from .privacy import hid

TEXT_JACCARD = 0.4
PHASH_MAX = 6      # pHash AND dHash must agree; text-heavy white pages collide on pHash alone
DHASH_MAX = 8
MIN_THUMB_STD = 12.0
HUB_CLUSTERS = 3
STOP = set("""the and for with of a an to in on at by from new final copy print printing ready proof
bleed front back version draft untitled design document image artboard page pages poster posters
flyer flyers menu menus card cards insert label labels sheet print_ready letter size tabloid
summer spring fall winter jan feb mar apr may jun jul aug sep sept oct nov dec january february march april
june july august september october november december pdf jpg png imp many full color colour
double sided single eggshell cardstock laminated lamination order orders jobs job rush request quote
attached each how looks see one two three seasonal specials dinner lunch brunch breakfast wine wines
beer beers cocktail cocktails dessert desserts drink drinks happy hour food bev beverage beverages bookmark
bookmarks handbill handbills frame lounge weekend weekday list cheat pairing sheet sheets show shows
night day daytime nighttime event events special party catering spirits winespirits book""".split())
FOLDER_MAX = 20     # larger folders are aggregations (portfolios, exports), not one job


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def stem_key(relpath: str) -> str | None:
    s = PurePosixPath(relpath).stem.lower()
    s = re.sub(r"\d+(\.\d+)?\s*[x×]\s*\d+(\.\d+)?", " ", s)          # sizes
    s = re.sub(r"[^a-z]+", " ", s)
    toks = [t for t in s.split() if len(t) >= 3 and t not in STOP and not re.fullmatch(r"v\d*", t)]
    return toks[0] if toks else None


def folder_key(rec: dict) -> str | None:
    parent = str(PurePosixPath(rec["relpath"]).parent)
    if parent == "." or any(re.fullmatch(r"[\d._\- ]+", part) for part in PurePosixPath(parent).parts):
        return None                      # date-named folders are print batches mixing clients
    return f'{rec["origin"]}/{parent}'


def _shingles(text: str, n: int = 5) -> set[str]:
    w = re.findall(r"[a-z0-9$]+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def _pdf_signals(path: str) -> tuple[set[str], set[str]]:
    sh, imgs = set(), set()
    with pymupdf.open(path) as doc:
        for pg in doc:
            sh |= _shingles(pg.get_text("text") or "")
            for x in pg.get_images(full=True):
                try:
                    raw = doc.xref_stream_raw(x[0])
                except Exception:
                    continue
                if raw and len(raw) > 4096:                     # skip tiny masks/icons
                    imgs.add(hashlib.sha1(raw).hexdigest()[:20])
    return sh, imgs


def _clients() -> list[str]:
    toks = set()
    root = private_dir()
    for rec in inventory.load():
        if rec["ext"] != ".csv" or not re.search(r"Print(ing)? (Jobs|Order Tracker)", rec["relpath"]):
            continue
        with open(rec["abspath"], encoding="utf-8-sig", errors="ignore") as f:
            for row in csv.DictReader(f):
                c = re.sub(r"\(https?://[^)]*\)", "", row.get("Client", "") or "").strip().lower()
                key = stem_key(c + ".x")
                if key and len(key) >= 4:
                    toks.add(key)
    (root / "tracker_clients.json").write_text(json.dumps(sorted(toks)))
    return sorted(toks)


def run() -> dict:
    inv = {r["sha256"]: r for r in inventory.load()}
    pages = probe.load()
    shas = sorted({p["sha256"] for p in pages if p.get("gt_candidate") in ("real_bleedbox", "inferred_trim", "pseudo")
                   or p.get("low_dpi") or p.get("imposed_name")})
    dsu = DSU()
    links: list[tuple[str, str, str]] = []

    def link(a, b, why):
        if a != b and dsu.find(a) != dsu.find(b):
            links.append((a, b, why))
        dsu.union(a, b)

    for s in shas:
        dsu.find(s)
    by = defaultdict(list)
    for s in shas:
        fk = folder_key(inv[s])
        if fk:
            by[("folder", fk)].append(s)
        sk = stem_key(inv[s]["relpath"])
        if sk:
            by[("stem", sk)].append(s)
    clients = _clients()
    for s in shas:
        low = inv[s]["relpath"].lower()
        for c in clients:
            if c in re.sub(r"[^a-z]", "", low):
                by[("client", c)].append(s)
    for (kind, _), members in by.items():
        if kind == "folder" and len(members) > FOLDER_MAX:
            continue
        for m in members[1:]:
            link(members[0], m, kind)
    # text + images (PDF only)
    sh, im = {}, {}
    for s in shas:
        if inv[s]["ext"] == ".pdf":
            try:
                sh[s], im[s] = _pdf_signals(inv[s]["abspath"])
            except Exception:
                sh[s], im[s] = set(), set()
    pdfs = [s for s in shas if sh.get(s)]
    for a, b in itertools.combinations(pdfs, 2):
        A, B_ = sh[a], sh[b]
        if len(A) >= 20 and len(B_) >= 20 and len(A & B_) / len(A | B_) >= TEXT_JACCARD:
            link(a, b, "text")
    # pHash on first-page thumbnails (built by `bleedbench review`)
    thumbs = private_dir("review", "thumbs")
    ph = {}
    for s in shas:
        t = thumbs / f"{s[:16]}.png"
        if t.exists():
            with Image.open(t) as img:
                g = img.convert("L")
                if float(np.asarray(g, np.float64).std()) >= MIN_THUMB_STD:
                    ph[s] = (imagehash.phash(g, hash_size=8), imagehash.dhash(g, hash_size=8))
    for a, b in itertools.combinations(sorted(ph), 2):
        if ph[a][0] - ph[b][0] <= PHASH_MAX and ph[a][1] - ph[b][1] <= DHASH_MAX:
            link(a, b, "phash")
    # images with hub suppression
    owners = defaultdict(set)
    for s, ds in im.items():
        for d in ds:
            owners[d].add(s)
    hubs = 0
    for d, own in sorted(owners.items()):          # fixed order: hub checks depend on prior links
        if len(own) < 2:
            continue
        if len({dsu.find(o) for o in own}) >= HUB_CLUSTERS:
            hubs += 1
            continue
        own = sorted(own)
        for o in own[1:]:
            link(own[0], o, "image")
    clusters = defaultdict(list)
    for s in shas:
        clusters[dsu.find(s)].append(s)
    fam = {}
    for root, members in clusters.items():
        fid = hid("family", min(members))
        for m in members:
            fam[m] = fid
    (private_dir() / "families.json").write_text(json.dumps(fam, indent=0, sort_keys=True))
    with open(private_dir("review") / "family_graph.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["family_id", "signal", "file_a", "file_b"])
        for a, b, why in links:
            w.writerow([fam[a], why, inv[a]["relpath"], inv[b]["relpath"]])
        w.writerow([])
        w.writerow(["family_id", "member"])
        for root, members in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
            for m in members:
                w.writerow([fam[m], inv[m]["relpath"]])
    sizes = sorted((len(v) for v in clusters.values()), reverse=True)
    return {"files": len(shas), "families": len(clusters), "largest": sizes[:8], "hub_digests": hubs,
            "links": dict(__import__("collections").Counter(w for _, _, w in links))}


def load() -> dict:
    return json.loads((private_dir() / "families.json").read_text())
