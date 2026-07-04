#!/usr/bin/env python3
"""
parse_pahole.py — pahole 출력 텍스트를 파싱하여 메모리 효율성 지표를 JSON으로 추출.

사용법:
  # 파이프 입력
  pahole example_structures.o | python3 parse_pahole.py

  # 파일 입력
  python3 parse_pahole.py pahole_output.txt

  # CI 메타데이터 포함
  pahole obj.o | python3 parse_pahole.py --project myapp --commit abc1234

  # 여러 파일
  python3 parse_pahole.py file1.txt file2.txt

출력:
  JSON — CI 대시보드 백엔드(Grafana, Elasticsearch 등)로 전송하기 좋은 형태.

추출 지표:
  - struct_name    : 구조체 이름
  - total_size     : 총 크기 (bytes)
  - sum_members    : 멤버 합계 크기 (bytes)
  - sum_holes      : 홀(낭비) 합계 크기 (bytes)
  - num_holes      : 홀 개수
  - cachelines     : 캐시라인 수
  - padding_end    : 구조체 끝 패딩 (bytes)
  - waste_pct      : 낭비 비율 (%)
  - layout         : 상세 메모리 레이아웃 (트리 뷰용)
"""

import sys
import re
import json
import argparse
import subprocess
from datetime import datetime, timezone
from typing import TextIO


def _detect_git_info() -> tuple[str | None, str | None]:
    """Git 저장소에서 프로젝트명과 커밋 해시를 자동 감지."""
    project = None
    commit = None
    try:
        toplevel = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        project = toplevel.rsplit('/', 1)[-1]
    except Exception:
        pass
    try:
        commit = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        pass
    return project, commit


def parse_pahole_output(stream: TextIO) -> list[dict]:
    """
    pahole 텍스트 출력을 파싱하여 구조체별 메모리 지표 딕셔너리 리스트 반환.
    """
    results: list[dict] = []

    # ── 정규표현식 패턴 ──

    # 최상위 구조체 시작: "struct Foo {" 또는 "class Foo : Base {"
    re_struct_start = re.compile(
        r'^(?:struct|class)\s+(\w+)\s*(?::.*?)?\s*\{'
    )

    # 중괄호 열기/닫기 (주석 내부 제외)
    re_open_brace = re.compile(r'\{')
    re_close_brace = re.compile(r'\}')

    # 요약 정보
    re_size = re.compile(r'/\*\s*size:\s*(\d+)', re.IGNORECASE)
    re_cachelines = re.compile(r'cachelines:\s*(\d+)', re.IGNORECASE)
    re_members = re.compile(r'members:\s*(\d+)', re.IGNORECASE)
    re_sum_members = re.compile(r'sum members:\s*(\d+)', re.IGNORECASE)
    re_sum_holes = re.compile(r'sum holes:\s*(\d+)', re.IGNORECASE)
    re_num_holes = re.compile(r'(?:^|,)\s*(\d+)\s+holes?', re.IGNORECASE)
    re_padding = re.compile(r'padding:\s*(\d+)', re.IGNORECASE)

    # 레이아웃 매칭용 정규식
    re_member = re.compile(r'^\s*(.*?)\s*;\s*/\*\s*(\d+)\s+(\d+)\s*\*/')
    re_member_closing_brace = re.compile(r'^\s*\}\s*(.*?)\s*;\s*/\*\s*(\d+)\s+(\d+)\s*\*/')
    re_inline_hole = re.compile(r'/\*\s*XXX\s+(\d+)\s+bytes?\s+hole', re.IGNORECASE)
    re_padding_comment = re.compile(r'/\*\s*padding:\s*(\d+)', re.IGNORECASE)

    # ── 파싱 상태 ──
    current_name: str | None = None
    block_lines: list[str] = []
    brace_depth: int = 0
    inline_holes_sum = 0
    inline_holes_count = 0
    stack: list[list[dict]] = []

    def _strip_comments(text: str) -> str:
        return re.sub(r'/\*.*?\*/', '', text)

    def _count_braces(text: str) -> tuple[int, int]:
        cleaned = _strip_comments(text)
        opens = len(re_open_brace.findall(cleaned))
        closes = len(re_close_brace.findall(cleaned))
        return opens, closes

    def _extract_struct_info(name: str, lines: list[str],
                             holes_sum: int, holes_count: int,
                             layout: list[dict]) -> dict:
        info: dict = {
            'struct_name': name,
            'total_size': 0,
            'sum_members': 0,
            'sum_holes': 0,
            'num_holes': 0,
            'cachelines': 0,
            'padding_end': 0,
            'waste_pct': 0.0,
            'layout': layout
        }

        tail_lines = lines[-25:] if len(lines) > 25 else lines
        combined = ' '.join(tail_lines)

        m = re_size.search(combined)
        if m: info['total_size'] = int(m.group(1))

        m = re_cachelines.search(combined)
        if m: info['cachelines'] = int(m.group(1))

        m = re_members.search(combined)
        if m: info['members'] = int(m.group(1))

        m = re_sum_members.search(combined)
        if m: info['sum_members'] = int(m.group(1))

        m = re_sum_holes.search(combined)
        if m: info['sum_holes'] = int(m.group(1))
        elif holes_sum > 0: info['sum_holes'] = holes_sum

        m = re_num_holes.search(combined)
        if m: info['num_holes'] = int(m.group(1))
        elif holes_count > 0: info['num_holes'] = holes_count

        m = re_padding.search(combined)
        if m: info['padding_end'] = int(m.group(1))

        total = info['total_size']
        if total > 0:
            wasted = info['sum_holes'] + info['padding_end']
            info['waste_pct'] = round(wasted / total * 100, 1)

        return info

    re_member_only = re.compile(r'^\s*(?![^;]*\})(?!})([^;]+?)\s*;\s*/\*\s*(\d+)\s+(\d+)\s*\*/')
    re_anon_close = re.compile(r'^\s*\};\s*(?:/\*.*?\*/)?')

    for raw_line in stream:
        line = raw_line.rstrip('\n')

        if current_name is None:
            m_start = re_struct_start.match(line)
            if m_start:
                current_name = m_start.group(1)
                block_lines = [line]
                brace_depth = 1
                inline_holes_sum = 0
                inline_holes_count = 0
                stack = [[]]
            continue

        block_lines.append(line)

        opens, closes = _count_braces(line)
        
        # Push for inner braces
        for _ in range(opens):
            stack.append([])
            brace_depth += 1

        # Process line contents
        # 홀 처리
        m_hole = re_inline_hole.search(line)
        if m_hole:
            hole_size = int(m_hole.group(1))
            inline_holes_sum += hole_size
            inline_holes_count += 1
            offset = stack[-1][-1]['offset'] + stack[-1][-1]['size'] if stack[-1] else 0
            stack[-1].append({
                'type': 'hole',
                'decl': f'/* XXX {hole_size} bytes hole */',
                'offset': offset,
                'size': hole_size
            })
        
        # 패딩 처리
        m_pad = re_padding_comment.search(line)
        if m_pad:
            pad_size = int(m_pad.group(1))
            offset = stack[-1][-1]['offset'] + stack[-1][-1]['size'] if stack[-1] else 0
            stack[-1].append({
                'type': 'padding',
                'decl': f'/* padding: {pad_size} bytes */',
                'offset': offset,
                'size': pad_size
            })

        # 일반 멤버 처리
        m_member = re_member_only.match(line)
        if m_member:
            decl = m_member.group(1).strip()
            offset = int(m_member.group(2))
            size = int(m_member.group(3))
            stack[-1].append({
                'type': 'member',
                'decl': decl,
                'offset': offset,
                'size': size
            })

        # 익명 구조체 닫는 멤버 처리 "} name; /* offset size */"
        m_close_member = re_member_closing_brace.search(line)
        if m_close_member:
            inner = stack.pop() if len(stack) > 1 else []
            decl = "struct/union " + m_close_member.group(1).strip()
            offset = int(m_close_member.group(2))
            size = int(m_close_member.group(3))
            stack[-1].append({
                'type': 'nested',
                'decl': decl,
                'offset': offset,
                'size': size,
                'children': inner
            })
            brace_depth -= 1

        # 이름 없는 익명 닫기 "};"
        m_anon_close_match = re_anon_close.search(line)
        if m_anon_close_match and not m_close_member:
            if len(stack) > 1:
                inner = stack.pop()
                first_offset = inner[0]['offset'] if inner and 'offset' in inner[0] else 0
                max_size = max([x.get('size', 0) for x in inner]) if inner else 0
                stack[-1].append({
                    'type': 'nested',
                    'decl': 'anonymous union/struct',
                    'offset': first_offset,
                    'size': max_size,
                    'children': inner
                })
                brace_depth -= 1
            else:
                # Top level struct closed
                brace_depth -= 1

        # For any other closes that didn't match member or anon
        if not m_close_member and not m_anon_close_match:
            for _ in range(closes):
                brace_depth -= 1
                if len(stack) > 1:
                    stack.pop()

        if brace_depth <= 0 and current_name is not None:
            final_layout = stack[0] if stack else []
            info = _extract_struct_info(
                current_name, block_lines,
                inline_holes_sum, inline_holes_count, final_layout
            )
            if info['total_size'] > 0:
                results.append(info)
            current_name = None
            block_lines = []
            brace_depth = 0
            stack = []

    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='pahole 출력을 파싱하여 메모리 효율성 지표를 JSON으로 추출',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('files', nargs='*', default=[])
    parser.add_argument('--project', default=None)
    parser.add_argument('--commit', default=None)
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    git_project, git_commit = _detect_git_info()
    project = args.project or git_project or 'unknown'
    commit = args.commit or git_commit or 'unknown'

    streams: list[TextIO] = []
    if args.files:
        for filepath in args.files:
            try:
                streams.append(open(filepath, 'r', encoding='utf-8'))
            except FileNotFoundError:
                sys.exit(1)
    else:
        streams.append(sys.stdin)

    all_results: list[dict] = []
    for stream in streams:
        all_results.extend(parse_pahole_output(stream))
        if stream is not sys.stdin:
            stream.close()

    output = {
        'tool': 'pahole',
        'version': '1.0',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'project': project,
        'commit_hash': commit,
        'num_structs': len(all_results),
        'structs': all_results,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
