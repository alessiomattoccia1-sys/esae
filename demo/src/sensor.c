#include "sensor.h"
uint16_t sensor_read(unsigned channel) {
    return (uint16_t)(100U + (channel % 4U) * 10U);
}
uint16_t sensor_average(const uint16_t *values, unsigned count) {
    if (values == 0 || count == 0 || count > 16) return 0;
    unsigned total = 0;
    for (unsigned i = 0; i < count; ++i) total += values[i];
    return (uint16_t)(total / count);
}
int sensor_uninitialized(int ready) {
    int sample;
    if (ready) sample = 10;
    return sample; /* DEFECT D03: sample is uninitialized when ready == 0. */
}
