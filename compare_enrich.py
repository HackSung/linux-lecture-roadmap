#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
보강 전(study_content_v1.json) / 후(study_content.json) 대조표 출력.

사용법: python3 compare_enrich.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BEFORE = os.path.join(HERE, "study_content_v1.json")
AFTER = os.path.join(HERE, "study_content.json")


def chars(ch):
    """학생이 실제로 읽는 본문 글자 수."""
    n = 0
    for b in ch.get("blocks") or []:
        for k in ("body", "wrapup", "answer"):
            n += len(b.get(k) or "")
        for ln in b.get("lines") or []:
            n += len(str(ln.get("note") or ""))
        for st in b.get("steps") or []:
            n += len(str(st.get("desc") or "")) + len(str(st.get("expect") or ""))
    return n


def types(ch):
    t = {}
    for b in ch.get("blocks") or []:
        t[b["type"]] = t.get(b["type"], 0) + 1
    return t


def index(path):
    with open(path, encoding="utf-8") as f:
        db = json.load(f)
    out = {}
    for s in db:
        for c in s.get("chapters") or []:
            out[(s["section_no"], c["no"])] = {
                "title": c["title"],
                "blocks": len(c.get("blocks") or []),
                "chars": chars(c),
                "types": types(c),
                "goals": len(c.get("goals") or []),
                "cmds": len(c.get("commands") or []),
            }
    return out


def pct(before, after):
    if not before:
        return "  —  "
    return f"{(after - before) / before * 100:+5.0f}%"


def main():
    if not os.path.exists(AFTER):
        print("study_content.json 이 없습니다.")
        return
    if not os.path.exists(BEFORE):
        print("기준선 study_content_v1.json 이 없어 대조할 수 없습니다.")
        return

    b, a = index(BEFORE), index(AFTER)
    keys = sorted(set(b) | set(a))

    tb = sum(v["blocks"] for v in b.values())
    ta = sum(v["blocks"] for v in a.values())
    cb = sum(v["chars"] for v in b.values())
    ca = sum(v["chars"] for v in a.values())

    print("=" * 78)
    print("보강 전후 대조 — 전체 합계")
    print("=" * 78)
    print(f"  챕터   {len(b):>6} → {len(a):>6}")
    print(f"  블록   {tb:>6} → {ta:>6}   ({ta - tb:+d}, {pct(tb, ta).strip()})")
    print(f"  글자   {cb:>6,} → {ca:>6,}   ({ca - cb:+,}, {pct(cb, ca).strip()})")
    print()

    # 섹션별
    print("=" * 78)
    print("섹션별")
    print("=" * 78)
    print(f"{'':4} {'챕터':>4} {'블록(전→후)':>16} {'글자(전→후)':>22} {'증감':>7}")
    for sn in range(1, 8):
        ks = [k for k in keys if k[0] == sn]
        if not ks:
            continue
        bb = sum(b[k]["blocks"] for k in ks if k in b)
        aa = sum(a[k]["blocks"] for k in ks if k in a)
        bc = sum(b[k]["chars"] for k in ks if k in b)
        ac = sum(a[k]["chars"] for k in ks if k in a)
        print(f"S{sn:<3} {len(ks):>4} {bb:>7} → {aa:<6} {bc:>10,} → {ac:<10,} {pct(bc, ac):>7}")
    print()

    # 얇았던 챕터가 실제로 두꺼워졌는지
    print("=" * 78)
    print("보강 최우선 대상이었던 얇은 챕터 15개")
    print("=" * 78)
    thin = sorted([k for k in b], key=lambda k: b[k]["chars"])[:15]
    print(f"{'챕터':<8} {'제목':<30} {'블록':>11} {'글자':>17} {'증감':>7}")
    for k in thin:
        bv = b[k]
        av = a.get(k)
        if not av:
            print(f"S{k[0]} C{k[1]:<4} {bv['title'][:30]:<30} {'(사라짐)':>11}")
            continue
        print(
            f"S{k[0]} C{k[1]:<4} {av['title'][:30]:<30} "
            f"{bv['blocks']:>4} → {av['blocks']:<4} "
            f"{bv['chars']:>7,} → {av['chars']:<7,} {pct(bv['chars'], av['chars']):>7}"
        )
    print()

    # 전체 챕터 상세
    print("=" * 78)
    print("전 챕터 상세")
    print("=" * 78)
    print(f"{'챕터':<8} {'제목':<32} {'블록':>11} {'글자':>17} {'증감':>7}")
    shrunk = []
    for k in keys:
        bv, av = b.get(k), a.get(k)
        if not bv:
            print(f"S{k[0]} C{k[1]:<4} {av['title'][:32]:<32} {'(신규)':>11} {av['chars']:>17,}")
            continue
        if not av:
            print(f"S{k[0]} C{k[1]:<4} {bv['title'][:32]:<32} {'(사라짐)':>11}")
            continue
        mark = ""
        if av["chars"] < bv["chars"]:
            mark = " ★얇아짐"
            shrunk.append(k)
        print(
            f"S{k[0]} C{k[1]:<4} {av['title'][:32]:<32} "
            f"{bv['blocks']:>4} → {av['blocks']:<4} "
            f"{bv['chars']:>7,} → {av['chars']:<7,} {pct(bv['chars'], av['chars']):>7}{mark}"
        )

    # 블록 유형 변화
    print()
    print("=" * 78)
    print("블록 유형별 총계")
    print("=" * 78)
    allt = set()
    for v in list(b.values()) + list(a.values()):
        allt |= set(v["types"])
    print(f"{'유형':<10} {'전':>6} {'후':>6} {'증감':>8}")
    for t in sorted(allt):
        bt = sum(v["types"].get(t, 0) for v in b.values())
        at = sum(v["types"].get(t, 0) for v in a.values())
        print(f"{t:<10} {bt:>6} {at:>6} {at - bt:>+8}")

    # 블록 유형 결손 해소 여부
    print()
    core = ("think", "pitfall", "analogy", "table", "code")
    mb = sum(1 for v in b.values() for t in core if t not in v["types"])
    ma = sum(1 for v in a.values() for t in core if t not in v["types"])
    print(f"핵심 블록 유형 결손(챕터×유형): {mb} → {ma} ({ma - mb:+d})")

    print()
    if shrunk:
        print(f"★ 얇아진 챕터 {len(shrunk)}개 — 확인 필요: " +
              ", ".join(f"S{k[0]}C{k[1]}" for k in shrunk))
    else:
        print("얇아진 챕터 없음 — 전 챕터 분량 유지 또는 증가")


if __name__ == "__main__":
    main()
