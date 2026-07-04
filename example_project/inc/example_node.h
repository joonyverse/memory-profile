#pragma once

#include <cstdint>
#include <cstddef>

struct ExampleBaseNode {
    virtual ~ExampleBaseNode() = default;
    virtual int serialize(void* buf, size_t len) const = 0;

    char        tag;                // 1B
    double      created_at;         // 8B (8-byte alignment 요구)
    bool        active;             // 1B
    uint32_t    id;                 // 4B (4-byte alignment 요구)
    char        priority;           // 1B
    double      weight;             // 8B
};

struct ExampleResourceHandle : public ExampleBaseNode {
    int serialize(void* buf, size_t len) const override;

    char        type_code;          // 1B
    uint64_t    handle;             // 8B
    bool        exclusive;          // 1B
    uint32_t    ref_count;          // 4B
    char        owner_tag;          // 1B
    double      timeout_sec;        // 8B
    bool        auto_release;       // 1B
};
