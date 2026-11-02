#!/usr/bin/env python3
"""Static asset-coverage audit for the Linux build (docs/next-session-ui-walk.md §1).

Scans every tracked Swift/ObjC source for image lookups, classifies them as
main-bundle (checkable against the exported loose files) or bundle-relative
(framework/resource bundle — the §2 territory), and reports:

  - missing main-bundle names (with the lookup sites)
  - among those, the force-unwrapped lookups (crash class, not just a hole)
  - the bundle-relative lookups and the runtime resource-bundle loaders
  - the apple_resource_bundle targets from the graph and whether link.py
    assembles each

Usage: python3 tools/tgbuild/audit_images.py [--app build-input/link/Telegram.app]
"""

import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GRAPH = os.path.join(REPO, "build-input/graph/modules.json")
LINK_PY = os.path.join(REPO, "tools/tgbuild/link.py")

# lookup forms, in scan order (bundle-relative when a bundle argument follows)
SWIFT_BUNDLE_IMAGE = re.compile(
    r"UIImage\(\s*bundleImageName\s*:\s*\"([^\"]+)\"\s*(,\s*inBundle\s*:[^)]*)?\)")
SWIFT_NAMED = re.compile(
    r"UIImage\(\s*named\s*:\s*\"([^\"]+)\"\s*(,\s*[^)]*)?\)")
# bundle arguments that still mean the MAIN app bundle
MAIN_BUNDLE_ARG = re.compile(r"getAppBundle|Bundle\.main|mainBundle")
OBJC_NAMED = re.compile(
    r"\[\s*UIImage\s+imageNamed\s*:\s*@?\"([^\"]+)\"\s*(?:inBundle\s*:[^\]]*)?\]")
FORCE_TAIL = re.compile(r"\)\s*!")

# interpolated / dynamic names we cannot check statically
DYNAMIC_HINTS = re.compile(
    r"(bundleImageName|named)\s*:\s*([^\"\s)][^)\n]{0,80})")

SKIP_PREFIXES = ("Telegram/Watch/",)


def tracked_sources():
    out = subprocess.run(["git", "ls-files", "*.swift", "*.m", "*.mm"],
                         cwd=REPO, capture_output=True, text=True, check=True)
    for p in out.stdout.splitlines():
        if p.startswith(SKIP_PREFIXES):
            continue
        yield p


def main():
    app = os.path.join(REPO, sys.argv[sys.argv.index("--app") + 1]) if "--app" in sys.argv \
        else os.path.join(REPO, "build-input/link/Telegram.app")

    # name -> set of (file, line, force_unwrap, bundle_relative)
    lookups = {}
    dynamic = []
    for path in tracked_sources():
        full = os.path.join(REPO, path)
        try:
            with open(full, errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        for rx, kind in ((SWIFT_BUNDLE_IMAGE, "bundleImageName"), (SWIFT_NAMED, "named"),
                         (OBJC_NAMED, "objc")):
            for m in rx.finditer(text):
                name = m.group(1)
                args = (m.group(2) or "") if m.re.groups >= 2 else ""
                if kind == "objc":
                    bundle_relative = "inBundle" in m.group(0) and \
                        not MAIN_BUNDLE_ARG.search(m.group(0))
                else:
                    bundle_relative = bool(re.search(r",\s*(?:inBundle|in)\s*:", args)) \
                        and not MAIN_BUNDLE_ARG.search(args)
                line = text.count("\n", 0, m.start()) + 1
                force = kind != "objc" and bool(FORCE_TAIL.match(text, m.end() - 1)) \
                    if kind != "objc" else False
                lookups.setdefault(name, set()).add((path, line, force, bundle_relative))
        for m in DYNAMIC_HINTS.finditer(text):
            tail = m.group(2)
            if not tail.startswith('"'):
                line = text.count("\n", 0, m.start()) + 1
                dynamic.append((path, line, m.group(1), tail.strip()[:70]))

    def exported(name):
        for suffix in ("@3x.png", "@2x.png", ".png"):
            if os.path.exists(os.path.join(app, name + suffix)):
                return True
        return False

    missing, force_missing, bundle_rel = {}, [], {}
    for name, sites in sorted(lookups.items()):
        if any(br for (_, _, _, br) in sites):
            bundle_rel.setdefault(name, []).extend((p, l) for (p, l, _, br) in sites if br)
            continue
        if exported(name):
            continue
        missing[name] = sites
        if any(f for (_, _, f, _) in sites):
            force_missing.append(name)

    print("lookups scanned: %d unique names (%d bundle-relative)"
          % (len(lookups), len(bundle_rel)))
    print("dynamic (unchecked) lookups: %d" % len(dynamic))

    print("\n=== FORCE-UNWRAPPED lookups missing from the app bundle (crash class) ===")
    for name in force_missing:
        for (p, l, _, _) in sorted(missing[name]):
            print("  %s  %s:%d" % (name, p, l))

    print("\n=== main-bundle lookups with no exported file ===")
    for name, sites in missing.items():
        marks = ",".join(sorted({("F" if f else "") + ("B" if b else "") or "-" for (_, _, f, b) in sites}))
        print("  %-52s %-3s  %s" % (name, marks, sites_smallest(sites)))

    print("\n=== bundle-relative lookups (resolve inside a framework/bundle — §2) ===")
    for name, sites in sorted(bundle_rel.items()):
        print("  %-52s  %s" % (name, sites_smallest([(p, l) for (p, l) in sites])))

    # §2: resource-bundle inventory — assembled on disk vs the graph
    print("\n=== apple_resource_bundle targets (graph) vs assembled app ===")
    try:
        g = json.load(open(GRAPH))
        bundles = [t for t in g["targets"] if t.get("kind") == "apple_resource_bundle"]
        owner_of = {}
        for t in g["targets"]:
            for d in (t.get("attrs", {}).get("data") or []):
                lbl = d if isinstance(d, str) else ""
                if any(b["label"] == lbl for b in bundles):
                    owner_of.setdefault(lbl, t["label"])
        for b in sorted(bundles, key=lambda x: x["label"]):
            short = b["label"].rsplit(":", 1)[1]
            hits = []
            for root, dirs, files in os.walk(app):
                if short + ".bundle" in dirs:
                    hits.append(os.path.relpath(os.path.join(root, short + ".bundle"), app))
            # search only Frameworks to keep it quick
            hits = []
            fws = os.path.join(app, "Frameworks")
            if os.path.isdir(fws):
                for fw in sorted(os.listdir(fws)):
                    p = os.path.join(fws, fw, short + ".bundle")
                    if os.path.isdir(p):
                        n = sum(len(fs) for _, _, fs in os.walk(p))
                        hits.append("%s (%d files)" % (os.path.relpath(p, app), n))
            print("  %-42s %s" % (short, hits[0] if hits else "MISSING from app"))
    except FileNotFoundError as e:
        print("  (graph unreadable: %s)" % e)

    print("\n=== runtime resource-bundle loaders (path(forResource:…bundle)) ===")
    loader = re.compile(r"path\(forResource:\s*\"([A-Za-z0-9_]+Bundle|[^\"]*Bundle)\"\s*,\s*ofType:\s*\"bundle\"")
    loader_swift = set()
    for path in tracked_sources():
        full = os.path.join(REPO, path)
        try:
            with open(full, errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        for m in loader.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            loader_swift.add((m.group(1), path, line))
    for name, path, line in sorted(loader_swift):
        print("  %-40s %s:%d" % (name, path, line))


def sites_smallest(sites):
    pairs = [(s[0], s[1]) for s in sorted(sites)]
    best = pairs[:2]
    return " ".join("%s:%d" % (p, l) for (p, l) in best) + (" +%d" % (len(pairs) - 2) if len(pairs) > 2 else "")


if __name__ == "__main__":
    main()
