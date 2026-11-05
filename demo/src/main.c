#include "sensor.h"
#include "data.h"
#include "comm.h"
#include <stdio.h>
int main(void) {
    uint16_t samples[2] = {sensor_read(0), sensor_read(1)};
    int output[2] = {0, 0};
    if (data_store_safe(output, 2, 0, sensor_average(samples, 2)) != 0) return 1;
    printf("Sensor simulator: average=%d\n", output[0]);
    return comm_send("Acquisition complete.");
}
