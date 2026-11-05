#include "data.h"
#include <stdlib.h>
int data_bad_index(void) {
    int values[4] = {1, 2, 3, 4};
    return values[4]; /* DEFECT D01: out-of-bounds read. */
}
int data_null(void) {
    int *value = 0;
    return *value; /* DEFECT D02: null dereference. */
}
void data_leak(void) {
    int *buffer = (int *)malloc(8 * sizeof(int));
    if (buffer != 0) buffer[0] = 42;
    /* DEFECT D04: owned allocation is not freed. Never called by main. */
}
int data_store_safe(int *values, size_t capacity, size_t index, int value) {
    if (values == 0 || index >= capacity) return -1;
    values[index] = value;
    return 0;
}
