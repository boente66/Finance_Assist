#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
PYINSTALLER_BIN="$PROJECT_ROOT/.venv/bin/pyinstaller"
EXECUTABLE="$PROJECT_ROOT/dist/FinanceAssist-test"
ARCH="$(dpkg --print-architecture)"
DEBIAN_VERSION="$(cd "$PROJECT_ROOT" && "$PYTHON_BIN" -c 'from core.version import DEBIAN_VERSION; print(DEBIAN_VERSION)')"
ASSET_VERSION="$(cd "$PROJECT_ROOT" && "$PYTHON_BIN" -c 'from core.version import APP_VERSION; print(APP_VERSION)')"
OUTPUT="$PROJECT_ROOT/dist/finance-assist_${ASSET_VERSION}_${ARCH}.deb"
TARGET_BASE="${FINANCE_ASSIST_DEB_BASE:-ubuntu22.04}"
LIBC_DEPENDENCY="libc6"
GLIB_DEPENDENCY="libglib2.0-0 | libglib2.0-0t64"
TARGET_DESCRIPTION="Compatível com Ubuntu 22.04, 24.04 e 26.04 LTS em arquitetura amd64."
case "$TARGET_BASE" in
    ubuntu22.04) ;;
    ubuntu24.04)
        # Do not relabel a Jammy executable as a Noble build.
        . /etc/os-release
        if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
            printf 'A variante Ubuntu 24.04 deve ser compilada no Ubuntu 24.04.\n' >&2
            exit 1
        fi
        if [[ "${FINANCE_ASSIST_SKIP_PYINSTALLER:-0}" == "1" ]]; then
            printf 'A variante Ubuntu 24.04 exige recompilação do executável.\n' >&2
            exit 1
        fi
        DEBIAN_VERSION="${DEBIAN_VERSION}+ubuntu24.04.1"
        OUTPUT="$PROJECT_ROOT/dist/finance-assist_${ASSET_VERSION}_ubuntu24.04_${ARCH}.deb"
        LIBC_DEPENDENCY="libc6 (>= 2.39)"
        GLIB_DEPENDENCY="libglib2.0-0t64"
        TARGET_DESCRIPTION="Compilado no Ubuntu 24.04; destinado ao Ubuntu 24.04 e Linux Mint 22.x amd64."
        ;;
    *) printf 'Base de pacote desconhecida: %s\n' "$TARGET_BASE" >&2; exit 1 ;;
esac
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
QT_XCB_PLUGIN="$("$PYTHON_BIN" -c 'from PyQt5.QtCore import QLibraryInfo; print(QLibraryInfo.location(QLibraryInfo.PluginsPath) + "/platforms/libqxcb.so")')"
if ldd "$QT_XCB_PLUGIN" | grep -q 'not found'; then
    ldd "$QT_XCB_PLUGIN" >&2
    printf 'Dependências nativas do Qt ausentes; build interrompido.\n' >&2
    exit 1
fi
if [[ "${FINANCE_ASSIST_SKIP_PYINSTALLER:-0}" != "1" ]]; then
    "$PYINSTALLER_BIN" --noconfirm --clean ControleFinanceiro-teste.spec
fi

if [[ ! -x "$EXECUTABLE" ]]; then
    printf 'Executável de teste não foi gerado: %s\n' "$EXECUTABLE" >&2
    exit 1
fi

"$PYTHON_BIN" packaging/verify_archive.py "$EXECUTABLE"
timeout 600s "$EXECUTABLE" --self-test-views --self-test-report "$PROJECT_ROOT/dist/views-linux.json"

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
    -e "s/@LIBC@/$LIBC_DEPENDENCY/g" \
    -e "s/@GLIB@/$GLIB_DEPENDENCY/g" \
    -e "s/@TARGET_DESCRIPTION@/$TARGET_DESCRIPTION/g" \
    "$SCRIPT_DIR/control.in" > "$PACKAGE_ROOT/DEBIAN/control"
chmod 0644 "$PACKAGE_ROOT/DEBIAN/control"

dpkg-deb --root-owner-group --build "$PACKAGE_ROOT" "$OUTPUT"
(
    cd "$(dirname -- "$OUTPUT")"
    sha256sum "$(basename -- "$OUTPUT")" > "$(basename -- "$OUTPUT").sha256"
)

printf 'Pacote criado: %s\n' "$OUTPUT"
printf 'Checksum: %s.sha256\n' "$OUTPUT"
