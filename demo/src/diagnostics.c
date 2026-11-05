#include "diagnostics.h"
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>
volatile unsigned shared_samples = 0;
unsigned diagnostics_retry(unsigned value) {
    if (value == 0) return 0;
    return diagnostics_retry(value - 1) + 1; /* RISK R03: recursion; bounded for this input. */
}
void Sensor_IRQHandler(void) {
    void *scratch = malloc(16); /* RISK R01/R04: allocation in ISR-named function. */
    usleep(1000); /* RISK R02/R04: potentially blocking in ISR-named function. */
    shared_samples += 1;
    free(scratch);
}
unsigned diagnostics_shared_value(void) {
    return shared_samples; /* RISK R05: shared candidate, no proof of a data race. */
}
uint8_t diagnostics_narrow_add(uint8_t a, uint8_t b) {
    uint8_t result = a + b; /* RISK R06: narrowing modulo arithmetic, not signed UB. */
    return result;
}
