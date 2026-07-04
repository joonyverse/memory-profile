# Memory Profile

C++ 구조체의 메모리 레이아웃을 `pahole`로 분석하고, 결과를 JSON으로 변환하여 대시보드와 연동하는 파이프라인. 이 저장소는 다중 파일 CMake 프로젝트에서 메모리 레이아웃 분석 파이프라인을 구축하는 실전 예제를 제공합니다.

## Quick Start

```bash
# 1. CMake 빌드
cd example_project
mkdir build && cd build
cmake ..
make

# 2. 파이프라인 실행 (여러 오브젝트 파일 통합 분석)
pahole CMakeFiles/memory_profile_example.dir/src/*.o | python3 ../tools/parse_pahole.py
```

## Directory Structure

| Path | Description |
|------|-------------|
| `example_project/inc/` | 도메인별 구조체 헤더 정의 (`example_node.h`, `example_events.h`, `example_system.h`) |
| `example_project/src/` | 관련 C++ 소스 파일 및 `main.cpp` |
| `example_project/CMakeLists.txt` | 표준 CMake 빌드 설정 (디버그 심볼 `-g` 강제 적용) |
| `tools/parse_pahole.py` | pahole 텍스트 출력 → JSON 변환 파서 |
| `tools/push_metrics.py` | JSON → InfluxDB/Prometheus 메트릭 전송 유틸리티 |
| `grafana/` | InfluxDB 데이터소스 및 대시보드 프로비저닝 설정 |
| `docker-compose.yml` | 로컬 시각화를 위한 InfluxDB + Grafana 컨테이너 |

## Requirements

```bash
sudo apt install dwarves       # pahole
sudo apt install cmake         # CMake 3.10+
g++ --version                  # GCC (with -g support)
python3 --version              # 3.10+
```

## Usage

```bash
cd example_project/build

# 전체 구조체 분석 (src 하위 모든 오브젝트 파일 대상)
pahole CMakeFiles/memory_profile_example.dir/src/*.o | python3 ../tools/parse_pahole.py

# 특정 구조체만 분석
pahole -C ExampleComplexRecord CMakeFiles/memory_profile_example.dir/src/*.o | python3 ../tools/parse_pahole.py

# 파일 입력
pahole CMakeFiles/memory_profile_example.dir/src/*.o > pahole_output.txt
python3 ../tools/parse_pahole.py pahole_output.txt

# JSON 결과 저장
pahole CMakeFiles/memory_profile_example.dir/src/*.o | python3 ../../tools/parse_pahole.py > report.json 2>summary.log
```

## CI Integration

### Jenkins

```groovy
stage('Memory Profile') {
    steps {
        sh 'cd example_project && mkdir build && cd build && cmake .. && make'
        sh 'pahole example_project/build/CMakeFiles/my_project.dir/src/*.o | python3 tools/parse_pahole.py > memory_report.json'
        archiveArtifacts 'memory_report.json'
    }
}
```

### GitLab CI

```yaml
memory-profile:
  stage: analysis
  script:
    - cd example_project && mkdir build && cd build && cmake .. && make
    - cd ../..
    - pahole example_project/build/CMakeFiles/my_project.dir/src/*.o | python3 tools/parse_pahole.py > memory_report.json
  artifacts:
    paths: [memory_report.json]
```

## Grafana Dashboard Integration

`tools/push_metrics.py`와 제공되는 `docker-compose.yml`을 활용하여 분석 결과를 시각화할 수 있습니다.

> **Note**: 리눅스 환경에서 권한 문제가 발생할 경우 `docker-compose` 앞에 `sudo`를 붙이거나 사용자를 `docker` 그룹에 추가하세요.

```bash
# 1. 인프라 실행 (권한 필요 시 sudo 추가)
sudo docker-compose up -d
# (주의: 최초 실행 시 DB 초기화에 시간이 소요될 수 있습니다. 'Connection reset' 에러 발생 시 잠시 후 다음 단계를 다시 실행하세요.)

# 2. 메트릭 추출 및 InfluxDB 전송
cd example_project
mkdir -p build && cd build && cmake .. && make
pahole CMakeFiles/memory_profile_example.dir/src/*.o | python3 ../../tools/parse_pahole.py --project myproject --commit abc1234 | python3 ../../tools/push_metrics.py --backend influxdb

# 3. 브라우저에서 대시보드 확인
# 접속: http://localhost:3000 (ID/PW: admin)
# "Memory Profile — Pahole Analysis" 대시보드 오픈
```

## Example Patterns

본 예제는 실무에서 흔히 발생하는 8가지 메모리 레이아웃 패턴을 다룹니다.

| # | Pattern | Struct | Description |
|---|---------|--------|-------------|
| 1 | vptr 오버헤드 | `ExampleBaseNode` | 가상 함수에 의한 8B vtable 포인터 삽입 |
| 2 | 상속 레이아웃 | `ExampleResourceHandle` | 기본 클래스 레이아웃 상속 + 경계 패딩 |
| 3 | 비트필드 쪼개짐 | `ExampleSchedulerEntry` | 일반 타입이 비트필드 패킹을 파괴 |
| 4 | Tagged Union | `ExampleEventMessage` | 익명 union + struct로 variant 구현 |
| 5 | 혼합 타입 | `ExampleSensorSample` | enum, 함수 포인터, 배열, volatile |
| 6 | 포인터/중첩 | `ExampleLogEntry` | 명명 중첩 구조체, 포인터 멤버 |
| 7 | 캐시라인 정렬 | `ExampleCacheAlignedBuffer` | alignas(64) 강제 패딩 |
| 8 | 종합 | `ExampleComplexRecord` | 모든 패턴의 복합 구조체 |
| 9 | 레퍼런스 멤버 | `ExampleReferenceMember` | 8B 포인터처럼 취급되는 참조형 변수에 의한 패딩 |
| 10| Pimpl 패턴 | `ExamplePimpl` | 불투명한 포인터(8B) 사용 시 발생하는 간격 |
| 11| Static / 동적할당 | `ExampleDynamicAndStatic` | 크기가 0B인 Static 멤버와 런타임 배열 포인터 |
