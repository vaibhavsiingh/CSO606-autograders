#include <stdio.h>
#include "moduleB/metrics.h"

int read_file(const char *path) {
    FILE *fp = fopen(path, "r");
    if (!fp) {
        return -1;
    }
    fclose(fp);
    return 0;
}
