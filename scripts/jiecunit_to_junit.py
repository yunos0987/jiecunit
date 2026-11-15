#!/usr/bin/env python
# coding: utf-8
"""Convert the output of JiecUnit to JUnit XML.

The input is the text JiecUnit prints: the standard output of `jiecc --run`,
or the lines of g_console copied from a PLC, in order (oldest first). If the
input holds more than one run (g_jiecunit_rerun), only the last run is
converted.

  [ RUN    ] Suite.name           -> <testcase classname="Suite" name="name">
  [     OK ] Suite.name (12us)    -> passed, time="0.000012"
  [ FAILED ] Suite.name (n/a)     -> <failure> per failure of the test
  [ SKIPPED] Suite.name (n/a)     -> <skipped>
  [  ERROR ] ...                  -> <error> (a test program that did not run, ...)

A test without a suite gets the classname given with --classname (default:
the name of the input file without its extension, or "JiecUnit" for the
standard input). The time attribute is left out when JiecUnit printed
"(n/a)". Each failure starts with its position line ("<file>:<line>:
Failure"); its first detail line becomes the message attribute, and all its
lines the text.

The XML is written even when the input is incomplete. A problem with the run
(no summary, a test without a result, a summary whose count does not match the
tests, a fatal registration error, an overflowed console buffer whose lines
may be missing) is reported as an <error> of the test case "(run)" in the
test suite "JiecUnit", and makes the exit code 1. The exit code is 0 for a
complete run, and 2 for a usage error. Characters that XML cannot hold (the
control characters other than tab, newline and carriage return) are replaced
with "?".

Usage:
  python scripts/jiecunit_to_junit.py output.txt -o result.xml
  jiecc --run test/test.iec -I. -Isys | python scripts/jiecunit_to_junit.py - -o result.xml
  python scripts/jiecunit_to_junit.py --self-test
"""
import argparse
import io
import os
import re
import sys
import xml.etree.ElementTree as ET

_RUNNING_RE = re.compile(r'^\[========\] Running (\d+) tests\.')
_RAN_RE = re.compile(r'^\[========\] (\d+) tests ran\.')
_RUN_RE = re.compile(r'^\[ RUN    \] (.+)$')
# A result line can follow text printed without a newline (print / Console_print)
# on the same line, so it is searched at the end of the line.
_RESULT_RE = re.compile(r'\[(     OK | FAILED | SKIPPED)\] (.+) \((\d+)us\)$|\[(     OK | FAILED | SKIPPED)\] (.+) \(n/a\)$')
_ERROR_RE = re.compile(r'^\[  ERROR \] (.*)$')
_WARNING_RE = re.compile(r'^\[ WARNING\] (.*)$')
_FATAL_RE = re.compile(r'^Fatal error: (.*)$')
_POSITION_RE = re.compile(r'^(?:.*:\d+: )?Failure(?: \(cycle \d+\))?$')
_SKIP_POSITION_RE = re.compile(r'^(?:.*:\d+: )?Skipped(?: \(cycle \d+\))?$')
_PASSED_RE = re.compile(r'^\[ PASSED \] (\d+) tests\.$')
_SKIPPED_RE = re.compile(r'^\[ SKIPPED\] (\d+) tests\.$')
_FAILED_COUNT_RE = re.compile(r'^\[ FAILED \] (\d+) tests, listed below\.$')
# A name in the list of the failed tests (no time after it).
_FAILED_NAME_RE = re.compile(r'^\[ FAILED \] (?!.* \((?:\d+us|n/a)\)$)')
_INVALID_XML_RE = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]')


class TestCase(object):
    def __init__(self, display_name, default_class):
        self.display_name = display_name
        if '.' in display_name:
            self.classname, self.name = display_name.split('.', 1)
        else:
            self.classname, self.name = default_class, display_name
        self.status = None      # 'passed', 'failed', 'skipped'
        self.time = None        # seconds, or None
        self.lines = []         # every line printed while the test ran
        self.errors = []        # [  ERROR ] texts

    def failures(self):
        """Split the output into failures, each starting at a position line."""
        result = []
        in_failure = False
        for line in self.lines:
            if _POSITION_RE.match(line):
                result.append([line])
                in_failure = True
            elif _SKIP_POSITION_RE.match(line):
                in_failure = False
            elif in_failure:
                result[-1].append(line)
        return result

    def skip_reason(self):
        """The reason of the last skip: the line after its position line."""
        reason = None
        for i, line in enumerate(self.lines):
            if _SKIP_POSITION_RE.match(line):
                following = self.lines[i + 1:i + 2]
                reason = following[0] if following and not _POSITION_RE.match(following[0]) else ''
        return reason


def parse(lines, default_class):
    """Parse the last run. Returns (tests, problems).

    The lines are read once, in order. While a test is open (after its RUN
    line and before its result line) every line is output of the test, also
    one that looks like the start of a run. Outside a test, a "Running" line
    starts a new run and discards the earlier one (a rerun). Nothing is
    guessed from the neighbouring lines, so a line of another program between
    the lines of the run does not change which run is read.
    """
    lines = [l.rstrip('\r') for l in lines]
    state = _Run()
    for line in lines:
        current = state.current
        if current is not None and current.status is None:
            # Inside a test.
            m = _RESULT_RE.search(line)
            if m:
                kind = (m.group(1) or m.group(4)).strip()
                name = m.group(2) or m.group(5)
                if name == current.display_name:
                    if m.start() > 0:
                        current.lines.append(line[:m.start()])
                    current.status = {'OK': 'passed', 'FAILED': 'failed', 'SKIPPED': 'skipped'}[kind]
                    if m.group(3) is not None:
                        current.time = int(m.group(3)) / 1e6
                    continue
            m = _RUN_RE.match(line)
            if m:
                # The next test started: the open one never got its result.
                state.open_test(m.group(1), default_class)
                continue
            m = _ERROR_RE.match(line)
            if m:
                current.errors.append(m.group(1))
                continue
            m = _WARNING_RE.match(line)
            if m:
                state.problems.append(m.group(1))
                continue
            current.lines.append(line)
            continue

        # Outside a test.
        m = _RUNNING_RE.match(line)
        if m:
            state = _Run()
            state.expected_count = int(m.group(1))
            continue
        m = _FATAL_RE.match(line)
        if m:
            # A fatal registration error comes before the "Running" line of its run.
            if state.finished or state.expected_count is None:
                state = _Run()
            state.problems.append('fatal error: ' + m.group(1))
            continue
        m = _WARNING_RE.match(line)
        if m:
            state.problems.append(m.group(1))
            continue
        m = _RUN_RE.match(line)
        if m:
            if state.finished:
                state.problems.append('test {} started after the summary of the run'.format(m.group(1)))
            state.open_test(m.group(1), default_class)
            continue
        m = _ERROR_RE.match(line)
        if m:
            state.problems.append('error outside a test: ' + m.group(1))
            continue
        m = _RESULT_RE.search(line)
        if m and not _FAILED_NAME_RE.match(line):
            state.problems.append('result line outside a test: ' + line)
            continue
        m = _RAN_RE.match(line)
        if m:
            if state.finished:
                state.problems.append('the run has two summaries')
            state.finished = True
            state.ran_count = int(m.group(1))
            continue
        if state.finished:
            for regex, key in ((_PASSED_RE, 'passed'), (_SKIPPED_RE, 'skipped'), (_FAILED_COUNT_RE, 'failed')):
                m = regex.match(line)
                if m:
                    state.summary[key] = int(m.group(1))
    return state.tests, state.result_problems()


class _Run(object):
    """The tests and problems of one run."""

    def __init__(self):
        self.tests = []
        self.problems = []
        self.current = None
        self.expected_count = None
        self.finished = False
        self.ran_count = None
        self.summary = {}

    def open_test(self, display_name, default_class):
        self.current = TestCase(display_name, default_class)
        self.tests.append(self.current)

    def result_problems(self):
        problems = list(self.problems)
        for t in self.tests:
            if t.status is None:
                problems.append('test {} has no result'.format(t.display_name))
        if not self.finished:
            problems.append('the run did not finish (no "[========] N tests ran." line)')
            return problems
        if self.ran_count != len(self.tests) or (
                self.expected_count is not None and self.expected_count != len(self.tests)):
            problems.append('the summary counts {} tests ({} announced) but {} were found'.format(
                self.ran_count, self.expected_count, len(self.tests)))
        # The summary lines must agree with the results that were read (a
        # count that is 0 has no line, except for the passed tests).
        for key in ('passed', 'skipped', 'failed'):
            found = sum(1 for t in self.tests if t.status == key)
            stated = self.summary.get(key, 0)
            if key == 'passed' and 'passed' not in self.summary:
                problems.append('the summary has no "[ PASSED ] N tests." line')
            elif stated != found:
                problems.append('the summary states {} {} tests but {} were found'.format(stated, key, found))
        return problems


def to_xml(tests, problems):
    root = ET.Element('testsuites', name='JiecUnit')
    suites = {}
    order = []
    for t in tests:
        if t.classname not in suites:
            suites[t.classname] = []
            order.append(t.classname)
        suites[t.classname].append(t)

    def counts(items):
        failures = sum(1 for t in items if t.status == 'failed' and t.failures())
        errors = sum(1 for t in items if t.errors or t.status is None or (t.status == 'failed' and not t.failures()))
        skipped = sum(1 for t in items if t.status == 'skipped')
        times = [t.time for t in items if t.time is not None]
        return failures, errors, skipped, (sum(times) if times else None)

    total_f, total_e, total_s, total_t = counts(tests)
    root.set('tests', str(len(tests) + len(problems)))
    root.set('failures', str(total_f))
    root.set('errors', str(total_e + len(problems)))
    root.set('skipped', str(total_s))
    if total_t is not None:
        root.set('time', '{:.6f}'.format(total_t))

    for name in order:
        items = suites[name]
        f, e, s, t = counts(items)
        suite = ET.SubElement(root, 'testsuite', name=name, tests=str(len(items)),
                              failures=str(f), errors=str(e), skipped=str(s))
        if t is not None:
            suite.set('time', '{:.6f}'.format(t))
        for test in items:
            case = ET.SubElement(suite, 'testcase', classname=test.classname, name=test.name)
            if test.time is not None:
                case.set('time', '{:.6f}'.format(test.time))
            for text in test.errors:
                err = ET.SubElement(case, 'error', message=text)
                err.text = text
            if test.status is None:
                err = ET.SubElement(case, 'error', message='the test has no result')
                err.text = '\n'.join(test.lines)
            elif test.status == 'skipped':
                skipped = ET.SubElement(case, 'skipped')
                reason = test.skip_reason()
                if reason:
                    skipped.set('message', reason)
            elif test.status == 'failed':
                blocks = test.failures()
                if not blocks and not test.errors:
                    err = ET.SubElement(case, 'error', message='the test failed without a failure message')
                    err.text = '\n'.join(test.lines)
                for block in blocks:
                    message = '\n'.join(block[:2])
                    failure = ET.SubElement(case, 'failure', message=message, type='')
                    failure.text = '\n'.join(block)
            other = _lines_outside_failures(test.lines)
            if other:
                out = ET.SubElement(case, 'system-out')
                out.text = '\n'.join(other)
    if problems:
        suite = ET.SubElement(root, 'testsuite', name='JiecUnit', tests=str(len(problems)),
                              failures='0', errors=str(len(problems)), skipped='0')
        for problem in problems:
            case = ET.SubElement(suite, 'testcase', classname='JiecUnit', name='(run)')
            err = ET.SubElement(case, 'error', message=problem)
            err.text = problem
    return root


def _lines_outside_failures(lines):
    """The lines of a test that are not part of a failure (for system-out)."""
    result = []
    in_failure = False
    for line in lines:
        if _POSITION_RE.match(line):
            in_failure = True
        elif _SKIP_POSITION_RE.match(line):
            in_failure = False
        if not in_failure:
            result.append(line)
    return result


def convert(text, default_class):
    """Return (xml string, problems)."""
    text = _INVALID_XML_RE.sub('?', text)
    tests, problems = parse(text.split('\n'), default_class)
    root = to_xml(tests, problems)
    _indent(root)
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode') + '\n'
    return xml, problems


def _indent(elem, level=0):
    pad = '\n' + '  ' * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = pad + '  '
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = pad
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = pad


_SELF_TEST_INPUT = """\
noise before the run
[========] Running 1 tests.
[ RUN    ] old_run
[     OK ] old_run (1us)
[========] 1 tests ran. (1us)
[========] Running 5 tests.
[ RUN    ] Suite.passes
[     OK ] Suite.passes (12us)
[ RUN    ] Suite.fails
a.iec:3: Failure
Expected equality of these values:
  1
  x
    Which is: 2
a.iec:4: Failure (cycle 1)
Failed
the message
[ FAILED ] Suite.fails (n/a)
[ RUN    ] plain
a.iec:9: Skipped
why
[ SKIPPED] plain (n/a)
[ RUN    ] not_assigned
[  ERROR ] The program 'not_assigned' was not found in active tasks.
[ FAILED ] not_assigned (n/a)
[ RUN    ] Suite.passes2
printed without a newline[     OK ] Suite.passes2 (3us)
[========] 5 tests ran. (15us)
[ PASSED ] 2 tests.
[ SKIPPED] 1 tests.
[ FAILED ] 2 tests, listed below.
[ FAILED ] Suite.fails
[ FAILED ] not_assigned
"""


def self_test():
    xml, problems = convert(_SELF_TEST_INPUT, 'file')
    root = ET.fromstring(xml)
    _check(problems == [], problems)
    _check(root.get('tests') == '5', root.attrib)
    _check(root.get('failures') == '1' and root.get('errors') == '1' and root.get('skipped') == '1', root.attrib)
    suites = {s.get('name'): s for s in root.findall('testsuite')}
    _check(sorted(suites) == ['Suite', 'file'], sorted(suites))
    fails = [c for c in root.iter('testcase') if c.get('name') == 'fails'][0]
    failures = fails.findall('failure')
    _check(len(failures) == 2, xml)
    _check(failures[0].get('message') == 'a.iec:3: Failure\nExpected equality of these values:', failures[0].attrib)
    _check(failures[1].get('message') == 'a.iec:4: Failure (cycle 1)\nFailed', failures[1].attrib)
    _check(fails.get('time') is None)
    passes = [c for c in root.iter('testcase') if c.get('name') == 'passes'][0]
    _check(passes.get('time') == '0.000012' and passes.get('classname') == 'Suite')
    plain = [c for c in root.iter('testcase') if c.get('name') == 'plain'][0]
    _check(plain.find('skipped') is not None and plain.get('classname') == 'file')
    _check(plain.find('skipped').get('message') == 'why', plain.find('skipped').attrib)
    na = [c for c in root.iter('testcase') if c.get('name') == 'not_assigned'][0]
    _check(na.find('error') is not None and na.find('failure') is None)
    _check(not [c for c in root.iter('testcase') if c.get('name') == 'old_run'], 'only the last run')
    passes2 = [c for c in root.iter('testcase') if c.get('name') == 'passes2'][0]
    _check(passes2.find('error') is None and passes2.get('time') == '0.000003', xml)
    _check(passes2.find('system-out').text == 'printed without a newline', xml)

    _, problems = convert('[========] Running 1 tests.\n[ RUN    ] t\n', 'f')
    _check(len(problems) == 2, problems)
    # A rerun: the last run is read, also when another program prints a line
    # right after its "Running" line, and a failure in it is not lost.
    first = '[========] Running 1 tests.\n[ RUN    ] t\n[     OK ] t (n/a)\n[========] 1 tests ran. (n/a)\n[ PASSED ] 1 tests.\n'
    second = ('[========] Running 1 tests.\nlogger: a line of another program\n[ RUN    ] t\na.iec:1: Failure\nFailed\n'
              '[ FAILED ] t (n/a)\n[========] 1 tests ran. (n/a)\n[ PASSED ] 0 tests.\n[ FAILED ] 1 tests, listed below.\n[ FAILED ] t\n')
    xml, problems = convert(first + second, 'f')
    _check(problems == [] and ET.fromstring(xml).get('failures') == '1', xml)
    # A test or a result after the summary, without a new "Running" line.
    _, problems = convert(first + '[ RUN    ] u\n[ FAILED ] u (n/a)\n', 'f')
    _check(any('after the summary' in p for p in problems), problems)
    # The summary lines must agree with the results.
    _, problems = convert(first.replace('[ PASSED ] 1 tests.', '[ PASSED ] 0 tests.\n[ FAILED ] 1 tests, listed below.'), 'f')
    _check(any('states' in p for p in problems), problems)
    # A test that prints a "Running" line does not start a run.
    xml, problems = convert('[========] Running 1 tests.\n[ RUN    ] t\n[========] Running 7 tests.\n[     OK ] t (n/a)\n[========] 1 tests ran. (n/a)\n[ PASSED ] 1 tests.\n', 'f')
    _check(problems == [] and ET.fromstring(xml).get('tests') == '1', problems)
    _, problems = convert(_SELF_TEST_INPUT + '[ WARNING] The console buffer is full (CONSOLE_MAX_ROWS=8); older lines may have been overwritten.\n', 'f')
    _check(len(problems) == 1 and 'console buffer' in problems[0], problems)
    _, problems = convert("Fatal error: program 'x' is already registered.\n", 'f')
    _check(any('fatal error' in p for p in problems), problems)
    # Control characters do not break the XML; a vertical tab does not split a line.
    xml, problems = convert('[========] Running 1 tests.\n[ RUN    ] t\nbad\x1b\x0b[ RUN    ] fake\n[     OK ] t (n/a)\n[========] 1 tests ran. (n/a)\n[ PASSED ] 1 tests.\n', 'f')
    root = ET.fromstring(xml)
    _check(problems == [], problems)
    _check(root.get('tests') == '1', xml)
    # A test that prints a summary line of its own does not end the run early.
    xml, problems = convert('[========] Running 2 tests.\n[ RUN    ] a\n[========] 9 tests ran.\n[     OK ] a (n/a)\n[ RUN    ] b\n[     OK ] b (n/a)\n[========] 2 tests ran. (n/a)\n', 'f')
    _check(any('summary' in p or 'no result' in p for p in problems), problems)
    _check(ET.fromstring(xml).get('errors') != '0', xml)
    print('OK: jiecunit_to_junit self-test passed.')
    return 0


def _check(condition, detail=''):
    if not condition:
        raise AssertionError(detail)


def main():
    # type: () -> int
    parser = argparse.ArgumentParser(description='Convert JiecUnit output to JUnit XML.')
    parser.add_argument('input', nargs='?', help='The JiecUnit output ("-" for the standard input)')
    parser.add_argument('-o', '--output', help='The JUnit XML file (default: the standard output)')
    parser.add_argument('--classname', help='The classname of the tests without a suite')
    parser.add_argument('--self-test', action='store_true', help='Run the built-in tests and exit')
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.input:
        parser.print_usage(sys.stderr)
        return 2
    if args.input == '-':
        text = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace').read()
        default_class = args.classname or 'JiecUnit'
    else:
        with open(args.input, encoding='utf-8', errors='replace') as f:
            text = f.read()
        default_class = args.classname or os.path.splitext(os.path.basename(args.input))[0]
    xml, problems = convert(text, default_class)
    if args.output:
        with open(args.output, 'w', encoding='utf-8', newline='\n') as f:
            f.write(xml)
    else:
        sys.stdout.write(xml)
    for p in problems:
        print('warning: ' + p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
