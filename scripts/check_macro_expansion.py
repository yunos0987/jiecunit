#!/usr/bin/env python
# coding: utf-8
"""Verify that every public assertion macro accepts an optional message argument.

For each public macro pair NAME / NAME_MSG declared in jiecunit.iec, this script
checks with the jiecc preprocessor (`jiecc -E`) that:

  NAME(v1..vK)             expands exactly like NAME_MSG(v1..vK, '')
  NAME(v1..vK, message)    expands exactly like NAME_MSG(v1..vK, message)

so the deprecated _MSG form and the new optional-message form stay equivalent.
It also verifies that:

  * the expansion reports the call site's own source line (via __LINE__),
    not some other line, and
  * a wrong argument count is rejected, through one of three negative-case
    groups, guarded by a fourth positive-control group that is not itself
    counted among the negative cases verified:
      - _EXCESS_CASES: too many trailing arguments expands to the deliberate
        JIECUNIT_ASSERTION_TAKES_<lo>_OR_<hi>_ARGUMENTS syntax error.
      - _MISSING_CASES: too few required arguments is rejected by the
        preprocessor itself with a `PP34: Argument count mismatch` error.
      - _EMPTY_CASES: no arguments at all is accepted by the preprocessor
        but fails to compile with `jiecc -c`, reporting `INVALID_SYNTAX`.
      - _COMPILE_CONTROL: a positive control (a valid call using the same
        wrapper as _EMPTY_CASES) that must compile successfully; if it does
        not, every _EMPTY_CASES probe is skipped rather than verified,
        since a broken wrapper could otherwise make _EMPTY_CASES pass for
        the wrong reason.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

_DEF_RE = re.compile(r'^\{#define\s+([A-Za-z_][A-Za-z0-9_]*)_MSG\(([^)]*)\)')
_MESSAGE = "'a, b (c)'"
_VALUES = ['v1', 'v2', 'v3', 'v4']

# [M5] Too-many-argument probes: (expression, lo, hi).
# lo/hi are the correct min/max *total* argument counts for the macro under
# test, and must match the (lo, hi) pair the macro's _JIECUNIT_BAD_ARGC_ call
# reports. These all preprocess successfully and expand to the sentinel.
_EXCESS_CASES = [
    ("EXPECT_TRUE(a, b, c)", 1, 2),
    ("EXPECT_EQ_INT(1, 2, 3, 4)", 2, 3),
    ("EXPECT_EQ_INT(1, 1, 2, 3, 4, 5)", 2, 3),
    ("EXPECT_EQ_INT(1, 2, 3, 4, 5, 6, 7, 8, 9)", 2, 3),
    ("EXPECT_EQ_INT(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)", 2, 3),
    ("EXPECT_EQ_INT(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18)", 2, 3),
    ("EXPECT_NEAR(1.0, 2.0, 0.1, 'm', 9)", 3, 4),
    ("FAIL('a', 'b')", 0, 1),
    ("FAIL('a', 'b', 'c', 'd')", 0, 1),
    ("ADD_FAILURE('a', 'b')", 0, 1),
]

# [M7] Too-few-argument probes. The public macros declare their required
# parameters by name, so jiecc rejects these in the preprocessor itself (PP34)
# and each one needs its own `jiecc -E` run that is expected to fail.
_MISSING_CASES = [
    "EXPECT_EQ_INT(1)",
    "EXPECT_NEAR(1.0, 2.0)",
]

# [M8] Empty-argument probes. `EXPECT_TRUE()` passes one empty argument, which
# satisfies the preprocessor but expands to `actual:=,`, so it is caught by
# `jiecc -c` at the call site instead.
_EMPTY_CASES = [
    "EXPECT_TRUE()",
    "EXPECT_FALSE()",
]

# [M8] Positive control: the same wrapper with a valid call must compile, so a
# broken wrapper cannot make _EMPTY_CASES pass for the wrong reason.
_COMPILE_CONTROL = "EXPECT_FALSE(b)"


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _is_executable_path(path):
    return os.path.isfile(path) or shutil.which(path) is not None


def _resolve_jiecc(explicit):
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


def _collect_pairs(header):
    pairs = []
    with open(header, encoding='utf-8') as f:
        for line in f:
            m = _DEF_RE.match(line)
            if m:
                name = m.group(1)
                params = [p.strip() for p in m.group(2).split(',') if p.strip()]
                pairs.append((name, len(params) - 1))
    return pairs


def _probe_source(pairs, negatives):
    # type: (list, list) -> tuple
    """Build the probe source. Returns (text, line_of_key) where line_of_key
    maps each probe key to the 1-based source line of its expression."""
    lines = ['{#include <jiecunit.iec>}']
    line_of_key = {}

    def _emit(key, expr):
        lines.append('PROBE_BEGIN_{}'.format(key))
        lines.append(expr)
        line_of_key[key] = len(lines)  # 1-based line number of expr
        lines.append('PROBE_END_{}'.format(key))

    for i, (name, arity) in enumerate(pairs):
        args = ', '.join(_VALUES[:arity])
        for kind, expr in (
                ('new_no_msg', '{}({})'.format(name, args)),
                ('old_no_msg', '{}({}{}'.format(name + '_MSG', args + ', ' if args else '', "''") + ')'),
                ('new_msg', '{}({}{})'.format(name, args + ', ' if args else '', _MESSAGE)),
                ('old_msg', '{}({}{})'.format(name + '_MSG', args + ', ' if args else '', _MESSAGE))):
            _emit('{}_{}'.format(i, kind), expr)

    for j, (expr, lo, hi) in enumerate(negatives):
        _emit('neg_{}'.format(j), expr)

    return '\n'.join(lines) + '\n', line_of_key


def _split_blocks(text):
    blocks = {}
    lineno = {}
    key = None
    buf = []
    start_line = None
    for lineno_1based, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        if s.startswith('PROBE_BEGIN_'):
            key = s[len('PROBE_BEGIN_'):]
            buf = []
            start_line = lineno_1based
        elif s.startswith('PROBE_END_'):
            if key is not None:
                body = '\n'.join(x for x in (b.strip() for b in buf) if x)
                blocks[key] = body
                lineno[key] = start_line
            key = None
        elif key is not None:
            buf.append(line)
    return blocks, lineno


def _run_jiecc_preprocess(jiecc, root, probe_path):
    proc = subprocess.run(
        [jiecc, '-E', probe_path, '-I', root, '-I', os.path.join(root, 'sys')],
        capture_output=True, text=True)
    return proc


def _write(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def _run_jiecc_compile(jiecc, root, path, out_xml):
    return subprocess.run(
        [jiecc, '-c', path, '-I', root, '-I', os.path.join(root, 'sys'),
         '-o', out_xml],
        capture_output=True, text=True)


# Line number the probed expression sits on in each generated probe file.
_MISSING_PROBE_LINE = 2
_EMPTY_PROBE_LINE = 4


def _compile_probe(expr):
    """A minimal compilable test whose assertion sits on _EMPTY_PROBE_LINE."""
    return ('{#include <jiecunit.iec>}\n'
            'TEST_S(t)\n'
            '{st}\n'
            '%s;\n'
            'EOT();\n'
            '{end}\n'
            'END_TEST_S\n' % expr)


def _check_missing_cases(jiecc, root, tmpdir):
    """[M7] Too few arguments must be rejected by the preprocessor (PP34)."""
    out = []
    for j, expr in enumerate(_MISSING_CASES):
        path = os.path.join(tmpdir, 'missing_{}.iec'.format(j))
        _write(path, '{#include <jiecunit.iec>}\n%s\n' % expr)
        proc = _run_jiecc_preprocess(jiecc, root, path)
        where = ':{}.'.format(_MISSING_PROBE_LINE)
        if proc.returncode == 0:
            out.append('{}: expected `jiecc -E` to fail, but it succeeded'.format(expr))
        elif 'PP34' not in proc.stderr:
            out.append('{}: expected PP34 in stderr, got: {}'.format(
                expr, proc.stderr.strip()[:200]))
        elif where not in proc.stderr:
            out.append('{}: expected the error to point at line {}, got: {}'.format(
                expr, _MISSING_PROBE_LINE, proc.stderr.strip()[:200]))
    return out


def _check_empty_cases(jiecc, root, tmpdir):
    """[M8] An empty argument list must still fail at the call site.

    Returns (control_error, failures). control_error is None when the
    _COMPILE_CONTROL call compiled successfully; otherwise it is a
    description of why it did not, and failures is empty because every
    _EMPTY_CASES probe is skipped (not verified) rather than risking a
    false pass caused by a broken wrapper.
    """
    control = os.path.join(tmpdir, 'control.iec')
    _write(control, _compile_probe(_COMPILE_CONTROL))
    proc = _run_jiecc_compile(jiecc, root, control,
                              os.path.join(tmpdir, 'control.xml'))
    if proc.returncode != 0:
        control_error = 'control {}: expected `jiecc -c` to succeed, got: {}'.format(
            _COMPILE_CONTROL, proc.stderr.strip()[:200])
        return control_error, []

    out = []
    where = ':{}.'.format(_EMPTY_PROBE_LINE)
    for j, expr in enumerate(_EMPTY_CASES):
        path = os.path.join(tmpdir, 'empty_{}.iec'.format(j))
        _write(path, _compile_probe(expr))
        proc = _run_jiecc_compile(jiecc, root, path,
                                  os.path.join(tmpdir, 'empty_{}.xml'.format(j)))
        if proc.returncode == 0:
            out.append('{}: expected `jiecc -c` to fail, but it succeeded'.format(expr))
        elif 'INVALID_SYNTAX' not in proc.stderr:
            out.append('{}: expected INVALID_SYNTAX in stderr, got: {}'.format(
                expr, proc.stderr.strip()[:200]))
        elif where not in proc.stderr:
            out.append('{}: expected the error to point at line {}, got: {}'.format(
                expr, _EMPTY_PROBE_LINE, proc.stderr.strip()[:200]))
    return None, out


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--jiecc', default=None,
                        help='Path to the jiecc executable. '
                             'Falls back to the JIECC environment variable, '
                             'then to jiecc/jiecc.exe on PATH.')
    args = parser.parse_args()
    jiecc = _resolve_jiecc(args.jiecc)
    root = _repo_root()
    header = os.path.join(root, 'jiecunit.iec')

    pairs = _collect_pairs(header)
    if not pairs:
        print('error: no NAME_MSG macro pairs found in jiecunit.iec', file=sys.stderr)
        return 2

    probe_text, expr_line_of_key = _probe_source(pairs, _EXCESS_CASES)

    tmpdir = tempfile.mkdtemp(prefix='jiecunit_check_macros_')
    probe = os.path.join(tmpdir, 'probe.iec')
    try:
        with open(probe, 'w', encoding='utf-8', newline='\n') as f:
            f.write(probe_text)
        proc = _run_jiecc_preprocess(jiecc, root, probe)
        if proc.returncode != 0 or 'error:' in proc.stderr:
            print(proc.stdout[-2000:])
            print(proc.stderr[-2000:], file=sys.stderr)
            print('error: jiecc -E failed.', file=sys.stderr)
            return 1
        blocks, out_lineno = _split_blocks(proc.stdout)
        missing_failures = _check_missing_cases(jiecc, root, tmpdir)
        control_error, empty_failures = _check_empty_cases(jiecc, root, tmpdir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    failures = []
    line_check_failures = []
    line_checked = 0

    # [M6] __LINE__ verification: check the expansion's own line:=N marker
    # against the probe source's actual line number, before normalizing it
    # away for the equivalence comparison below.
    _LINE_RE = re.compile(r'line:=(\d+)')

    def _check_line(key):
        nonlocal line_checked
        body = blocks.get(key)
        if body is None:
            return
        m = _LINE_RE.search(body)
        if not m:
            return
        line_checked += 1
        actual = int(m.group(1))
        expected = expr_line_of_key[key]
        if actual != expected:
            line_check_failures.append(
                '{}: line:={} but the call site is on line {}'.format(key, actual, expected))

    for i, (name, arity) in enumerate(pairs):
        for kind in ('new_no_msg', 'old_no_msg', 'new_msg', 'old_msg'):
            _check_line('{}_{}'.format(i, kind))

    expected_line_checked = 4 * len(pairs)
    if line_checked != expected_line_checked:
        line_check_failures.append(
            'expected to verify __LINE__ for {} call sites but only found a '
            'line:= marker in {} (some probe blocks were missing one)'.format(
                expected_line_checked, line_checked))

    for i, (name, arity) in enumerate(pairs):
        for kind in ('no_msg', 'msg'):
            new = blocks.get('{}_new_{}'.format(i, kind))
            old = blocks.get('{}_old_{}'.format(i, kind))
            if new is None or old is None:
                failures.append('{}: probe block missing ({})'.format(name, kind))
                continue
            if not new.strip() or not old.strip():
                failures.append('{}: probe block empty ({})'.format(name, kind))
                continue
            new_norm = _LINE_RE.sub('line:=#', new)
            old_norm = _LINE_RE.sub('line:=#', old)
            if new_norm != old_norm:
                failures.append('{} ({}):\n  new: {}\n  old: {}'.format(
                    name, kind, new.replace('\n', ' '), old.replace('\n', ' ')))

    # [M5] Negative (wrong-argument-count) cases.
    negative_failures = []
    for j, (expr, lo, hi) in enumerate(_EXCESS_CASES):
        key = 'neg_{}'.format(j)
        body = blocks.get(key)
        if body is None:
            negative_failures.append('{}: probe block missing'.format(expr))
            continue
        expected_marker = 'JIECUNIT_ASSERTION_TAKES_{}_OR_{}_ARGUMENTS'.format(lo, hi)
        if expected_marker not in body:
            negative_failures.append(
                '{}: expected {!r} in expansion, got: {}'.format(
                    expr, expected_marker, body.replace('\n', ' ')))

    negative_failures.extend(missing_failures)
    negative_failures.extend(empty_failures)

    total_neg = len(_EXCESS_CASES) + len(_MISSING_CASES) + len(_EMPTY_CASES)
    skipped = len(_EMPTY_CASES) if control_error else 0
    verified = total_neg - skipped

    if failures or line_check_failures or negative_failures or control_error:
        for f in failures:
            print('FAIL (equivalence) ' + f)
        for f in line_check_failures:
            print('FAIL (__LINE__) ' + f)
        if control_error:
            print('FAIL (control) ' + control_error)
        for f in negative_failures:
            print('FAIL (negative case) ' + f)
        print('{} of {} macros mismatched; {} __LINE__ mismatches; '
              '{} of {} negative cases failed.'.format(
                  len(failures), len(pairs), len(line_check_failures),
                  len(negative_failures), total_neg))
        if control_error:
            print('control failed; {} of {} negative cases verified, '
                  '{} skipped.'.format(verified, total_neg, skipped))
        return 1

    print('OK: {} macro pairs verified (optional message == _MSG form).'.format(len(pairs)))
    print('OK: {} __LINE__ call sites verified.'.format(line_checked))
    print('OK: {} of {} negative (wrong argument count) cases verified '
          '({} too many -> sentinel, {} too few -> PP34, {} empty -> '
          'compile error).'.format(
              total_neg, total_neg, len(_EXCESS_CASES), len(_MISSING_CASES),
              len(_EMPTY_CASES)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
