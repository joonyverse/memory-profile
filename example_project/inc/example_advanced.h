#pragma once

#include <cstddef>
#include <memory>

// ============================================================================
// 9. ExampleReferenceMember
//    ┌─ Pattern: 레퍼런스 멤버 변수
//    │
//    │  C++에서 레퍼런스(&)는 내부적으로 포인터로 구현되므로 64비트 시스템에서
//    │  8바이트를 차지하며 8바이트 정렬을 요구합니다.
//    └─────────────────────────────────────────────────────────────────
struct ExampleReferenceMember {
    int&        ref_val;            // 8B
    char        status_flag;        // 1B
    double      cached_value;       // 8B (앞에 7B 패딩 발생)
    
    // 레퍼런스 멤버는 반드시 초기화가 필요함
    ExampleReferenceMember(int& r) : ref_val(r), status_flag(0), cached_value(0.0) {}
};

// ============================================================================
// 10. ExamplePimpl
//    ┌─ Pattern: Pimpl (Pointer to implementation) 관용구
//    │
//    │  ABI 안정성과 컴파일 의존성을 줄이기 위해 구현부를 포인터로 숨기는 패턴.
//    │  포인터(8B)와 일반 멤버 간의 정렬 차이로 인해 패딩이 발생합니다.
//    └─────────────────────────────────────────────────────────────────
class ExamplePimpl {
public:
    ExamplePimpl();
    ~ExamplePimpl();

private:
    struct Impl;
    Impl*       pimpl;              // 8B
    char        config_mode;        // 1B
    int32_t     session_id;         // 4B (앞에 3B 패딩 발생)
};

// ============================================================================
// 11. ExampleDynamicAndStatic
//    ┌─ Pattern: 동적 할당 배열과 Static 멤버
//    │
//    │  static 멤버 변수는 클래스 인스턴스의 메모리 레이아웃(sizeof)에 
//    │  포함되지 않습니다 (0B 차지). 
//    │  동적 할당 배열은 크기와 포인터만 구조체에 남습니다.
//    └─────────────────────────────────────────────────────────────────
struct ExampleDynamicAndStatic {
    static int  global_instance_count;  // 0B (메모리 레이아웃에 미포함)
    static const char* version_string;  // 0B

    int*        dynamic_array;          // 8B (동적 할당 배열 포인터)
    size_t      array_capacity;         // 8B (배열 크기)
    char        buffer_type;            // 1B
    bool        is_allocated;           // 1B
};
