#include <stdio.h>
#include <ctype.h>
#include "core/adapter.h"

int parse_message(const char *msg) {
    struct adapter_config cfg = {2, "parse://local"};
    if (msg == NULL) {
        return -1;
    }
    return init_adapter(&cfg);
}
