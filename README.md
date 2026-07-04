# Memory Profile & GDB Heap Tracker

C++ 구조체의 DWARF 디버그 정보를 DWARF 파서 없이 GDB Python으로 분석하고, 런타임 동적 할당(malloc/new)을 후킹하여 알려진 구조체 크기와 매칭해 주는 vRAN 및 임베디드 실시간 시스템용 메모리 프로파일러 패키지입니다.

기존 `pahole`의 한계(인라인 구조체, 템플릿 멤버, 동적 할당 분석 불가)를 극복하기 위해 **GDB 원격 디버깅 및 DWARF 분석 엔진**으로 마이그레이션되었습니다.

---

## 📂 Directory Structure

| Path | Description |
|------|-------------|
| `example_project/inc/` | 도메인별 구조체 헤더 정의 (`example_node.h`, `example_events.h`, 등) |
| `example_project/src/` | 소스 코드 및 `main.cpp` (셀 셋업 동적 할당 시뮬레이션 포함) |
| `tools/memory_analyzer/` | **핵심 프로파일러 도구 모음** |
| `├── auto_scan.sh` | 헤더에서 구조체/클래스명을 스캔하는 스크립트 |
| `├── analyze_struct.py` | 정적 DWARF 구조체 레이아웃 및 낭비 오프셋 분석기 |
| `├── heap_tracker.py` | 런타임 malloc/operator new 후킹 및 구조체 매칭 추적기 |
| `├── cell_trace.gdb.in` | 로컬 힙 매핑용 GDB 템플릿 |
| `└── remote_trace.gdb.in` | 이기종 원격 서버 자동 아키텍처 인지 디버깅용 GDB 템플릿 |
| `archive/` | 기존 `pahole` 및 대시보드(React/Vite) 백업 아카이브 |

---

## 🛠️ Requirements

```bash
sudo apt update
sudo apt install -y gdb             # 로컬 GDB 디버거
sudo apt install -y gdb-multiarch   # (선택) ARM Grace-C1 등 이기종 원격 디버깅 시 필요
sudo apt install -y cmake build-essential
```

---

## 🚀 Quick Start (Local)

### 1. CMake 빌드 환경 설정
```bash
cd example_project
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug
make -j$(nproc)
```

### 2. 정적 구조체 레이아웃 분석 (`make trace-static`)
헤더의 모든 구조체를 DWARF 정보를 토대로 계층 트리로 시각화하고, 오프셋 별 홀(Hole)/패딩을 추출합니다.
```bash
make trace-static
cat struct_report.txt
```

### 3. 구조체 인식 동적 힙 추적 (`make trace-dynamic-detailed`)
`malloc`과 `new`를 실시간 후킹하여, 셀 셋업 완료 시점마다 어떤 구조체가 어느 소스 라인에서 할당되었는지 추적합니다.
```bash
make trace-dynamic-detailed
cat heap_alloc_report.txt
```

---

## 🌐 Multi-Architecture Remote Profiling

서버 사양(Grace-C1 ARM64, Sapphire Rapids x86_64 등)이 계속 확장될 때 코드를 수정하지 않고 환경 설정 파일(`.env.*`)을 변경하여 디버깅할 수 있습니다.

### 1. 환경 설정 프로필 설정
로컬 루트 디렉토리에 정의된 각 서버의 환경 파일을 불러옵니다:
* 로컬/기본: `.env`
* Sapphire Rapids (x86): `.env.sapphirerapids`
* Grace-C1 (ARM64): `.env.grace-c1`

```bash
# Grace-C1 ARM64 서버 프로필로 빌드 환경 설정
cd example_project/build
cmake .. -DENV_FILE=../../.env.grace-c1
make show-profile
```

### 2. 원격 타겟 디버깅 실행
원격 타겟 서버에서 `gdbserver`를 구동합니다:
```bash
# (원격 서버 측)
gdbserver :9999 /opt/vran/bin/vran_main
```

로컬 빌드 디렉토리에서 원격 추적을 가동합니다:
```bash
# (로컬 서버 측)
make trace-dynamic-remote
```
GDB의 `set architecture auto` 속성에 의해 이기종 아키텍처(x86_64 → ARM64) 및 확장 명령어셋 정보가 원격 장비로부터 동적 인지되어 정상 동작합니다.

---

## 💡 Example Struct Patterns

본 예제는 실무 vRAN 개발 시 최적화가 빈번한 11가지 메모리 레이아웃 패턴을 포함하고 있습니다:

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
