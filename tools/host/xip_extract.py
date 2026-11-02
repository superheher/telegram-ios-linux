#!/usr/bin/env python3
"""Stream members of one SDK directory out of an Xcode .xip without unpacking Xcode.

Companion to xip_version.py: same xar -> pbzx -> odc cpio pipeline, but instead of one
small plist it writes every member under <SDK>/System/Library/PrivateFrameworks whose
file part is a header or a module map. Restores what `xtool sdk build` drops from the
sdk-cache bundle — public framework headers import private frameworks unguarded
(UIUtilities out of UIKit), so a compile needs those Headers/Modules back.

    python3 xip_extract.py <Xcode.xip> <dest SDK root> [--platform iPhoneOS] [--list]
                           [--only NAME[,NAME...]] [--keep-binaries]

  --platform          iPhoneOS (default) | iPhoneSimulator | MacOSX
  --only              extract just these frameworks (comma-separated names)
  --keep-binaries     also extract .a/.tbd (not needed for compilation)

Exit 0: files written, one line per file on stdout; a final "n members" summary.
Exit 3: structurally unreadable archive (mirrors xip_version.py's error contract).
"""
import argparse
import lzma
import os
import struct
import sys
import xml.etree.ElementTree as ET
import zlib

XZ_MAGIC = b"\xfd7zXZ\x00"
ODC_HEADER = 76
MAX_NAME = 4096
TEXT_SUFFIXES = (".h", ".modulemap")
TEXT_NAMES = {"module.modulemap", "module.map", "Info.plist"}
BIN_SUFFIXES = (".a", ".tbd")


def content_range(f):
    head = f.read(28)
    if len(head) < 28:
        raise ValueError("not a xar archive (file too short)")
    magic, hsize, _version, toc_c, _toc_u, _alg = struct.unpack(">4sHHQQI", head)
    if magic != b"xar!":
        raise ValueError("not a xar archive (bad magic)")
    f.seek(hsize)
    packed = f.read(toc_c)
    if len(packed) < toc_c:
        raise ValueError("truncated xar table of contents")
    try:
        root = ET.fromstring(zlib.decompress(packed))
    except ET.ParseError as e:
        raise ValueError(f"xar table of contents is not XML ({e})") from e
    for entry in root.find("toc").findall("file"):
        if entry.findtext("name") == "Content":
            try:
                offset = int(entry.findtext("data/offset"))
                length = int(entry.findtext("data/length"))
            except (TypeError, ValueError) as e:
                raise ValueError("Content member has no usable offset and length") from e
            return hsize + toc_c + offset, length
    raise ValueError("no Content member in the xar archive")


def pbzx_chunks(f, start, length):
    f.seek(start)
    if f.read(4) != b"pbzx":
        raise ValueError("Content member is not a pbzx stream")
    if len(f.read(8)) < 8:
        raise ValueError("truncated pbzx header")
    consumed = 12
    while consumed < length:
        head = f.read(16)
        if len(head) < 16:
            raise ValueError("truncated pbzx stream")
        _flags, size = struct.unpack(">QQ", head)
        data = f.read(size)
        if len(data) < size:
            raise ValueError("truncated pbzx stream")
        consumed += 16 + size
        yield lzma.decompress(data) if data[:6] == XZ_MAGIC else data


class Stream:
    def __init__(self, chunks):
        self.chunks = chunks
        self.chunk = b""
        self.pos = 0

    def _fill(self):
        while self.pos >= len(self.chunk):
            try:
                self.chunk = next(self.chunks)
            except StopIteration:
                raise EOFError("truncated cpio stream") from None
            self.pos = 0

    def read(self, n):
        out = []
        while n > 0:
            self._fill()
            piece = self.chunk[self.pos:self.pos + n]
            self.pos += len(piece)
            n -= len(piece)
            out.append(piece)
        return b"".join(out)

    def skip(self, n):
        while n > 0:
            self._fill()
            step = min(n, len(self.chunk) - self.pos)
            self.pos += step
            n -= step


def members(stream, prefix, only, keep_binaries, list_only, no_clobber=False, dest=""):
    """Yield (relative path, bytes) for every member under prefix, walking the cpio."""
    written = 0
    while True:
        head = stream.read(ODC_HEADER)
        if not head or head[:6] != b"070707":
            break  # TRAILER!!! or truncation; the Content length bounds the walk
        try:
            namesize = int(head[59:65], 8)
            filesize = int(head[65:76], 8)
        except ValueError:
            continue
        if not 0 < namesize <= MAX_NAME:
            continue
        name = stream.read(namesize)[:-1].decode("utf-8", "replace")
        if name.startswith("./"):
            name = name[2:]
        if not name.startswith(prefix):
            if filesize:
                stream.skip(filesize)
            continue
        rel = name[len(prefix):]
        base = rel.rsplit("/", 1)[-1]
        keep = base.endswith(TEXT_SUFFIXES) or base in TEXT_NAMES \
            or (keep_binaries and base.endswith(BIN_SUFFIXES))
        if only is not None and "/" in rel:
            top = rel.split("/", 1)[0]
            keep = keep and (top in only or top.rsplit(".", 1)[0] in only)
        if not keep or (no_clobber and os.path.exists(os.path.join(dest, rel))):
            if filesize:
                stream.skip(filesize)
            continue
        if list_only:
            print(rel)
            if filesize:
                stream.skip(filesize)
            continue
        yield rel, stream.read(filesize)
        written += 1
    if list_only:
        yield None, written


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("xip")
    parser.add_argument("dest", help="destination SDK root (the iPhoneOS27.2.sdk dir)")
    parser.add_argument("--platform", default="iPhoneOS")
    parser.add_argument("--only", help="comma-separated framework names")
    parser.add_argument("--prefix", help="member path prefix overriding the PrivateFrameworks default")
    parser.add_argument("--list", action="store_true", help="print matching paths, write nothing")
    parser.add_argument("--keep-binaries", action="store_true")
    parser.add_argument("--no-clobber", action="store_true",
                        help="skip members whose destination file already exists (the cache's "
                             "files are real while the .xip carries NULLcanary placeholders "
                             "for some of the same paths)")
    args = parser.parse_args(argv[1:])
    only = set(args.only.split(",")) if args.only else None
    prefix = args.prefix or (
        "Xcode.app/Contents/Developer/Platforms/%s.platform/Developer/SDKs/"
        "%s.sdk/System/Library/PrivateFrameworks/"
        % (args.platform, args.platform))
    try:
        with open(args.xip, "rb") as f:
            start, length = content_range(f)
            stream = Stream(pbzx_chunks(f, start, length))
            for rel, data in members(stream, prefix, only, args.keep_binaries, args.list,
                                     args.no_clobber, args.dest):
                if rel is None:
                    sys.stdout.write("%d members\n" % data)
                    return 0
                out = os.path.join(args.dest, rel)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out, "wb") as g:
                    g.write(data)
                print(rel)
                written = 1
    except (struct.error, lzma.LZMAError, zlib.error, EOFError, ValueError, OSError) as e:
        sys.stderr.write(f"xip_extract.py: {e}\n")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
