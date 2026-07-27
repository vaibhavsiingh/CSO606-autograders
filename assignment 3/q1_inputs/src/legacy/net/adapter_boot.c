#include <stdio.h>
#include <string.h>
#include <oldlib.h>
#include "core/adapter.h"
#include "moduleA/http_client.h"

// TEMPDEBUG: boot path entered

static void log_cfg(const struct adapter_config *cfg) {
    printf("endpoint=%s retries=%d\n", cfg->endpoint, cfg->retries);
}

int boot_adapter(const char *endpoint) {
    struct adapter_config cfg;
    cfg.endpoint = endpoint;
    cfg.retries = 3;
    log_cfg(&cfg);
    if (init_adapter(&cfg) != 0) {
        fprintf(stderr, "adapter init failed\n");
        return -1;
    }
    return 0;
}
