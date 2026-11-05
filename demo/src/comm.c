#include "comm.h"
#include <stdio.h>
int comm_send(const char *message) {
    if (message == 0) return -1;
    return puts(message) < 0 ? -1 : 0;
}
