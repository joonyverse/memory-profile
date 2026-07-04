#pragma once

#include <cstdint>

struct ExampleSchedulerEntry {
    // ── bit field group 1 ──
    uint8_t     priority    : 3;
    uint8_t     state       : 2;

    // ❌ 일반 타입이 비트필드 패킹을 깨뜨림
    double      deadline_ms;

    // ── bit field group 2 (새 저장 단위) ──
    uint8_t     cpu_affinity : 4;
    uint8_t     preemptible  : 1;

    int32_t     stack_size_kb;      // ❌ 다시 깨뜨림

    // ── bit field group 3 ──
    uint8_t     log_level    : 3;
    uint8_t     isolated     : 1;
    uint8_t     daemon       : 1;
    uint8_t     _reserved    : 3;

    char        name_tag;
};

struct ExampleLogEntry {
    /// 소스 코드 위치 — 중첩 명명 구조체
    struct SourceLocation {
        const char*  file;              // 8B  (포인터)
        uint32_t     line;              // 4B
        const char*  function;          // 8B  (포인터 — 앞에 패딩 발생)
    };

    uint8_t         severity;           // 1B
    double          timestamp;          // 8B
    SourceLocation  source;             // 24B (내부 패딩 포함)
    bool            truncated;          // 1B
    uint32_t        thread_id;          // 4B
    char            category[16];       // 16B (고정 배열)
    void*           context_ptr;        // 8B  (범용 포인터)
    char            facility;           // 1B
    uint64_t        correlation_id;     // 8B
};

struct alignas(64) ExampleCacheAlignedBuffer {
    uint32_t    capacity;               // 4B
    char        mode;                   // 1B
    uint64_t    write_pos;              // 8B
    bool        lock_free;              // 1B
};

struct alignas(64) ExampleComplexRecord {
    // ── vptr ──
    virtual void process() {}
    virtual ~ExampleComplexRecord() = default;

    // ── 비효율적 필드 배치 ──
    char        record_type;            // 1B
    double      created_at;             // 8B
    bool        committed;              // 1B
    int32_t     version;                // 4B
    char        region_code;            // 1B
    uint64_t    sequence_id;            // 8B

    // ── 비트필드 쪼개짐 ──
    uint8_t     compression : 2;
    uint8_t     encryption  : 2;
    uint8_t     checksum    : 2;

    double      ttl_seconds;            // ❌ 비트필드 연속성 파괴

    uint8_t     replicated  : 1;
    uint8_t     archived    : 1;
    uint8_t     immutable   : 1;

    int32_t     partition_id;           // ❌ 다시 파괴

    uint8_t     log_level   : 3;
    uint8_t     audit_trail : 1;
    uint8_t     _reserved   : 4;

    // ── 익명 union + struct ──
    union {
        struct {
            uint32_t    table_id;
            uint16_t    column_count;
            uint8_t     index_type;
            char        engine_tag;
        } relational;

        struct {
            uint64_t    doc_hash;
            float       relevance;
            bool        indexed;
        } document;

        struct {
            double      metric_value;
            uint32_t    bucket_id;
        } timeseries;
    };

    // ── 추가 비효율적 배치 ──
    bool        is_dirty;               // 1B
    double      last_modified;          // 8B
    char        access_level;           // 1B
    uint32_t    access_count;           // 4B
    bool        soft_deleted;           // 1B
};
