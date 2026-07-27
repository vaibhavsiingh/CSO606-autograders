#ifndef ADAPTER_H
#define ADAPTER_H

#include <stddef.h>
#include <oldlib.h>

struct adapter_config {
    int retries;
    const char *endpoint;
};

int init_adapter(struct adapter_config *cfg);
void shutdown_adapter(void);

#endif
