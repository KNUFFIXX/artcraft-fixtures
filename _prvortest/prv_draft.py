#!/usr/bin/env python3
"""prv_draft.py (THV-AC03, 14.10.2026) - result JSON + English comment draft for one PR pre-test (called by pr_vortest.sh).
Call: python3 -I prv_draft.py <checks.json|-> <out.json> <out-draft.md> [<baseline-checks.json>]
Metadata comes from the PRV_* environment variables set by pr_vortest.sh. Posts nothing: the draft is for review.
The draft starts with an HTML comment (German review notes, invisible on GitHub); the rest is the comment text.
THV-AC04 (17.10.2026): (a) only byte-size/timing differences in `detail` count as "same" as main; (b) "gridcraft#410/#417"
counts for both issues; (c) role "extra" gets "unchanged, as intended" / "unchanged" / "changed"; (d) a target fixture
already FIXED on main (baseline, or known_main starting with "FIXED") gets an ACHTUNG note and "already fixed on `main`".
DRACO-AC06 (17.10.2026): (e) same verdicts as the latest earlier check of this PR (other head, e.g. after a rebase) -> ACHTUNG
note "nicht posten" and unchanged_since = old sha7 (re-checks without news are noise).
DRACO-AC09 (20.10.2026): (e) also reads the earlier check from PRV_HISTORY (history.json from prv_history.py), because the
scheduled run builds in the cloud container where the old results/ are missing.
THV-AC09 (23.10.2026): no check for the PR's target issues and no other fixture differing from main -> ACHTUNG "nicht posten".
THV-AC10 (24.10.2026): repository from PRV_REPO (projects outside storytold); PRV_PR may be "main" (main-head run, no PR)."""
import datetime
import json
import os
import re
import sys

FOOTER = ('*Tested and written by Claude (Anthropic). Posted for Udo Funk (@KNUFFIXX), emotional support human, '
          'who reads every report after it goes out.*')
WORD = {'FIXED': 'fixed', 'NOT FIXED': 'not fixed', 'CHANGED': 'changed', 'ERROR': 'check error'}
OFFICE_APPS = ('wordcraft', 'gridcraft')


def env(k, d=''):
    return os.environ.get('PRV_' + k, d)


def load(p):
    if not p or p == '-' or not os.path.exists(p):
        return None
    with open(p, encoding='utf-8-sig') as f:
        return json.load(f)


def issue_no(s):
    m = re.search(r'#(\d+)$', s or '')
    return int(m.group(1)) if m else None


def issue_nos(s):
    """all issue numbers of an entry: 'gridcraft#410/#417' -> [410, 417] (THV-AC04)"""
    return [int(x) for x in re.findall(r'#(\d+)', s or '')]


def issue_ref(s):
    return '/'.join('#%d' % i for i in issue_nos(s)) or str(s)


# detail keys that only carry a byte size or a timing: a difference there alone is not a change (THV-AC04)
NOISE_KEY = re.compile(r'^(bytes|size|file_?size|\w+_bytes|bytes_\w+|seconds|\w+_seconds|secs|ms|\w+_ms|elapsed|duration)$', re.I)


def strip_noise(d):
    if isinstance(d, dict):
        return {k: strip_noise(v) for k, v in d.items() if not NOISE_KEY.match(str(k))}
    if isinstance(d, list):
        return [strip_noise(v) for v in d]
    return d


def main_fixed(e, base):
    """target fixture already FIXED on main: baseline verdict, else known_main written as 'FIXED on main ...' (THV-AC04)"""
    if base is not None and 'main_verdict' in e:
        return e.get('main_verdict') == 'FIXED'
    return str(e.get('known_main') or '').upper().startswith('FIXED')


def cell(s, n=140):
    s = str(s if s is not None else '').replace('|', '/').replace('\n', ' ')
    return s if len(s) <= n else s[:n - 1] + '…'


def word(e):
    v = e.get('verdict')
    if e.get('already_fixed_on_main'):
        return 'already fixed on `main`' if v == 'FIXED' else '**regressed** (fixed on `main`)'
    if e.get('role') == 'extra' and v != 'ERROR':      # side observation, not a fix target (THV-AC04)
        if e.get('vs_main') == 'same':
            return 'unchanged, as intended' if v == 'FIXED' else 'unchanged'
        if e.get('vs_main') == 'differs':
            return 'changed'
    if e.get('role') == 'control':
        return {'FIXED': 'still correct', 'CHANGED': '**regressed**'}.get(v, WORD.get(v, v))
    return WORD.get(v, v)


def key(e):
    return (e.get('issue'), e.get('fixture'), e.get('aspect'))


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        sys.stderr.write(__doc__)
        return 2
    checks, out_json, out_md = load(a[0]), a[1], a[2]
    base = load(a[3]) if len(a) > 3 else None
    app, pr, sha = env('APP'), env('PR'), env('SHA')
    sha7 = sha[:7]
    issues = [int(x) for x in env('ISSUES').replace(' ', '').split(',') if x.strip().isdigit()]
    results = (checks or {}).get('results', [])
    base_idx = {key(e): e for e in (base or {}).get('results', [])}
    known_issues = sorted({i for e in results for i in issue_nos(e['issue'])})
    target = [i for i in issues if i in known_issues]
    tgt = [e for e in results if set(issue_nos(e['issue'])) & set(target)]
    oth = [e for e in results if not set(issue_nos(e['issue'])) & set(target)]

    # comparison with main: the baseline build (if run) or the values known from the issues
    for e in results:
        b = base_idx.get(key(e))
        if b is not None:
            e['main_actual'], e['main_verdict'] = b.get('actual'), b.get('verdict')
            same = b.get('verdict') == e.get('verdict')
            if same and isinstance(b.get('detail'), dict) and isinstance(e.get('detail'), dict) and b['detail'] != e['detail']:
                # same verdict but other measured values = changed too; byte sizes/timings alone do not count (THV-AC04)
                same = strip_noise(b['detail']) == strip_noise(e['detail'])
                if same:
                    e['vs_main_note'] = 'only byte size/timing differs from main'
            e['vs_main'] = 'same' if same else 'differs'
        else:
            exp_old = (e.get('role') == 'control' or main_fixed(e, None)) and 'FIXED' or 'NOT FIXED'
            e['vs_main'] = 'same' if e.get('verdict') == exp_old else ('unknown' if e.get('known_main') == 'not measured' else 'differs')

    build_ok = env('BUILD_STATUS') == 'ok'
    notes = []
    # (d) target fixture already FIXED on main (THV-AC04)
    main_ref = ('main (%s)' % env('BASE')[:7]) if base else 'main (laut known_main)'
    for e in tgt:
        if e.get('role') == 'repro' and main_fixed(e, base):
            e['already_fixed_on_main'] = True
            if e.get('verdict') == 'FIXED':
                notes.append('ACHTUNG: %s ist auf %s bereits FIXED \u2014 der PR bringt dafuer nichts; Entwurf nicht posten' % (e['fixture'], main_ref))
            else:
                notes.append('ACHTUNG: %s ist auf %s FIXED, auf diesem Branch %s \u2014 Regression? Entwurf nicht posten' % (e['fixture'], main_ref, e.get('verdict')))
    if not build_ok:
        notes.append('Build fehlgeschlagen: ' + env('BUILD_ERROR', '?')[:600])
    if checks is None and build_ok:
        notes.append('Pruefskript lieferte kein Ergebnis (siehe Log).')
    if env('HEAD_MOVED'):
        notes.append('PR-Head hat sich seit der Kandidatenliste bewegt: ' + env('HEAD_MOVED'))
    if issues and not target:
        # THV-AC09 (23.10.2026): ohne Pruefung fuer das Ziel-Issue zeigt die Tabelle nur unsere anderen Fixtures ->
        # nicht postbar, ausser eine andere Fixture weicht von main ab.
        if any(e.get('vs_main') == 'differs' for e in oth):
            notes.append('Keine Pruefung fuer die Issues ' + ', '.join('#%d' % i for i in issues) + ' in checks/%s.py (andere Fixture weicht ab, s. u.).' % app)
        else:
            notes.append('ACHTUNG: Keine Pruefung fuer die Ziel-Issues ' + ', '.join('#%d' % i for i in issues) + ' in checks/%s.py \u2014 die Tabelle zeigt nur unsere anderen Fixtures, alle wie main; Entwurf nicht posten' % app)
    if not issues:
        notes.append('Keine Issue-Nummer bekannt (weder --issue noch #nnnn in den PR-Commits): alle Fixtures als Kontext.')
    for e in oth:
        if e['vs_main'] == 'differs':
            notes.append('Andere Fixture weicht von main ab: %s %s -> %s (%s)%s' % (
                e['issue'], e['fixture'], e['verdict'], cell(e.get('actual'), 100),
                '' if base else '; ohne --baseline unklar, ob vom PR oder von neuerem main'))
    for e in results:
        if e.get('verdict') == 'ERROR':
            notes.append('ERROR bei %s %s: %s' % (e['issue'], e['fixture'], cell(e.get('actual'), 160)))
    if env('BEHIND') and env('BEHIND') != '0':
        notes.append('Branch liegt %s Commits hinter main (%s); Basis %s.' % (env('BEHIND'), env('MAIN')[:7], env('BASE')[:7]))
    if env('LOCK_CHANGED'):
        notes.append('Cargo.lock wurde beim Bauen von cargo angepasst (Branch-Lockfile nicht aktuell).')
    if app in OFFICE_APPS:
        where = ('results/' + os.path.basename(env('OFFICE_DIR'))) if env('OFFICE_DIR') else env('WORK')
        notes.append('Office-Gegenprobe: gespeicherte Dateien (%s) in Word/Excel oeffnen, bevor ein FIXED fuer ein Speicher-Issue gepostet wird.' % where)
    notes.append('Build %s s (%s), Pruefungen %s s%s.' % (env('BUILD_SECONDS', '?'), env('TARGET_STATE', '?'), (checks or {}).get('seconds', '?'),
                 ('; Baseline %s: Build %s' % (env('BASE')[:7], (env('BASE_BUILD_SECONDS') + ' s') if env('BASE_BUILD_SECONDS').isdigit()
                                               else env('BASE_BUILD_SECONDS', '?').replace('cached', 'gecacht'))) if base else ''))
    # (e) same verdicts as an earlier check of this PR (same head checked again, or a new head e.g. after a rebase) = noise: do not post (DRACO-AC06)
    unchanged_since = None
    if build_ok and results:
        cur = {'target': {('%s %s' % (e['fixture'], e.get('aspect') or '')).strip(): e['verdict'] for e in tgt},
               'other': {('%s %s %s' % (e['issue'], e['fixture'], e.get('aspect') or '')).strip(): e['verdict'] for e in oth}}
        root = os.path.dirname(os.path.abspath(out_json))
        while os.path.basename(root) not in ('results', '') and os.path.dirname(root) != root:
            root = os.path.dirname(root)
        prev = []
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d != '_to_delete']
            for f in fn:
                fp = os.path.join(dp, f)
                if f.startswith('%s-pr%s-' % (app, pr)) and f.endswith('.json') and os.path.abspath(fp) != os.path.abspath(out_json):
                    d = load(fp)
                    if d and (d.get('build') or {}).get('status') == 'ok':
                        prev.append(d)
        # DRACO-AC09 (20.10.2026): in the cloud container the old results are missing -> PRV_HISTORY (from prv_history.py)
        hp = env('HISTORY')
        if hp and os.path.exists(hp):
            h = ((load(hp) or {}).get('prs') or {}).get('%s#%s' % (app, pr))
            if h and h.get('head_sha') and h.get('generated_utc', '') < datetime.datetime.now(datetime.timezone.utc).isoformat():
                prev.append(h)
        if prev:
            last = max(prev, key=lambda d: d.get('generated_utc', ''))
            if last.get('verdicts') == cur:
                unchanged_since = last.get('head_sha', '')[:7]
                notes.insert(0, 'ACHTUNG: Ergebnis unveraendert gegenueber dem Check von %s (%s UTC) \u2014 Re-Check nicht posten (Regel DRACO-AC06: nur posten, wenn sich das Ergebnis aendert)' % (
                    unchanged_since, last.get('generated_utc', '?')[:16].replace('T', ' ')))
    notes.append('Vor dem Posten lesen; nichts wurde gepostet.')

    doc = {
        'app': app, 'repo': env('REPO') or ('storytold/' + app), 'pr': int(pr) if pr.isdigit() else pr,
        'head_sha': sha, 'head_arg': env('HEAD_ARG'), 'head_moved': env('HEAD_MOVED'),
        'base_sha': env('BASE'), 'main_sha': env('MAIN'), 'behind_main': env('BEHIND'),
        'pr_commits': [ln for ln in env('COMMITS').splitlines() if ln.strip()],
        'issues': issues, 'issues_checked': target,
        'build': {'status': env('BUILD_STATUS'), 'seconds': int(env('BUILD_SECONDS', '0') or 0), 'cmd': env('BUILD_CMD'),
                  'rustc': env('RUSTC'), 'cargo': env('CARGO'), 'host': env('HOST'), 'log': env('BUILD_LOG'),
                  'lock_changed': bool(env('LOCK_CHANGED')), 'cli': env('CLI'), 'cli_bytes': env('BIN_SIZE'),
                  'target_dir': env('TARGET_STATE'),
                  'error_tail': env('BUILD_ERROR')},
        'baseline': None if base is None else {'sha': env('BASE'), 'build_seconds': env('BASE_BUILD_SECONDS'),
                                                'cli_version': base.get('cli_version')},
        'fixtures': {'repo': 'KNUFFIXX/artcraft-fixtures', 'sha': env('FIX_SHA'), 'dir': env('FIX_DIR')},
        'cli_version': (checks or {}).get('cli_version'), 'checks_seconds': (checks or {}).get('seconds'),
        'known_main_source': (checks or {}).get('known_main_source'), 'work': env('WORK'), 'office_files': env('OFFICE_DIR'),
        'verdicts': {'target': {('%s %s' % (e['fixture'], e.get('aspect') or '')).strip(): e['verdict'] for e in tgt},
                     'other': {('%s %s %s' % (e['issue'], e['fixture'], e.get('aspect') or '')).strip(): e['verdict'] for e in oth}},
        'results': results, 'review_notes': notes, 'unchanged_since': unchanged_since,
        'generated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
    }
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)

    # ---------- draft ----------
    L = ['<!--', 'PRUEFHINWEISE (nicht posten) - pr_vortest.sh %s UTC, %s %s, head %s' % (
        doc['generated_utc'][:16].replace('T', ' '), doc['repo'], ('PR #%s' % pr) if pr.isdigit() else pr, sha7)]
    L += ['- ' + n for n in notes if n.startswith('ACHTUNG')]     # warnings first (THV-AC04)
    if tgt:
        L.append('- Ergebnis: ' + '; '.join('%s %s%s: %s%s' % (e['issue'], e['fixture'], (' [%s]' % e['aspect']) if e.get('aspect') else '', e['verdict'],
                                                              (' (Zusatz: %s)' % word(e)) if e.get('role') == 'extra' else '') for e in tgt))
    L += ['- ' + n for n in notes if not n.startswith('ACHTUNG')]
    L += ['-->', '']
    refs = ', '.join('#%d' % i for i in target) or ', '.join('#%d' % i for i in issues) or '(no issue found)'
    btxt = 'Linux x86_64 build of `%s-cli`' % app
    label = (checks or {}).get('known_main_label') or 'the release in the issue'
    this = 'this branch' if pr.isdigit() else '`main`'   # main-head run (THV-AC10)
    if not build_ok:
        L.append('Tried %s (%s, %s) for the fixtures from %s: it does not build.' % (this, sha7, btxt.replace('build of', 'release build of'), refs))
        L += ['', '```', env('BUILD_ERROR', '')[-1500:].strip(), '```', '']
    elif checks is None:
        L.append('Built %s (%s, %s), but the fixture checks did not run.' % (this, sha7, btxt))
        L.append('')
    else:
        main_head = ('`main` @ %s' % env('BASE')[:7]) if base else ('%s (as reported)' % label)
        rows = tgt if tgt else results
        L.append('Checked %s (%s, %s) with the fixtures from %s:' % (this, sha7, btxt, refs))
        L += ['', '| Fixture | Expected | %s | %s | |' % (main_head, 'This branch' if pr.isdigit() else 'main @ ' + sha7), '|---|---|---|---|---|']
        for e in rows:
            multi = len([x for x in rows if x['fixture'] == e['fixture']]) > 1
            fx = '`%s`' % e['fixture'] + (' (%s)' % e['aspect'] if e.get('aspect') and multi else '')
            if e.get('role') == 'control':
                fx += ' (control)'
            mv = e.get('main_actual') if 'main_actual' in e else (e.get('known_main') if e.get('known_main') != 'not measured' else '–')
            L.append('| %s | %s | %s | %s | %s |' % (fx, cell(e.get('expected')), cell(mv), cell(e.get('actual')), word(e)))
        L.append('')
        if tgt and oth:
            per = {}
            for e in oth:
                for i in issue_nos(e['issue']):
                    per.setdefault(i, []).append(e['vs_main'])
            same_issues = sorted(i for i, v in per.items() if all(x == 'same' for x in v))
            diff = [e for e in oth if e['vs_main'] == 'differs']
            if same_issues:
                L.append('The other checks from our reports (%s) are unchanged.' % ', '.join('#%d' % i for i in same_issues))
                L.append('')
            if diff and base:
                L.append('Other checks from our reports that differ from `main` on this branch:')
                L.append('')
                for e in diff:
                    L.append('- %s `%s`: `main` %s, this branch %s' % (issue_ref(e['issue']), e['fixture'], cell(e.get('main_actual'), 90), cell(e.get('actual'), 90)))
                L.append('')
        if app in OFFICE_APPS and any(e.get('aspect') == 'save' and e.get('verdict') == 'FIXED' for e in tgt):
            L.append('The saved files were checked as XML only (not yet opened in %s).' % ('Word' if app == 'wordcraft' else 'Excel'))
            L.append('')
    L.append('Build: `%s` with %s on Linux x86_64%s; fixtures: [KNUFFIXX/artcraft-fixtures](https://github.com/KNUFFIXX/artcraft-fixtures) @ %s.' % (
        env('BUILD_CMD'), env('RUSTC').split(' (')[0], (' (`%s`)' % doc['cli_version']) if doc.get('cli_version') else '', env('FIX_SHA')[:7]))
    L += ['', FOOTER, '']
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    print('result %s' % out_json)
    print('draft  %s' % out_md)
    for e in results:
        print('  %-9s %-16s %s %s' % (e['verdict'], e['issue'], e['fixture'], ('[' + e['aspect'] + ']') if e.get('aspect') else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
