#!/bin/bash
# USAGE: tools/push.sh   -- push local branches main and seat to Joe's GitHub repo (masterminnich/essick-rocker)
# Goes through the sandbox clone because that is where Joe's own GitHub sign-in is configured. Fast-forward only.
R="$(cd "$(dirname "$0")/.." && git rev-parse --path-format=absolute --git-common-dir)"; R="${R%/.git}"
S=/Users/sean/.cc-sessions/code2-fresh-home/.cc-sessions/sandboxes/essick-rocker-joe/repo
git -C "$S" fetch -q "$R" main:main seat:seat && git -C "$S" push -q origin main seat && git -C "$S" for-each-ref --format='%(refname:short) %(objectname:short)' refs/remotes/origin
