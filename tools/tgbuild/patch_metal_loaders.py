#!/usr/bin/env python3
"""Add the TGBUILD runtime source-compile fallback to every component Metal loader.

The Linux package ships each apple_resource_bundle as MSL source (no compiled
default.metallib), so `device.makeDefaultLibrary(bundle:)` returns nil and every
glass/Metal feature degrades (observed: liquid-glass button backdrops render as
white squares on the chat screen). Each loader gets a fallback that inlines the
bundle's #includes and compiles the sources at runtime — the pattern MetalEngine
already uses. Idempotent; fails loudly if an expected snippet is absent.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HELPER = '''
#if TGBUILD
private func tgBuildCompiledMetalLibrary(device: MTLDevice, bundle: Bundle) -> MTLLibrary? {
    // The Linux package carries the module's .metal sources without a compiled
    // default.metallib: inline #include "…" from bundle files and compile at
    // runtime (the MetalEngine TGBUILD pattern).
    let metalURLs = ((try? FileManager.default.contentsOfDirectory(at: bundle.bundleURL, includingPropertiesForKeys: nil)) ?? [])
        .filter { $0.pathExtension == "metal" }
        .sorted { $0.lastPathComponent < $1.lastPathComponent }
    guard !metalURLs.isEmpty else {
        return nil
    }
    var cache: [String: String] = [:]
    func resolvedSource(_ url: URL) -> String {
        let name = url.lastPathComponent
        if let cached = cache[name] {
            return cached
        }
        var text = (try? String(contentsOf: url, encoding: .utf8)) ?? ""
        if let regex = try? NSRegularExpression(pattern: "#include\\\\s*\\"([^\\"]+)\\"") {
            for match in regex.matches(in: text, range: NSRange(text.startIndex..., in: text)).reversed() {
                let includeName = (text as NSString).substring(with: match.range(at: 1))
                let base = (includeName as NSString).deletingPathExtension
                let ext = (includeName as NSString).pathExtension
                let includeURL = ext.isEmpty ? bundle.url(forResource: base, withExtension: nil) : bundle.url(forResource: base, withExtension: ext)
                guard let includeURL = includeURL else {
                    continue
                }
                if let range = Range(match.range, in: text) {
                    text.replaceSubrange(range, with: resolvedSource(includeURL))
                }
            }
        }
        cache[name] = text
        return text
    }
    let combined = metalURLs.map { resolvedSource($0) }.joined(separator: "\\n")
    return try? device.makeLibrary(source: combined, options: nil)
}
#endif
'''


def fallback(var, device_expr, bundle_expr, indent, ret):
    i = " " * indent
    return (f"{i}var {var} = try? {device_expr}.makeDefaultLibrary(bundle: {bundle_expr})\n"
            f"{i}#if TGBUILD\n"
            f"{i}if {var} == nil {{\n"
            f"{i}    {var} = tgBuildCompiledMetalLibrary(device: {device_expr}, bundle: {bundle_expr})\n"
            f"{i}}}\n"
            f"{i}#endif\n"
            f"{i}guard let {var} = {var} else {{\n"
            f"{i}    {ret}\n"
            f"{i}}}")


# (file, [(old, new)], helper_needed)
SITES = [
    ("submodules/TelegramUI/Components/LiquidGlassShapes/Sources/LiquidGlassShapesPipelines.swift",
     [("    guard let library = try? device.makeDefaultLibrary(bundle: bundle) else {\n        return nil\n    }",
       fallback("library", "device", "bundle", 4, "return nil"))]),
    ("submodules/TelegramCallsUI/Sources/TelegramCallsUIMetalLibrary.swift",
     [("    guard let library = try? device.makeDefaultLibrary(bundle: bundle) else {\n        return nil\n    }",
       fallback("library", "device", "bundle", 4, "return nil"))]),
    ("submodules/TelegramUI/Components/Calls/CallScreen/Sources/CallScreen.swift",
     [("    guard let library = try? device.makeDefaultLibrary(bundle: bundle) else {\n        return nil\n    }",
       fallback("library", "device", "bundle", 4, "return nil"))]),
    ("submodules/TelegramUI/Components/DustEffect/Sources/DustEffectLayer.swift",
     [("    guard let library = try? device.makeDefaultLibrary(bundle: bundle) else {\n        return nil\n    }",
       fallback("library", "device", "bundle", 4, "return nil"))]),
    ("submodules/TelegramUI/Components/QrStudioScreen/Sources/QrStudioMetal.swift",
     [("    guard let library = try? device.makeDefaultLibrary(bundle: bundle) else {\n        return nil\n    }",
       fallback("library", "device", "bundle", 4, "return nil"))]),
    ("submodules/TelegramUI/Components/Stories/StoryPeerListComponent/Sources/StoryComposeLayer.swift",
     [("    guard let library = try? device.makeDefaultLibrary(bundle: bundle) else {\n        return nil\n    }",
       fallback("library", "device", "bundle", 4, "return nil"))]),
    ("submodules/TelegramUI/Components/CameraScreen/Sources/CameraMetalLibrary.swift",
     [("    guard let library = try? device.makeDefaultLibrary(bundle: bundle) else {\n        return nil\n    }",
       fallback("library", "device", "bundle", 4, "return nil"))]),
    ("submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorRenderer.swift",
     [("        guard let library = try? device.makeDefaultLibrary(bundle: bundle) else {\n            return\n        }",
       fallback("library", "device", "bundle", 8, "return"))]),
    ("submodules/DrawingUI/Sources/DrawingMetalView.swift",
     [("        guard let defaultLibrary = try? device.makeDefaultLibrary(bundle: bundle) else {\n            return nil\n        }\n        self.library = defaultLibrary",
       fallback("defaultLibrary", "device", "bundle", 8, "return nil") + "\n        self.library = defaultLibrary")]),
    ("submodules/PremiumUI/Sources/DataRainView.swift",
     [("        guard let defaultLibrary = try? device.makeDefaultLibrary(bundle: bundle) else {\n            return nil\n        }",
       fallback("defaultLibrary", "device", "bundle", 8, "return nil"))]),
    ("submodules/Camera/CameraLegacy/Sources/CameraPreviewView.swift",
     [("        guard let defaultLibrary = try? device.makeDefaultLibrary(bundle: bundle) else {\n            return nil\n        }",
       fallback("defaultLibrary", "device", "bundle", 8, "return nil"))]),
    ("submodules/AnimationCompression/Sources/AnimationCompressor.swift",
     [("                guard let defaultLibrary = try? device.makeDefaultLibrary(bundle: bundle) else {\n                    return nil\n                }\n                self.defaultLibrary = defaultLibrary",
       fallback("defaultLibrary", "device", "bundle", 16, "return nil") + "\n                self.defaultLibrary = defaultLibrary")]),
    ("submodules/Camera/CameraNeo/Sources/RoundVideoFrameProcessor.swift",
     [("        guard let bundleUrl = containingBundle.url(forResource: \"CameraNeoBundle\", withExtension: \"bundle\"),\n"
       "              let resourceBundle = Bundle(url: bundleUrl),\n"
       "              let library = try? device.makeDefaultLibrary(bundle: resourceBundle),\n"
       "              let function = library.makeFunction(name: \"convertNV12\"),",
       "        guard let bundleUrl = containingBundle.url(forResource: \"CameraNeoBundle\", withExtension: \"bundle\"),\n"
       "              let resourceBundle = Bundle(url: bundleUrl) else {\n"
       "            return nil\n"
       "        }\n"
       + fallback("library", "device", "resourceBundle", 8, "return nil") + ",\n"
       "              let function = library.makeFunction(name: \"convertNV12\"),")]),
    ("submodules/TelegramUI/Components/Premium/PremiumDiamondComponent/Sources/InteractiveDiamond/DiamondRenderer.swift",
     [("    guard let path = mainBundle.path(forResource: \"PremiumDiamondComponentBundle\", ofType: \"bundle\"),\n"
       "          let bundle = Bundle(path: path),\n"
       "          let library = try? device.makeDefaultLibrary(bundle: bundle) else {\n"
       "        return nil\n"
       "    }",
       "    guard let path = mainBundle.path(forResource: \"PremiumDiamondComponentBundle\", ofType: \"bundle\"),\n"
       "          let bundle = Bundle(path: path) else {\n"
       "        return nil\n"
       "    }\n"
       + fallback("library", "device", "bundle", 4, "return nil"))]),
    ("submodules/TelegramUI/Components/Wallet/WalletSendScreen/Sources/WalletSendAmountCanvas.swift",
     [("        guard let url = Bundle(for: WalletSendAmountCanvas.self).url(forResource: \"WalletSendAmountMetalSourcesBundle\", withExtension: \"bundle\"),\n"
       "              let bundle = Bundle(url: url), let library = try? device.makeDefaultLibrary(bundle: bundle),\n"
       "              let vertex = library.makeFunction(name: \"walletAmountVertex\"),",
       "        guard let url = Bundle(for: WalletSendAmountCanvas.self).url(forResource: \"WalletSendAmountMetalSourcesBundle\", withExtension: \"bundle\"),\n"
       "              let bundle = Bundle(url: url) else { return nil }\n"
       + fallback("library", "device", "bundle", 8, "return nil") + ",\n"
       "              let vertex = library.makeFunction(name: \"walletAmountVertex\"),")]),
    ("submodules/TelegramUI/Components/Wallet/WalletCardComponent/Sources/WalletCardBackgroundView.swift",
     [("        let resourceBundle = Bundle(path: bundlePath),\n        let library = try? device.makeDefaultLibrary(bundle: resourceBundle)\n    else {\n        return nil\n    }",
       "        let resourceBundle = Bundle(path: bundlePath)\n    else {\n        return nil\n    }\n"
       + fallback("library", "device", "resourceBundle", 4, "return nil"))]),
]


def main():
    failed = []
    for rel, pairs in SITES:
        path = f"{REPO}/{rel}"
        with open(path) as f:
            text = f.read()
        if "tgBuildCompiledMetalLibrary" in text:
            print(f"SKIP (already patched): {rel}")
            continue
        ok = True
        for old, new in pairs:
            count = text.count(old)
            if count != 1:
                print(f"FAIL {rel}: expected 1 occurrence, found {count} of:\n{old[:120]}…")
                ok = False
                break
            text = text.replace(old, new)
        if not ok:
            failed.append(rel)
            continue
        if not text.endswith("\n"):
            text += "\n"
        text += HELPER
        with open(path, "w") as f:
            f.write(text)
        print(f"PATCHED {rel}")
    if failed:
        sys.exit(f"{len(failed)} files failed: {failed}")


if __name__ == "__main__":
    main()
