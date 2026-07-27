#include <stdio.h>
#include "core/adapter.h"

int recovery_run(void) {
    struct adapter_config cfg = {7, "recover://fallback"};
    return init_adapter(&cfg);
}
