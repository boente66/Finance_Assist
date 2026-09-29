#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
PYINSTALLER_BIN="$PROJECT_ROOT/.venv/bin/pyinstaller"
APP_PATH="$PROJECT_ROOT/dist/Finance Assist Test.app"
VERSION="$(cd "$PROJECT_ROOT" && "$PYTHON_BIN" -c 'from core.version import APP_VERSION; print(APP_VERSION)')"
MACHINE="$(uname -m)"
case "$MACHINE" in
    arm64) ARCH="arm64" ;;
    x86_64) ARCH="x64" ;;
    *) printf 'Arquitetura macOS não suportada: %s\n' "$MACHINE" >&2; exit 1 ;;
esac
RELEASE_DIR="$PROJECT_ROOT/dist/release"
ARCHIVE="$RELEASE_DIR/finance-assist_${VERSION}_macos-${ARCH}.zip"

cd "$PROJECT_ROOT"
"$PYINSTALLER_BIN" --noconfirm --clean ControleFinanceiro-macos.spec
test -x "$APP_PATH/Contents/MacOS/FinanceAssist-test"
"$PYTHON_BIN" packaging/verify_archive.py "$APP_PATH/Contents/MacOS/FinanceAssist-test"
QT_QPA_PLATFORM=offscreen "$APP_PATH/Contents/MacOS/FinanceAssist-test" --self-test-views --self-test-report "$PROJECT_ROOT/dist/views-macos-${ARCH}.json"

mkdir -p "$RELEASE_DIR"
rm -f "$ARCHIVE" "$ARCHIVE.sha256"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ARCHIVE"
(
    cd "$RELEASE_DIR"
    shasum -a 256 "$(basename -- "$ARCHIVE")" > "$(basename -- "$ARCHIVE").sha256"
)
printf 'Pacote criado: %s\n' "$ARCHIVE"
