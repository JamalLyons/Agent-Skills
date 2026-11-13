#!/usr/bin/env python3
"""Run each test directory in its own Python process, then portable static checks."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    commands = []
    directories = [ROOT / 'tests', *sorted((ROOT / 'skills').glob('*/tests'))]
    for path in directories:
        if path.is_dir() and any(path.glob('test_*.py')):
            commands.append([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(path), '-v'])
    commands.append([sys.executable, '-B', str(ROOT / 'scripts/evaluate.py'), 'validate'])
    shell_files = [ROOT / 'install.sh', *sorted((ROOT / 'skills').rglob('*.sh'))]
    if shutil.which('bash'):
        commands.extend(['bash', '-n', str(path)] for path in shell_files)
    else:
        print('SKIP Bash syntax checks: bash not installed', flush=True)
    if shutil.which('shellcheck'):
        commands.append(['shellcheck', *map(str, shell_files)])
    else:
        print('SKIP ShellCheck: shellcheck not installed', flush=True)
    failed = 0
    for command in commands:
        print('\nRunning ' + ' '.join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT)
        failed += result.returncode != 0
    print(f'\n{len(commands)} check commands; {failed} failed. Behavioral agent grades are separate.', flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
