#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자습서 HTML 생성기.

입력:
  - study_content.json   : 섹션 7개의 자습서 본문(구조화 콘텐츠)
  - quiz_data.json       : 기존 로드맵 퀴즈 데이터(챕터별 연동)
출력:
  - study.html           : 자체 완결형(single-file) 자습서

재생성: python3 build_study.py
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

CONTENT = os.path.join(HERE, "study_content.json")
QUIZ = os.path.join(HERE, "quiz_data.json")
OUT = os.path.join(HERE, "study.html")


# --------------------------------------------------------------------------
# 데이터 로드 및 정합성 점검
# --------------------------------------------------------------------------

def load():
    with open(CONTENT, encoding="utf-8") as f:
        sections = json.load(f)
    with open(QUIZ, encoding="utf-8") as f:
        quizzes = json.load(f)

    # 퀴즈를 (섹션, 챕터) 키로 묶어 챕터 본문 끝에 붙일 수 있게 한다
    bucket = {}
    for q in quizzes:
        key = f"{q['section_no']}-{q['chapter_no']}"
        bucket.setdefault(key, []).append({
            "id": q["id"],
            "question": q["question"],
            "choices": q["choices"],
            "correct_index": q["correct_index"],
            "explanation": q["explanation"],
        })

    # 매칭되지 않은 퀴즈가 있으면 알려준다(챕터 번호 재매핑 누락 감지용)
    valid = {f"{s['section_no']}-{c['no']}" for s in sections for c in s["chapters"]}
    orphans = sorted(set(bucket) - valid)
    if orphans:
        print(f"  [경고] 본문 챕터와 매칭되지 않은 퀴즈 키: {orphans}")

    return sections, bucket


# --------------------------------------------------------------------------
# 치트시트: 전 챕터 commands 집계
# --------------------------------------------------------------------------

def build_cheatsheet(sections):
    """명령어별로 설명·예시·등장 챕터를 모은다. 같은 명령어는 병합."""
    table = {}
    for sec in sections:
        for ch in sec["chapters"]:
            for c in ch.get("commands", []):
                name = c["cmd"].strip()
                if not name:
                    continue
                entry = table.setdefault(name, {
                    "cmd": name,
                    "descs": [],
                    "examples": [],
                    "refs": [],
                })
                if c.get("desc") and c["desc"] not in entry["descs"]:
                    entry["descs"].append(c["desc"])
                if c.get("example") and c["example"] not in entry["examples"]:
                    entry["examples"].append(c["example"])
                ref = {
                    "s": sec["section_no"],
                    "c": ch["no"],
                    "t": ch["title"],
                }
                if ref not in entry["refs"]:
                    entry["refs"].append(ref)

    rows = []
    for name in sorted(table, key=lambda n: (n.lower(), n)):
        e = table[name]
        rows.append({
            "cmd": e["cmd"],
            "desc": " · ".join(e["descs"][:2]),
            "examples": e["examples"][:3],
            "refs": e["refs"],
        })
    return rows


# --------------------------------------------------------------------------
# 검색 색인: 챕터별 평문 텍스트
# --------------------------------------------------------------------------

def block_text(b):
    parts = []
    for key in ("heading", "title", "body", "wrapup", "answer"):
        if b.get(key):
            parts.append(b[key])
    for h in b.get("headers", []) or []:
        parts.append(h)
    for row in b.get("rows", []) or []:
        parts.extend(str(x) for x in row)
    for ln in b.get("lines", []) or []:
        parts.extend(str(ln.get(k, "")) for k in ("cmd", "out", "note"))
    for st in b.get("steps", []) or []:
        parts.extend(str(st.get(k, "")) for k in ("desc", "cmd", "expect"))
    return " ".join(parts)


def build_index(sections):
    idx = []
    for sec in sections:
        for ch in sec["chapters"]:
            text = " ".join(
                [ch["title"]]
                + ch.get("goals", [])
                + ch.get("summary", [])
                + ch.get("keywords", [])
                + [c.get("cmd", "") + " " + c.get("desc", "") for c in ch.get("commands", [])]
                + [block_text(b) for b in ch.get("blocks", [])]
            )
            text = re.sub(r"\s+", " ", text)
            idx.append({
                "s": sec["section_no"],
                "c": ch["no"],
                "title": ch["title"],
                "sectionTitle": sec["section_title"],
                "practice": bool(ch.get("is_practice")),
                "text": text.lower(),
            })
    return idx


# --------------------------------------------------------------------------
# HTML 조립
# --------------------------------------------------------------------------

def render(sections, quizzes, cheatsheet, search_index):
    payload = {
        "sections": sections,
        "quizzes": quizzes,
        "cheatsheet": cheatsheet,
        "searchIndex": search_index,
    }
    data_js = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    # 인라인 <script> 안에 들어가므로, 스크립트 블록을 조기 종료시킬 수 있는
    # 시퀀스를 JS 문자열 수준에서 이스케이프한다(값은 파싱 후 동일).
    data_js = (
        data_js.replace("</", "<\\/")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )

    total_ch = sum(len(s["chapters"]) for s in sections)
    total_practice = sum(
        1 for s in sections for c in s["chapters"] if c.get("is_practice")
    )
    total_cmd = len(cheatsheet)
    total_quiz = sum(len(v) for v in quizzes.values())

    with open(os.path.join(HERE, "study_template.html"), encoding="utf-8") as f:
        tpl = f.read()

    return (
        tpl.replace("/*__DATA__*/", "const DB = " + data_js + ";")
        .replace("__TOTAL_SECTIONS__", str(len(sections)))
        .replace("__TOTAL_CHAPTERS__", str(total_ch))
        .replace("__TOTAL_PRACTICE__", str(total_practice))
        .replace("__TOTAL_COMMANDS__", str(total_cmd))
        .replace("__TOTAL_QUIZ__", str(total_quiz))
    )


def main():
    sections, quizzes = load()
    cheatsheet = build_cheatsheet(sections)
    search_index = build_index(sections)
    html = render(sections, quizzes, cheatsheet, search_index)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    total_ch = sum(len(s["chapters"]) for s in sections)
    total_blocks = sum(
        len(c.get("blocks", [])) for s in sections for c in s["chapters"]
    )
    print(f"생성 완료: {OUT}")
    print(f"  섹션 {len(sections)}개 · 챕터 {total_ch}개 · 콘텐츠 블록 {total_blocks}개")
    print(f"  명령어 색인 {len(cheatsheet)}개 · 퀴즈 {sum(len(v) for v in quizzes.values())}문항")
    print(f"  파일 크기 {os.path.getsize(OUT) / 1024:.0f}KB")


if __name__ == "__main__":
    main()
