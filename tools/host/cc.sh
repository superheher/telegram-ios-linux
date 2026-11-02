#!/usr/bin/env bash
# clang for iOS arm64 against the sdk-free sysroot only (no Xcode, no SDK files).
#   sdk-free/cc.sh [-c] main.m -o main.o        NOSDK_MIN=15.0 sets the deployment target (default 17.0)
# Link with:  $SDKFREE_HOME/toolset/ld64.lld -arch arm64 -platform_version ios 17.0 26.0 -syslibroot $SDKFREE_HOME/iPhoneOS.sdk \
#   -lSystem -lobjc -framework UIKit -framework Foundation -o App main.o
set -euo pipefail
SDKFREE_HOME=${SDKFREE_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/omarchy-apple-dev/sdk-free}
SR=${NOSDK_SYSROOT:-$SDKFREE_HOME/iPhoneOS.sdk}
CLANG=${SDKFREE_CLANG:-$(dirname "$(readlink -f "$(command -v swift)")")/clang}
MIN=${NOSDK_MIN:-17.0}
FW=()
[ -n "${FLUTTER_FW_DIR:-}" ] && FW=(-F"$FLUTTER_FW_DIR")
# Resource include before the sysroot: the compiler's float.h/limits.h must shadow the
# SDK's canary-wrapped copies (usr/include/module.modulemap _c_standard_library_obsolete
# fires "requires feature found_incompatible_headers__check_search_paths" if a sysroot
# stdc header is reached before the compiler's own).
# NOSDK_CXX_V1 (set per C++ TU by tools/tgbuild/objc.py): libc++ BEFORE the resource
# dir — the order Apple's own driver uses; libc++'s <cstddef> requires its own
# <stddef.h> wrapper to win the name lookup.
CXXLINE=()
[ -n "${NOSDK_CXX_V1:-}" ] && CXXLINE=(-isystem "$NOSDK_CXX_V1")
exec "$CLANG" -target "arm64-apple-ios$MIN" -isysroot "$SR" -nostdinc \
  "${CXXLINE[@]}" \
  -isystem "$("$CLANG" -print-resource-dir)/include" -isystem "$SR/usr/include" \
  -iframework "$SR/System/Library/Frameworks" \
  -iframework "$SR/System/Library/PrivateFrameworks" \
  -iframework "$SR/System/Library/SubFrameworks" \
  "${FW[@]}" -fobjc-arc -fobjc-runtime="ios-$MIN" "$@"
