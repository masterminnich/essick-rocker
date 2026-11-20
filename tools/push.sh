#!/bin/bash
# USAGE: tools/push.sh [BRANCH ...]   -- push local branches to Joe's GitHub repo (masterminnich/essick-rocker); default: main seat
#        tools/push.sh --pull-main    -- after a squash merge on GitHub: fast-forward local main to GitHub's main
# Goes through the sandbox clone because that is where Joe's own GitHub sign-in is configured. Fast-forward only.
# Big changes go through a pull request that is squash-merged (Joe, 2026-11-20): work on a branch, `tools/push.sh BRANCH`,
# open the PR with the journey and figures (figures committed under figures/, linked by commit hash), squash-merge, --pull-main.
R="$(cd "$(dirname "$0")/.." && git rev-parse --path-format=absolute --git-common-dir)"; R="${R%/.git}"
S=/Users/sean/.cc-sessions/code2-fresh-home/.cc-sessions/sandboxes/essick-rocker-joe/repo
if [ "$1" = "--pull-main" ]; then
  git -C "$S" fetch -q origin && git -C "$R" fetch -q "$S" refs/remotes/origin/main && git -C "$R" merge -q --ff-only FETCH_HEAD && git -C "$R" log --oneline -1
  exit
fi
[ $# -eq 0 ] && set -- main seat
specs=(); for b in "$@"; do specs+=("$b:$b"); done
git -C "$S" fetch -q "$R" "${specs[@]}" && git -C "$S" push -q origin "$@" && git -C "$S" for-each-ref --format='%(refname:short) %(objectname:short)' refs/remotes/origin
