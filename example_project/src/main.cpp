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

// Simulated function to be debugged / traced by GDB
extern "C" void complete_cell_setup(int cell_id) {
    std::cout << "[Cell Setup] Cell " << cell_id << " setup completed!" << std::endl;
}

void simulate_vran_flow() {
    std::vector<void*> allocated_ptrs;
    for (int i = 1; i <= 5; ++i) {
        // Simulate some dynamic memory allocation (heap usage changes)
        void* ptr = malloc(i * 1024 * 1024); // 1MB, 2MB, 3MB ...
        allocated_ptrs.push_back(ptr);
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        complete_cell_setup(i);
    }
    for (void* ptr : allocated_ptrs) {
        free(ptr);
    }
}

int main() {
    force_emit();
    simulate_vran_flow();
    return 0;
}
