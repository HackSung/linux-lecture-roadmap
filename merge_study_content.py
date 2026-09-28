#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
섹션별 자습서 JSON 7개를 study_content.json 하나로 합치고 스키마를 검증한다.

사용법: python3 merge_study_content.py <섹션JSON들이_있는_디렉터리>
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "study_content.json")

# 기준 목차 (data.json / quiz_data.json 과 챕터 번호가 일치해야 함)
EXPECTED = {
    1: ("리눅스란 무엇인가?", 7),
    2: ("최소한의 커맨드라인 사용법", 13),
    3: ("파일", 9),
    4: ("사용자와 그룹", 8),
    5: ("프로세스와 시그널", 13),
    6: ("리디렉션과 파이프라인", 8),
    7: ("쉘 스크립트 프로그래밍", 7),
}

BLOCK_REQUIRED = {
    "prose":   ["heading", "body"],
    "analogy": ["title", "body"],
    "tip":     ["title", "body"],
    "pitfall": ["title", "body"],
    "think":   ["body"],
    "table":   ["headers", "rows"],
    "code":    ["lines"],
    "lab":     ["title", "steps"],
}


def validate(sec, problems):
    no = sec.get("section_no")
    if no not in EXPECTED:
        problems.append(f"S{no}: 알 수 없는 섹션 번호")
        return

    want_title, want_n = EXPECTED[no]
    chapters = sec.get("chapters") or []

    if len(chapters) != want_n:
        problems.append(f"S{no}: 챕터 수 {len(chapters)}개 (기대 {want_n}개)")

    nos = [c.get("no") for c in chapters]
    if nos != list(range(1, len(chapters) + 1)):
        problems.append(f"S{no}: 챕터 번호가 1..N 연속이 아님 → {nos}")

    if not sec.get("intro"):
        problems.append(f"S{no}: intro 누락")

    for ch in chapters:
        tag = f"S{no}C{ch.get('no')}"
        if not ch.get("title"):
            problems.append(f"{tag}: title 누락")
        if not ch.get("blocks"):
            problems.append(f"{tag}: blocks 없음")
        if not ch.get("goals"):
            problems.append(f"{tag}: goals 누락")
        if not ch.get("summary"):
            problems.append(f"{tag}: summary 누락")

        for i, b in enumerate(ch.get("blocks") or []):
            t = b.get("type")
            if t not in BLOCK_REQUIRED:
                problems.append(f"{tag} block#{i}: 알 수 없는 type '{t}'")
                continue
            for f in BLOCK_REQUIRED[t]:
                if not b.get(f):
                    problems.append(f"{tag} block#{i}({t}): '{f}' 누락")

            if t == "table":
                w = len(b.get("headers") or [])
                for r_i, row in enumerate(b.get("rows") or []):
                    if len(row) != w:
                        problems.append(
                            f"{tag} block#{i}(table) row{r_i}: 칸 {len(row)}개 (헤더 {w}개)"
                        )
            if t == "code":
                for l_i, ln in enumerate(b.get("lines") or []):
                    if not ln.get("cmd"):
                        problems.append(f"{tag} block#{i}(code) line{l_i}: cmd 누락")
            if t == "lab":
                for s_i, st in enumerate(b.get("steps") or []):
                    if not st.get("desc"):
                        problems.append(f"{tag} block#{i}(lab) step{s_i}: desc 누락")


def load_baseline():
    """1차 검증본(백업)의 챕터별 블록 수. 보강 후 분량이 줄면 경고한다."""
    for cand in (
        os.path.join(HERE, "study_content_v1.json"),
        os.path.join(os.path.dirname(HERE), "study_content_v1.json"),
    ):
        if os.path.exists(cand):
            with open(cand, encoding="utf-8") as f:
                old = json.load(f)
            return {
                (s["section_no"], c["no"]): len(c.get("blocks") or [])
                for s in old
                for c in s.get("chapters") or []
            }
    return None


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else HERE
    sections, problems = [], []
    baseline = load_baseline()

    for n in sorted(EXPECTED):
        path = os.path.join(src, f"study_section{n}.json")
        if not os.path.exists(path):
            problems.append(f"S{n}: 파일 없음 ({path})")
            continue
        with open(path, encoding="utf-8") as f:
            try:
                sec = json.load(f)
            except json.JSONDecodeError as e:
                problems.append(f"S{n}: JSON 파싱 실패 — {e}")
                continue
        # 섹션 제목은 기준 목차로 통일
        sec["section_no"] = n
        sec["section_title"] = EXPECTED[n][0]
        validate(sec, problems)
        sections.append(sec)

    if problems:
        print(f"[검증 문제 {len(problems)}건]")
        for p in problems:
            print("  -", p)
    else:
        print("[검증 통과] 스키마 문제 없음")

    # 보강 회귀 점검: 1차본보다 얇아진 챕터를 잡아낸다
    if baseline:
        shrunk, grown = [], 0
        for s in sections:
            for c in s.get("chapters") or []:
                k = (s["section_no"], c["no"])
                if k not in baseline:
                    continue
                now, was = len(c.get("blocks") or []), baseline[k]
                if now < was:
                    shrunk.append((k[0], k[1], c["title"], was, now))
                elif now > was:
                    grown += 1
        if shrunk:
            print(f"[회귀 경고] 1차본보다 블록이 줄어든 챕터 {len(shrunk)}개")
            for s_no, c_no, title, was, now in shrunk:
                print(f"  - S{s_no} C{c_no} {title[:28]}: {was} → {now}")
        print(f"[보강 현황] 늘어난 챕터 {grown}개 / 줄어든 챕터 {len(shrunk)}개")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=1)

    tot_ch = sum(len(s.get("chapters") or []) for s in sections)
    tot_bl = sum(len(c.get("blocks") or []) for s in sections for c in s.get("chapters") or [])
    print(f"병합 완료: {OUT}")
    print(f"  섹션 {len(sections)}개 · 챕터 {tot_ch}개 · 블록 {tot_bl}개")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
