#!/usr/bin/env python3
"""
push_metrics.py — parse_pahole.py의 JSON 출력을 메트릭 백엔드로 전송.

지원 백엔드:
  - influxdb     : InfluxDB 2.x (Line Protocol, HTTP API)
  - prometheus   : Prometheus Pushgateway
  - file         : 로컬 JSONL 파일 (히스토리 보관, fallback)

사용법:
  # InfluxDB로 전송
  pahole obj.o | python3 parse_pahole.py | python3 push_metrics.py --backend influxdb

  # Prometheus Pushgateway로 전송
  pahole obj.o | python3 parse_pahole.py | python3 push_metrics.py --backend prometheus

  # Dry-run (전송 없이 변환 결과만 출력)
  pahole obj.o | python3 parse_pahole.py | python3 push_metrics.py --backend influxdb --dry-run

  # 파일로 저장 (기본값)
  pahole obj.o | python3 parse_pahole.py | python3 push_metrics.py

의존성:
  Python 표준 라이브러리만 사용 (외부 패키지 불필요).
"""

import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path


# ============================================================================
#  InfluxDB Backend
# ============================================================================

def to_influxdb_line_protocol(data: dict, compiler: str = 'gcc', arch: str = 'x86_64') -> str:
    """
    parse_pahole.py JSON → InfluxDB Line Protocol 변환.

    Line Protocol 형식:
      measurement,tag1=val1,tag2=val2 field1=val1i,field2=val2 timestamp_ns
    """
    lines: list[str] = []
    project = data.get('project', 'unknown')
    commit = data.get('commit_hash', 'unknown')
    ts = data.get('timestamp')

    # 타임스탬프를 나노초로 변환
    if ts:
        try:
            dt = datetime.fromisoformat(ts)
            ts_ns = int(dt.timestamp() * 1_000_000_000)
        except (ValueError, TypeError):
            ts_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
    else:
        ts_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)

    for s in data.get('structs', []):
        # 태그 (인덱싱됨, 문자열)
        tags = (
            f'struct_name={_escape_tag(s["struct_name"])},'
            f'project={_escape_tag(project)},'
            f'commit={_escape_tag(commit)},'
            f'compiler={_escape_tag(compiler)},'
            f'arch={_escape_tag(arch)}'
        )

        # 필드 (값, 숫자)
        fields = (
            f'total_size={s["total_size"]}i,'
            f'sum_members={s.get("sum_members", 0)}i,'
            f'sum_holes={s["sum_holes"]}i,'
            f'num_holes={s["num_holes"]}i,'
            f'cachelines={s["cachelines"]}i,'
            f'padding_end={s["padding_end"]}i,'
            f'waste_pct={s["waste_pct"]}'
        )
        
        layout_json = json.dumps(s.get("layout", []))
        escaped_json = layout_json.replace('"', r'\"')
        fields += f',layout_json="{escaped_json}"'

        lines.append(f'struct_metrics,{tags} {fields} {ts_ns}')

    return '\n'.join(lines)


def _escape_tag(value: str) -> str:
    """InfluxDB 태그 값 이스케이프 (공백, 콤마, 등호)."""
    return value.replace(' ', r'\ ').replace(',', r'\,').replace('=', r'\=')


def push_to_influxdb(line_protocol: str, url: str, token: str,
                     org: str, bucket: str) -> bool:
    """InfluxDB 2.x HTTP API로 Line Protocol 전송."""
    write_url = f'{url}/api/v2/write?org={org}&bucket={bucket}&precision=ns'

    req = urllib.request.Request(
        write_url,
        data=line_protocol.encode('utf-8'),
        headers={
            'Authorization': f'Token {token}',
            'Content-Type': 'text/plain; charset=utf-8',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 204):
                return True
            print(f'[WARN] InfluxDB responded with status {resp.status}',
                  file=sys.stderr)
            return False
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f'[ERROR] InfluxDB HTTP {e.code}: {body}', file=sys.stderr)
        return False
    except urllib.error.URLError as e:
        print(f'[ERROR] InfluxDB connection failed: {e.reason}',
              file=sys.stderr)
        return False


# ============================================================================
#  Prometheus Pushgateway Backend
# ============================================================================

def to_prometheus_exposition(data: dict) -> str:
    """
    parse_pahole.py JSON → Prometheus exposition format 변환.

    각 구조체에 대해 다음 메트릭을 Gauge로 생성:
      - pahole_struct_total_size
      - pahole_struct_sum_holes
      - pahole_struct_waste_pct
      - pahole_struct_cachelines
      - pahole_struct_padding_end
    """
    lines: list[str] = []
    project = data.get('project', 'unknown')
    commit = data.get('commit_hash', 'unknown')

    metrics = [
        ('pahole_struct_total_size',  'Total struct size in bytes',    'total_size'),
        ('pahole_struct_sum_members', 'Sum of member sizes in bytes',  'sum_members'),
        ('pahole_struct_sum_holes',   'Sum of padding holes in bytes', 'sum_holes'),
        ('pahole_struct_num_holes',   'Number of padding holes',       'num_holes'),
        ('pahole_struct_cachelines',  'Number of cache lines used',    'cachelines'),
        ('pahole_struct_padding_end', 'End padding in bytes',          'padding_end'),
        ('pahole_struct_waste_pct',   'Waste percentage',              'waste_pct'),
    ]

    for metric_name, help_text, field_key in metrics:
        lines.append(f'# HELP {metric_name} {help_text}')
        lines.append(f'# TYPE {metric_name} gauge')

        for s in data.get('structs', []):
            labels = (
                f'struct_name="{s["struct_name"]}",'
                f'project="{project}",'
                f'commit="{commit}"'
            )
            value = s.get(field_key, 0)
            lines.append(f'{metric_name}{{{labels}}} {value}')

        lines.append('')  # 메트릭 간 빈 줄

    return '\n'.join(lines)


def push_to_prometheus(exposition: str, url: str, job: str) -> bool:
    """Prometheus Pushgateway로 메트릭 전송."""
    push_url = f'{url}/metrics/job/{job}'

    req = urllib.request.Request(
        push_url,
        data=exposition.encode('utf-8'),
        headers={'Content-Type': 'text/plain; charset=utf-8'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 202):
                return True
            print(f'[WARN] Pushgateway responded with status {resp.status}',
                  file=sys.stderr)
            return False
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f'[ERROR] Pushgateway HTTP {e.code}: {body}', file=sys.stderr)
        return False
    except urllib.error.URLError as e:
        print(f'[ERROR] Pushgateway connection failed: {e.reason}',
              file=sys.stderr)
        return False


# ============================================================================
#  File Backend (fallback)
# ============================================================================

def push_to_file(data: dict, filepath: str) -> bool:
    """JSON을 로컬 JSONL 파일에 append (히스토리 보관용)."""
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
        return True
    except OSError as e:
        print(f'[ERROR] File write failed: {e}', file=sys.stderr)
        return False


# ============================================================================
#  CLI
# ============================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서."""
    p = argparse.ArgumentParser(
        description='parse_pahole.py의 JSON 출력을 메트릭 백엔드로 전송',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            '사용 예시:\n'
            '  python3 parse_pahole.py out.txt | python3 push_metrics.py --backend influxdb\n'
            '  python3 parse_pahole.py out.txt | python3 push_metrics.py --backend prometheus --dry-run\n'
            '  python3 parse_pahole.py out.txt | python3 push_metrics.py --backend file -o history.jsonl\n'
        ),
    )
    p.add_argument(
        'input', nargs='?', default=None,
        help='입력 JSON 파일 (생략 시 stdin)',
    )
    p.add_argument(
        '--backend', choices=['influxdb', 'prometheus', 'file'],
        default='file',
        help='메트릭 전송 백엔드 (기본: file)',
    )
    p.add_argument(
        '--dry-run', action='store_true',
        help='변환 결과만 출력, 실제 전송하지 않음',
    )
    p.add_argument(
        '--compiler', default='gcc',
        help='컴파일러 이름 (기본: gcc)',
    )
    p.add_argument(
        '--arch', default='x86_64',
        help='아키텍처 이름 (기본: x86_64)',
    )

    # InfluxDB 옵션
    influx = p.add_argument_group('InfluxDB options')
    influx.add_argument('--influx-url', default='http://localhost:8086',
                        help='InfluxDB URL (기본: http://localhost:8086)')
    influx.add_argument('--influx-token', default='dev-token-123',
                        help='InfluxDB API 토큰')
    influx.add_argument('--influx-org', default='memory-profile',
                        help='InfluxDB organization')
    influx.add_argument('--influx-bucket', default='pahole',
                        help='InfluxDB bucket')

    # Prometheus 옵션
    prom = p.add_argument_group('Prometheus options')
    prom.add_argument('--prom-url', default='http://localhost:9091',
                      help='Pushgateway URL (기본: http://localhost:9091)')
    prom.add_argument('--prom-job', default='pahole',
                      help='Pushgateway job 이름')

    # File 옵션
    file_grp = p.add_argument_group('File options')
    file_grp.add_argument('-o', '--output', default='pahole_history.jsonl',
                          help='출력 JSONL 파일 경로 (기본: pahole_history.jsonl)')

    return p


def main():
    """메인 엔트리포인트."""
    parser = build_arg_parser()
    args = parser.parse_args()

    # JSON 입력 읽기
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                raw = f.read()
        except FileNotFoundError:
            print(f'[ERROR] File not found: {args.input}', file=sys.stderr)
            sys.exit(1)
    else:
        raw = sys.stdin.read()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f'[ERROR] Invalid JSON input: {e}', file=sys.stderr)
        sys.exit(1)

    num_structs = data.get('num_structs', len(data.get('structs', [])))
    project = data.get('project', 'unknown')
    commit = data.get('commit_hash', 'unknown')

    # 백엔드별 처리
    if args.backend == 'influxdb':
        payload = to_influxdb_line_protocol(data, args.compiler, args.arch)
        if args.dry_run:
            print('--- InfluxDB Line Protocol ---')
            print(payload)
            print(f'\n[DRY-RUN] {num_structs} struct(s) would be sent to '
                  f'{args.influx_url} ({args.influx_org}/{args.influx_bucket})',
                  file=sys.stderr)
        else:
            ok = push_to_influxdb(
                payload, args.influx_url, args.influx_token,
                args.influx_org, args.influx_bucket
            )
            if ok:
                print(f'[OK] {num_structs} struct(s) pushed to InfluxDB '
                      f'({project}@{commit})', file=sys.stderr)
            else:
                sys.exit(1)

    elif args.backend == 'prometheus':
        payload = to_prometheus_exposition(data)
        if args.dry_run:
            print('--- Prometheus Exposition Format ---')
            print(payload)
            print(f'\n[DRY-RUN] {num_structs} struct(s) would be sent to '
                  f'{args.prom_url}/metrics/job/{args.prom_job}',
                  file=sys.stderr)
        else:
            ok = push_to_prometheus(payload, args.prom_url, args.prom_job)
            if ok:
                print(f'[OK] {num_structs} struct(s) pushed to Pushgateway '
                      f'({project}@{commit})', file=sys.stderr)
            else:
                sys.exit(1)

    elif args.backend == 'file':
        if args.dry_run:
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print(f'\n[DRY-RUN] Would append to {args.output}',
                  file=sys.stderr)
        else:
            ok = push_to_file(data, args.output)
            if ok:
                print(f'[OK] {num_structs} struct(s) saved to {args.output} '
                      f'({project}@{commit})', file=sys.stderr)
            else:
                sys.exit(1)


if __name__ == '__main__':
    main()
