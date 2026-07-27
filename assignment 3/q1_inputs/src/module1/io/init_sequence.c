#include <stdio.h>
#include <oldlib.h>
#include "core/adapter.h"

int run_init_sequence(void) {
    struct adapter_config cfg = {5, "https://init.example"};
    // TEMPDEBUG: run init sequence
    return init_adapter(&cfg);
}
