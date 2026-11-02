#!/bin/sh
# Apply the Linux build series to a checkout of the base commit.
#
# Usage: patches/apply-patches.sh <path-to-repo-checkout>
#
# Expects <repo> to be a git checkout of the Telegram-iOS repository with the
# base commit (see base-commit) checked out. 0001-0007 land as commits via
# `git am`; 0008 patches the tgcalls submodule working tree in place (the
# submodule's own history is upstream's and is not rewritten).
set -eu
d=$(cd "$(dirname "$0")" && pwd)
root=$(cd "${1:?usage: apply-patches.sh <repo-checkout>}" && pwd)

base=$(awk '{print $1}' "$d/base-commit")
head=$(git -C "$root" rev-parse HEAD)
if [ "$head" != "$base" ]; then
    echo "warning: HEAD is $head, base is $base" >&2
    git -C "$root" checkout "$base"
fi

grep -v '^#' "$d/series" | while read -r p; do
    case "$p" in
    0008-*)
        # Submodule-internal fix: paths inside the patch are relative to the
        # submodule root, so apply it there.
        sub="$root/submodules/TgVoipWebrtc/tgcalls"
        [ -d "$sub" ] || git -C "$root" submodule update --init submodules/TgVoipWebrtc/tgcalls
        git -C "$sub" apply "$d/$p"
        ;;
    *)
        git -C "$root" am --quiet "$d/$p"
        ;;
    esac
done
echo "series applied; verify with: git -C $root log --oneline $base..HEAD"
