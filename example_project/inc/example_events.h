#pragma once

#include <cstdint>

enum class SensorType : uint8_t {
    Temperature  = 0,
    Pressure     = 1,
    Humidity     = 2,
    Acceleration = 3,
    Gyroscope    = 4,
};

enum MessageType : uint16_t {
    MSG_KEYBOARD = 0x0001,
    MSG_MOUSE    = 0x0002,
    MSG_TIMER    = 0x0003,
    MSG_RESIZE   = 0x0004,
};

struct ExampleEventMessage {
    MessageType msg_type;           // 2B (enum : uint16_t)

    union {
        struct {
            uint32_t    key_code;
            uint8_t     modifiers;
            bool        repeat;
            uint16_t    scan_code;
        } keyboard;                 // 8B

        struct {
            double      pos_x;
            double      pos_y;
            uint32_t    button_mask;
            bool        dragging;
        } mouse;                    // 24B+ (내부 패딩 포함)

        struct {
            uint64_t    timer_id;
            double      interval_ms;
            uint32_t    fire_count;
        } timer;                    // 24B+

        struct {
            int32_t     new_width;
            int32_t     new_height;
            bool        fullscreen;
            float       scale_factor;
        } resize;                   // 16B+
    };

    bool        handled;            // 1B
    uint64_t    timestamp_ns;       // 8B
};

struct ExampleSensorSample;
typedef void (*SensorCallback)(const ExampleSensorSample* sample, void* ctx);

struct ExampleSensorSample {
    SensorType      type;               // 1B  (enum class : uint8_t)
    double          value;              // 8B
    char            unit[8];            // 8B  (고정 배열)
    bool            calibrated;         // 1B
    uint32_t        sensor_id;          // 4B
    float           accuracy;           // 4B
    char            location_tag;       // 1B
    uint64_t        sequence_num;       // 8B
    SensorCallback  on_threshold;       // 8B  (함수 포인터)
    volatile bool   alert_active;       // 1B  (volatile 한정자)
    int32_t         error_code;         // 4B
    float           raw_readings[4];    // 16B (배열)
    bool            overflow_flag;      // 1B
    double          moving_average;     // 8B
};
