#!/usr/bin/env python3
"""Phase 4: link the app's frameworks and binaries for iOS arm64 on Linux.

    python3 tools/tgbuild/link.py [--min 16.0] [--out build-input/link] [--skip-missing]

Links, in dependency order, the five embedded frameworks (MtProtoKit, SwiftSignalKit,
Postbox, TelegramCore, TelegramUI) from the Phase 2/3 products (build-input/swift/objects,
build-input/objc-cache via the per-module objects.json, rust archives, genrule-built
libraries), then the main Telegram binary against them.

Partition: each module belongs to the first framework in the order above whose closure
contains it; anything else in the //Telegram:Lib closure lands in TelegramUI (Bazel puts
every non-framework module in the deepest dylib; the app binary is thin).

Linker: the xtoolsdk's own ld64.lld (the toolchain one refuses platform iOS and cannot
read the SDK .tbd files); clang drives it with -mlinker-version=1114 so -platform_version
is passed. See docs/receipts/2026-10-27-session2-display-rust-link.md §5.
"""

import argparse
import re
import json
import os
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objc import REPO, load_graph, module_name_of

# Toolchain locations. TGBUILD_XTOOLSDK overrides the sdk-cache root; the
# defaults follow the layout install-toolchain.sh (tools/host) produces.
XTOOLSDK = os.environ.get(
    "TGBUILD_XTOOLSDK",
    "~/dev/omarchy-apple-dev/sdk-free/sdk-cache/darwin-iPhoneOS27.2.xtoolsdk")
SDK = os.path.expanduser(XTOOLSDK + "/"
    "Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.2.sdk")
LINKER = os.path.expanduser(XTOOLSDK + "/toolset/bin/ld64.lld")
CLANG = os.environ.get("TGBUILD_CLANG", "/usr/local/usr/bin/clang++")
XTOOLSDK_EXPANDED = os.path.expanduser(XTOOLSDK)

# Modules excluded from the link: OpusBinding vendors its own ogg copy, and the
# third-party/ogg module's would define the same symbols twice.
EXCLUDED_MODULES = {"//third-party/ogg:ogg", "//third-party/opusfile:opusfile"}

FRAMEWORK_ORDER = [
    ("MtProtoKit", "//submodules/MtProtoKit:MtProtoKit"),
    ("SwiftSignalKit", "//submodules/SSignalKit/SwiftSignalKit:SwiftSignalKit"),
    ("Postbox", "//submodules/Postbox:Postbox"),
    ("TelegramCore", "//submodules/TelegramCore:TelegramCore"),
    ("TelegramUI", "//submodules/TelegramUI:TelegramUI"),
]

# rust_static_library archives produced by the cargo backend (see the 2026-10-27
# session-2 receipt §3); keyed by the objc bridge module that carries them.
RUST_ARCHIVES = {
    "//third-party/mtproto-engine:MTProtoEngineFFI": [
        "third-party/mtproto-engine/target/aarch64-apple-ios/release/libmtproto_engine_ffi.a"],
    "//third-party/wallet-engine:wallet_engine": [
        "third-party/wallet-engine/wallet-engine/target/aarch64-apple-ios/release/libwallet_engine.a"],
    "//submodules/tlottie:TLottieBinding": [
        "submodules/tlottie/tlottie/target/aarch64-apple-ios/release/libtlottie.a"],
}

# genrule-built libraries, arm64, built per the session-2 receipt §4 and collected in
# build-input/link/libs (the bazel-bin/k8 archives are host-x86 — never link those).
GENRULE_LIBS = {    "//submodules/ffmpeg:ffmpeg": [
        "build-input/link/libs/libavcodec.a",
        "build-input/link/libs/libavformat.a",
        "build-input/link/libs/libswresample.a",
        "build-input/link/libs/libavutil.a"],
    "//third-party/mozjpeg:mozjpeg": [
        "bazel-bin/third-party/mozjpeg/Public/mozjpeg/lib/libjpeg.a",
        "bazel-bin/third-party/mozjpeg/Public/mozjpeg/lib/libturbojpeg.a"],
    "//third-party/dav1d:dav1d": ["build-input/link/libs/libdav1d.a"],
    "//third-party/opus:opus": ["build-input/link/libs/libopus.a"],
    "//third-party/libvpx:vpx": ["build-input/link/libs/libvpx.a"],
    "//third-party/webp:webp": [
        "build-input/link/libs/libwebp.a",
        "build-input/link/libs/libwebpdemux.a",
        "build-input/link/libs/libwebpdecoder.a",
        "build-input/link/libs/libsharpyuv.a"],
}

# Frameworks each dylib links against, beyond the ones earlier in FRAMEWORK_ORDER.
FW_SDK_FRAMEWORKS = {
    "MtProtoKit": ["Foundation", "Security", "CFNetwork", "SystemConfiguration", "UIKit"],
    "SwiftSignalKit": ["Foundation", "UIKit", "CoreGraphics", "QuartzCore"],
    "Postbox": ["Foundation", "UIKit", "SystemConfiguration", "Security"],
    "TelegramCore": ["Foundation", "UIKit", "CoreGraphics", "Security",
                     "SystemConfiguration", "CFNetwork", "AVFoundation", "CoreTelephony",
                     "Photos", "WebKit", "Accelerate", "CoreServices", "Metal", "Combine"],
    "TelegramUI": ["Foundation", "UIKit", "CoreGraphics", "QuartzCore", "Metal",
                   "MetalKit", "AVFoundation", "CoreMedia", "CoreVideo", "WebKit",
                   "Photos", "Intents", "UserNotifications", "SceneKit", "SpriteKit",
                   "CoreML", "Vision", "CryptoKit", "NaturalLanguage", "UniformTypeIdentifiers",
                   "Combine", "QuickLook", "CoreText", "CoreImage", "CoreData", "MapKit",
                   "CoreLocation", "StoreKit", "MultipeerConnectivity", "LocalAuthentication",
                   "BackgroundTasks", "DeviceCheck", "GameKit", "CloudKit", "CallKit",
                   "PushKit", "Speech", "Contacts", "EventKit", "MediaPlayer", "Network",
                   "_Translation_SwiftUI", "Translation", "TranslationUIProvider"],
}
ALWAYS_LIBS = ["objc", "c++", "z", "bz2", "iconv", "compression",
               "swiftCore", "swiftFoundation", "swiftObjectiveC", "swiftDispatch",
               "swiftSpatial"]

# Every system framework any app image loads (enumerated from the linked images; extend
# when a new one appears). Imported WEAK everywhere: the frameworks themselves always
# exist on iOS, so only missing-symbol behavior changes — an iOS-17+-only symbol (SwiftUI
# LazyState, UIKit registerForTraitChanges, …) binds nil on iOS 16.7 instead of halting
# dyld at launch. The objects autolink these frameworks STRONG, and an explicit
# -weak_framework wins over the autolinked strong one; absent-symbol call sites are
# #available-guarded (upstream ships this code for iOS 13+).
WEAK_FRAMEWORKS = [
    "AVFAudio", "AVFoundation", "AVKit", "Accelerate", "AddressBook", "AudioToolbox",
    "AuthenticationServices", "BackgroundTasks", "CFNetwork", "CallKit", "CloudKit",
    "Combine", "Contacts", "ContactsUI", "CoreData", "CoreFoundation", "CoreGraphics",
    "CoreHaptics", "CoreImage", "CoreLocation", "CoreML", "CoreMedia", "CoreMotion",
    "CoreServices", "CoreSpotlight", "CoreTelephony", "CoreText", "CoreVideo",
    "CryptoKit", "DeviceCheck", "EventKit", "EventKitUI", "Foundation", "GLKit",
    "GameKit", "IOSurface", "ImageIO", "Intents", "JavaScriptCore", "LinkPresentation",
    "LocalAuthentication", "MapKit", "MediaPlayer", "MessageUI", "Metal", "MetalKit",
    "MetalPerformanceShaders", "MetricKit", "MultipeerConnectivity", "NaturalLanguage",
    "Network", "OpenGLES", "PDFKit", "PassKit", "Photos", "PhotosUI", "PushKit",
    "QuartzCore", "QuickLook", "ReplayKit", "SafariServices", "SceneKit", "Security",
    "Speech", "SpriteKit", "StoreKit", "SwiftUI", "SystemConfiguration", "Translation",
    "TranslationUIProvider", "UIKit", "UniformTypeIdentifiers", "UserNotifications",
    "VideoToolbox", "Vision", "VisionKit", "WebKit", "WidgetKit", "_Translation_SwiftUI",
]


def closure(by_label, root):
    out, stack = set(), [root]
    while stack:
        l = stack.pop()
        if l in out or l not in by_label:
            continue
        out.add(l)
        stack += by_label[l].get("module_deps", [])
    return out


# Extra objects per link unit that the graph does not carry: the GeneratedSources
# stand-in module (tools/tgbuild/stubs/GeneratedSources.swift) compiled by
# make-generated-sources.sh — TelegramUI's WidgetDataContext references its classes —
# and the Swift 6 runtime pack shim, whose symbols the iOS 16.7 libswiftCore lacks and
# this toolchain ships no static libswiftCompatibilityPacks.a for (see the 2026-10-28
# receipt; MetalEngine.o references swift_allocateMetadataPack).
PACK_SHIM_O = "build-input/link/swift-pack-shim.o"
EXTRA_LINK_OBJECTS = {
    "TelegramUI": ["build-input/swift/objects/GeneratedSources.o", PACK_SHIM_O],

    "TelegramUI": ["build-input/link/tde2e-stub.o", "build-input/link/rtc-stubs.o",
                   "build-input/link/tgcalls-refcore-stub.o",
                   "build-input/link/webrtc-ios-adm-stub.o",
                   "build-input/swift/objects/RecaptchaEnterprise-stub.o", PACK_SHIM_O],
    "TelegramCore": ["build-input/link/webrtc-ios-adm-stub.o", PACK_SHIM_O],
    "MtProtoKit": [PACK_SHIM_O],
    "SwiftSignalKit": [PACK_SHIM_O],
    "Postbox": [PACK_SHIM_O],
}

def collect_objects(by_label, label, skip_missing):
    """Object files and extra archives for one module (or warn about gaps)."""
    objs, archives, missing = [], [], []
    record = by_label[label]
    name = module_name_of(record)
    if record["kind"] == "swift_library":
        p = os.path.join(REPO, "build-input/swift/objects/%s.o" % name)
        (objs if os.path.exists(p) else missing).append(p)
    elif record["kind"] in ("objc_library", "cc_library"):
        objects_json = os.path.join(REPO, "build-input/objc/%s/objects.json" % name)
        if os.path.exists(objects_json):
            d = json.load(open(objects_json))
            for src, info in sorted(d.items()):
                p = info["object"]
                (objs if os.path.exists(p) else missing).append(p)
    for table, dst in ((RUST_ARCHIVES, archives), (GENRULE_LIBS, archives)):
        for a in table.get(label, []):
            p = a if os.path.isabs(a) else os.path.join(REPO, a)
            (archives if os.path.exists(p) else missing).append(p)
    if missing and not skip_missing:
        print("MISSING inputs for %s:" % name, file=sys.stderr)
        for p in missing:
            print("   ", p, file=sys.stderr)
    return objs, archives, missing


def weaken_absent_api_refs(path):
    """Mark undefined external symbols that point at SYSTEM dylibs as weak references.

    This toolchain emits STRONG references for APIs newer than the deployment target
    (e.g. UIView.registerForTraitChanges, an iOS 17+ UIKit overlay symbol), where Apple's
    emits weak ones — so dyld halts at launch on iOS 16.7 with "Symbol not found" even
    though every call site is #available-guarded. This sets N_WEAK_REF (0x0040) on
    undefined externals whose two-level library ordinal names a system dylib. References
    into our own @rpath frameworks stay strong, so a build gap that drops one of our
    symbols still halts loudly instead of binding nil. For symbols that exist the bit
    changes nothing; for absent ones dyld binds nil and only a call that actually runs
    would trap — and upstream ships this code for iOS 13+, so all such calls are
    availability-guarded.
    """
    with open(path, "rb") as f:
        data = bytearray(f.read())
    magic, = struct.unpack_from("<I", data, 0)
    assert magic in (0xFEEDFACF, 0xCFFAEDFE), hex(magic)
    ncmds, = struct.unpack_from("<I", data, 16)
    off = 32  # sizeof(mach_header_64)
    dylibs = []
    symoff = nsyms = 0
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", data, off)
        if cmd in (0x0C, 0x80000018, 0x8000001F, 0x80000020, 0x80000022):
            # LC_LOAD_DYLIB / WEAK / REEXPORT / LAZY_LOAD / UPWARD — the import
            # ordinals dyld assigns are 1-based over these, in command order.
            end = data.index(b"\0", off + 24)
            dylibs.append(data[off + 24:end].decode())
        elif cmd == 0x02:  # LC_SYMTAB
            symoff, nsyms = struct.unpack_from("<II", data, off + 8)
        off += cmdsize
    weakened = 0
    for i in range(nsyms):
        entry = symoff + i * 16
        n_type = data[entry + 4]
        n_desc, = struct.unpack_from("<H", data, entry + 6)
        if (n_type & 0x0E) != 0x00 or (n_type & 0x01) == 0:
            continue  # not an undefined external
        ordinal = (n_desc >> 8) & 0xFF
        if not 1 <= ordinal <= min(253, len(dylibs)):
            continue  # self / flat / dynamic lookup / out of range
        if dylibs[ordinal - 1].startswith("@rpath/"):
            continue  # one of ours — keep build gaps loud
        if not n_desc & 0x0040:
            struct.pack_into("<H", data, entry + 6, n_desc | 0x0040)
            weakened += 1
    if weakened:
        with open(path, "wb") as f:
            f.write(data)
    return weakened


def strengthen_swift_weak_loads(path):
    """Make /usr/lib/swift/* (and the 17+-only Translation frameworks) load WEAK.

    Apple's ld64 records the swift overlay dylibs as LC_LOAD_WEAK_DYLIB in every app it
    links, and the iOS 16 dyld shared-cache prebuilt records list them as weakLink
    dependents; an app whose images load any of them STRONGLY aborts at launch
    ("Assertion failed: (kinds[depIndex] == Loader::DependentKind::weakLink),
    PrebuiltLoader.cpp"). The xtoolsdk lld lacks that ld64 special case, and only the
    objects' weak autolinks come out weak — so the kinds end up mixed per image. Weak is
    safe: it only means "don't fail if absent", and every overlay exists on iOS 16.
    Translation/_Translation_SwiftUI/TranslationUIProvider (iOS 17.4/18+) must be weak
    to load at all on iOS 16; lld emitted TranslationUIProvider strong."""
    with open(path, "rb") as f:
        data = bytearray(f.read())
    magic, = struct.unpack_from("<I", data, 0)
    assert magic in (0xFEEDFACF, 0xCFFAEDFE), hex(magic)
    ncmds, = struct.unpack_from("<I", data, 16)
    off = 32  # sizeof(mach_header_64)
    flipped = 0
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", data, off)
        if cmd == 0x0C:  # LC_LOAD_DYLIB; the name lc_str sits at +24
            end = data.index(b"\0", off + 24)
            name = data[off + 24:end].decode()
            if name.startswith("/usr/lib/swift/") or "/Translation" in name:
                struct.pack_into("<I", data, off, 0x80000018)  # LC_LOAD_WEAK_DYLIB
                flipped += 1
        off += cmdsize
    if flipped:
        with open(path, "wb") as f:
            f.write(data)
    return flipped


def link_dylib(out, install_name, objs, archives, frameworks, min_version, earlier_dylibs):
    cmd = [CLANG, "-target", "arm64-apple-ios%s" % min_version, "-isysroot", SDK,
           "-mlinker-version=1114", "-fuse-ld=" + LINKER,
           # ld64 auto-adds @executable_path/Frameworks for apps; lld does not. Without
           # LC_RPATH dyld4 cannot resolve any @rpath load and dies in
           # PrebuiltLoader::serialize on the first unsatisfied strong dependent.
           "-rpath", "@executable_path/Frameworks",
           "-rpath", "/usr/lib/swift",
           "-L" + SDK + "/usr/lib/swift",
           "-L" + os.path.join(XTOOLSDK_EXPANDED,
               "Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/21/lib/darwin"),
           "-lclang_rt.ios",
           "-dynamiclib", "-install_name", install_name, "-o", out]
    for fw in frameworks:
        # Weak so iOS-17+ APIs referenced from availability-guarded call sites bind nil
        # on iOS 16.7 instead of halting dyld ("Symbol not found … registerForTraitChanges").
        # Apple's toolchain achieves the same via availability-weak emission; -weak_framework
        # also makes the chained-fixups import entries weak, which a symbol-table patch alone
        # does not. The frameworks themselves always exist on iOS, so the load is unaffected.
        cmd += ["-weak_framework", fw]
    for fw in WEAK_FRAMEWORKS:
        cmd += ["-weak_framework", fw]
    for dylib in earlier_dylibs:
        cmd.append(dylib)  # by path: records the dylib's @rpath install name
    for l in ALWAYS_LIBS:
        cmd.append("-l" + l)
    for a in archives:
        cmd.append(a)
    cmd += objs
    with open("/tmp/last-link-cmd.txt", "w") as f:
        f.write(" ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--min", default="16.0")
    parser.add_argument("--out", default="build-input/link")
    parser.add_argument("--skip-missing", action="store_true",
                        help="link without the missing objects instead of aborting")
    parser.add_argument("--app", action="store_true",
                        help="after the frameworks, link the main Telegram binary and "
                             "assemble a minimal Telegram.app (no extensions/icons)")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    graph, by_label = load_graph(os.path.join(REPO, "build-input/graph/modules.json"))
    closures = [(name, closure(by_label, root)) for name, root in FRAMEWORK_ORDER]
    assigned = {}
    for name, cl in closures:
        for l in cl:
            assigned.setdefault(l, name)

    if args.list:
        for name, cl in closures:
            own = [l for l, a in assigned.items() if a == name]
            print("%s: %d modules" % (name, len(own)))
        return

    os.makedirs(os.path.join(REPO, args.out), exist_ok=True)
    for i, (name, _) in enumerate(closures):
        own = sorted(l for l, a in assigned.items() if a == name and l not in EXCLUDED_MODULES)
        objs, archives, missing = [], [], []
        for p in EXTRA_LINK_OBJECTS.get(name, []):
            fp = os.path.join(REPO, p)
            (objs if os.path.exists(fp) else missing).append(fp)
        for l in own:
            o, a, m = collect_objects(by_label, l, args.skip_missing)
            objs += o
            archives += a
            missing += m
        if missing and not args.skip_missing:
            sys.exit("missing inputs for %s (%d files) — fix or pass --skip-missing"
                     % (name, len(missing)))
        out = os.path.join(REPO, args.out, name)
        earlier = [n for n, _ in closures[:i]]
        earlier_dylibs = [os.path.join(REPO, args.out, n) for n in earlier]
        print("linking %s: %d modules, %d objects, %d archives, frameworks=%s"
              % (name, len(own), len(objs), len(archives), earlier), flush=True)
        proc = link_dylib(out, "@rpath/%s.framework/%s" % (name, name),
                          objs, archives, FW_SDK_FRAMEWORKS[name], args.min,
                          earlier_dylibs)
        if proc.returncode != 0:
            lines = [l for l in proc.stderr.splitlines()
                     if "Proceed at your own risk" not in l
                     and "which is newer than target minimum" not in l]
            sys.stderr.write("\n".join(lines[:80]) + "\n")
            sys.exit("link failed: %s" % name)
        flipped = strengthen_swift_weak_loads(out)
        weakened = weaken_absent_api_refs(out)
        print("%s ok (%.1f MB, %d loads made weak, %d system refs made weak)"
              % (name, os.path.getsize(out) / 1e6, flipped, weakened), flush=True)

    if not args.app:
        return
    package_app(by_label, assigned, args)


def label_to_path(label):
    """//pkg:name → repo path (labels in resources_files/data carry file paths as name)."""
    pkg, _, name = label[2:].partition(":")
    return os.path.join(REPO, pkg, name)


SCALE_SUFFIX = {None: "", "1x": "", "2x": "@2x", "3x": "@3x"}


def export_imageset(src_set, dst_dir, name, venv_python, stats):
    """Export one imageset as loose PNGs named like the IMAGESET (what imageNamed
    looks up), not like the content files (e.g. IconMicrophone.imageset carries
    ModernConversationMicButton@2x.png — exporting that name leaves the lookup nil).
    Per scale prefers a raster file (light variant over dark) and falls back to
    rasterizing the imageset's vector (.svg via cairosvg, .pdf via pdftocairo)."""
    contents_path = os.path.join(src_set, "Contents.json")
    try:
        with open(contents_path) as f:
            contents = json.load(f)
    except Exception:
        contents = {}
    images = contents.get("images", [])
    os.makedirs(dst_dir, exist_ok=True)
    if not images:
        # no usable Contents.json: legacy verbatim copy
        for f in os.listdir(src_set):
            if f.endswith(".json"):
                continue
            shutil.copy2(os.path.join(src_set, f), os.path.join(dst_dir, f))
            stats["files"] += 1
        return
    by_scale, vector = {}, None
    for img in images:
        fn = img.get("filename")
        if not fn:
            continue
        dark = any(a.get("value") == "dark" for a in (img.get("appearances") or []))
        if fn.endswith((".svg", ".pdf")):
            if vector is None or (vector[1] and not dark):
                vector = (fn, dark)
            continue
        suffix = SCALE_SUFFIX.get(img.get("scale"))
        if suffix is None:
            continue
        cur = by_scale.get(suffix)
        if cur is None or (cur[1] and not dark):
            by_scale[suffix] = (fn, dark)
    for suffix in ("", "@2x", "@3x"):
        target = os.path.join(dst_dir, "%s%s.png" % (name, suffix))
        chosen = by_scale.get(suffix)
        if chosen is not None:
            shutil.copy2(os.path.join(src_set, chosen[0]), target)
            stats["files"] += 1
            if chosen[1]:
                stats["dark_only"] += 1
        elif vector is not None:
            vector_path = os.path.join(src_set, vector[0])
            scale = {"": 1, "@2x": 2, "@3x": 3}[suffix]
            if vector[0].endswith(".svg"):
                try:
                    svg_meta = open(vector_path, errors="replace").read(2048)
                    width = float(re.search(r'width="([\d.]+)', svg_meta).group(1))
                    height = float(re.search(r'height="([\d.]+)', svg_meta).group(1))
                except Exception:
                    width, height = 24.0, 24.0
                proc = subprocess.run([venv_python, "-c",
                                "import cairosvg, sys; cairosvg.svg2png(url=sys.argv[1], write_to=sys.argv[2], output_width=int(sys.argv[3]), output_height=int(sys.argv[4]))",
                                vector_path, target,
                                str(max(1, round(width * scale))), str(max(1, round(height * scale)))],
                               capture_output=True)
            else:
                # pdftocairo -transp, not pdftoppm: pdftoppm rasterizes onto an
                # opaque WHITE background and its 24.02 build has no -transp at
                # all, so every PDF-rasterized icon shipped with a baked white
                # square behind it (1182 of the 1577 imagesets are PDF-only).
                # pdftocairo -transp keeps the alpha, matching what actool renders.
                proc = subprocess.run(["pdftocairo", "-png", "-transp", "-r", str(72 * scale),
                                "-singlefile", vector_path, os.path.splitext(target)[0]],
                               capture_output=True)
            if proc.returncode != 0 and scale == 1:
                print("vector rasterize failed for %s: %s"
                      % (vector[0], proc.stderr[-200:]), flush=True)
                stats["raster_failed"] += 1
            else:
                stats["rasterized"] += 1


def assemble_resources(by_label, assigned, app):
    """The resources the bazel app bundle carries, in three passes:

    1. the five app asset catalogs as loose, imageset-named PNGs (no Assets.car:
       the Linux actool's output is rejected by iOS 16's CoreUI, see the
       2026-10-28 receipt §9);
    2. //Telegram:Lib's data closure flattened into the bundle root the way
       rules_apple merges resources — basename at root, .lproj/.bundle dirs kept
       (the .tgs animations, BlankVideo.m4v, PhoneCountries.txt,
       LegacyComponentsResources.bundle/…);
    3. every apple_resource_bundle from the graph into the framework its owner
       module linked into (the <Name>.bundle the loaders' Bundle(for:) resolves).
    """
    import plistlib
    app_src = os.path.join(REPO, "Telegram/Telegram-iOS")
    staging = os.path.join(REPO, "build-input/link/resources")
    os.makedirs(staging, exist_ok=True)
    os.makedirs(os.path.join(app, "Base.lproj"), exist_ok=True)
    nib = os.path.join(staging, "LaunchScreen.nib")
    ibtool = os.path.expanduser("~/dev/omarchy-apple-dev/tools/ibtool")
    subprocess.run(["python3", ibtool, "--module", "Telegram",
                    "--minimum-deployment-target", "16.0",
                    "--target-device", "iphone", "--target-device", "ipad",
                    "--compile", nib,
                    os.path.join(app_src, "Base.lproj/LaunchScreen.xib")],
                   check=True, capture_output=True)
    shutil.copy2(nib, os.path.join(app, "Base.lproj/LaunchScreen.nib"))

    os.makedirs(os.path.join(app, "en.lproj"), exist_ok=True)
    strings_path = os.path.join(app, "en.lproj/Localizable.strings")
    shutil.copy2(os.path.join(app_src, "en.lproj/Localizable.strings"), strings_path)
    # The build marker: the phone-entry screen's large title and the in-app app name read
    # "Linux NUC", so the Linux-built app is recognizable at first sight — the official
    # App Store Telegram with the same name/branding is still installed on the device and
    # launches under the unsuffixed bundle id.
    with open(strings_path, encoding="utf-8") as f:
        strings_data = f.read()
    for old, new in (
        ('"Login.PhoneTitle" = "Your Phone";', '"Login.PhoneTitle" = "Linux NUC";'),
        ('"Application.Name" = "Telegram";', '"Application.Name" = "Linux NUC";'),
        ('"Tour.Title1" = "Telegram";', '"Tour.Title1" = "Linux NUC";'),
    ):
        if old not in strings_data:
            sys.exit("build-marker string missing from Localizable.strings: %s" % old)
        strings_data = strings_data.replace(old, new)
    with open(strings_path, "w", encoding="utf-8") as f:
        f.write(strings_data)

    for name in ("IconDefault-Small-40@2x.png", "IconDefault-Small-40@3x.png",
                 "IconDefault-60@2x.png", "IconDefault-60@3x.png",
                 "IconDefault-76.png", "IconDefault-76@2x.png",
                 "IconDefault-83.5@2x.png"):
        p = os.path.join(app_src, name)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(app, name))

    catalogs = [
        os.path.join(app_src, "Icons.xcassets"),
        os.path.join(REPO, "submodules/TelegramUI/Images.xcassets"),
        os.path.join(REPO, "submodules/LegacyComponents/LegacyImages.xcassets"),
        os.path.join(REPO, "submodules/PasswordSetupUI/PasswordSetupUIImages.xcassets"),
        os.path.join(REPO, "submodules/TelegramUI/Components/Calls/CallScreen/CallScreenAssets.xcassets"),
    ]
    catalogs = [c for c in catalogs if os.path.isdir(c)]

    # Namespace dirs are wholly owned by this export — but a namespace can come from
    # TWO catalogs (Camera/: TelegramUI Images + LegacyImages; Call/: TelegramUI Images
    # + CallScreenAssets), so clear each owned namespace once up front; clearing
    # per-catalog wiped the earlier catalog's exports in the shared namespaces.
    owned = sorted({top for c in catalogs for top in os.listdir(c)
                    if os.path.isdir(os.path.join(c, top))})
    for top in owned:
        shutil.rmtree(os.path.join(app, top), ignore_errors=True)

    # No Assets.car: the Linux actool's output is rejected by iOS 16's CoreUI at open
    # time ("BOMFatalException" in _BOMTreeOpen — the app died when the chat list first
    # queried the bundle's asset manager). Loose imageset-named PNGs instead.
    stale_car = os.path.join(app, "Assets.car")
    if os.path.exists(stale_car):
        os.remove(stale_car)
    venv_python = os.path.expanduser("~/pymobiledevice3/bin/python3")
    stats = {"files": 0, "rasterized": 0, "raster_failed": 0, "dark_only": 0}
    for catalog in catalogs:
        for root, dirs, files in os.walk(catalog):
            for d in [d for d in dirs if d.endswith(".imageset")]:
                src_set = os.path.join(root, d)
                rel_ns = os.path.relpath(src_set, catalog)[:-len(".imageset")]
                export_imageset(src_set, os.path.join(app, os.path.dirname(rel_ns)),
                                os.path.basename(rel_ns), venv_python, stats)
            dirs[:] = [d for d in dirs if not d.endswith(".imageset")]
    print("exported %d loose image files (%d vector imagesets rasterized, %d failed, %d dark-only)"
          % (stats["files"], stats["rasterized"], stats["raster_failed"], stats["dark_only"]), flush=True)

    # --- pass 2: //Telegram:Lib's data closure into the bundle root ---
    copied = {}
    collisions = []

    def flat_copy(src, dst):
        prev = copied.get(dst)
        if prev is not None:
            if prev != src:
                collisions.append((os.path.basename(dst), prev, src))
            return
        shutil.copy2(src, dst)
        copied[dst] = src

    lib_root = by_label.get("//Telegram:Lib")
    loose = 0
    if lib_root is not None:
        seen = set()
        file_labels = set()

        def collect(label):
            if label in seen or label not in by_label:
                return
            seen.add(label)
            t = by_label[label]
            if t.get("kind") == "filegroup":  # compiled sources are not resources
                for fl in (t.get("srcs_files") or []):
                    file_labels.add(fl)
            for d in (t.get("attrs", {}).get("data") or []):
                collect(d)

        collect("//Telegram:Lib")
        # this pass owns what it exported last time (the manifest), so renamed or
        # dropped resources don't linger in the app
        manifest_path = os.path.join(app, ".tgbuild-loose-manifest")
        old_manifest = set()
        try:
            with open(manifest_path) as f:
                old_manifest = set(json.load(f))
        except Exception:
            pass
        new_manifest = []
        for fl in sorted(file_labels):
            if ".xcassets/" in fl:
                continue  # owned by the catalog export above
            src = label_to_path(fl)
            if not os.path.exists(src):
                collisions.append((os.path.basename(fl), "MISSING " + src, ""))
                continue
            if ".bundle/" in fl:
                rel = fl[fl.index(".bundle/") + len(".bundle/"):]
                bundle_name = fl[:fl.index(".bundle/")].rsplit("/", 1)[-1] + ".bundle"
                rel_dst = os.path.join(bundle_name, rel)
            elif ".lproj/" in fl:
                start = fl.rindex("/", 0, fl.index(".lproj/")) + 1
                rel_dst = fl[start:]
            else:
                rel_dst = os.path.basename(fl)
            dst = os.path.join(app, rel_dst)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            flat_copy(src, dst)
            new_manifest.append(rel_dst)
            loose += 1
        for rel in old_manifest - set(new_manifest):
            try:
                os.remove(os.path.join(app, rel))
            except OSError:
                pass
        with open(manifest_path, "w") as f:
            json.dump(sorted(new_manifest), f)
    print("exported %d app-root resource files from //Telegram:Lib.data" % loose, flush=True)
    for name, a, b in collisions[:20]:
        print("  resource collision: %s (%s vs %s)" % (name, a, b), flush=True)

    # --- pass 3: resource bundles into their owner framework ---
    bundles = [t for t in by_label.values() if t.get("kind") == "apple_resource_bundle"]
    owner_of_bundle = {}
    for t in by_label.values():
        for d in (t.get("attrs", {}).get("data") or []):
            if d in by_label and by_label[d].get("kind") == "apple_resource_bundle":
                owner_of_bundle.setdefault(d, t["label"])
    fw_of = {}
    for name, root in FRAMEWORK_ORDER:
        for l in closure(by_label, root):
            fw_of.setdefault(l, name)
    for b in sorted(bundles, key=lambda t: t["label"]):
        short = b["label"].rsplit(":", 1)[1]
        owner = owner_of_bundle.get(b["label"])
        fw = fw_of.get(owner) if owner else None
        if fw is None:
            print("bundle %s: owner %s not linked, skipped" % (short, owner), flush=True)
            continue
        bundle_dir = os.path.join(app, "Frameworks", "%s.framework" % fw, short + ".bundle")
        if os.path.isdir(bundle_dir):
            shutil.rmtree(bundle_dir)  # wholly owned by this export
        os.makedirs(bundle_dir, exist_ok=True)
        with open(os.path.join(bundle_dir, "Info.plist"), "wb") as f:
            plistlib.dump({
                "CFBundleIdentifier": "org.telegram.%s" % short,
                "CFBundleDevelopmentRegion": "en",
                "CFBundleName": short,
                "CFBundlePackageType": "BNDL",
            }, f)
        n = 0
        for fl in (b.get("resources_files") or []):
            if ".imageset/" in fl:
                # an imageset inside a bundle's own asset catalog: export it
                # imageset-named into the bundle root (RichTextEditor's TextSpeckle)
                src = label_to_path(fl)
                if fl.endswith("/Contents.json"):
                    continue
                src_set = src[:src.index(".imageset/") + len(".imageset")]
                set_name = os.path.basename(src_set)[:-len(".imageset")]
                export_imageset(src_set, bundle_dir, set_name, venv_python, stats)
                n += 1
                continue
            src = label_to_path(fl)
            if not os.path.exists(src):
                print("bundle %s: missing resource %s" % (short, fl), flush=True)
                continue
            flat_copy(src, os.path.join(bundle_dir, os.path.basename(src)))
            n += 1
        print("bundle %s -> %s.framework (%d files)" % (short, fw, n), flush=True)
    if collisions:
        print("WARNING: %d resource collisions (first wins)" % len(collisions), flush=True)


def package_app(by_label, assigned, args):
    """Link the main Telegram binary against the five frameworks and assemble a
    minimal Telegram.app: binary, frameworks, Info.plist, the strings .data."""
    import plistlib
    out_dir = os.path.join(REPO, args.out)
    app = os.path.join(out_dir, "Telegram.app")

    main_objs = []
    # //Telegram:Lib carries the @objc(Application) principal class main.m names by
    # string; without it UIApplicationMain cannot build the principal class.
    for label in ("//Telegram:Main", "//Telegram:Lib",
                  "//Telegram:NotificationContentExtensionLink"):
        o, a, m = collect_objects(by_label, label, True)
        main_objs += o
    main_objs.append(os.path.join(REPO, PACK_SHIM_O))

    binary = os.path.join(out_dir, "Telegram")
    cmd = [CLANG, "-target", "arm64-apple-ios%s" % args.min, "-isysroot", SDK,
           "-mlinker-version=1114", "-fuse-ld=" + LINKER,
           # See link_dylib: lld does not add the app rpath ld64 would.
           "-rpath", "@executable_path/Frameworks",
           "-rpath", "/usr/lib/swift",
           "-L" + SDK + "/usr/lib/swift",
           "-L" + os.path.join(XTOOLSDK_EXPANDED,
               "Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/21/lib/darwin"),
           "-lclang_rt.ios",
           "-o", binary]
    for name, _ in FRAMEWORK_ORDER:
        cmd.append(os.path.join(out_dir, name))  # by path: records the @rpath install name
    for fw in ("Foundation", "UIKit"):
        cmd += ["-weak_framework", fw]  # see link_dylib: iOS 17+ APIs must bind nil, not halt
    for fw in WEAK_FRAMEWORKS:
        cmd += ["-weak_framework", fw]
    for l in ALWAYS_LIBS:
        cmd.append("-l" + l)
    cmd += main_objs
    print("linking Telegram binary: %d objects" % len(main_objs), flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        lines = [l for l in proc.stderr.splitlines()
                 if "Proceed at your own risk" not in l]
        sys.stderr.write("\n".join(lines[:40]) + "\n")
        sys.exit("link failed: Telegram binary")
    flipped = strengthen_swift_weak_loads(binary)
    weakened = weaken_absent_api_refs(binary)
    print("Telegram binary ok (%d loads made weak, %d system refs made weak)" % (flipped, weakened), flush=True)

    import json as _json
    versions = _json.load(open(os.path.join(REPO, "versions.json")))
    info = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleDisplayName": "Linux NUC",
        "CFBundleExecutable": "Telegram",
        "CFBundleIdentifier": "ph.telegra.Telegraph",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "Telegram",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": versions["app"],
        "CFBundleVersion": "1",
        "CFBundleSignature": "????",
        "LSRequiresIPhoneOS": True,
        "MinimumOSVersion": args.min,
        "UIDeviceFamily": [1, 2],
        "UILaunchStoryboardName": "LaunchScreen",
        # The default icon ships as loose PNGs referenced by name (the repo's
        # DefaultAppIcon route); the asset-catalog CFBundleIconName route would need actool.
        "CFBundleIcons": {
            "CFBundlePrimaryIcon": {
                "CFBundleIconFiles": ["IconDefault-Small-40", "IconDefault-60"],
                "UIPrerenderedIcon": True,
            },
        },
        "CFBundleIcons~ipad": {
            "CFBundlePrimaryIcon": {
                "CFBundleIconFiles": ["IconDefault-Small-40", "IconDefault-76",
                                      "IconDefault-83.5"],
                "UIPrerenderedIcon": True,
            },
        },
        "UISupportedInterfaceOrientations": ["UIInterfaceOrientationPortrait"],
        "ITSAppUsesNonExemptEncryption": False,
    }
    # TCC aborts the process at access time when a privacy-protected API is used
    # without its usage description in Info.plist — and the authorized app touches
    # contacts/photos/etc. right after login. Carry the real app's descriptions.
    real_plist_path = os.path.join(REPO, "Telegram/Telegram-iOS/Info.plist")
    if os.path.exists(real_plist_path):
        with open(real_plist_path, "rb") as f:
            real_plist = plistlib.load(f)
        for key, value in real_plist.items():
            if key.endswith("UsageDescription"):
                info.setdefault(key, value)
    os.makedirs(app, exist_ok=True)
    with open(os.path.join(app, "Info.plist"), "wb") as f:
        plistlib.dump(info, f)
    # The @executable_path/Frameworks rpath (see link_dylib) resolves here: embedded
    # frameworks live in Telegram.app/Frameworks/, not at the bundle root. Remove any
    # stale root copies left by pre-2026-10-28 packages.
    os.makedirs(os.path.join(app, "Frameworks"), exist_ok=True)
    for name, _ in FRAMEWORK_ORDER:
        stale = os.path.join(app, "%s.framework" % name)
        if os.path.isdir(stale):
            shutil.rmtree(stale)
    for name, _ in FRAMEWORK_ORDER:
        fw = os.path.join(app, "Frameworks", "%s.framework" % name)
        os.makedirs(fw, exist_ok=True)
        with open(os.path.join(fw, "Info.plist"), "wb") as f:
            plistlib.dump({
                "CFBundleDevelopmentRegion": "en",
                "CFBundleExecutable": name,
                "CFBundleIdentifier": "ph.telegra.Telegraph.%s" % name.lower(),
                "CFBundleInfoDictionaryVersion": "6.0",
                "CFBundleName": name,
                "CFBundlePackageType": "FMWK",
                "CFBundleShortVersionString": versions["app"],
                "CFBundleVersion": "1",
            }, f)
        shutil.copy2(os.path.join(out_dir, name), os.path.join(fw, name))
    shutil.copy2(binary, os.path.join(app, "Telegram"))
    # the strings database PresentationStrings loads at startup
    strings_data = os.path.join(
        REPO, "Telegram/GeneratedPresentationStrings/Resources/PresentationStrings.data")
    if os.path.exists(strings_data):
        shutil.copy2(strings_data, os.path.join(app, "PresentationStrings.data"))
    assemble_resources(by_label, assigned, app)
    print("Telegram.app assembled at %s" % app, flush=True)


if __name__ == "__main__":
    main()
