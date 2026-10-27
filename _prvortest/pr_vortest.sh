#!/usr/bin/env bash
# pr_vortest.sh (THV-AC03, 14.10.2026) - PR pre-test for the ArtCraft apps (storytold/<app>) and the projects outside
# storytold (THV-AC10: tangency-labs/solidcraft, AdriaanBoshoff/OpenMailClient; owner from --repo or repo_default), Linux container.
# Builds <app>-cli from a pull request (cargo build --release), runs the fixture checks checks/<app>.py against
# KNUFFIXX/artcraft-fixtures/<app>/ and writes results/<app>-pr<n>-<sha7>.json + ...-draft.md (English comment
# draft with German review notes in an HTML comment on top). Posts nothing.
#
# Usage: pr_vortest.sh <app> <pr-number|main> [--head <sha>] [--repo <owner/name>] [--fixtures <dir>] [--issue <n>]...
#                      [--baseline] [--results <dir>] [--jobs <n>] [--no-fetch]
#   main              instead of a PR number: test the current main head (projects without releases, e.g. openmailclient
#                     after a fix landed on main; no baseline, result <app>-main-<sha7>)
#   --repo <o/n>      GitHub repository (default repo_default: storytold/<app>, tangency-labs/solidcraft, AdriaanBoshoff/OpenMailClient)
#   --head <sha>      test exactly this commit (from candidates.json); if the PR moved on, that is noted
#   --fixtures <dir>  artcraft-fixtures checkout (or its <app> folder) instead of the cached clone
#   --issue <n>       issue(s) the PR fixes (default: #nnnn found in the PR's commit messages)
#   --baseline        also build the merge base with main (cached per base) and run the same checks on it
#   --results <dir>   where the .json/-draft.md go (default: <script dir>/results)
#   --no-fetch        do not update the repo/fixture caches (offline re-run of a cached PR ref)
# Env:  PRV_HOME = cache (repos/, target/, bin/, fixtures/, work/, logs/); default ${TMPDIR:-/tmp}/prvortest
# Exit: 0 checks ran (verdicts in the JSON) | 2 usage | 3 git/fetch | 4 build failed | 5 checks did not run
# Runtime: first build of an app 8-15 min (2 cores); later PRs of the same app reuse target/<app> (2-6 min).
# Run it detached and poll the log:  nohup bash pr_vortest.sh filmcraft 1829 > <log> 2>&1 &
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRV_HOME="${PRV_HOME:-${TMPDIR:-/tmp}/prvortest}"
APPS="pdfcraft gridcraft filmcraft lightcraft wordcraft effectcraft deckcraft vectorcraft photocraft soundcraft solidcraft openmailclient"
repo_default() { case "$1" in solidcraft) echo tangency-labs/solidcraft ;; openmailclient) echo AdriaanBoshoff/OpenMailClient ;; *) echo "storytold/$1" ;; esac; }

usage() { sed -n '2,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2; }
say() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { local code="$1"; shift; say "ERROR: $*"; exit "$code"; }

[ $# -ge 2 ] || usage
APP="$1"; PR="$2"; shift 2
HEAD_ARG=""; FIXTURES=""; ISSUES=""; BASELINE=0; RESULTS="$HERE/results"; JOBS=""; FETCH=1; REPO_FULL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --head) HEAD_ARG="${2:-}"; shift 2 ;;
    --repo) REPO_FULL="${2:-}"; shift 2 ;;
    --fixtures) FIXTURES="${2:-}"; shift 2 ;;
    --issue) ISSUES="${ISSUES:+$ISSUES,}${2:-}"; shift 2 ;;
    --baseline) BASELINE=1; shift ;;
    --results) RESULTS="${2:-}"; shift 2 ;;
    --jobs) JOBS="-j ${2:-2}"; shift 2 ;;
    --no-fetch) FETCH=0; shift ;;
    -h|--help) usage ;;
    *) die 2 "unknown option $1" ;;
  esac
done
case " $APPS " in *" $APP "*) ;; *) die 2 "unknown app '$APP' (one of: $APPS)" ;; esac
[[ "$PR" =~ ^[0-9]+$ || "$PR" = main ]] || die 2 "PR number (or main) expected, got '$PR'"
[ -n "$REPO_FULL" ] || REPO_FULL="$(repo_default "$APP")"
[[ "$REPO_FULL" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || die 2 "--repo expects owner/name, got '$REPO_FULL'"
CHECK="$HERE/checks/$APP.py"
[ -f "$CHECK" ] || die 2 "no fixture checks for $APP yet ($CHECK missing; see README)"
for t in git cargo python3; do command -v "$t" >/dev/null || die 2 "$t not found"; done

mkdir -p "$PRV_HOME"/{repos,target,bin,work,logs} "$RESULTS"
REPO="$PRV_HOME/repos/$APP"
G() { git -C "$REPO" "$@"; }

# ---- 1. repo cache (blobless clone: full history for merge-base, file contents on demand)
if [ ! -d "$REPO/.git" ]; then
  say "clone $REPO_FULL (blobless)"
  git clone -q --filter=blob:none --no-checkout --no-tags "https://github.com/$REPO_FULL.git" "$REPO" || die 3 "clone failed"
fi
if [ "$(G rev-parse --is-shallow-repository)" = "true" ]; then   # older shallow cache: make it a blobless full-history clone
  say "unshallow $APP cache (blobless)"
  G config remote.origin.promisor true; G config remote.origin.partialclonefilter blob:none
  G fetch -q --unshallow --no-tags origin || die 3 "unshallow failed"
fi
if [ "$FETCH" = 1 ]; then
  G fetch -q --no-tags origin "+HEAD:refs/prvortest/main" || die 3 "fetch of main failed"
  [ "$PR" = main ] || G fetch -q --no-tags origin "+refs/pull/$PR/head:refs/prvortest/pr$PR" || die 3 "fetch of pull/$PR/head failed (does PR #$PR exist in $REPO_FULL?)"
fi
if [ "$PR" = main ]; then SHA="$(G rev-parse --verify -q "refs/prvortest/main^{commit}")" || die 3 "no ref for main"
else SHA="$(G rev-parse --verify -q "refs/prvortest/pr$PR^{commit}")" || die 3 "no ref for PR #$PR"; fi
HEAD_MOVED=""
if [ -n "$HEAD_ARG" ] && [[ "$SHA" != "$HEAD_ARG"* ]]; then
  if ! G cat-file -e "$HEAD_ARG^{commit}" 2>/dev/null; then
    [ "$FETCH" = 1 ] && G fetch -q --no-tags origin "$HEAD_ARG" 2>/dev/null
  fi
  if G cat-file -e "$HEAD_ARG^{commit}" 2>/dev/null; then
    HEAD_MOVED="PR head is now ${SHA:0:7}; tested ${HEAD_ARG:0:7} as requested"
    SHA="$(G rev-parse "$HEAD_ARG^{commit}")"
  else
    HEAD_MOVED="requested ${HEAD_ARG:0:7} not found; tested the current head ${SHA:0:7}"
  fi
  say "$HEAD_MOVED"
fi
SHA7="${SHA:0:7}"
MAIN="$(G rev-parse refs/prvortest/main)"
BASE="$(G merge-base "$SHA" "$MAIN" 2>/dev/null || true)"
[ "$PR" = main ] && { BASE=""; BASELINE=0; }   # main run: no base, no baseline (THV-AC10)
BEHIND=""; [ -n "$BASE" ] && BEHIND="$(G rev-list --count "$BASE..$MAIN")"
NLOG=30; [ "$PR" = main ] && NLOG=5
COMMITS="$(G log --format='%h %s' "${BASE:+$BASE..}$SHA" -n $NLOG)"
if [ -z "$ISSUES" ] && [ "$PR" != main ]; then   # main run: issues only via --issue (THV-AC10)
  ISSUES="$(G log --format='%B' "${BASE:+$BASE..}$SHA" -n 30 | grep -oE '#[0-9]{2,5}' | tr -d '#' | sort -un | paste -sd, -)"
fi
if [ "$PR" = main ]; then STEM="$APP-main-$SHA7"; PRLABEL="main"; else STEM="$APP-pr$PR-$SHA7"; PRLABEL="PR #$PR"; fi
say "$REPO_FULL $PRLABEL head $SHA7, base ${BASE:0:7}, main ${MAIN:0:7} (+$BEHIND), issues ${ISSUES:-?}"

# ---- 2. fixtures (shallow clone of KNUFFIXX/artcraft-fixtures, refreshed per run)
if [ -n "$FIXTURES" ]; then
  FIX_ROOT="$(cd "$FIXTURES" && pwd)" || die 2 "fixtures dir $FIXTURES missing"
else
  FIX_ROOT="$PRV_HOME/fixtures"
  if [ ! -d "$FIX_ROOT/.git" ]; then
    git clone -q --depth 1 https://github.com/KNUFFIXX/artcraft-fixtures.git "$FIX_ROOT" || die 3 "fixture clone failed"
  elif [ "$FETCH" = 1 ]; then
    git -C "$FIX_ROOT" fetch -q --depth 1 origin main && git -C "$FIX_ROOT" reset -q --hard FETCH_HEAD || say "fixture update failed, using the cached copy"
  fi
fi
FIX_SHA="$(git -C "$FIX_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
FIX_DIR="$FIX_ROOT/$APP"; [ -d "$FIX_DIR" ] || FIX_DIR="$FIX_ROOT"

# ---- 3. build
build() {   # build <sha> <log> -> sets BUILD_RC, BUILD_S, BUILD_ERR, LOCK_CHANGED
  local sha="$1" log="$2" t0
  G checkout -q --force --detach "$sha" || { BUILD_RC=90; BUILD_ERR="checkout of $sha failed"; return; }
  G clean -ffdxq
  t0=$(date +%s)
  say "build $APP-cli at ${sha:0:7} (log $log)"
  ( cd "$REPO" && CARGO_TARGET_DIR="$PRV_HOME/target/$APP" cargo build --release -p "$APP-cli" $JOBS ) > "$log" 2>&1
  BUILD_RC=$?
  BUILD_S=$(( $(date +%s) - t0 ))
  BUILD_ERR=""
  [ "$BUILD_RC" -ne 0 ] && BUILD_ERR="$(grep -E -A12 '^error(\[E[0-9]+\])?:' "$log" | head -60)"
  [ "$BUILD_RC" -ne 0 ] && [ -z "$BUILD_ERR" ] && BUILD_ERR="$(tail -30 "$log")"
  LOCK_CHANGED=""; [ -n "$(G status --porcelain -- Cargo.lock)" ] && LOCK_CHANGED=1
  say "build rc=$BUILD_RC in ${BUILD_S}s"
}
WORK="$PRV_HOME/work/$STEM"; rm -rf "$WORK"; mkdir -p "$WORK"
if [ -d "$PRV_HOME/target/$APP/release" ]; then TARGET_STATE="target/$APP reused"; else TARGET_STATE="target/$APP new"; fi
BUILD_LOG="$PRV_HOME/logs/$STEM.build.log"
build "$SHA" "$BUILD_LOG"
CLI="$PRV_HOME/bin/$STEM"
export PRV_APP="$APP" PRV_REPO="$REPO_FULL" PRV_PR="$PR" PRV_SHA="$SHA" PRV_HEAD_ARG="$HEAD_ARG" PRV_HEAD_MOVED="$HEAD_MOVED" PRV_BASE="$BASE" \
  PRV_MAIN="$MAIN" PRV_BEHIND="$BEHIND" PRV_ISSUES="$ISSUES" PRV_COMMITS="$COMMITS" PRV_BUILD_SECONDS="$BUILD_S" \
  PRV_BUILD_LOG="$BUILD_LOG" PRV_BUILD_ERROR="$BUILD_ERR" PRV_LOCK_CHANGED="$LOCK_CHANGED" PRV_FIX_SHA="$FIX_SHA" \
  PRV_FIX_DIR="$FIX_DIR" PRV_WORK="$WORK" PRV_HOST="$(uname -srm)" PRV_RUSTC="$(rustc --version 2>/dev/null)" \
  PRV_CARGO="$(cargo --version 2>/dev/null)" PRV_BUILD_CMD="cargo build --release -p $APP-cli" PRV_TARGET_STATE="$TARGET_STATE"
OUT_JSON="$RESULTS/$STEM.json"; OUT_MD="$RESULTS/$STEM-draft.md"
if [ "$BUILD_RC" -ne 0 ]; then
  export PRV_BUILD_STATUS=failed PRV_CLI="" PRV_BIN_SIZE=""
  python3 -I "$HERE/prv_draft.py" - "$OUT_JSON" "$OUT_MD"
  die 4 "build failed (see $BUILD_LOG)"
fi
cp -f "$PRV_HOME/target/$APP/release/$APP-cli" "$CLI"
export PRV_BUILD_STATUS=ok PRV_CLI="$CLI" PRV_BIN_SIZE="$(stat -c %s "$CLI")"

# ---- 4. checks on the branch
say "checks: $CHECK"
timeout 1800 python3 -I "$CHECK" "$CLI" "$FIX_DIR" "$WORK/checks.json" --work "$WORK/branch" | sed 's/^/  /'

# saved documents for the Office cross-check on the PC (Word/Excel), next to the results
OFFICE_DIR=""
case "$APP" in wordcraft|gridcraft)
  OFFICE_DIR="$RESULTS/$STEM-files"; rm -rf "$OFFICE_DIR"; mkdir -p "$OFFICE_DIR"
  find "$WORK/branch" -maxdepth 1 -type f \( -name '*.docx' -o -name '*.xlsx' -o -name '*.pdf' \) -exec cp -f {} "$OFFICE_DIR/" \;
  say "saved files for the Office cross-check: $OFFICE_DIR" ;;
esac
export PRV_OFFICE_DIR="$OFFICE_DIR"

# ---- 5. optional baseline (merge base with main), cached per base commit
BASE_JSON=""
if [ "$BASELINE" = 1 ] && [ -n "$BASE" ]; then
  BCLI="$PRV_HOME/bin/$APP-base-${BASE:0:7}"
  if [ ! -x "$BCLI" ]; then
    build "$BASE" "$PRV_HOME/logs/$APP-base-${BASE:0:7}.build.log"
    export PRV_BASE_BUILD_SECONDS="$BUILD_S"
    if [ "$BUILD_RC" -eq 0 ]; then cp -f "$PRV_HOME/target/$APP/release/$APP-cli" "$BCLI"
    else export PRV_BASE_BUILD_SECONDS="$BUILD_S (FAILED, rc $BUILD_RC)"; say "baseline build failed, no main column"; fi
  else
    export PRV_BASE_BUILD_SECONDS="cached"
  fi
  if [ -x "$BCLI" ]; then
    say "baseline checks (${BASE:0:7})"
    timeout 1800 python3 -I "$CHECK" "$BCLI" "$FIX_DIR" "$WORK/baseline.json" --work "$WORK/baseline" | sed 's/^/  /'
    BASE_JSON="$WORK/baseline.json"
  fi
elif [ "$BASELINE" = 1 ]; then
  say "no merge base with main found, baseline skipped"
fi

# ---- 6. result + draft
if [ ! -s "$WORK/checks.json" ]; then
  python3 -I "$HERE/prv_draft.py" - "$OUT_JSON" "$OUT_MD"
  die 5 "checks did not produce $WORK/checks.json"
fi
python3 -I "$HERE/prv_draft.py" "$WORK/checks.json" "$OUT_JSON" "$OUT_MD" $BASE_JSON
say "DONE $STEM"
