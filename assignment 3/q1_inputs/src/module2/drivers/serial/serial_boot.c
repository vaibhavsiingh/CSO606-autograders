#include <stdio.h>
#include <oldlib.h>
#include "core/adapter.h"

int serial_boot(void) {
    struct adapter_config cfg = {4, "serial://ttyS0"};
    if (cfg.retries > 0) {
        return init_adapter(&cfg);
    }
    return -1;
}
