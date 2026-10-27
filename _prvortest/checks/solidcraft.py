#!/usr/bin/env python3
"""solidcraft.py (THV-AC10, 24.10.2026) - SolidCraft fixture checks for the PR pre-test (tangency-labs/solidcraft).
Call:
  python3 -I solidcraft.py <solidcraft-cli> <artcraft-fixtures/solidcraft> <out.json> [--work DIR]
Issue: tangency-labs/solidcraft #4451 (OBJ export writes every triangle with its own three vertices, nothing shared;
PR #4462 shares them but leaves cracks = boundary edges, see our comment issuecomment-6372782628 on the PR).
Fixtures: the synthetic parts syn01..syn06 (*.json designs written by Claude for the THV scoreboard, no third-party
geometry): fillet box, chamfer box, shell box, beam with a hole and a space in the body name, stair with anchors,
sphere joined to a rod. Per part, as in AC\solidcraft\scoreboard_run.ps1: eval --json-out; run with STEP/STL/3MF/OBJ
export and --save; eval of the STEP export; eval of the saved design.
Target solidcraft#4451, two aspects over all parts: "obj shared vertices" (v < 3*f) and "obj watertight" (no boundary
or non-manifold edge per body, like the 3MF/STL of the same run). Controls (role control, aggregated over the parts):
eval ok (>= 1 body), STL closed (every edge used an even number of times), STEP round trip (same body count and names,
volume within 1e-3), save/reopen (same total volume within 1e-9).
known_main = v0.20.0 (THV scoreboard baseline 23.10.2026: obj_shared_vertices 0/14, all other metrics green).
Standard library only."""
import collections
import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

ck = C.Checker('solidcraft', sys.argv)
W = ck.work
ISSUE = 'solidcraft#4451'
N = [0]


def sc(args, tag, timeout=300):
    N[0] += 1
    return C.run([ck.cli] + args, timeout=timeout, cwd=W, log_prefix=os.path.join(W, '%02d_%s' % (N[0], tag)))


def load(p):
    try:
        with open(p, encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception:
        return None


def bodies(j):
    return (j or {}).get('bodies') or []


def errline(so, se):
    t = (se.strip() or so.strip()).replace(W + os.sep, '').splitlines()
    return t[-1][:200] if t else ''


# ---- geometry helpers (as AC\solidcraft\prvortest\objcheck.py and sc_sb.py)
def obj_topology(p):
    """-> {'v', 'f', 'shared', 'bodies': [{'name', 'faces', 'boundary_edges', 'nonmanifold_edges'}]}"""
    V = 0
    objs = collections.OrderedDict()
    cur = '(none)'
    with open(p, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if line.startswith('v '):
                V += 1
            elif line.startswith('o ') or line.startswith('g '):
                cur = line[2:].strip() or cur
                objs.setdefault(cur, [])
            elif line.startswith('f '):
                idx = [int(t.split('/')[0]) for t in line.split()[1:]]
                objs.setdefault(cur, []).append(idx)
    nf = sum(len(F) for F in objs.values())
    out = {'v': V, 'f': nf, 'shared': bool(nf) and V < 3 * nf, 'bodies': []}
    for name, F in objs.items():
        ec = collections.Counter()
        for face in F:
            for i in range(len(face)):
                a, b = face[i], face[(i + 1) % len(face)]
                ec[(a, b) if a <= b else (b, a)] += 1
        out['bodies'].append({'name': name, 'faces': len(F), 'boundary_edges': sum(1 for c in ec.values() if c == 1),
                              'nonmanifold_edges': sum(1 for c in ec.values() if c > 2)})
    return out


def stl_closed(p):
    with open(p, 'rb') as fh:
        d = fh.read()
    if len(d) < 84:
        return None
    tris = []
    if d[:5] == b'solid' and b'facet' in d[:512]:
        cur = []
        for line in d.decode('ascii', 'replace').splitlines():
            t = line.split()
            if t and t[0] == 'vertex':
                cur.append(tuple(t[1:4]))
                if len(cur) == 3:
                    tris.append(tuple(cur))
                    cur = []
    else:
        n = struct.unpack('<I', d[80:84])[0]
        if 84 + n * 50 > len(d):
            return None
        for i in range(n):
            v = struct.unpack('<12f', d[84 + i * 50:84 + i * 50 + 48])
            tris.append((v[3:6], v[6:9], v[9:12]))
    if not tris:
        return None
    ec = collections.Counter()
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            ec[(a, b) if a <= b else (b, a)] += 1
    return all(c % 2 == 0 for c in ec.values())


# ---- run every part once
parts = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ck.fixtures, 'syn*.json')))
R = collections.OrderedDict()
for name in parts:
    pid = name[:-5]
    src = ck.fx(name)
    o = lambda ext, _p=pid: os.path.join(W, _p + '.' + ext)  # noqa: E731
    r = {'eval': None, 'run': None, 'err': ''}
    rc, so, se = sc(['eval', src, '--json-out', o('eval.json')], pid + '_eval')
    r['eval_rc'] = rc
    B = bodies(load(o('eval.json')))
    r['eval'] = rc == 0 and len(B) > 0
    if rc != 0:
        r['err'] = 'eval: ' + errline(so, se)
    rc, so, se = sc(['run', src, '--out', o('step'), '--out', o('stl'), '--out', o('3mf'), '--out', o('obj'),
                     '--save', o('saved.solidcraft'), '--quiet'], pid + '_run')
    r['run_rc'] = rc
    r['run'] = rc == 0 and all(os.path.exists(o(e)) and os.path.getsize(o(e)) > 0 for e in ('step', 'stl', '3mf', 'obj'))
    if rc != 0 and not r['err']:
        r['err'] = 'run: ' + errline(so, se)
    if r['run']:
        try:
            r['obj'] = obj_topology(o('obj'))
        except Exception as ex:  # noqa: BLE001
            r['obj'] = {'error': repr(ex)[:120]}
        try:
            r['stl_closed'] = stl_closed(o('stl'))
        except Exception as ex:  # noqa: BLE001
            r['stl_closed'] = None
            r['err'] = r['err'] or ('stl: ' + repr(ex)[:120])
        rc, so, se = sc(['eval', o('step'), '--json-out', o('evalstep.json')], pid + '_evalstep')
        RB = bodies(load(o('evalstep.json')))
        ok = rc == 0 and len(RB) == len(B)
        if ok:
            for x, y in zip(sorted(B, key=lambda b: b.get('name', '')), sorted(RB, key=lambda b: b.get('name', ''))):
                vx, vy = x.get('volume_mm3', 0), y.get('volume_mm3', 0)
                if x.get('name') != y.get('name') or abs(vx - vy) > 1e-3 * max(abs(vx), 1e-9):
                    ok = False
                    break
        r['step_roundtrip'] = ok
        rc, so, se = sc(['eval', o('saved.solidcraft'), '--json-out', o('evalsave.json')], pid + '_evalsave')
        SB = bodies(load(o('evalsave.json')))
        tv, ts = sum(b.get('volume_mm3', 0) for b in B), sum(b.get('volume_mm3', 0) for b in SB)
        r['save_reopen'] = rc == 0 and len(SB) == len(B) and abs(tv - ts) <= 1e-9 * max(abs(tv), 1.0)
    R[pid] = r

FX = '%s–%s (%d parts)' % (parts[0][:5], parts[-1][:5], len(parts)) if parts else '(no syn*.json)'
ran = [p for p, r in R.items() if r.get('run')]


def agg(fn, label):
    """fn(part result) -> True/False/None; aggregated verdict over the parts that ran"""
    def inner():
        if not parts:
            return 'no syn*.json in ' + ck.fixtures, 'ERROR', None
        if not ran:
            return 'no part ran (%s)' % '; '.join(r['err'] for r in R.values() if r.get('err'))[:160], 'ERROR', {p: r.get('err') for p, r in R.items()}
        vals = {p: fn(R[p]) for p in ran}
        good = [p for p, v in vals.items() if v is True]
        bad = [p for p, v in vals.items() if v is False]
        unk = [p for p, v in vals.items() if v is None]
        actual = '%s in %d/%d parts' % (label, len(good), len(ran)) + ((' (not measurable: %s)' % ', '.join(unk)) if unk else '')
        if len(ran) < len(parts):
            actual += '; %d part(s) did not run' % (len(parts) - len(ran))
        verdict = 'FIXED' if good and not bad and not unk and len(ran) == len(parts) else 'NOT FIXED'
        return actual, verdict, {'per_part': vals, 'failed_parts': {p: R[p].get('err') for p in R if not R[p].get('run')}}
    return inner


def topo(r):
    t = r.get('obj') or {}
    return None if 'error' in t or not t.get('f') else bool(t.get('shared'))


def watertight(r):
    t = r.get('obj') or {}
    if 'error' in t or not t.get('bodies'):
        return None
    return all(b['boundary_edges'] == 0 and b['nonmanifold_edges'] == 0 for b in t['bodies'])


def detail_topo():
    return {p: {'v': R[p]['obj'].get('v'), 'f': R[p]['obj'].get('f'),
                'boundary_edges': [b['boundary_edges'] for b in R[p]['obj'].get('bodies', [])],
                'nonmanifold_edges': [b['nonmanifold_edges'] for b in R[p]['obj'].get('bodies', [])]} for p in ran if isinstance(R[p].get('obj'), dict) and 'error' not in R[p]['obj']}


# ---- target: #4451 OBJ export
def t_shared():
    a, v, d = agg(topo, 'vertices shared (v < 3*f)')()
    if d is not None:
        d['topology'] = detail_topo()
    return a, v, d


def t_watertight():
    a, v, d = agg(watertight, 'no boundary/non-manifold edge')()
    if d is not None:
        d['topology'] = detail_topo()
        be = [b for p in ran for b in (R[p].get('obj') or {}).get('bodies', [])]
        if be:
            a += '; boundary edges per body %d–%d' % (min(b['boundary_edges'] for b in be), max(b['boundary_edges'] for b in be))
    return a, v, d


ck.check(FX, ISSUE, 'OBJ export shares vertices between neighbouring triangles', 'v < 3*f in every part',
         'NOT FIXED: v0.20.0 writes 3 vertices per triangle, nothing shared (scoreboard 0/14 parts)', t_shared, aspect='obj shared vertices')
ck.check(FX, ISSUE, 'OBJ export is watertight per body (every edge used twice, none more)', 'boundary and non-manifold edges 0 in every body',
         'NOT FIXED: v0.20.0 every edge is a boundary edge (unshared vertices); PR #4462 @ 5a0d569: 16-692 boundary edges per body', t_watertight, aspect='obj watertight')
# ---- controls
ck.check(FX, ISSUE, 'eval of the design: at least one body, exit 0', 'ok in every part', 'ok in 14/14 parts (v0.20.0 scoreboard)',
         agg(lambda r: r.get('eval'), 'eval ok'), role='control', aspect='eval')
ck.check(FX, ISSUE, 'STL export closed (every edge used an even number of times)', 'closed in every part', 'ok in 14/14 parts (v0.20.0 scoreboard)',
         agg(lambda r: r.get('stl_closed'), 'STL closed'), role='control', aspect='stl closed')
ck.check(FX, ISSUE, 'STEP export read back: same bodies and names, volume within 1e-3', 'ok in every part', 'ok in 14/14 parts (v0.20.0 scoreboard)',
         agg(lambda r: r.get('step_roundtrip'), 'STEP round trip ok'), role='control', aspect='step roundtrip')
ck.check(FX, ISSUE, 'saved .solidcraft reopens with the same bodies and total volume', 'ok in every part', 'ok in 14/14 parts (v0.20.0 scoreboard)',
         agg(lambda r: r.get('save_reopen'), 'save/reopen ok'), role='control', aspect='save reopen')

ck.write({'known_main_source': 'THV scoreboard baseline v0.20.0 (23.10.2026, 14 parts) and PR #4462 check',
          'known_main_label': 'v0.20.0 (scoreboard)', 'parts': parts, 'parts_ran': ran})
