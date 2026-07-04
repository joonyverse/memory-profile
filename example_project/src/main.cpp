#include "example_node.h"
#include "example_events.h"
#include "example_system.h"
#include "example_advanced.h"

// 인스턴스화 — 컴파일러가 DWARF 디버그 정보를 emit하도록 강제
void force_emit() {
    volatile ExampleBaseNode*          a = nullptr;
    volatile ExampleResourceHandle     b;
    volatile ExampleSchedulerEntry     c;
    volatile ExampleEventMessage       d;
    volatile ExampleSensorSample       e;
    volatile ExampleLogEntry           f;
    volatile ExampleCacheAlignedBuffer g;
    volatile ExampleComplexRecord      h;

    int dummy_ref = 42;
    volatile ExampleReferenceMember    i(dummy_ref);
    volatile ExamplePimpl              j;
    volatile ExampleDynamicAndStatic   k;

    (void)a; (void)b; (void)c; (void)d;
    (void)e; (void)f; (void)g; (void)h;
    (void)i; (void)j; (void)k;
}

// Self-check: alignas가 올바르게 적용되었는지 컴파일 타임 검증
static_assert(alignof(ExampleCacheAlignedBuffer) == 64,
    "ExampleCacheAlignedBuffer must be 64-byte aligned");
static_assert(alignof(ExampleComplexRecord) == 64,
    "ExampleComplexRecord must be 64-byte aligned");
static_assert(sizeof(ExampleCacheAlignedBuffer) % 64 == 0,
    "ExampleCacheAlignedBuffer size must be a multiple of 64");
static_assert(sizeof(ExampleComplexRecord) % 64 == 0,
    "ExampleComplexRecord size must be a multiple of 64");

#include <iostream>
#include <thread>
#include <chrono>
#include <vector>
#include <cstdlib>
#include <cstring>

// Simulated function to be debugged / traced by GDB
extern "C" void complete_cell_setup(int cell_id) {
    std::cout << "[Cell Setup] Cell " << cell_id << " setup completed!" << std::endl;
}

// 실제 구조체들을 동적 할당하여 vRAN 셀 셋업을 시뮬레이션
void simulate_vran_flow() {
    std::vector<void*> allocated_ptrs;

    // --- Cell 1: 노드 등록 단계 ---
    auto* node1 = new ExampleResourceHandle();
    allocated_ptrs.push_back(node1);
    auto* handle1 = new ExampleResourceHandle();
    allocated_ptrs.push_back(handle1);
    complete_cell_setup(1);

    // --- Cell 2: 스케줄러 및 이벤트 설정 ---
    auto* sched1 = new ExampleSchedulerEntry();
    allocated_ptrs.push_back(sched1);
    auto* sched2 = new ExampleSchedulerEntry();
    allocated_ptrs.push_back(sched2);
    auto* event1 = new ExampleEventMessage();
    allocated_ptrs.push_back(event1);
    complete_cell_setup(2);

    // --- Cell 3: 센서 및 로그 초기화 ---
    auto* sensor1 = new ExampleSensorSample();
    allocated_ptrs.push_back(sensor1);
    auto* sensor2 = new ExampleSensorSample();
    allocated_ptrs.push_back(sensor2);
    auto* log1 = new ExampleLogEntry();
    allocated_ptrs.push_back(log1);
    complete_cell_setup(3);

    // --- Cell 4: 추가 리소스 핸들 및 대량 할당 ---
    auto* handle2 = new ExampleResourceHandle();
    allocated_ptrs.push_back(handle2);
    auto* handle3 = new ExampleResourceHandle();
    allocated_ptrs.push_back(handle3);
    // 대량 버퍼 할당 (구조체가 아닌 raw 메모리)
    void* bulk = malloc(4 * 1024 * 1024); // 4MB raw buffer
    allocated_ptrs.push_back(bulk);
    complete_cell_setup(4);

    // --- Cell 5: 최종 설정 ---
    auto* node2 = new ExampleResourceHandle();
    allocated_ptrs.push_back(node2);
    auto* log2 = new ExampleLogEntry();
    allocated_ptrs.push_back(log2);
    auto* event2 = new ExampleEventMessage();
    allocated_ptrs.push_back(event2);
    complete_cell_setup(5);

    // Cleanup (역순)
    delete static_cast<ExampleEventMessage*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    delete static_cast<ExampleLogEntry*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    delete static_cast<ExampleResourceHandle*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    free(allocated_ptrs.back()); allocated_ptrs.pop_back(); // 4MB raw
    delete static_cast<ExampleResourceHandle*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    delete static_cast<ExampleResourceHandle*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    delete static_cast<ExampleLogEntry*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    delete static_cast<ExampleSensorSample*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    delete static_cast<ExampleSensorSample*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    delete static_cast<ExampleEventMessage*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    delete static_cast<ExampleSchedulerEntry*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    delete static_cast<ExampleSchedulerEntry*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    delete static_cast<ExampleResourceHandle*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
    delete static_cast<ExampleResourceHandle*>(allocated_ptrs.back()); allocated_ptrs.pop_back();
}

int main() {
    force_emit();
    simulate_vran_flow();
    return 0;
}
