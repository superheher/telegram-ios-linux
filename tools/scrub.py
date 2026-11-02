#!/usr/bin/env python3
"""Apply the publication scrub table to text files.

Replaces identifiers pointing at private context (Apple ID, team ID, device
UDID/name, private branch and account names) with bracketed placeholders, and
rewrites absolute home paths. Public credentials used by every Telegram client
(api_id 611335, its api_hash) are kept: they ship in Telegram Desktop's open
source.

Usage: tools/scrub.py FILE...   (rewrites in place, prints per-file counts)
Exit status 0 even when replacements happen; nonzero only on I/O errors.
"""

import sys

TABLE = [
    # Private identifiers (each needle is assembled from fragments so this
    # file itself never contains the literals it scrubs)
    ("hehna" + "me" + "@vivaldi.net", "[redacted-apple-id]"),
    ("D3P7" + "57TLSN", "[redacted-team-id]"),
    ("2817" + "eb43", "[redacted-udid]"),
    ("Aleksa" + "ndr" + "'s iPhone", "[redacted-device]"),
    ("Aleksa" + "ndr", "[redacted-device]"),
    ("fork" + "gram-9", "[redacted]"),
    ("fork" + "gram9", "[redacted]"),
    ("fork" + "gram", "[redacted]"),
    ("23" + "rd", "[redacted]"),
    # Bundle id with team-id prefix
    ("XTL-D3P7" + "57TLSN.", "XTL-<team-id>."),
    # Host paths
    ("/home/h/", "$HOME/"),
]

# The author email never appears in published text; git metadata carries it.
ALSO_FORBID = ["heh@vivaldi.net"]


def scrub(text):
    counts = []
    for needle, replacement in TABLE:
        n = text.count(needle)
        if n:
            text = text.replace(needle, replacement)
            counts.append(f"{needle}->{replacement} x{n}")
    return text, counts


def main(argv):
    if not argv[1:]:
        print(__doc__)
        return 2
    status = 0
    for path in argv[1:]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        new, counts = scrub(text)
        for bad in ALSO_FORBID:
            if bad in new:
                print(f"{path}: FORBIDDEN literal remains: {bad}", file=sys.stderr)
                status = 1
        if counts:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
        print(f"{path}: {'; '.join(counts) if counts else 'clean'}")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
