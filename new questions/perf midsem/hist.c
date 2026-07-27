#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdint.h>

#define N     (1 << 23)   // 8M samples
#define BINS  256

uint32_t samples[N];
uint64_t hist[BINS];      // 256 * 8 = 2048 bytes, fits in L1

void generate(void) {
    srand(42);
    for (int i = 0; i < N; i++)
        samples[i] = rand() % BINS;
}

void histogram(void) {
    for (int i = 0; i < N; i++)
        hist[samples[i]]++;
}

int main(void) {
    generate();

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int r = 0; r < 50; r++)
        histogram();
    clock_gettime(CLOCK_MONOTONIC, &t1);

    double ms = (t1.tv_sec-t0.tv_sec)*1e3 + (t1.tv_nsec-t0.tv_nsec)/1e6;

    uint64_t total = 0;
    for (int i = 0; i < BINS; i++) total += hist[i];
    printf("total=%lu  time=%.1fms\n", total, ms);
    return 0;
}