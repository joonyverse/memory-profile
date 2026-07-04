#include "example_advanced.h"

// ============================================================================
// Pimpl 구현부
// ============================================================================
struct ExamplePimpl::Impl {
    double internal_state;
    int array[100];
};

ExamplePimpl::ExamplePimpl() : pimpl(new Impl()), config_mode(0), session_id(0) {}
ExamplePimpl::~ExamplePimpl() { delete pimpl; }

// ============================================================================
// Static 멤버 변수 초기화
// ============================================================================
int ExampleDynamicAndStatic::global_instance_count = 0;
const char* ExampleDynamicAndStatic::version_string = "1.0.0";
