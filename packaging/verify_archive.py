"""Fail a build when a source view is absent from the actual frozen archive."""
from pathlib import Path
import sys

from PyInstaller.archive.readers import CArchiveReader


def verify(executable):
    root = Path(__file__).resolve().parents[1]
    archive = CArchiveReader(str(executable)).open_embedded_archive('PYZ.pyz')
    expected = {'views.' + path.stem for path in (root / 'views').glob('*.py')
                if path.stem != '__init__'}
    missing = sorted(expected - set(archive.toc))
    if missing:
        raise RuntimeError('Views ausentes do executável: ' + ', '.join(missing))
    print(f'Inventário aprovado: {len(expected)} módulos de views no executável.')


if __name__ == '__main__':
    verify(sys.argv[1])
