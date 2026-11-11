#!/bin/bash
# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Run DaskToon tests in the built DaskToon (Git Bash):
#
#   tools/dasktoon_run_tests.sh dasktoon_machine_test dasktoon_translations_test
#   tools/dasktoon_run_tests.sh --all          # every tests/python/dasktoon_*_test.py
#   tools/dasktoon_run_tests.sh --nosync NAME  # skip copying scripts/ into the install first
#
# Python changes only reach the program after the sync (tools/dasktoon_sync_build.py), so it runs first by default.
# One line per test: exit code, "Ran N tests", OK/FAILED; the first errors of a failing test follow it.
# Full logs: $DASKTOON_TEST_OUT (default: $TEMP/dasktoon_tests/<test>.log).

cd "$(dirname "$0")/.." || exit 2
BUILD=${DASKTOON_BUILD:-/d/build_windows_x64_vc18_Release/bin/Release}
DT="$BUILD/DaskToon.exe"
PY="$BUILD/5.2/python/bin/python.exe"
OUT=${DASKTOON_TEST_OUT:-${TEMP:-/tmp}/dasktoon_tests}
mkdir -p "$OUT"

sync=1
tests=()
for a in "$@"; do
  case "$a" in
    --nosync) sync=0 ;;
    --all) for f in tests/python/dasktoon_*_test.py; do tests+=("$(basename "$f" .py)"); done ;;
    *) tests+=("${a%.py}") ;;
  esac
done
if [ ${#tests[@]} -eq 0 ]; then
  echo "usage: $0 [--nosync] (--all | test_name...)" >&2
  exit 2
fi
if [ ! -x "$DT" ]; then
  echo "DaskToon.exe not found at $DT (set DASKTOON_BUILD)" >&2
  exit 2
fi
if [ $sync -eq 1 ]; then
  "$PY" tools/dasktoon_sync_build.py "$BUILD/5.2" > "$OUT/_sync.log" 2>&1 || { echo "sync failed, see $OUT/_sync.log"; exit 2; }
fi

status=0
passed=0
for t in "${tests[@]}"; do
  if [ ! -f "tests/python/$t.py" ]; then
    echo "$t: NO SUCH TEST (tests/python/$t.py)"
    status=1
    continue
  fi
  "$DT" --background --factory-startup --python-exit-code 1 --python "tests/python/$t.py" > "$OUT/$t.log" 2>&1
  code=$?
  summary=$(grep -E "^Ran [0-9]+ tests" "$OUT/$t.log" | tail -1)
  result=$(grep -E "^(OK|FAILED)" "$OUT/$t.log" | tail -1)
  echo "$t: exit $code | $summary | $result"
  if [ $code -ne 0 ]; then
    status=1
    grep -E "^(FAIL|ERROR):|Error|assert|Traceback" "$OUT/$t.log" | head -20
  else
    passed=$((passed + 1))
  fi
done
echo "== $passed/${#tests[@]} passed (logs: $OUT)"
exit $status
