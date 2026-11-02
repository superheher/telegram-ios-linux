#!/usr/bin/env python3
"""Extract the build graph of the Telegram app into modules.json for the Linux build driver.

    python3 tools/tgbuild/extract.py [--target //Telegram:Telegram] [-o FILE] [--xml FILE] [--bazel PATH]

The plan (docs/linux-build-research-plan.md, Phase 1) sketched this over `bazel cquery
--output=starlark`, but cquery needs target *analysis*, and analysis of objc_library targets
requires the Apple CC toolchain, which does not exist on Linux ("Compiling objc_library targets
requires the Apple CC toolchain" — checked 2026-10-25). Loading-phase `bazel query --output=xml`
carries the same attribute data (srcs, hdrs, deps, copts, module_name, sdk_frameworks, ...) with
no toolchain resolution, so that is what this tool runs. Select() branches are unresolved at this
stage: query flattens each select-valued attribute to the union of its branches, which is the
superset the driver wants (it had rather compile one module too many than miss one).

Writes a JSON document:

    meta     targets, timestamp, bazel invocation, per-kind counts, warnings
    order    topological order over module deps (swift/objc/cc libraries, prebuilt imports)
    targets  one record per rule: label, kind, attrs (verbatim), srcs/hdrs/data resolved to
             concrete file labels through filegroup/alias closure, deps (module deps split out)
    files    generated files -> producing rule label (source files need no entry; the label is
             the path)

Prints per-kind counts and every module that resolved to no sources, exiting nonzero if a
swift/objc/cc library has neither srcs nor hdrs (a header-only cc_library is legal; an empty
swift_library is a lost glob and a broken graph).
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

DEFAULT_TARGET = "//Telegram:Telegram"
DEFAULT_BAZEL = "./build-input/bazel-9.2.0-linux-x86_64"
DEFAULT_OUT = "build-input/graph/modules.json"

# Rules the compile backends (Phase 2/3) consume as units. rust_library is carried in the graph
# (mtproto-engine) but has no Linux backend yet — see docs/linux-build-2026-10-25.md.
MODULE_KINDS = {
    "swift_library",
    "objc_library",
    "cc_library",
    "swift_import",
    "objc_import",
    "cc_import",
    "rust_library",
    "rust_static_library",
    "apple_static_xcframework_import",
}
PREBUILT_KINDS = {
    "swift_import",
    "objc_import",
    "cc_import",
    "apple_static_xcframework_import",
}
# Attributes that name source files; resolved through filegroup/alias closure.
FILE_ATTRS = ["srcs", "hdrs", "non_arc_srcs", "textual_hdrs", "data", "resources", "outs",
              "xcframework_imports", "imported_library"]
# Build-infra kinds whose deps routinely point at tool-configured targets outside the closure.
NOISE_KINDS = {"cargo_build_script", "cargo_build_script_runfiles", "cargo_toml_env_vars"}
INTENT_KINDS = {"apple_intent_library"}


def parse_query_xml(path):
    """Parse `bazel query --output=xml` into nodes keyed by label.

    Returns (rules, source_files, generated_files, producers):
      rules[label]           {"kind", "location", "attrs": {name: str|bool|list}, "inputs", "outputs"}
      source_files           set of labels of source files
      generated_files        set of labels of generated files
      producers[genfile]     label of the rule whose output it is
    """
    rules, source_files, generated_files, producers = {}, set(), set(), {}
    for event, elem in ET.iterparse(path, events=("end",)):
        # Clear only the top-level nodes (<query> holds a flat list of them); clearing a child
        # on its own end event would wipe its attributes before the enclosing rule reads them.
        if elem.tag not in ("rule", "source-file", "generated-file", "package", "error"):
            continue
        if elem.tag == "rule":
            label = elem.get("name")
            attrs = {}
            for child in elem:
                if child.tag == "list":
                    attrs[child.get("name")] = [
                        item.get("value") for item in child if item.get("value")
                    ]
                elif child.tag == "string":
                    attrs[child.get("name")] = child.get("value")
                elif child.tag == "boolean":
                    attrs[child.get("name")] = child.get("value") == "true"
            inputs = [i.get("name") for i in elem.findall("rule-input")]
            outputs = [o.get("name") for o in elem.findall("rule-output")]
            rules[label] = {
                "kind": elem.get("class"),
                "location": elem.get("location"),
                "attrs": attrs,
                "inputs": inputs,
                "outputs": outputs,
            }
            for out in outputs:
                producers[out] = label
        elif elem.tag == "source-file":
            source_files.add(elem.get("name"))
        elif elem.tag == "generated-file":
            generated_files.add(elem.get("name"))
        elem.clear()
    return rules, source_files, generated_files, producers


def resolve_files(label, rules, source_files, generated_files, _seen=None):
    """Resolve a label through filegroup/alias closure to concrete source/generated file labels."""
    if _seen is None:
        _seen = set()
    if label in _seen:
        return []
    _seen.add(label)
    if label in source_files or label in generated_files:
        return [label]
    node = rules.get(label)
    if node is None:
        return []
    kind = node["kind"]
    if kind == "source file" or kind == "generated file":
        return [label]
    if kind == "filegroup" or kind == "alias":
        edge = node["attrs"].get("srcs", []) if kind == "filegroup" else [node["attrs"].get("actual")]
        files = []
        for dep in edge:
            if dep:
                files += resolve_files(dep, rules, source_files, generated_files, _seen)
        return files
    # Any other rule named as a source (a genrule in srcs): its outputs stand in for it.
    return list(node["outputs"])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", action="append", default=None,
                        help="target label(s) to close over (default: %s)" % DEFAULT_TARGET)
    parser.add_argument("--xml", default=None,
                        help="use a pre-rendered query XML file instead of running bazel")
    parser.add_argument("--bazel", default=DEFAULT_BAZEL, help="bazel binary (default: %(default)s)")
    parser.add_argument("-o", "--out", default=DEFAULT_OUT, help="output path (default: %(default)s)")
    args = parser.parse_args()
    targets = args.target or [DEFAULT_TARGET]

    if args.xml:
        xml_path, query_cmd = args.xml, None
    else:
        xml_path = args.out + ".query.xml"
        os.makedirs(os.path.dirname(xml_path) or ".", exist_ok=True)
        query_cmd = [args.bazel, "query", "deps(%s)" % " + ".join(targets),
                     "--output=xml", "--noimplicit_deps", "--notool_deps"]
        print("running: %s > %s" % (" ".join(query_cmd), xml_path), file=sys.stderr)
        with open(xml_path, "w") as f:
            subprocess.run(query_cmd, stdout=f, check=True)

    rules, source_files, generated_files, producers = parse_query_xml(xml_path)
    print("loaded %d rules, %d source files, %d generated files" %
          (len(rules), len(source_files), len(generated_files)), file=sys.stderr)

    def canonical(label):
        """Follow alias chains to the rule that actually declares the target."""
        seen = set()
        while label in rules and rules[label]["kind"] == "alias" and label not in seen:
            seen.add(label)
            label = rules[label]["attrs"].get("actual", label)
        return label

    warnings, records = [], []
    for label, node in sorted(rules.items()):
        attrs = node["attrs"]
        record = {
            "label": label,
            "kind": node["kind"],
            "location": node["location"],
            "package": label[2:].split(":")[0] if ":" in label else label[2:],
            "attrs": attrs,
        }
        for attr in FILE_ATTRS + ["src"]:
            value = attrs.get(attr)
            if value is None:
                continue
            entries = [value] if isinstance(value, str) else value
            files, intent_rules = [], []
            for entry in entries:
                target = canonical(entry)
                if rules.get(target, {}).get("kind") in INTENT_KINDS:
                    intent_rules.append(target)  # code generated by Apple intent tooling
                else:
                    files += resolve_files(entry, rules, source_files, generated_files)
            record[attr + "_files"] = sorted(set(files))
            if intent_rules:
                record["intent_srcs"] = intent_rules
        module_deps, other_deps = [], []
        for dep in attrs.get("deps", []):
            target = canonical(dep)
            if rules.get(target, {}).get("kind") in MODULE_KINDS:
                module_deps.append(target)
            else:
                other_deps.append(dep)
        if module_deps:
            record["module_deps"] = module_deps
        if other_deps:
            record["other_deps"] = other_deps
        if node["kind"] in MODULE_KINDS:
            record["module"] = True
            record["prebuilt"] = node["kind"] in PREBUILT_KINDS
        records.append(record)

    by_label = {r["label"]: r for r in records}
    order, failures = topo_order(records)
    for label, cycle in failures:
        warnings.append("dependency cycle involving %s: %s" % (label, " -> ".join(cycle)))

    # Deps that point outside the extracted closure would silently break the driver.
    for r in records:
        if r["kind"] in NOISE_KINDS:
            continue
        for dep in r.get("module_deps", []) + r.get("other_deps", []):
            if dep not in by_label:
                warnings.append("%s depends on %s, which is not in the graph" % (r["label"], dep))

    # Acceptance: no compile module without sources. Header-only and dep-only libraries are
    # legal (boost_regex, td, webp, mozjpeg wrap headers/prebuilt archives); modules whose
    # sources are generated from an intentdefinition are tracked separately. What fails the
    # graph is a module whose declared srcs resolve to nothing (a broken filegroup) or that
    # carries no srcs, hdrs, deps or intent source at all (a lost glob).
    empty_modules = []
    for r in records:
        if not r.get("module") or r.get("intent_srcs") or r.get("prebuilt"):
            continue
        declared = r["attrs"].get("srcs") or ([r["attrs"]["src"]] if isinstance(r["attrs"].get("src"), str) else [])
        resolved = r.get("srcs_files") or []
        if declared and not resolved:
            empty_modules.append(r["label"])
        elif not resolved and not r.get("hdrs_files") and not r.get("module_deps"):
            empty_modules.append(r["label"])
    if empty_modules:
        warnings.append("modules with no sources: " + ", ".join(sorted(set(empty_modules))))

    counts = {}
    for r in records:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1

    document = {
        "meta": {
            "targets": targets,
            "generated": datetime.datetime.now().isoformat(timespec="seconds"),
            "query": query_cmd,
            "query_xml": os.path.abspath(xml_path),
            "counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
            "modules": sum(1 for r in records if r.get("module")),
            "prebuilt_modules": sum(1 for r in records if r.get("prebuilt")),
            "warnings": warnings,
        },
        "order": order,
        "targets": records,
        "files": {f: producers[f] for f in sorted(generated_files)},
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(document, f, indent=1, sort_keys=False)
        f.write("\n")

    print("per-kind counts:")
    for kind, count in document["meta"]["counts"].items():
        print("  %4d  %s" % (count, kind))
    print("modules (compile units): %d, prebuilt: %d" %
          (document["meta"]["modules"], document["meta"]["prebuilt_modules"]))
    print("topological order covers %d modules" % len(order))
    for extension in [t for t in by_label if by_label[t]["kind"] == "ios_extension"]:
        print("extension in graph: %s" % extension)
    for warning in warnings:
        print("WARNING: %s" % warning, file=sys.stderr)
    print("wrote %s (%.1f MiB)" % (args.out, os.path.getsize(args.out) / 1048576.0))
    sys.exit(1 if empty_modules or failures else 0)


def topo_order(records):
    """Order module records so every module comes after its module deps; report cycles."""
    modules = {r["label"]: r for r in records if r.get("module")}
    state, order, failures = {}, [], []

    def visit(label, stack):
        if state.get(label) == 2:
            return
        if state.get(label) == 1:
            failures.append((label, stack[stack.index(label):] + [label]))
            return
        state[label] = 1
        for dep in modules[label].get("module_deps", []):
            if dep in modules:
                visit(dep, stack + [label])
        state[label] = 2
        order.append(label)

    for label in sorted(modules):
        visit(label, [])
    return order, failures


if __name__ == "__main__":
    main()
