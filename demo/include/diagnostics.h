#ifndef ESAE_DIAGNOSTICS_H
#define ESAE_DIAGNOSTICS_H
#include "comm.h"
unsigned diagnostics_retry(unsigned value);
void Sensor_IRQHandler(void);
unsigned diagnostics_shared_value(void);
#endif
