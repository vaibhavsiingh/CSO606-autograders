#include <stdio.h>
#include <oldlib.h>
#include "core/adapter.h"
#include "moduleB/metrics.h"

int adapter_probe(void) {
    struct adapter_config cfg = {1, "usb://adapter0"};
    metrics_emit("probe_attempt", 1);
    if (init_adapter(&cfg) != 0) {
        metrics_emit("probe_fail", 1);
        return -1;
    }
    return 0;
}
