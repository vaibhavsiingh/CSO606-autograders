#ifndef RECOVERY_H
#define RECOVERY_H

#include <oldlib.h>
#include "core/adapter.h"

static inline int recovery_prepare(struct adapter_config *cfg) {
    return init_adapter(cfg);
}

#endif
