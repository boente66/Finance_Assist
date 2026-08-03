#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
PYINSTALLER_BIN="$PROJECT_ROOT/.venv/bin/pyinstaller"
EXECUTABLE="$PROJECT_ROOT/dist/ControleFinanceiro-teste"
ARCH="$(dpkg --print-architecture)"
DEBIAN_VERSION="$(cd "$PROJECT_ROOT" && "$PYTHON_BIN" -c 'from core.version import DEBIAN_VERSION; print(DEBIAN_VERSION)')"
ASSET_VERSION="$(cd "$PROJECT_ROOT" && "$PYTHON_BIN" -c 'from core.version import APP_VERSION; print(APP_VERSION)')"
OUTPUT="$PROJECT_ROOT/dist/finance-assist_${ASSET_VERSION}_${ARCH}.deb"
PACKAGE_ROOT="$(mktemp -d /tmp/finance-assist-deb.XXXXXX)"
chmod 0755 "$PACKAGE_ROOT"

cleanup() {
    case "$PACKAGE_ROOT" in
        /tmp/finance-assist-deb.*) rm -rf -- "$PACKAGE_ROOT" ;;
        *) printf 'Diretório temporário inesperado; limpeza ignorada: %s\n' "$PACKAGE_ROOT" >&2 ;;
    esac
}
trap cleanup EXIT

if [[ ! -x "$PYTHON_BIN" || ! -x "$PYINSTALLER_BIN" ]]; then
    printf 'Ambiente de build ausente em %s\n' "$PROJECT_ROOT/.venv" >&2
    exit 1
fi

cd "$PROJECT_ROOT"
if [[ "${FINANCE_ASSIST_SKIP_PYINSTALLER:-0}" != "1" ]]; then
    "$PYINSTALLER_BIN" --noconfirm --clean ControleFinanceiro-teste.spec
fi

if [[ ! -x "$EXECUTABLE" ]]; then
    printf 'Executável de teste não foi gerado: %s\n' "$EXECUTABLE" >&2
    exit 1
fi

install -d \
    "$PACKAGE_ROOT/DEBIAN" \
    "$PACKAGE_ROOT/opt/finance-assist" \
    "$PACKAGE_ROOT/usr/bin" \
    "$PACKAGE_ROOT/usr/share/applications" \
    "$PACKAGE_ROOT/usr/share/icons/hicolor/scalable/apps" \
    "$PACKAGE_ROOT/usr/share/doc/finance-assist-test"

install -m 0755 "$EXECUTABLE" "$PACKAGE_ROOT/opt/finance-assist/finance-assist-test"
ln -s /opt/finance-assist/finance-assist-test "$PACKAGE_ROOT/usr/bin/finance-assist-test"
install -m 0644 "$SCRIPT_DIR/finance-assist.desktop" "$PACKAGE_ROOT/usr/share/applications/finance-assist-test.desktop"
install -m 0644 "$PROJECT_ROOT/assets/icons/finance_assist.svg" "$PACKAGE_ROOT/usr/share/icons/hicolor/scalable/apps/finance-assist.svg"
install -m 0644 "$PROJECT_ROOT/LICENSE" "$PACKAGE_ROOT/usr/share/doc/finance-assist-test/copyright"

INSTALLED_SIZE="$(du -sk "$PACKAGE_ROOT" | cut -f1)"
sed \
    -e "s/@VERSION@/$DEBIAN_VERSION/g" \
    -e "s/@ARCH@/$ARCH/g" \
    -e "s/@INSTALLED_SIZE@/$INSTALLED_SIZE/g" \
    "$SCRIPT_DIR/control.in" > "$PACKAGE_ROOT/DEBIAN/control"
chmod 0644 "$PACKAGE_ROOT/DEBIAN/control"

dpkg-deb --root-owner-group --build "$PACKAGE_ROOT" "$OUTPUT"
(
    cd "$(dirname -- "$OUTPUT")"
    sha256sum "$(basename -- "$OUTPUT")" > "$(basename -- "$OUTPUT").sha256"
)

printf 'Pacote criado: %s\n' "$OUTPUT"
printf 'Checksum: %s.sha256\n' "$OUTPUT"
