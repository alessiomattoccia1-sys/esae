#ifndef ESAE_DATA_H
#define ESAE_DATA_H
#include <stddef.h>
int data_bad_index(void);
int data_null(void);
void data_leak(void);
int data_store_safe(int *values, size_t capacity, size_t index, int value);
#endif
