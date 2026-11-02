#!/usr/bin/env bash
# Rebuild the sdk-free Foundation Swift overlay with tools/tgbuild/overlay/Foundation+Tgbuild.swift
# added, installing over the sdk-free copies (same recipe as sdk-free/swift/overlays.sh's
# build_module Foundation: the curated swift-5.3 sources under cache/ovlsrc/Foundation plus
# NSValue.swift, -O -wmo -enable-library-evolution). Re-run after editing the +Tgbuild source.
set -euo pipefail
export PATH=/usr/local/usr/bin:$PATH
REPO=$(cd "$(dirname "$0")/../.." && pwd)
SDKFREE=${SDKFREE_HOME:-$HOME/.local/share/omarchy-apple-dev/sdk-free}
SR=$SDKFREE/iPhoneOS.sdk
RES=$SDKFREE/swift/res
OVL=$SDKFREE/swift/ovl
DARWININC=$SDKFREE/swift/darwin/usr/include
SDKM=$SDKFREE/swift/sdkm
CACHE=$SDKFREE/cache
GEN=$SDKFREE/swift/gen53
TC=$(dirname "$(dirname "$(readlink -f "$(command -v swiftc)")")")

OUT=$REPO/build-input/swift/overlay/Foundation.build
mkdir -p "$OUT"

swiftc -module-name Foundation -O \
  -target "arm64-apple-ios${NOSDK_SWIFT_MIN:-17.0}" -sdk "$SR" -resource-dir "$RES" \
  -parse-as-library -wmo -enable-library-evolution -swift-version 5 \
  -Xfrontend -disable-availability-checking -Xfrontend -disable-implicit-string-processing-module-import \
  -Xcc -fapinotes-modules -Xcc -fapinotes \
  -Xcc "-fmodule-map-file=$TC/lib/swift/shims/module.modulemap" -Xcc "-I$TC/lib/swift/shims" \
  -I "$OVL" -I "$SDKM/ovlshims" -F "$SDKM/Frameworks" -Xcc -F -Xcc "$SDKM/Frameworks" \
  -I "$DARWININC" -Xcc -isystem -Xcc "$DARWININC" -Xcc -isystem -Xcc "$SR/usr/include" \
  -Xcc '-D__unused=__attribute__((unused))' -Xcc -DSWIFT_STDLIB_HAS_ENVIRON=1 \
  -emit-module -emit-module-path "$OUT/Foundation.swiftmodule" \
  "$CACHE"/ovlsrc/Foundation/*.swift "$GEN/NSValue.swift" \
  "$REPO"/tools/tgbuild/overlay/Foundation+Tgbuild.swift

# Small Swift shim modules (os, Network): `import os.log` resolves to a Swift module named os.
# Built into their own dir — NOT into $OVL: a swiftmodule named os on the overlay search path
# collides with the Darwin clang module os and cycles the module graph (Foundation<->os).
SHIMS=$REPO/build-input/swift/shims
mkdir -p "$SHIMS"
for shim in os Network; do
  swiftc -module-name "$shim" -O -parse-as-library -wmo -swift-version 5 \
    -target "arm64-apple-ios${NOSDK_SWIFT_MIN:-17.0}" -sdk "$SR" -resource-dir "$RES" \
    -Xcc "-fmodule-map-file=$TC/lib/swift/shims/module.modulemap" -Xcc "-I$TC/lib/swift/shims" \
    -I "$OVL" -I "$SDKM/ovlshims" -F "$SDKM/Frameworks" -Xcc -F -Xcc "$SDKM/Frameworks" \
    -I "$DARWININC" -Xcc -isystem -Xcc "$DARWININC" -Xcc -isystem -Xcc "$SR/usr/include" \
    -Xcc -nostdinc -Xcc -isystem -Xcc /usr/local/usr/lib/clang/21/include \
    -emit-module -emit-module-path "$SHIMS/$shim.swiftmodule" \
    "$REPO/tools/tgbuild/overlay/$shim.swift"
done

for dest in "$OVL/Foundation.swiftmodule" "$RES/iphoneos/Foundation.swiftmodule"; do
  mkdir -p "$dest"
  cp "$OUT/Foundation.swiftmodule" "$dest/arm64-apple-ios.swiftmodule"
done
echo "Foundation overlay rebuilt with +Tgbuild additions"
