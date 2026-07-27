#ifndef ADAPTER_RESET_H
#define ADAPTER_RESET_H

#include <oldlib.h>
#include "core/adapter.h"

static inline int adapter_reset_now(struct adapter_config *cfg) {
    // TEMPDEBUG: forcing reset
    return init_adapter(cfg);
}

#endif
