#!/bin/bash
# Compile the GeneratedSources stand-in (see the .swift header) with the tgbuild driver
# flags and install its products where the ladder and link.py expect them.
set -euo pipefail
cd "$(dirname "$0")/../.."
export PATH=/usr/local/usr/bin:$HOME/.local/bin:$PATH
python3 - <<'PYEOF'
import os, subprocess, sys
sys.path.insert(0, 'tools/tgbuild')
from objc import toolchain_env
from swift import swiftc_base_flags
os.makedirs('build-input/swift/modules', exist_ok=True)
os.makedirs('build-input/swift/objects', exist_ok=True)
src = 'tools/tgbuild/stubs/GeneratedSources.swift'
for what, extra in (('swiftmodule', ['-emit-module', '-o', 'build-input/swift/modules/GeneratedSources.swiftmodule']),
                    ('object', ['-c', '-o', 'build-input/swift/objects/GeneratedSources.o'])):
    cmd = ['swiftc'] + swiftc_base_flags('16.0') + ['-module-name', 'GeneratedSources', '-wmo', '-parse-as-library'] + extra + [src]
    p = subprocess.run(cmd, capture_output=True, text=True, env=toolchain_env)
    if p.returncode != 0:
        print(p.stderr[:2000]); sys.exit(1)
    print(what, 'ok')
PYEOF
