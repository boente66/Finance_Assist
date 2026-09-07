"""Use one coherent, redistributable MSVC runtime in Windows bundles."""
from pathlib import Path


def replace_runtime(binaries, runtime_dir):
    directory = Path(runtime_dir)
    runtime = {p.name.lower(): p for p in directory.glob('*.dll')}
    required = {'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll'}
    if not required.issubset(runtime):
        raise RuntimeError('Diretório MSVC redistribuível incompleto')
    result = []
    for destination, source, kind in binaries:
        replacement = runtime.get(Path(destination).name.lower())
        result.append((destination, str(replacement) if replacement else source, kind))
    destinations = {item[0].lower() for item in result}
    for name, source in sorted(runtime.items()):
        if name not in destinations:
            result.append((source.name, str(source), 'BINARY'))
    return result
