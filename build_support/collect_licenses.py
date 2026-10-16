"""Collect the installed distributions' shipped notices for binary redistribution."""
from pathlib import Path
import importlib.metadata
import json
import shutil
import sys

def collect():
    root = Path(__file__).resolve().parent.parent
    destination = root / 'work' / 'third-party-licenses'
    if destination.exists():shutil.rmtree(destination)
    destination.mkdir(parents=True)
    packages = []
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata['Name']
        packages.append({'name': name, 'version': distribution.version,
                         'license': distribution.metadata.get('License-Expression') or distribution.metadata.get('License'),
                         'source': distribution.metadata.get_all('Project-URL') or []})
        for file in distribution.files or []:
            if '..' in file.parts or file.is_absolute():continue
            if not any(word in str(file).lower() for word in ('license', 'copying', 'copyright', 'notice')):continue
            source = Path(distribution.locate_file(file))
            if source.is_file():
                target = destination / name / file
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    for name in ('LICENSE.txt', 'LICENSE'):
        source = Path(sys.base_prefix) / name
        if source.is_file():shutil.copy2(source, destination / 'Python-LICENSE.txt');break
    shutil.copytree(root / 'docs/licenses', destination / 'Qt-LGPL', dirs_exist_ok=True)
    shutil.copy2(root / 'docs/THIRD_PARTY.md', destination / 'README.md')
    (destination / 'packages.json').write_text(json.dumps(sorted(packages, key=lambda p:p['name'].lower()), indent=2)+'\n')
    return destination

if __name__ == '__main__':print(collect())
