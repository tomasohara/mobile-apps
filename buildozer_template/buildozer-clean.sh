#!/bin/bash
#
# buildozer-clean.sh: Wrapper for 'buildozer -v android clean' that works
# even when p4a hasn't been cloned yet (works around upstream bug where
# cmd_clean doesn't guard against a missing python-for-android directory).
#
# Usage: ./buildozer-clean.sh [--quiet]
#

set -euo pipefail

quiet=false
for arg in "$@"; do
    case "$arg" in
        --quiet|-q) quiet=true ;;
        *)
            echo "Usage: $0 [--quiet|-q]" >&2
            exit 1
            ;;
    esac
done

log() {
    if [ "$quiet" = false ]; then
        echo "$*"
    fi
}

BUILDOZER_DIR=".buildozer"
P4A_DIR="$BUILDOZER_DIR/android/platform/python-for-android"

created_skeleton=false
if [ ! -d "$P4A_DIR" ]; then
    log "Workaround: $P4A_DIR not found (p4a not yet cloned)."
    log "Workaround: Creating skeleton directory so 'buildozer android clean' can proceed."
    mkdir -p "$P4A_DIR"
    created_skeleton=true
else
    log "Status: $P4A_DIR exists; proceeding with clean."
fi

log "Status: Running 'buildozer -v android clean'..."
buildozer -v android clean
log "Status: Clean completed successfully."

# Remove the skeleton if we created it and it's still empty
if [ "$created_skeleton" = true ] && [ -z "$(ls -A "$P4A_DIR" 2>/dev/null)" ]; then
    log "Workaround: Removing skeleton directory (nothing was created by clean)."
    rmdir "$P4A_DIR"
fi
