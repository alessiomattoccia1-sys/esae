#ifndef ESAE_SENSOR_H
#define ESAE_SENSOR_H
#include <stdint.h>
uint16_t sensor_read(unsigned channel);
uint16_t sensor_average(const uint16_t *values, unsigned count);
int sensor_uninitialized(int ready);
#endif
