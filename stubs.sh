#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# stubs.sh — Convenience wrapper for py4godot type-stub generation
# ──────────────────────────────────────────────────────────────────────
#
# Commands:
#   generate   Generate .pyi stubs into py4godot/  (default)
#   sync       Copy generated stubs into py4godot-stubs/ for distribution
#   install    Generate + sync + pip-install in editable mode
#   clean      Remove all generated .pyi files
#   validate   Run pyright to check stubs for errors
#   status     Show stub file counts and last-generation time
#   help       Show this help message
#
# Usage:
#   ./stubs.sh                  # generate stubs
#   ./stubs.sh generate -v      # generate with verbose output
#   ./stubs.sh sync             # copy stubs into py4godot-stubs/
#   ./stubs.sh install          # full local install for IDE pickup
#   ./stubs.sh clean            # remove all .pyi files
#   ./stubs.sh validate         # type-check the stubs with pyright
#   ./stubs.sh status           # overview of generated stubs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── colours (disabled when stdout is not a terminal) ────────────────
if [[ -t 1 ]]; then
  GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
  CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; CYAN=''; BOLD=''; RESET=''
fi

info()  { echo -e "${CYAN}ℹ${RESET}  $*"; }
ok()    { echo -e "${GREEN}✔${RESET}  $*"; }
warn()  { echo -e "${YELLOW}⚠${RESET}  $*"; }
err()   { echo -e "${RED}✖${RESET}  $*" >&2; }

# ── helper: count .pyi files ────────────────────────────────────────
count_stubs() {
  find py4godot -name '*.pyi' 2>/dev/null | wc -l | tr -d ' '
}

# ── helper: sync stubs into the distribution package ────────────────
do_sync() {
  local src="py4godot"
  local dst="py4godot-stubs/py4godot"

  if [[ ! -d "$src" ]]; then
    err "No py4godot/ directory — run 'generate' first."
    exit 1
  fi

  info "Syncing stubs → ${dst}/"

  # Create destination layout
  mkdir -p "$dst/classes" "$dst/core" "$dst/utils"

  # Copy top-level .pyi files
  for f in "$src"/*.pyi; do
    [[ -e "$f" ]] || continue
    cp "$f" "$dst/"
  done

  # Copy classes/ stubs
  if [[ -d "$src/classes" ]]; then
    cp "$src/classes"/*.pyi "$dst/classes/" 2>/dev/null || true
    # Also copy the __init__.py that lives in classes/
    [[ -f "$src/classes/__init__.py" ]] && cp "$src/classes/__init__.py" "$dst/classes/"
  fi

  # Copy core.pyi if present
  [[ -f "$src/classes/core.pyi" ]] && cp "$src/classes/core.pyi" "$dst/classes/"

  # Ensure py.typed marker exists for PEP 561
  touch "$dst/py.typed"

  local count
  count=$(find "$dst" -name '*.pyi' 2>/dev/null | wc -l | tr -d ' ')
  ok "Synced ${count} stub files to ${dst}/"
}

# ── generate ────────────────────────────────────────────────────────
do_generate() {
  info "Generating type stubs from extension_api.json ..."
  python3 generate_stubs.py "$@"
  local count
  count=$(count_stubs)
  ok "Generated ${count} stub files in py4godot/"
}

# ── clean ───────────────────────────────────────────────────────────
do_clean() {
  info "Cleaning generated .pyi files ..."

  local removed=0

  # Remove top-level stubs in py4godot/
  for f in py4godot/*.pyi; do
    [[ -e "$f" ]] || continue
    rm "$f"
    removed=$((removed + 1))
  done

  # Remove class stubs
  if [[ -d py4godot/classes ]]; then
    for f in py4godot/classes/*.pyi; do
      [[ -e "$f" ]] || continue
      rm "$f"
      removed=$((removed + 1))
    done
  fi

  # Remove sync'd stubs in py4godot-stubs/
  if [[ -d py4godot-stubs/py4godot ]]; then
    for f in py4godot-stubs/py4godot/*.pyi py4godot-stubs/py4godot/classes/*.pyi; do
      [[ -e "$f" ]] || continue
      rm "$f"
      removed=$((removed + 1))
    done
  fi

  ok "Removed ${removed} stub files"
}

# ── validate ────────────────────────────────────────────────────────
do_validate() {
  if ! command -v pyright &>/dev/null && ! python3 -m pyright --version &>/dev/null 2>&1; then
    warn "pyright not found — install with: pip install pyright"
    exit 1
  fi

  info "Running pyright on stubs ..."
  if command -v pyright &>/dev/null; then
    pyright py4godot-stubs/py4godot --outputjson 2>/dev/null || true
    pyright py4godot-stubs/py4godot
  else
    python3 -m pyright py4godot-stubs/py4godot
  fi
}

# ── install ─────────────────────────────────────────────────────────
do_install() {
  do_generate "$@"
  do_sync

  info "Installing py4godot-stubs in editable mode ..."
  pip install -e "./py4godot-stubs" 2>/dev/null \
    && ok "Installed py4godot-stubs — IDE should now pick up types" \
    || warn "pip install failed — try manually: pip install -e ./py4godot-stubs"
}

# ── status ──────────────────────────────────────────────────────────
do_status() {
  echo -e "\n${BOLD}py4godot stub status${RESET}"
  echo "──────────────────────────────"

  local count
  count=$(count_stubs)
  echo -e "  Generated stubs (py4godot/) : ${count} files"

  if [[ -d py4godot-stubs/py4godot ]]; then
    local sync_count
    sync_count=$(find py4godot-stubs/py4godot -name '*.pyi' 2>/dev/null | wc -l | tr -d ' ')
    echo -e "  Synced stubs (stubs/)       : ${sync_count} files"
  else
    echo -e "  Synced stubs (stubs/)       : ${RED}not synced${RESET}"
  fi

  # Show newest .pyi modification time
  local newest
  newest=$(find py4godot -name '*.pyi' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
  if [[ -n "$newest" ]]; then
    echo -e "  Latest modified             : ${newest}"
  fi

  echo ""
}

# ── help ────────────────────────────────────────────────────────────
do_help() {
  cat <<'EOF'

  stubs.sh — py4godot type-stub convenience tool

  COMMANDS
    generate [flags]   Generate .pyi stubs (pass extra args to generate_stubs.py)
    sync               Copy stubs into py4godot-stubs/ for PEP 561 distribution
    install            generate + sync + pip install -e
    clean              Remove all generated .pyi files
    validate           Type-check stubs with pyright
    status             Show stub file counts and timestamps
    help               Show this message

  EXAMPLES
    ./stubs.sh                    # generate stubs (default command)
    ./stubs.sh generate -v        # verbose generation
    ./stubs.sh install            # full local install
    ./stubs.sh sync               # sync into py4godot-stubs/
    ./stubs.sh validate           # check for type errors
    ./stubs.sh clean              # clean all generated stubs

  EDITOR SETUP
    PyCharm       — Stubs are auto-detected when py4godot is installed
    VS Code       — Add "py4godot" to python.analysis.extraPaths
    Vim / Neovim  — Configure pylsp or pyright to find the stubs
    Pyright       — Stubs are found automatically via py.typed marker

EOF
}

# ── main ────────────────────────────────────────────────────────────
cmd="${1:-generate}"
[[ "$cmd" == "help" || "$cmd" == "--help" || "$cmd" == "-h" ]] && { do_help; exit 0; }

case "$cmd" in
  generate)
    shift
    do_generate "$@"
    ;;
  sync)
    do_sync
    ;;
  install)
    shift
    do_install "$@"
    ;;
  clean)
    do_clean
    ;;
  validate)
    do_validate
    ;;
  status)
    do_status
    ;;
  *)
    err "Unknown command: ${cmd}"
    do_help
    exit 1
    ;;
esac
