#!/usr/bin/env python
# coding: utf-8
"""Run the golden-output cases under test/golden/ with jiecc and compare.

Each case is a file test/golden/<name>.iec. The script interprets it with
`jiecc --run` (from the repository root, so __FILE__ is the repository-relative
path), and compares the combined stdout/stderr and the exit code with
test/golden/<name>.out.

Before the comparison the output is normalized so that it does not depend on
the machine:
  - the elapsed-time suffix such as "(123us)" or "(n/a)" becomes "(<time>)",
  - the absolute repository path becomes "<root>",
  - backslashes inside paths that end with ".iec" become slashes.

A case can pass extra jiecc arguments on its FIRST line (a "golden-args"
comment on any other line is reported as an error):
  // golden-args: --max-cycles 50
The default arguments are: --max-cycles 1000 -Werror -Wundef.
A case whose preprocessing is expected to fail is written the same way; its
.out file records the error text and the nonzero exit code.

Files in subdirectories of test/golden/ are not cases; cases can include them.

To add a case, write test/golden/<name>.iec, run this script with --update and
the case path, and review the new .out file (git diff) before committing it.
The .out files contain source line numbers, so editing a case usually needs
--update as well. A run that times out is never written by --update.

Usage:
  python scripts/check_golden.py
  python scripts/check_golden.py --update            # rewrite every .out
  python scripts/check_golden.py test/golden/x.iec   # only the given cases
"""
import argparse
import difflib
import glob
import os
import re
import shlex
import shutil
import subprocess
import sys

_DEFAULT_ARGS = ['--max-cycles', '1000', '-Werror', '-Wundef']
_ARGS_RE = re.compile(r'^\s*//\s*golden-args:(.*)$')
_TIME_RE = re.compile(r'\((?:\d+[a-z]+|n/a)\)')
_PATH_RE = re.compile(r'[\w.:/\\-]+\.iec')


def _repo_root():
    # type: () -> str
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_jiecc(explicit):
    # type: (str) -> str
    candidates = [explicit, os.environ.get('JIECC')]
    for c in candidates:
        if c:
            if os.path.isfile(c):
                return os.path.abspath(c)
            if shutil.which(c):
                return shutil.which(c)
            print('error: jiecc executable not found at {!r}.'.format(c), file=sys.stderr)
            sys.exit(2)
    found = shutil.which('jiecc') or shutil.which('jiecc.exe')
    if found:
        return found
    print('error: jiecc executable not found. Specify it with --jiecc PATH, '
          'set the JIECC environment variable, or add jiecc to PATH.', file=sys.stderr)
    sys.exit(2)


def _case_args(path):
    # type: (str) -> list
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines()
    for line in lines[1:]:
        if _ARGS_RE.match(line):
            raise ValueError('"golden-args" must be on the first line of the case')
    m = _ARGS_RE.match(lines[0]) if lines else None
    extra = shlex.split(m.group(1)) if m else []
    args = list(_DEFAULT_ARGS)
    if any(a == '--max-cycles' or a.startswith('--max-cycles=') for a in extra):
        i = args.index('--max-cycles')
        del args[i:i + 2]
    return args + extra


def normalize(text, root):
    # type: (str, str) -> str
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    for r in {root, root.replace('\\', '/')}:
        text = text.replace(r, '<root>')
    text = _PATH_RE.sub(lambda m: m.group(0).replace('\\', '/'), text)
    text = _TIME_RE.sub('(<time>)', text)
    return text


def run_case(jiecc, root, path, timeout):
    # type: (str, str, str, int) -> tuple
    """Return (normalized output ending with the exit code line, recordable).

    A run that timed out is not recordable: --update must not store it.
    """
    rel = os.path.relpath(path, root).replace('\\', '/')
    cmd = [jiecc, '--run', rel, '-I', root, '-I', os.path.join(root, 'sys')] + _case_args(path)
    recordable = True
    try:
        proc = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout)
        raw = proc.stdout or b''
        code = proc.returncode
    except subprocess.TimeoutExpired as e:
        raw = e.output or b''
        code = 'timeout after {}s'.format(timeout)
        recordable = False
    text = normalize(raw.decode('utf-8', errors='replace'), root)
    if text and not text.endswith('\n'):
        text += '\n'
    return text + '[exit code: {}]\n'.format(code), recordable


def main():
    # type: () -> int
    parser = argparse.ArgumentParser(description='Compare jiecc --run output of '
                                     'test/golden/*.iec with the .out files.')
    parser.add_argument('cases', nargs='*', help='Case files (default: test/golden/*.iec)')
    parser.add_argument('--jiecc', default=None, help='Path to jiecc (default: JIECC env, then PATH)')
    parser.add_argument('--update', action='store_true', help='Rewrite the .out files')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout per case in seconds')
    args = parser.parse_args()

    root = _repo_root()
    jiecc = _resolve_jiecc(args.jiecc)
    cases = [os.path.abspath(c) for c in args.cases] or sorted(
        glob.glob(os.path.join(root, 'test', 'golden', '*.iec')))
    if not cases:
        print('error: no golden cases found.', file=sys.stderr)
        return 2

    failed = []
    for path in cases:
        expected_path = os.path.splitext(path)[0] + '.out'
        name = os.path.relpath(path, root).replace('\\', '/')
        try:
            actual, recordable = run_case(jiecc, root, path, args.timeout)
        except (OSError, ValueError) as e:
            failed.append(name)
            print('FAIL: {} ({})'.format(name, e))
            continue
        if args.update:
            if not recordable:
                failed.append(name)
                print('FAIL: {} (timed out; not written)'.format(name))
                sys.stdout.write(actual)
                continue
            with open(expected_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(actual)
            print('updated: {}'.format(name))
            continue
        if not os.path.isfile(expected_path):
            failed.append(name)
            print('FAIL: {} (no .out file; run with --update)'.format(name))
            continue
        with open(expected_path, encoding='utf-8') as f:
            expected = f.read()
        if expected != actual:
            failed.append(name)
            print('FAIL: {}'.format(name))
            sys.stdout.writelines(difflib.unified_diff(
                expected.splitlines(True), actual.splitlines(True),
                fromfile=name + ' (expected)', tofile=name + ' (actual)'))
    if not args.cases:
        for out in sorted(glob.glob(os.path.join(root, 'test', 'golden', '*.out'))):
            if not os.path.isfile(os.path.splitext(out)[0] + '.iec'):
                name = os.path.relpath(out, root).replace('\\', '/')
                failed.append(name)
                print('FAIL: {} has no matching .iec case'.format(name))
    if args.update:
        if failed:
            print('{} golden cases could not be updated.'.format(len(failed)))
            return 1
        print('Review the changes with git diff before committing.')
        return 0
    if failed:
        print('{} of {} golden cases differ.'.format(len(failed), len(cases)))
        return 1
    print('OK: {} golden cases matched.'.format(len(cases)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
