#!/usr/bin/env python3
"""Print the full swiftc stderr for one Swift module (the driver shows only the first error).

    python3 tools/tgbuild/probe.py //submodules/TelegramCore:TelegramCore [--emit-only]
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objc import REPO, generate_modulemap, include_flags, label_to_path, load_graph, module_name_of
from objc import toolchain_env
from swift import swiftc_base_flags, transitive_objc_deps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("--min", default="17.0")
    args = parser.parse_args()

    graph, by_label = load_graph(os.path.join(REPO, "build-input/graph/modules.json"))
    record = by_label[args.label]
    base = swiftc_base_flags(args.min)
    deps = transitive_objc_deps(record, by_label)
    flags = list(base)
    for dep in deps:
        map_path, _ = generate_modulemap(dep, "build-input/objc")
        flags += ["-Xcc", "-fmodule-map-file=" + map_path]
    flags += include_flags(deps)
    flags += ["-module-name", module_name_of(record)]
    srcs = [os.path.join(REPO, label_to_path(l)) for l in record.get("srcs_files", [])
            if l.endswith(".swift")]
    cmd = ["swiftc", "-wmo", "-emit-module", "-o", "/tmp/probe.swiftmodule", "-Xcc", "-fmodules-cache-path=/tmp/tg-mcache"] + flags + srcs
    proc = subprocess.run(cmd, capture_output=True, text=True, env=toolchain_env, cwd=REPO)
    for line in proc.stderr.splitlines():
        print(line)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
