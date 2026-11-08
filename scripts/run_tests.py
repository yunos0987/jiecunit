#!/usr/bin/env python
# coding: utf-8
"""Compile and run the JiecUnit test suites with jiecc.

Compiles each suite for every requested target (to catch vendor-specific
compile errors) and, separately, interprets and runs each suite with the
jiecc jier interpreter (`jiecc --run`), parsing its stdout summary lines
to determine pass/fail/skip counts. It also runs scripts/check_macro_expansion.py
to verify that the optional-message assertion macros stay equivalent to their
deprecated *_MSG aliases.

JiecUnit requires Jiecc 9.4.0 or later (src/jiecunit_config.iec stops the
preprocessor with {#error} on older compilers). The exit code of
`jiecc --run` reflects the test result (JiecUnitMain calls halt after the
summary: 0 when every test passed, 1 on failures or a fatal registration
error). This script judges a run by its stdout summary lines and
additionally fails a run whose exit code is not 0.

The compile phase runs up to --jobs jiecc processes at the same time
(default and maximum: 4); the run and macro-check phases run one at a time.
Every compile and run passes -Werror and -Wundef.

An interpreted run whose UNDEFINED_SYMBOL error is only visible in the
output text is still possible, so this script also treats any "error: "
line in the compile/run output as a failure, independent of the process
exit code.

The macro-check phase runs by default; pass --skip-macro-check to disable it.
--compile-only and --run-only both skip the macro-check phase as well, since
it is neither a compile nor a run step.

Usage:
  python scripts/run_tests.py
  python scripts/run_tests.py --jiecc /path/to/jiecc.exe
  python scripts/run_tests.py test/test.iec --targets OMRON,STD
  python scripts/run_tests.py --compile-only
  python scripts/run_tests.py --compile-only --jobs 2
  python scripts/run_tests.py --run-only --max-cycles 500
  python scripts/run_tests.py --skip-macro-check
"""
import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import tempfile

_DEFAULT_SUITES = ['test/test.iec', 'samples/sample.iec']
_DEFAULT_TARGETS = ['OMRON', 'KEYENCE', 'CODESYS', 'MITSUBISHI', 'STD']

# Upper limit (and default) of --jobs. More concurrent jiecc processes made
# the antivirus scan of each new process overload the OS.
_MAX_JOBS = 4

# Warning flags passed to every compile and run. -Wundef is accepted by
# jiecc 9.4.0 and later, which JiecUnit requires anyway.
_WARNING_FLAGS = ['-Werror', '-Wundef']

_RE_TESTS_RAN = re.compile(r'^\[========\] (\d+) tests ran\.')
_RE_PASSED = re.compile(r'^\[ PASSED \] (\d+) tests\.')
_RE_SKIPPED = re.compile(r'^\[ SKIPPED\] (\d+) tests\.')
_RE_FAILED_LINE = re.compile(r'\[ FAILED \]')
_RE_ERROR_LINE = re.compile(r'\[  ERROR \]')
# Older jiecc could exit 0 while still reporting an error on stderr (e.g.
# PP34 during -c), and --run can print UNDEFINED_SYMBOL text, so scan the output text for
# "error: " lines regardless of the process exit code.
_RE_ERROR_TEXT = re.compile(r'(?m)^\S.*: error: | error: ')


def _repo_root():
    # type: () -> str
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _is_executable_path(path):
    # type: (str) -> bool
    return os.path.isfile(path) or shutil.which(path) is not None


def _resolve_jiecc(explicit):
    # type: (str) -> str
    if explicit:
        if _is_executable_path(explicit):
            return explicit
        print(
            'error: jiecc executable not found at {!r} '
            '(from --jiecc).'.format(explicit),
            file=sys.stderr)
        sys.exit(2)
    from_env = os.environ.get('JIECC')
    if from_env:
        if _is_executable_path(from_env):
            return from_env
        print(
            'error: jiecc executable not found at {!r} '
            '(from the JIECC environment variable).'.format(from_env),
            file=sys.stderr)
        sys.exit(2)
    found = shutil.which('jiecc') or shutil.which('jiecc.exe')
    if found:
        return found
    print(
        'error: jiecc executable not found. '
        'Specify it with --jiecc PATH, set the JIECC environment variable, '
        'or add jiecc to PATH.',
        file=sys.stderr)
    sys.exit(2)


def _suite_stem(suite):
    # type: (str) -> str
    return os.path.splitext(os.path.basename(suite))[0]


def compile_suite(jiecc, root, suite, target, outdir, timeout, flags):
    # type: (str, str, str, str, str, int, list) -> tuple
    out_xml = os.path.join(outdir, '{}.{}.xml'.format(_suite_stem(suite), target))
    cmd = [
        jiecc, '-c', suite,
        '-I', root,
        '-I', os.path.join(root, 'sys'),
        '-t', target,
        '-o', out_xml,
    ] + list(flags)
    try:
        proc = subprocess.run(
            cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, 'timed out after {}s'.format(timeout)
    output = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ''
    error_lines = [line for line in output.splitlines() if _RE_ERROR_TEXT.search(line)]
    if proc.returncode != 0:
        return False, output.strip() or 'exit code {}'.format(proc.returncode)
    if error_lines:
        return False, (
            'exit code 0 but output contains "error: " line(s) (jiecc can '
            'emit an XML file despite a preprocessing error):\n'
            + '\n'.join(error_lines))
    return True, ''


def run_suite(jiecc, root, suite, max_cycles, timeout, flags):
    # type: (str, str, str, int, int, list) -> tuple
    cmd = [
        jiecc, '--run', suite,
        '-I', root,
        '-I', os.path.join(root, 'sys'),
        '--max-cycles', str(max_cycles),
    ] + list(flags)
    try:
        proc = subprocess.run(
            cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, 'timed out after {}s'.format(timeout)
    output = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ''
    lines = output.splitlines()

    error_lines = [line for line in lines if _RE_ERROR_TEXT.search(line)]
    if error_lines:
        return False, 'output contains "error: " line(s):\n' + '\n'.join(error_lines)

    ran = None
    passed = None
    skipped = 0
    for line in lines:
        m = _RE_TESTS_RAN.match(line)
        if m:
            ran = int(m.group(1))
            continue
        m = _RE_PASSED.match(line)
        if m:
            passed = int(m.group(1))
            continue
        m = _RE_SKIPPED.match(line)
        if m:
            skipped = int(m.group(1))
            continue

    if ran is None:
        return False, 'no "[========] N tests ran." line found in output:\n' + output
    if passed is None:
        return False, 'no "[ PASSED ] N tests." line found in output:\n' + output
    if any(_RE_FAILED_LINE.search(line) for line in lines):
        return False, 'output contains "[ FAILED ]":\n' + output
    if any(_RE_ERROR_LINE.search(line) for line in lines):
        return False, 'output contains "[  ERROR ]":\n' + output
    if passed + skipped != ran:
        return False, 'passed ({}) + skipped ({}) != ran ({})'.format(passed, skipped, ran)
    # jiecc --run exits 1 when a test failed (JiecUnitMain calls halt).
    if proc.returncode != 0:
        return False, 'exit code {}:\n'.format(proc.returncode) + output

    summary = '{} ran, {} passed, {} skipped'.format(ran, passed, skipped)
    return True, summary


def run_macro_check(jiecc, root, timeout):
    # type: (str, str, int) -> tuple
    script = os.path.join(root, 'scripts', 'check_macro_expansion.py')
    cmd = [sys.executable, script, '--jiecc', jiecc]
    try:
        proc = subprocess.run(
            cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, 'timed out after {}s'.format(timeout)
    output = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ''
    if proc.returncode != 0:
        return False, output.strip() or 'exit code {}'.format(proc.returncode)
    ok_lines = [line for line in output.strip().splitlines() if line.startswith('OK:')]
    if ok_lines:
        return True, '; '.join(ok_lines)
    return True, output.strip().splitlines()[-1] if output.strip() else ''


def main():
    # type: () -> int
    parser = argparse.ArgumentParser(
        description='Compile and run the JiecUnit test suites with jiecc. '
                     'A run is judged by its stdout summary lines and also '
                     'fails when jiecc exits with a nonzero code (jiecc --run '
                     'exits 1 on test failures). Any "error: " line in the '
                     'compile/run output also fails the check, regardless of '
                     'the exit code. Compiles and runs pass -Werror and -Wundef. '
                     'Requires Jiecc 9.4.0 or later.')
    parser.add_argument('suites', nargs='*', default=_DEFAULT_SUITES,
                        help='Test suite files, relative to the repository root '
                             '(default: {})'.format(', '.join(_DEFAULT_SUITES)))
    parser.add_argument('--jiecc', default=None,
                        help='Path to the jiecc executable. '
                             'Falls back to the JIECC environment variable, '
                             'then to jiecc/jiecc.exe on PATH.')
    parser.add_argument('--max-cycles', type=int, default=200,
                        help='Maximum scan cycles for jiecc --run (default: 200)')
    parser.add_argument('--targets', default=','.join(_DEFAULT_TARGETS),
                        help='Comma-separated list of compile targets '
                             '(default: {})'.format(','.join(_DEFAULT_TARGETS)))
    parser.add_argument('--outdir', default=None,
                        help='Directory for compiled XML output. '
                             'Default: a temporary directory, removed on exit.')
    parser.add_argument('--compile-only', action='store_true',
                        help='Only compile the suites; do not run them.')
    parser.add_argument('--run-only', action='store_true',
                        help='Only run the suites; do not compile them.')
    parser.add_argument('--skip-macro-check', action='store_true',
                        help='Skip the scripts/check_macro_expansion.py phase '
                             '(also skipped automatically when --compile-only '
                             'or --run-only is given).')
    parser.add_argument('--timeout', type=int, default=600,
                        help='Timeout in seconds for each jiecc invocation (default: 600)')
    parser.add_argument('--jobs', type=int, default=_MAX_JOBS,
                        help='Number of jiecc processes the compile phase runs at '
                             'the same time, 1 to {0} (default: {0}). The run '
                             'and macro-check phases always run one at a '
                             'time.'.format(_MAX_JOBS))
    args = parser.parse_args()

    if args.compile_only and args.run_only:
        print('error: --compile-only and --run-only are mutually exclusive.', file=sys.stderr)
        return 2
    if not 1 <= args.jobs <= _MAX_JOBS:
        print('error: --jobs must be between 1 and {}.'.format(_MAX_JOBS), file=sys.stderr)
        return 2

    jiecc = _resolve_jiecc(args.jiecc)
    root = _repo_root()
    targets = [t.strip() for t in args.targets.split(',') if t.strip()]

    outdir = args.outdir
    cleanup_outdir = False
    if outdir is None:
        outdir = tempfile.mkdtemp(prefix='jiecunit_run_tests_')
        cleanup_outdir = True
    else:
        os.makedirs(outdir, exist_ok=True)

    results = []
    all_ok = True

    do_compile = not args.run_only
    do_run = not args.compile_only
    do_macro_check = not args.run_only and not args.compile_only and not args.skip_macro_check

    flags = list(_WARNING_FLAGS)

    try:
        if do_compile:
            jobs = [(suite, target) for suite in args.suites for target in targets]
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs)
            try:
                futures = [
                    pool.submit(compile_suite, jiecc, root, suite, target, outdir,
                                args.timeout, flags)
                    for suite, target in jobs]
                # Collect in submission order so the table order does not
                # depend on which compile finishes first.
                for (suite, target), future in zip(jobs, futures):
                    ok, detail = future.result()
                    results.append(('compile', suite, target, ok, detail))
                    all_ok = all_ok and ok
            finally:
                # On Ctrl-C (or any other exception) do not start the queued
                # compiles; only the ones already running finish.
                pool.shutdown(wait=True, cancel_futures=True)

        if do_run:
            for suite in args.suites:
                ok, detail = run_suite(jiecc, root, suite, args.max_cycles, args.timeout, flags)
                results.append(('run', suite, '-', ok, detail))
                all_ok = all_ok and ok

        if do_macro_check:
            ok, detail = run_macro_check(jiecc, root, args.timeout)
            results.append(('macro-check', 'jiecunit.iec', '-', ok, detail))
            all_ok = all_ok and ok
    finally:
        if cleanup_outdir:
            shutil.rmtree(outdir, ignore_errors=True)

    print('{:<11} {:<24} {:<12} {:<6} {}'.format('PHASE', 'SUITE', 'TARGET', 'OK', 'DETAIL'))
    for phase, suite, target, ok, detail in results:
        status = 'OK' if ok else 'FAIL'
        first_line = detail.splitlines()[0] if detail else ''
        print('{:<11} {:<24} {:<12} {:<6} {}'.format(phase, suite, target, status, first_line))
        if not ok and detail:
            for line in detail.splitlines()[1:]:
                print('         ' + line)

    if all_ok:
        print('All checks passed.')
        return 0
    else:
        print('One or more checks failed.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
