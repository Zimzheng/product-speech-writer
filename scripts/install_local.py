#!/usr/bin/env python3
"""Copy this skill into a supported local agent directory without overwriting."""
import argparse
import shutil
from pathlib import Path

ROOTS = {'codex': '.agents/skills', 'claude-code': '.claude/skills',
         'cursor': '.cursor/skills', 'copilot': '.copilot/skills',
         'opencode': '.config/opencode/skills'}
PROJECT_ROOTS = dict(ROOTS, copilot='.github/skills', opencode='.opencode/skills')
ITEMS = ('SKILL.md', 'LICENSE', 'README.md', 'README.en.md', '.gitignore',
         'agents', 'references', 'scripts', 'assets', 'examples', 'tests')


def install(source, destination):
    source, destination = source.resolve(), destination.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f'Target already exists; not overwritten: {destination}')
    if not (source / 'SKILL.md').is_file():
        raise ValueError('Source does not contain SKILL.md')
    destination.mkdir(parents=True)
    for name in ITEMS:
        item = source / name
        if item.is_dir():
            shutil.copytree(item, destination / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
        elif item.is_file():
            shutil.copy2(item, destination / name)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool', choices=ROOTS)
    parser.add_argument('--scope', choices=('user', 'project'), default='user')
    parser.add_argument('--project', type=Path)
    parser.add_argument('--destination', type=Path,
                        help='Explicit skill folder; bypass tool directory selection')
    args = parser.parse_args()
    if args.destination:
        target = args.destination
    elif not args.tool:
        parser.error('--tool or --destination is required')
    elif args.scope == 'project':
        if not args.project:
            parser.error('--project is required for project scope')
        target = args.project / PROJECT_ROOTS[args.tool] / 'product-speech-writer'
    else:
        target = Path.home() / ROOTS[args.tool] / 'product-speech-writer'
    try:
        print(install(Path(__file__).resolve().parents[1], target))
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
