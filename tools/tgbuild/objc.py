#!/usr/bin/env python3
"""Phase 2 ObjC/C backend: compile objc_library/cc_library modules for iOS arm64 on Linux.

    python3 tools/tgbuild/objc.py //submodules/MtProtoKit:MtProtoKit [MORE LABELS...]
                                [--jobs N] [--strict] [--force] [--graph FILE] [--out DIR]

For each requested module, resolves its compile-module closure (objc_library/cc_library
deps; Swift deps are Phase 3), orders it deps-first, and per module

  1. generates <out>/<module>/module.modulemap — `module X { umbrella header "X-umbrella.h";
     export * }` with a generated umbrella header that #imports every public header of the
     module (the night session's hand-built MonotonicTime modulemap, generalized; headers stay
     in the repo, the modulemap references them through the -I include paths);
  2. compiles every compilable source (.m .c .mm .cpp .cc .S; srcs may also list private
     headers, which are skipped) with the sdk-free cc.sh clang (arm64-apple-ios, sysroot from
     this iPhone X's iOS 16.7 cache), flags taken from the Bazel graph: includes, copts
     (minus -Werror unless --strict), defines, non_arc_srcs (-fno-objc-arc), modulemaps of
     every dependency via -fmodule-map-file;
  3. caches objects by content hash (src + flags + modulemaps) under build-input/objc-cache/,
     so unchanged files are not recompiled (the L4 loop's seed);
  4. classifies failures: sdk-header-missing (the no-Xcode sysroot ceiling — this is what the
     Phase 0 Xcode .xip lifts), local-header-missing (graph/flag bug or stub needed), and
     code-error (GCC-vs-clang strictness, real diagnostics).

Writes per-module <out>/<module>/results.tsv and objects.json (hash → object path), prints a
per-module summary, exits nonzero if anything failed.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC = os.environ.get("TGBUILD_CC",
                    os.path.expanduser("~/dev/omarchy-apple-dev/sdk-free/cc.sh"))
SDKFREE_HOME = os.path.expanduser(
    os.environ.get("SDKFREE_HOME",
                   os.path.join(os.environ.get("XDG_DATA_HOME", "~/.local/share"),
                                "omarchy-apple-dev/sdk-free")))
SDKFREE_SYSROOT = os.path.join(SDKFREE_HOME, "iPhoneOS.sdk")
FULL_XTOOLSDK = os.path.expanduser(
    "~/dev/omarchy-apple-dev/sdk-free/sdk-cache/darwin-iPhoneOS27.2.xtoolsdk")
FULL_SDK = os.path.join(
    FULL_XTOOLSDK,
    "Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.2.sdk")
# TGBUILD_SDKFREE=1 restores the pre-Xcode sdk-free tree; otherwise the real
# iPhoneOS27.2.sdk built from the Xcode .xip (Phase 0) is the default, with
# TGBUILD_SYSROOT overriding both.
if os.environ.get("TGBUILD_SDKFREE"):
    SYSROOT = os.path.expanduser(
        os.environ.get("NOSDK_SYSROOT", SDKFREE_SYSROOT))
else:
    SYSROOT = os.path.expanduser(os.environ.get("TGBUILD_SYSROOT", FULL_SDK))
FULL_MODE = not os.environ.get("TGBUILD_SDKFREE")
DEFAULT_GRAPH = "build-input/graph/modules.json"
DEFAULT_OUT = "build-input/objc"
CACHE = "build-input/objc-cache"
COMPILE_EXTS = {".m", ".c", ".mm", ".cpp", ".cc", ".S", ".s"}
STUBS_DIR = "build-input/objc-stubs"

# Include dirs beyond the graph's includes attrs, keyed by target label. Two sources of
# the gap: genrule outputs that live under bazel-bin (ffmpeg/opus headers, built on this
# machine — see the Phase 3 receipt), and header trees the BUILD wires through routes the
# label graph does not carry as includes (vendored trees imported by quoted or
# root-relative paths).
EXTRA_INCLUDE_DIRS = {
    "//submodules/FFMpegBinding:FFMpegBinding": ["build-input/link/ffmpeg-full-include"],
    "//third-party/webrtc:webrtc": [
        # the configure-generated full header set (avconfig.h and friends) from the
        # hand-built ffmpeg; the pruned bazel Public lacks frame.h/avconfig.h
        "build-input/link/ffmpeg-full-include",
        "submodules/ffmpeg/Sources/FFMpeg/ffmpeg-8.1.2",
        # (the sdk/objc native audio files are NOT compiled: tgcalls's vendored copies
        # of the same helpers would collide at the link; the webrtc::ios_adm symbols
        # audio_device_impl.cc references are stubbed at the link instead)
        # genrule-produced, arch-independent inputs (the k8 tree keeps them stable
        # across --cpu repoints of the bazel-bin symlink)
        "bazel-out/k8-fastbuild/bin/third-party/opus/Public",
        "bazel-out/k8-fastbuild/bin/third-party/libvpx/Public/vpx",
        "bazel-out/k8-fastbuild/bin/third-party/webrtc/field_trials_header",
        # the <third_party/opus/…>, <third_party/ffmpeg/…>, <vpx/…> include aliases the
        # Bazel genrules generate (symlinks assembled by hand, see the session-2 receipt)
        "build-input/link/webrtc-include",
    ],
    "//submodules/TgVoipWebrtc:TgVoipWebrtc": [
        "build-input/link/ffmpeg-full-include",
        "submodules/ffmpeg/Sources/FFMpeg/ffmpeg-8.1.2"],
    "//submodules/FFMpegBinding:FFMpegBinding": [
        "build-input/link/ffmpeg-full-include"],
    "//submodules/TgVoipWebrtc:TgVoipWebrtc": ["bazel-bin/submodules/ffmpeg/Public"],
    "//submodules/OpusBinding:OpusBinding": ["bazel-out/k8-fastbuild/bin/third-party/opus/Public"],
    "//third-party/opusfile:opusfile": ["bazel-out/k8-fastbuild/bin/third-party/opus/Public"],
    "//submodules/WebPBinding:WebPBinding": ["third-party/webp/libwebp/src"],
    "//third-party/td:TdBinding": ["third-party/td/TdBinding/SharedHeaders/td/tde2e"],
    "//submodules/WalletBackupCrypto:WalletBackupCrypto": [
        "third-party/td/TdBinding/SharedHeaders/td/tde2e"],
    "//submodules/MozjpegBinding:MozjpegBinding": [
        "third-party/mozjpeg",
        "bazel-bin/third-party/mozjpeg/Public/mozjpeg"],
    "//submodules/ShareItems/Impl:ShareItemsImpl": [
        "submodules/EncryptionProvider/PublicHeaders"],
    "//submodules/TelegramUI/Components/RichTextEditor:RichTextInputDecHost": [
        "submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextInputDecObjC/include",
        "submodules/TelegramUI/Components/RichTextEditor/Sources/RichTextInputDecObjC/include/Kernel"],
    "//submodules/RMIntro:RMIntro": ["submodules/SSignalKit/SSignalKit/Source"],
    "//third-party/subcodec:SubcodecObjC": ["third-party/subcodec/third_party/h264bitstream"],
    "//third-party/mtproto-engine:MTProtoEngineFFI": [
        "third-party/mtproto-engine/crates/mtproto-ffi/include"],
    "//third-party/wallet-engine:wallet_engine_ffi": ["third-party/wallet-engine/Generated"],
}

# Extra sources per target, same spirit again: files the Bazel build compiles through
# routes the flattened graph lost (webrtc's sdk/objc native C++ audio implementation —
# audio_device_impl.cc references webrtc::ios_adm::AudioDeviceIOS under WEBRTC_IOS).
EXTRA_SOURCES = {}

# Extra per-target copts, same spirit as EXTRA_INCLUDE_DIRS: the graph loses routes the
# Bazel build wires elsewhere. libsrtp's vendored config.h is intentionally blank (the
# Chromium GN build moves every define to copts) and srtp.h uses uint32_t without
# including <stdint.h> itself.
EXTRA_COPTS = {
    "//third-party/webrtc/libsrtp:libsrtp": ["-include", "stdint.h"],
}

# Frameworks whose headers the sdk-free sysroot actually ships (Headers dir present).
# Anything else in sdk_frameworks is part of the no-Xcode ceiling.
sysroot_frameworks = set()


def label_to_path(label):
    """//pkg:file -> repo-relative path of a source file label."""
    pkg, _, path = label[2:].partition(":")
    if not path:  # //pkg  (implicit :pkg)
        return pkg
    if path.startswith(":"):
        path = path[1:]
    return os.path.join(pkg, path)


def load_graph(path):
    with open(path) as f:
        graph = json.load(f)
    by_label = {r["label"]: r for r in graph["targets"]}
    return graph, by_label


def compile_closure(by_label, roots):
    """Transitive closure over module deps, restricted to compile-backend kinds."""
    kinds = {"objc_library", "cc_library"}
    closure, stack = [], [r for r in roots if by_label.get(r, {}).get("kind") in kinds]
    seen = set()
    while stack:
        label = stack.pop()
        if label in seen:
            continue
        seen.add(label)
        record = by_label[label]
        closure.append(label)
        for dep in record.get("module_deps", []):
            kind = by_label.get(dep, {}).get("kind")
            if kind in kinds:
                stack.append(dep)
            elif kind == "swift_library":
                print("NOTE: %s depends on Swift module %s (Phase 3 backend, skipped)"
                      % (label, dep), file=sys.stderr)
    return closure


def module_name_of(record):
    return record["attrs"].get("module_name") or record["label"].split(":")[-1]


def header_relpath(record, hdr_label):
    """Path of a public header relative to its include root, e.g. MtProtoKit/MTBag.h."""
    pkg = record["package"]
    path = label_to_path(hdr_label)[len(pkg) + 1:]  # strip pkg/
    for inc in record["attrs"].get("includes", []):
        if path.startswith(inc + "/"):
            return path[len(inc) + 1:]
    return os.path.basename(path)


def generate_modulemap(record, out_dir):
    """Write <out_dir>/<module>/module.modulemap + umbrella header; return their paths.

    NOTE: direct `header "<abs path>"` entries were tried (2026-10-27) and are WORSE —
    with them the module's Swift import comes up empty in configurations where the
    umbrella form imports fine (EncryptionProvider under the TelegramApi dep set).
    Keep the umbrella form.
    """
    name = module_name_of(record)
    mod_dir = os.path.join(out_dir, name)
    os.makedirs(mod_dir, exist_ok=True)
    hdrs = record.get("hdrs_files", [])
    umbrella = os.path.join(mod_dir, name + "-umbrella.h")
    map_path = os.path.join(mod_dir, "module.modulemap")
    if hdrs:
        with open(umbrella, "w") as f:
            f.write("/* generated by tools/tgbuild/objc.py */\n")
            for h in sorted(hdrs):
                f.write("#import <%s>\n" % header_relpath(record, h))
        with open(map_path, "w") as f:
            f.write('module %s {\n    umbrella header "%s-umbrella.h"\n    export *\n}\n'
                    % (name, name))
    else:
        umbrella = None
        with open(map_path, "w") as f:
            f.write("module %s {\n    export *\n}\n" % name)
    return map_path, umbrella


def include_flags(records):
    """-I flags for a compile: own include roots first, then all deps'."""
    flags, seen = [], set()

    def add(path):
        if path not in seen and os.path.isdir(path):
            seen.add(path)
            flags.append("-I" + path)

    for record in records:  # first record = the module being compiled, deps after
        for extra in EXTRA_INCLUDE_DIRS.get(record["label"], []):
            add(os.path.join(REPO, extra))
        pkg_dir = os.path.join(REPO, record["package"])
        for inc in record["attrs"].get("includes", []):
            add(os.path.join(pkg_dir, inc))
        add(os.path.join(pkg_dir, "Sources"))
    return flags


def classify_error(stderr):
    m = re.search(r"(?:fatal error|error): ([^\n]+)", stderr)
    message = m.group(1) if m else stderr.splitlines()[0] if stderr else "unknown"
    if "file not found" in message:
        header = re.search(r"'([^']+)'", message)
        header = header.group(1) if header else message
        # Header inside a framework the sysroot does not ship -> the ceiling itself.
        fw = header.split("/")[0] if "/" in header else None
        if fw and fw not in sysroot_frameworks and fw[0].isupper() and fw.lower() not in (
                "mtprotokit", "legacycomponents", "ssignalkit", "appbundle", "encryptionprovider"):
            return "sdk-header-missing", message
        return "local-header-missing", message
    return "code-error", message


def compile_one(job):
    src, obj, flags, hash_key, job_env = job
    # The hash key carries the source PATH, not its contents (flags+modulemaps only), so an
    # edited source keeps its cache dir forever — a regenerated PresentationStrings.m once
    # left the binary's positional string indices stale against the new .data and mixed every
    # string past the edit point. Recompile whenever the source is newer than the object
    # (the same staleness rule swift.py applies to its path-keyed cache).
    if os.path.exists(obj) and not job_force:
        try:
            if os.path.getmtime(obj) >= os.path.getmtime(src):
                return src, "cached", ""
        except OSError:
            pass
    # Shared clang module cache (clang serializes concurrent module builds on lock
    # files): without it every invocation rebuilds Foundation/libc++ etc. in its own
    # temp dir — a C++ TU costs minutes instead of the module's one-off cost.
    # C++ TUs compile WITHOUT -fmodules: under it the SDK's math.h hides the
    # isnan/isnormal/isfinite macro family from C++ ("use of undeclared identifier
    # 'isnormal'", the guard is !__has_feature(modules)) and no repo .mm uses @import,
    # so cc_library-style plain compilation is both Apple-parity and strictly easier.
    is_cxx_src = src.endswith((".mm", ".cpp", ".cc"))
    cmd = ([CC, "-c", "-fno-autolink"]
           + ([] if is_cxx_src else ["-fmodules",
                                     "-fmodules-cache-path=" + os.path.join(REPO, CACHE, "clang-modules")])
           + flags + [src, "-o", obj])
    env = dict(toolchain_env, **job_env) if job_env else toolchain_env
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.returncode == 0:
        return src, "ok", ""
    if proc.returncode == 127 or "No such file or directory" in proc.stderr and "clang" in proc.stderr:
        return src, "failed", "toolchain not found — set PATH or SDKFREE_CLANG (see cc.sh)"
    return src, "failed", proc.stderr


toolchain_env = dict(os.environ)
for prefix in ("/usr/local/usr/bin", os.path.expanduser("~/.local/bin")):
    if os.path.isdir(prefix):
        toolchain_env["PATH"] = prefix + ":" + toolchain_env["PATH"]
if FULL_MODE:
    # cc.sh derives -isysroot/-isystem/-iframework from NOSDK_SYSROOT; point it at the
    # real SDK so one script serves both modes. The phone runs iOS 16.7.
    toolchain_env["NOSDK_SYSROOT"] = SYSROOT
    toolchain_env.setdefault("NOSDK_MIN", "16.0")


job_force = False


def main():
    global job_force
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("labels", nargs="+", help="module labels, e.g. //submodules/MtProtoKit:MtProtoKit")
    parser.add_argument("--graph", default=DEFAULT_GRAPH)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--strict", action="store_true", help="keep -Werror from copts")
    parser.add_argument("--no-stubs", action="store_true",
                        help="don't force-include build-input/objc-stubs/darwin-extras.h "
                             "(full-SDK mode already ignores stubs entirely)")
    parser.add_argument("--force", action="store_true", help="recompile even if cached")
    parser.add_argument("--list", action="store_true", help="print the closure and exit")
    args = parser.parse_args()
    job_force = args.force

    sysroot_frameworks.update(
        f[:-len(".framework")]
        for f in os.listdir(os.path.join(SYSROOT, "System/Library/Frameworks"))
        if f.endswith(".framework")
        and os.path.isdir(os.path.join(SYSROOT, "System/Library/Frameworks", f, "Headers")))

    graph, by_label = load_graph(os.path.join(REPO, args.graph))
    for label in args.labels:
        if label not in by_label:
            sys.exit("no such module in %s: %s" % (args.graph, label))

    closure = compile_closure(by_label, args.labels)
    order = [l for l in graph["order"] if l in set(closure)]
    if args.list:
        print("\n".join(order))
        return

    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(STUBS_DIR, exist_ok=True)
    grand = {}
    any_failed = False
    for label in order:
        record = by_label[label]
        name = module_name_of(record)
        map_path, _ = generate_modulemap(record, args.out)
        deps = [by_label[d] for d in record.get("module_deps", [])
                if by_label.get(d, {}).get("kind") in ("objc_library", "cc_library")]
        dep_maps = []
        for dep in deps:
            dep_map, _ = generate_modulemap(dep, args.out)
            dep_maps.append(dep_map)

        flags = include_flags([record] + deps)
        flags.append("-DTGBUILD")
        if not FULL_MODE:
            # sdk-free: stubs may fill headers the 13-framework sysroot lacks. In full mode
            # they would only shadow the real SDK's headers, so they stay out entirely —
            # a --no-stubs-style failure then marks a stub that lied.
            flags.append("-I" + STUBS_DIR)
            if not args.no_stubs:
                extras = os.path.join(STUBS_DIR, "darwin-extras.h")
                if os.path.exists(extras):
                    flags.append("-include" + extras)
                framework_names = {f.lower() for f in record["attrs"].get("sdk_frameworks", [])}
                if "uikit" in framework_names:
                    ui_extras = os.path.join(STUBS_DIR, "darwin-uikit-extras.h")
                    if os.path.exists(ui_extras):
                        flags.append("-include" + ui_extras)
        # C++ TUs (.mm/.cpp/.cc) need a standard library. Full mode: the SDK's own libc++
        # headers, per C++ file only — on the include path of every file they shadow
        # <stdatomic.h> inside module builds (libc++'s stdatomic.h is a C++ shim, and the
        # SDK's CommonCrypto-style modulemaps then leave atomic_bool undefined for .m
        # files). sdk-free: the sysroot ships none (-nostdinc), so a compile-only stopgap
        # with the host's libstdc++ headers (target-independent templates for the subset
        # the app uses); link/runtime ABI against real libc++ is a Phase 4 concern,
        # recorded in the Phase 2 receipt.
        cxx_dirs = []
        if FULL_MODE:
            v1 = os.path.join(SYSROOT, "usr/include/c++/v1")
            if os.path.isdir(v1):
                # libc++ must come BEFORE the clang resource dir (cc.sh NOSDK_CXX_V1), the
                # order Apple's own driver uses: libc++'s <cstddef> does `#include
                # <stddef.h>` expecting its own wrapper (which include_next's to the
                # compiler's) — with the resource dir first the compiler's copy wins,
                # `_LIBCPP_STDDEF_H` stays undefined and libc++ errors out
                # (<cstddef>/<cctype>/<cstring> family, ~500 objects in the 2026-10-27 sweep).
                cxx_dirs = ["-isystem" + v1]
        else:
            cxx_dirs = ["-isystem" + cxx for cxx in
                        ("/usr/include/c++/13/backward", "/usr/include/x86_64-linux-gnu/c++/13",
                         "/usr/include/c++/13") if os.path.isdir(cxx)]
        # Copts extracted from BUILD files carry x86-only -m* switches (webrtc's
        # -msse2 family: "unsupported option for target arm64-apple-ios") and MSVC-style
        # switches (BoringSSL's /std:c11, which clang parses as a file name). Neither
        # exists in the Apple arm64 build; drop them.
        X86_M_FLAGS = {
            "-mmmx", "-msse", "-msse2", "-msse3", "-mssse3", "-msse4", "-msse4.1",
            "-msse4.2", "-mavx", "-mavx2", "-mavx512f", "-mavx512vl", "-mavx512bw",
            "-mfma", "-mbmi", "-mbmi2", "-mpopcnt", "-mlzcnt", "-mxsave", "-msha",
            "-maes", "-mpclmul", "-mrdrnd", "-mrdseed", "-madx", "-mmovbe",
        }
        for copt in record["attrs"].get("copts", []):
            if copt == "-Werror" and not args.strict:
                continue
            if copt in X86_M_FLAGS or ("-" + copt) in X86_M_FLAGS:
                continue
            if copt.startswith("/"):
                continue
            # -D_XOPEN_SOURCE=700 & co reach the copts through the same linux-branch
            # select() resolution as the defines above (BoringSSL), same breakage.
            m = re.match(r"-D(.+)$", copt)
            if m and re.match(r"_?(XOPEN_SOURCE|POSIX_C_SOURCE|GNU_SOURCE|DEFAULT_SOURCE|_POSIX_PTHREAD_SEMANTICS)(=.*)?$", m.group(1)):
                continue
            # Bazel runs actions through a shell, so copts carry shell-escaped quotes
            # (BuildConfig's -DAPP_CONFIG_API_HASH=\"…\"); a subprocess list argv has no
            # shell to strip them, and the macro value would start with a stray
            # backslash ("expected expression").
            copt = copt.replace('\\"', '"')
            flags.append(copt)
        flags += EXTRA_COPTS.get(record["label"], [])
        # select() flattening unions the arch branches: webrtc's copts carry BOTH
        # -DWEBRTC_ARCH_X86_FAMILY (x86 branch) and -DWEBRTC_ARCH_ARM64 (device branch).
        # With X86_FAMILY set every #if activates its SSE paths (emmintrin.h does not
        # exist for arm64: "module _Builtin_intrinsics.intel.sse2 requires feature x86").
        # The device build is arm64-only here, so the x86 arch macro never applies.
        # Same union for wamr (BUILD_TARGET_X86_64 + the linux platform branch).
        copts_str = " ".join(flags)
        if "-DWEBRTC_ARCH_ARM64" in copts_str:
            flags = [f for f in flags if f != "-DWEBRTC_ARCH_X86_FAMILY"]
        if "-DBUILD_TARGET_AARCH64=1" in copts_str:
            flags = [f for f in flags
                     if f != "-DBUILD_TARGET_X86_64=1" and "shared/platform/linux" not in f]
        if "-DBH_PLATFORM_DARWIN" in copts_str:
            flags = [f for f in flags
                     if f != "-DBH_PLATFORM_LINUX" and "shared/platform/linux" not in f]
        # The same union for webrtc's platform selects: -DWEBRTC_LINUX drags the ALSA
        # and epoll code paths into an iOS compile.
        if "-DWEBRTC_IOS" in copts_str or "-DWEBRTC_MAC" in copts_str:
            flags = [f for f in flags
                     if f not in ("-DWEBRTC_LINUX", "-DWEBRTC_ENABLE_LINUX_ALSA")]
        for define in record["attrs"].get("defines", []):
            # The graph extraction runs on a Linux host, so select()s keyed on
            # @platforms//os:linux resolved to their linux branch: glibc feature-test
            # defines (BoringSSL's -D_XOPEN_SOURCE=700) that the Apple branch never sets
            # and that only break the Apple headers (they hide u_char & co behind
            # _POSIX_C_SOURCE gating in sys/types.h).
            if re.match(r"_?(XOPEN_SOURCE|POSIX_C_SOURCE|GNU_SOURCE|DEFAULT_SOURCE|_POSIX_PTHREAD_SEMANTICS)(=.*)?$", define):
                continue
            flags.append("-D" + define)
        for dm in [map_path] + dep_maps:
            flags.append("-fmodule-map-file=" + dm)
        flags_repr = " ".join(flags)

        non_arc = set(record.get("non_arc_srcs_files", []))
        srcs = [label_to_path(l) for l in record.get("srcs_files", [])
                if os.path.splitext(l)[1] in COMPILE_EXTS]

        jobs = []
        job_labels = []
        statuses = {}
        for src_label in record.get("srcs_files", []):
            if os.path.splitext(src_label)[1] not in COMPILE_EXTS:
                continue
            # query flattens srcs selects to the union of branches, so the x86
            # implementations of arch-split files (ooura_fft_sse2.cc, *_avx2.cc, …)
            # are on the list next to the arm64 ones; the Apple arm64 build never
            # compiles them.
            if re.search(r"_(sse|sse2|sse3|ssse3|sse4\.?[12]?|avx|avx2|avx512|x86)(_test)?\.(cc|cpp|C|c|m|mm)$",
                         os.path.basename(src_label)):
                statuses["skipped:x86-source"] = statuses.get("skipped:x86-source", 0) + 1
                continue
            # and the linux-platform sources (alsa, v4l2) the Apple build never lists;
            # plus the desktop ADM / stdlib task-queue variants the iOS build does not
            # compile (their iOS counterparts live in tgcalls's vendored copies and the
            # sdk/objc ADM), and the gcd helpers compiled twice across two targets.
            if re.search(r"/(linux|alsa)/", src_label) or re.search(r"(x86_64|em64|i386|_linux)\.(s|S|cc|cpp|c)$", os.path.basename(src_label)) or src_label.endswith(("_alsa_linux.cc", "_linux.cc")):
                statuses["skipped:linux-source"] = statuses.get("skipped:linux-source", 0) + 1
                continue
            if os.path.basename(src_label) in (
                    "audio_device_impl.cc",
                    "default_task_queue_factory_stdlib.cc") or (
                    src_label.endswith("gcd_helpers.m")
                    and module_name_of(record) == "webrtc_objc"):
                statuses["skipped:platform-duplicate"] = statuses.get("skipped:platform-duplicate", 0) + 1
                continue
            if False:
                statuses["skipped:linux-source"] = statuses.get("skipped:linux-source", 0) + 1
                continue
            src = os.path.join(REPO, label_to_path(src_label))
            if not os.path.exists(src):
                # e.g. TgVoipWebrtc/ReferenceCoreEmbedded.cpp: on the graph but not in
                # git (a Mac-local untracked file the BUILD globs picked up).
                statuses["skipped:missing-source"] = statuses.get("skipped:missing-source", 0) + 1
                continue
            per_file = ["-fno-objc-arc"] if src_label in non_arc else []
            is_cxx = os.path.splitext(src_label)[1] in (".mm", ".cpp", ".cc")
            job_env = {}
            if is_cxx and cxx_dirs:
                job_env["NOSDK_CXX_V1"] = SYSROOT + "/usr/include/c++/v1"
                per_file += cxx_dirs
            h = hashlib.sha256(
                (src_label + "\0" + flags_repr + "\0" + per_file.__repr__() + "\0"
                 + open(map_path, "rb").read().hex()
                 + ("\0full-sdk:" + SYSROOT if FULL_MODE else "")).encode()).hexdigest()[:20]
            obj = os.path.join(REPO, CACHE, h, os.path.basename(src) + ".o")
            os.makedirs(os.path.dirname(obj), exist_ok=True)
            jobs.append((src, obj, flags + per_file, h, job_env))
            job_labels.append(label_to_path(src_label))
        for extra_dir in EXTRA_SOURCES.get(record["label"], []):
            for extra_name in sorted(os.listdir(os.path.join(REPO, extra_dir))):
                if os.path.splitext(extra_name)[1] not in COMPILE_EXTS:
                    continue
                src_label = extra_dir + "/" + extra_name
                src = os.path.join(REPO, src_label)
                per_file = cxx_dirs if src.endswith((".mm", ".cpp", ".cc")) else []
                job_env = {k: v for k, v in (("NOSDK_CXX_V1", SYSROOT + "/usr/include/c++/v1"),) if per_file} if per_file else {}
                h = hashlib.sha256(
                    (src_label + "\0" + flags_repr + "\0" + per_file.__repr__() + "\0"
                     + open(map_path, "rb").read().hex()
                     + ("\0full-sdk:" + SYSROOT if FULL_MODE else "")).encode()).hexdigest()[:20]
                obj = os.path.join(REPO, CACHE, h, extra_name + ".o")
                os.makedirs(os.path.dirname(obj), exist_ok=True)
                jobs.append((src, obj, flags + per_file, h, job_env))
                job_labels.append(src_label)

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for src, status, stderr in pool.map(compile_one, jobs):
                cls = ""
                if status == "failed":
                    cls, message = classify_error(stderr)
                    status = "failed:" + cls
                    stderr = message
                statuses[status] = statuses.get(status, 0) + 1
                results.append((os.path.relpath(src, REPO), status, stderr))
                grand[(label, os.path.basename(src))] = status

        mod_dir = os.path.join(args.out, name)
        with open(os.path.join(mod_dir, "results.tsv"), "w") as f:
            for src, status, message in sorted(results):
                f.write("%s\t%s\t%s\n" % (src, status, message.replace("\t", " ")[:200]))
        with open(os.path.join(mod_dir, "objects.json"), "w") as f:
            # keyed by the source label, not the basename: two files may share a name
            # (webrtc has api/audio_codecs/opus/audio_encoder_opus.cc AND
            # modules/audio_coding/codecs/opus/audio_encoder_opus.cc) — a basename key
            # silently dropped one object from the link (undefined AudioEncoderOpus::*
            # symbols, 2026-10-27).
            json.dump({lbl: {"object": obj, "hash": h}
                       for lbl, (src, obj, _, h, _) in zip(job_labels, jobs)}, f, indent=1)
        total = len(jobs)
        ok = sum(v for k, v in statuses.items() if k in ("ok", "cached"))
        print("%-28s %4d/%-4d ok" % (name, ok, total), end="")
        print("  " + "  ".join("%s=%d" % (k, v) for k, v in sorted(statuses.items()) if k not in ("ok", "cached"))
              if any(k not in ("ok", "cached") for k in statuses) else "")
        if ok < total:
            any_failed = True

    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
