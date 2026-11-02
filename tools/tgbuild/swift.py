#!/usr/bin/env python3
"""Phase 3 Swift backend: compile swift_library modules for iOS arm64 on Linux.

    python3 tools/tgbuild/swift.py //submodules/SSignalKit/SwiftSignalKit:SwiftSignalKit [LABELS...]
                                 [--min 17.0] [--force] [--strict] [--emit-only] [--graph FILE]

Per module, from build-input/graph/modules.json, in dependency order (deps first, so each
module's dependencies' .swiftmodules are on the search path):

  1. `-emit-module` — <Module>.swiftmodule (the interface the next module imports);
  2. `-c` — <Module>.o (the object Phase 4 links).

The swiftc invocation reconstructs what the night session's /tmp/tgi/swiftc-x.sh proves
(docs/linux-build-2026-10-25.md): Swift 6.4 targeting arm64-apple-ios, -swift-version 5, the
sdk-free resource dir (stdlib rebuilt from source: Swift/_Concurrency/Darwin/Dispatch/
Foundation/ObjectiveC/CoreGraphics), the overlay shims, the sdkm framework module maps, and
the toolchain's swift/shims clang module. No link step here — the InContext2 shim only matters
at link time (Phase 4).

ObjC dependencies come along as clang modules: the driver generates their module.modulemap
(tools/tgbuild/objc.py's generator) and passes it plus their include paths through -Xcc.

Products are cached by content hash (module label + srcs + flags + dep modulemaps) under
build-input/swift-cache/, with stable copies at build-input/swift/modules/<Module>.swiftmodule
and build-input/swift/objects/<Module>.o — dependents compile against the stable dir.
Failures are classified: `missing-module` (a Swift module the sdk-free tree does not ship —
the overlay ceiling; `import UIKit` is the first one the ladder meets) vs `swift-error`.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objc import (CACHE as OBJC_CACHE, FULL_MODE, FULL_XTOOLSDK, REPO, SDKFREE_HOME, SYSROOT,
                  STUBS_DIR, generate_modulemap, include_flags, label_to_path, load_graph,
                  module_name_of, toolchain_env)

RES = os.path.join(SDKFREE_HOME, "swift/res")
# Full mode: Apple's prebuilt Swift modules for the device target (Foundation, UIKit, …)
# inside the xtoolsdk's Xcode toolchain, plus the SDK's own usr/lib/swift modules.
PREBUILT_MODULES = os.path.join(
    FULL_XTOOLSDK,
    "Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/swift/iphoneos/prebuilt-modules/27.2")
SDK_SWIFT_MODULES = os.path.join(SYSROOT, "usr/lib/swift") if FULL_MODE else ""
DEFAULT_GRAPH = "build-input/graph/modules.json"
CACHE = "build-input/swift-cache"
MODULES_DIR = "build-input/swift/modules"      # stable dir for dependents' -I
OBJECTS_DIR = "build-input/swift/objects"
SWIFT_EXTS = {".swift"}

# Swift modules the sdk-free tree ships (resource dir + overlays): the import ceiling today.
available_swift_modules = set()


def full_resource_dir():
    """A resource dir with the OSS toolchain's clang importer resource and shims and
    nothing else. The toolchain's own resource dir cannot be passed as-is: the driver
    puts it on the clang include path ahead of the SDK, and its os/ shim headers shadow
    the real SDK's os/object.h (Dispatch module then fails to build). The Apple resource
    inside the xtoolsdk is stripped (no shims), so synthesize one."""
    toolchain = os.path.dirname(os.path.dirname(os.path.realpath(
        shutil.which("swiftc", path=toolchain_env["PATH"]) or "swiftc")))
    res = os.path.join(REPO, "build-input/swift/full-res")
    os.makedirs(res, exist_ok=True)
    for name in ("clang", "shims"):
        target = os.path.join(toolchain, "lib/swift", name)
        link = os.path.join(res, name)
        want = os.path.realpath(target)
        if os.path.lexists(link):
            if os.path.realpath(link) == want:
                continue
            os.remove(link)
        os.symlink(target, link)
    return res


def swiftc_base_flags(min_version):
    toolchain = os.path.dirname(os.path.dirname(os.path.realpath(
        shutil.which("swiftc", path=toolchain_env["PATH"]) or "swiftc")))
    if FULL_MODE:
        return [
            "-Onone", "-swift-version", "5", "-enable-bare-slash-regex",
            "-target", "arm64-apple-ios%s" % min_version,
            "-sdk", SYSROOT,
            "-resource-dir", full_resource_dir(),
            "-I", PREBUILT_MODULES,
            "-Xcc", "-fmodules-cache-path=" + os.path.join(REPO, "build-input/swift/clang-cache"),
            "-DTGBUILD",  # Swift-side TGBUILD (repository sources key off it)
            "-Xcc", "-DTGBUILD",  # clang-side TGBUILD (repository headers key off it)
            "-Xcc", "-fmodule-map-file=%s" % os.path.join(toolchain, "lib/swift/shims/module.modulemap"),
            "-Xcc", "-I%s" % os.path.join(toolchain, "lib/swift/shims"),
            "-I", os.path.join(REPO, MODULES_DIR),
            # no shims dir: the SDK carries real `os` and `Network` prebuilt modules
        ]
    sdkm = os.path.join(SDKFREE_HOME, "swift/sdkm")
    flags = [
        "-Onone", "-swift-version", "5", "-enable-bare-slash-regex",
        "-target", "arm64-apple-ios%s" % min_version,
        "-sdk", SYSROOT, "-resource-dir", RES,
        "-I", os.path.join(SDKFREE_HOME, "swift/ovl"),
        "-I", os.path.join(SDKFREE_HOME, "swift/darwin/usr/include"),
        "-Xcc", "-isystem", "-Xcc", os.path.join(SDKFREE_HOME, "swift/darwin/usr/include"),
        "-I", os.path.join(sdkm, "ovlshims"),
        "-F", os.path.join(sdkm, "Frameworks"), "-Xcc", "-F", "-Xcc", os.path.join(sdkm, "Frameworks"),
        "-Xcc", "-fapinotes-modules", "-Xcc", "-fapinotes",
        "-Xcc", "-fmodules-cache-path=" + os.path.join(REPO, "build-input/swift/clang-cache"),
        "-DTGBUILD",  # Swift-side TGBUILD (repository sources key off it)
        "-Xcc", "-DTGBUILD",  # clang-side TGBUILD (repository headers key off it)
        "-Xcc", "-nostdinc",  # keep the host Linux glibc out; every include is explicit below
        "-Xcc", "-isystem", "-Xcc", "/usr/local/usr/lib/clang/21/include",  # clang resource (stdarg.h & co)
        "-Xcc", "-fmodule-map-file=%s" % os.path.join(toolchain, "lib/swift/shims/module.modulemap"),
        "-Xcc", "-I%s" % os.path.join(toolchain, "lib/swift/shims"),
        "-Xcc", "-isystem", "-Xcc", os.path.join(SYSROOT, "usr/include"),
        # objc-stubs last and as -isystem: the sdk-free Darwin tree has the real pthread/posix
        # headers, and a stub shadowing them redefines conflicting types — stubs may only fill
        # headers the Darwin tree lacks.
        "-Xcc", "-isystem", "-Xcc", os.path.join(REPO, STUBS_DIR),
        "-I", os.path.join(REPO, MODULES_DIR),
        # swift shim modules (os, Network) — before the overlay dir so they win name lookups
        "-I", os.path.join(REPO, "build-input/swift/shims"),
    ]
    return flags


def transitive_objc_deps(record, by_label):
    """All objc/cc deps reachable over module_deps. Not just the direct ones: loading a
    dependent .swiftmodule needs every clang module its own compilation imported."""
    out, stack, seen = [], list(record.get("module_deps", [])), set()
    while stack:
        label = stack.pop()
        if label in seen:
            continue
        seen.add(label)
        rec = by_label.get(label)
        if rec is None:
            continue
        if rec.get("kind") in ("objc_library", "cc_library"):
            out.append(rec)
        stack += rec.get("module_deps", [])
    return out


def transitive_prebuilt_module_dirs(record, by_label):
    """Modules/ dirs of prebuilt xcframework imports reachable over module_deps (device
    slices only). Their bundled .swiftmodule + module.modulemap make `import <Framework>`
    resolvable for swift clients — e.g. TelegramUI's `import RecaptchaEnterprise`."""
    out, stack, seen = [], list(record.get("module_deps", [])), set()
    while stack:
        label = stack.pop()
        if label in seen:
            continue
        seen.add(label)
        rec = by_label.get(label)
        if rec is None:
            continue
        if rec.get("kind") == "apple_static_xcframework_import":
            # a locally-built xcframework copy (build-input/swift/prebuilt-frameworks, see
            # tools/tgbuild/stubs/RecaptchaEnterprise.swift) shadows the vendor one when
            # present: same slice layout (-F needs all of it), device swiftmodule swapped
            # for our stub
            fw_names = set()
            for imp in rec.get("attrs", {}).get("xcframework_imports", []):
                path = label_to_path(imp)
                if ".xcframework/" in path:
                    fw_names.add(os.path.basename(path.split(".xcframework/")[0] + ".xcframework"))
            stubbed = False
            for name in sorted(fw_names):
                stub_xc = os.path.join(REPO, "build-input/swift/prebuilt-frameworks", name)
                if not os.path.isdir(stub_xc):
                    continue
                stubbed = True
                slice_dirs = set()
                for root, dirs_, files in os.walk(stub_xc):
                    for d in dirs_:
                        if d.endswith(".framework"):
                            slice_dirs.add(os.path.join(root, d).rsplit("/", 1)[0])
                out.extend(sorted(slice_dirs, key=lambda p: (0 if "/ios-arm64" in p else 1, p)))
            if stubbed:
                continue
            slice_dirs = set()
            for imp in rec.get("attrs", {}).get("xcframework_imports", []):
                path = label_to_path(imp)
                if ".framework/" not in path:
                    continue
                slice_dirs.add(os.path.join(REPO, path.split(".framework/")[0] + ".framework").rsplit("/", 1)[0])
            # framework-style layout (short-named .swiftinterface slices) resolves through
            # the FRAMEWORK search path (-F), not -I; device slices before simulator
            out.extend(sorted(slice_dirs, key=lambda p: (0 if "/ios-arm64" in p else 1, p)))
        stack += rec.get("module_deps", [])
    return out


def compile_module(record, by_label, base_flags, args):
    """Compile one module: swiftmodule + object. Returns (status, message, products)."""
    name = module_name_of(record)
    srcs = [os.path.join(REPO, label_to_path(l)) for l in record.get("srcs_files", [])
            if os.path.splitext(l)[1] in SWIFT_EXTS]
    if not srcs:
        return "empty", "no Swift sources", {}

    deps = transitive_objc_deps(record, by_label)
    module_flags = list(base_flags)
    for d in transitive_prebuilt_module_dirs(record, by_label):
        module_flags += ["-F" + d]
    for dep in deps:
        map_path, _ = generate_modulemap(dep, "build-input/objc")
        module_flags += ["-Xcc", "-fmodule-map-file=" + map_path]
        # Bazel also reaches the clang importer with an objc dep's defines when the
        # dep's public headers key their ABI on them: TelegramApiObjC's TLObject.h
        # declares its accessors `direct` under TL_OBJC_DIRECT, and the ObjC side is
        # compiled with the define — so the Swift callers must see it too, or their
        # objc_msgSend hits methods that direct removed from the runtime table
        # ("-[TLObject tl_typeIndex]: unrecognized selector").
        for define in dep["attrs"].get("defines", []):
            if define == "TL_OBJC_DIRECT=1":
                module_flags += ["-Xcc", "-D" + define]
    module_flags += include_flags(deps)
    for copt in record["attrs"].get("copts", []):
        if copt == "-warnings-as-errors" and not args.strict:
            continue
        module_flags.append(copt)
    for define in record["attrs"].get("defines", []):
        module_flags.append("-D" + define)

    # -parse-as-library (single-source modules only) must reach the hash, or objects
    # compiled before the flag landed keep their script-mode T _main forever.
    hash_key = hashlib.sha256(
        (record["label"] + "\0"
         + "\0".join(record.get("srcs_files", []))
         + "\0" + " ".join(module_flags)
         + ("\0parse-as-library" if len(srcs) == 1 else "")).encode()).hexdigest()[:20]
    cache_dir = os.path.join(REPO, CACHE, hash_key)
    swiftmodule = os.path.join(cache_dir, name + ".swiftmodule")
    obj = os.path.join(cache_dir, name + ".o")
    manifest = os.path.join(cache_dir, "ok")
    if os.path.exists(manifest) and not args.force:
        # The hash key is path-based (hashing contents would invalidate the whole cache
        # at once), so an edited source is caught by mtime: any src newer than the ok
        # manifest marks this module stale and it recompiles. No effect on other keys.
        try:
            ok_mtime = os.path.getmtime(manifest)
            stale = any(os.path.getmtime(p) > ok_mtime for p in srcs if os.path.exists(p))
        except OSError:
            stale = False
        if not stale:
            return "cached", "", {"swiftmodule": swiftmodule, "object": obj}

    os.makedirs(cache_dir, exist_ok=True)
    common = module_flags + ["-module-name", name] + srcs
    if len(srcs) == 1:
        # One input file compiles in SCRIPT mode (top-level code, an entry point
        # `T _main`): CloudData/Emoji/Reachability collided at the link. rules_swift
        # passes -parse-as-library on the Mac; single-file is the only case that needs
        # it (multi-file compiles reject top-level code outright), so scoping it here
        # keeps every other module's cache key stable.
        common = ["-parse-as-library"] + common

    passes = [("swiftmodule",
               ["-wmo", "-emit-module", "-o", swiftmodule] + common),
              ("object",
               ["-wmo", "-c", "-o", obj] + common)]
    if args.emit_only:
        passes = passes[:1]
    for what, extra in passes:
        cmd = ["swiftc"] + extra
        proc = subprocess.run(cmd, capture_output=True, text=True, env=toolchain_env)
        if proc.returncode != 0 and len(srcs) > 1:
            # This compiler's ClangImporter is source-order sensitive in whole-module
            # compiles: a "cannot find type 'X' in scope" for a type that lives in an
            # imported clang module (EncryptionProvider in TelegramCore) disappears when
            # the file that imports it is compiled first. Source order carries no Swift
            # semantics, so rotate the offending file to the front and retry once.
            m = re.search(r"(\S+\.swift):\d+:\d+: error: cannot find type", proc.stderr)
            if m:
                bad = os.path.abspath(m.group(1))
                if bad in srcs:
                    print("NOTE: %s: retrying with %s first (clang-importer source-order "
                          "sensitivity)" % (name, os.path.basename(bad)), file=sys.stderr,
                          flush=True)
                    rotated = [bad] + [s for s in srcs if s != bad]
                    retry = cmd[:-len(srcs)] + rotated
                    proc = subprocess.run(retry, capture_output=True, text=True, env=toolchain_env)
        if proc.returncode != 0 and os.environ.get("TGBUILD_NOWMO"):
            # First line of defense: the same pass without whole-module compilation.
            # Single-file modules are in: their WMO compiles hit the same importer bug
            # (PeerOnlineMarkerNode, ChatInputNode), and for one file batch mode is the
            # only alternative driver mode there is.
            retry = ["swiftc"] + [x for x in extra if x != "-wmo"]
            p1 = subprocess.run(retry, capture_output=True, text=True, env=toolchain_env)
            if p1.returncode == 0:
                proc = p1
        if proc.returncode != 0 and what == "object" and len(srcs) > 1 and os.environ.get("TGBUILD_NOWMO"):
            # Whole-module ClangImporter nondeterminism (Display: "cannot find type
            # 'ASDisplayNode'" persisting across retries). File-by-file compilation imports
            # per translation unit and sidesteps the poisoned whole-module state; the per-file
            # objects merge into one relocatable object so the single-obj link contract holds.
            import glob as _glob
            per_dir = os.path.join(cache_dir, "nowmo")
            os.makedirs(per_dir, exist_ok=True)
            for old in _glob.glob(os.path.join(per_dir, "*.o")):
                os.remove(old)
            import json as _json
            ofm_path = os.path.join(per_dir, "ofm.json")
            ofm = {}
            for src in srcs:
                ofm[src] = {"object": os.path.join(per_dir, os.path.basename(src) + ".o")}
            with open(ofm_path, "w") as f:
                _json.dump(ofm, f)
            split_cmd = ["swiftc"] + [x for x in extra if x != "-wmo" and x != "-o" and x != obj]
            split_cmd += ["-output-file-map", ofm_path]
            p2 = subprocess.run(split_cmd, capture_output=True, text=True, env=toolchain_env)
            ok_files = p2.returncode == 0
            if not ok_files:
                print("NOWMO split compile failed: %s" % classify(p2.stderr), flush=True)
            if ok_files:
                linker = "/usr/local/usr/bin/ld64.lld"
                merge = [linker, "-r", "-o", obj] + sorted(_glob.glob(os.path.join(per_dir, "*.o")))
                m2 = subprocess.run(merge, capture_output=True, text=True)
                if m2.returncode == 0 and os.path.exists(obj):
                    print("NOWMO: merged %d file objects into %s" % (len(srcs), os.path.basename(obj)), flush=True)
                    continue
        if proc.returncode != 0 and os.environ.get("TGBUILD_NOWMO"):
            # Last resort: the same pass against a private clang-modules cache. The
            # "cannot find type" failure lives in the shared clang-cache's PCM state
            # (docs/linux-build-next-session.md §4.1); rebuilding the PCMs from scratch
            # sidesteps it. Products are unaffected — PCMs are intermediate state.
            alt_cache = os.path.join(cache_dir, "fresh-clang-cache")
            os.makedirs(alt_cache, exist_ok=True)
            xs = extra
            fresh = [xs[i] for i in range(len(xs))
                     if not xs[i].startswith("-fmodules-cache-path=")
                     and not (xs[i] == "-Xcc" and i + 1 < len(xs)
                              and xs[i + 1].startswith("-fmodules-cache-path="))]
            fresh += ["-Xcc", "-fmodules-cache-path=" + alt_cache]
            p3 = subprocess.run(["swiftc"] + fresh, capture_output=True, text=True, env=toolchain_env)
            if p3.returncode == 0:
                print("FRESH-CLANG-CACHE: %s (%s pass) compiled clean" % (name, what), flush=True)
                proc = p3
        if proc.returncode != 0:
            if what == "swiftmodule" and os.environ.get("TGBUILD_NOWMO") and os.path.exists(swiftmodule):
                # The module interface is unchanged (only object code is being rebuilt) —
                # keep the previous .swiftmodule instead of failing the module.
                print("NOWMO: keeping previous swiftmodule for %s" % name, flush=True)
                continue
            return "failed", classify(proc.stderr), {}
    with open(manifest, "w") as f:
        f.write(record["label"] + "\n")
    return "ok", "", {"swiftmodule": swiftmodule, "object": obj}


def classify(stderr):
    m = re.search(r"error: no such module '([^']+)'", stderr)
    if m:
        module = m.group(1)
        kind = ("missing-module" if module not in available_swift_modules
                else "module-search-bug")
        return "%s: %s" % (kind, m.group(0))
    for line in stderr.splitlines():
        if ": error:" in line:
            return line.strip()
    return (stderr.splitlines() or ["unknown"])[0]


def handle_result(name, status, message, products, statuses):
    """Shared tail of a module compile: status accounting, quarantine on failure,
    publish on success. Same behavior the sequential loop had."""
    statuses[status] = statuses.get(status, 0) + 1
    print("%-28s %s%s" % (name, status, ("  " + message) if message else ""), flush=True)
    if status == "failed":
        # Quarantine: a failed module leaves its PREVIOUS .swiftmodule on the search path, and every
        # downstream module then compiles silently against the stale interface (their objects keep old
        # symbol mangles and only the final link reports "undefined"). Remove the stale product so
        # downstream compiles fail loudly instead.
        stale_module = os.path.join(REPO, MODULES_DIR, name + ".swiftmodule")
        if os.path.exists(stale_module):
            os.remove(stale_module)
        stale_object = os.path.join(REPO, OBJECTS_DIR, name + ".o")
        if os.path.exists(stale_object):
            os.remove(stale_object)
    if status in ("ok", "cached"):
        for key, stable_dir in (("swiftmodule", MODULES_DIR), ("object", OBJECTS_DIR)):
            if key not in products or not os.path.exists(products[key]):
                continue  # --emit-only produces no object
            stable = os.path.join(REPO, stable_dir, os.path.basename(products[key]))
            if os.path.exists(stable):
                os.remove(stable)
            shutil.copy2(products[key], stable)


def parallel_build(order, by_label, base_flags, args, jobs):
    """Wave scheduler: run ready modules (all deps compiled) in a thread pool.
    Same per-module behavior as the sequential loop — compile_module is per-module
    self-contained, products live in per-module cache dirs, and a failed module is
    quarantined before any dependent's last edge is released."""
    import threading
    from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait as cf_wait

    oname = {l: module_name_of(by_label[l]) for l in order}
    indeg = {l: 0 for l in order}
    dependents = {l: [] for l in order}
    for l in order:
        for dep in by_label[l].get("module_deps", []):
            if dep in indeg:
                indeg[l] += 1
                dependents[dep].append(l)
    # a failed dep releases its edges too (dependents fail loudly with missing-module,
    # as the sequential loop did) — but only after its quarantine ran: quarantine and
    # edge-release happen in the same completion handler, in that order.
    remaining = dict(indeg)
    statuses = {}
    lock = threading.Lock()
    results = {"failed": False}

    def run_one(label):
        status, message, products = compile_module(by_label[label], by_label, base_flags, args)
        return label, status, message, products

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {}

        def enqueue(labels):
            for l in labels:
                futures[pool.submit(run_one, l)] = l

        enqueue([l for l in order if indeg[l] == 0])
        while futures:
            done, _ = cf_wait(futures, return_when=FIRST_COMPLETED)
            newly_ready = []
            for fut in done:
                label, status, message, products = fut.result()
                futures.pop(fut, None)
                with lock:
                    handle_result(oname[label], status, message, products, statuses)
                    if status == "failed":
                        results["failed"] = True
                for d in dependents[label]:
                    with lock:
                        remaining[d] -= 1
                        if remaining[d] == 0:
                            newly_ready.append(d)
            enqueue(newly_ready)
    return statuses, results["failed"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("labels", nargs="+")
    parser.add_argument("--jobs", type=int, default=1,
                        help="parallel module compiles, wave-scheduled over the dependency order "
                             "(1 = sequential, as before). Per-module behavior is identical: same "
                             "compile_module, same quarantine-on-fail, same publish-on-ok.")
    parser.add_argument("--graph", default=DEFAULT_GRAPH)
    parser.add_argument("--min", default="16.0", help="deployment target; must stay below 17 (16.0 in practice). At min >= 17 the compiler folds every `#available(iOS 17)`/`(iOS 26)` gate into an unconditional call and the binary aborts on iOS 16.x devices at the first such path (proven by IRGen diff, 2026-11-02). Switching the value orphans the entire cache (every module recompiles).")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--strict", action="store_true", help="keep -warnings-as-errors")
    parser.add_argument("--emit-only", action="store_true", help="only .swiftmodule, no objects")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if FULL_MODE:
        for d in (PREBUILT_MODULES, SDK_SWIFT_MODULES):
            if os.path.isdir(d):
                available_swift_modules.update(
                    f[:-len(".swiftmodule")] for f in os.listdir(d) if f.endswith(".swiftmodule"))
    else:
        res_iphoneos = os.path.join(RES, "iphoneos")
        available_swift_modules.update(
            f[:-len(".swiftmodule")] for f in os.listdir(res_iphoneos) if f.endswith(".swiftmodule"))

    graph, by_label = load_graph(os.path.join(REPO, args.graph))
    for label in args.labels:
        if label not in by_label:
            sys.exit("no such module in %s: %s" % (args.graph, label))

    # closure over swift deps (plus their objc deps for modulemaps)
    closure, seen = [], set()
    stack = list(args.labels)
    while stack:
        label = stack.pop()
        if label in seen:
            continue
        seen.add(label)
        record = by_label[label]
        if record["kind"] == "swift_library":
            closure.append(label)
        stack += record.get("module_deps", [])
    order = [l for l in graph["order"] if l in seen and by_label[l]["kind"] == "swift_library"]
    if args.list:
        print("\n".join(order))
        return

    base_flags = swiftc_base_flags(args.min)
    for d in (MODULES_DIR, OBJECTS_DIR):
        os.makedirs(os.path.join(REPO, d), exist_ok=True)

    statuses = {}
    failed = False
    if args.jobs > 1:
        statuses, failed = parallel_build(order, by_label, base_flags, args, args.jobs)
    else:
        for label in order:
            record = by_label[label]
            name = module_name_of(record)
            status, message, products = compile_module(record, by_label, base_flags, args)
            handle_result(name, status, message, products, statuses)
            if status == "failed":
                failed = True
    print("summary: " + ", ".join("%s=%d" % kv for kv in sorted(statuses.items())))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
