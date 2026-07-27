#include <chrono>
#include <iostream>
#include <thread>
#include <vector>
#include <atomic>
#include <cstdint>
#include "ring_buffer.hpp"

// ── Configuration ────────────────────────────────────────────────────────────
constexpr size_t BUFFER_CAPACITY = 65536;
constexpr int    NUM_PRODUCERS   = 6;
constexpr auto   RUN_DURATION    = std::chrono::seconds(5);

// ── Shared state ─────────────────────────────────────────────────────────────
std::atomic<bool>     running{true};
std::atomic<uint64_t> total_produced{0};
std::atomic<uint64_t> total_consumed{0};

// ── Thread functions ──────────────────────────────────────────────────────────
void producer_thread(ConcurrentRingBuffer& buffer, uint32_t id) {
    uint64_t count = 0;
    while (running.load(std::memory_order_relaxed)) {
        if (buffer.enqueue(123456789ULL, id, "Telemetry_Payload_Data")) {
            ++count;
        } else {
            std::this_thread::yield();
        }
    }
    total_produced.fetch_add(count, std::memory_order_relaxed);
}

void consumer_thread(ConcurrentRingBuffer& buffer) {
    uint64_t count = 0;
    LogEntry output{};
    while (true) {
        if (buffer.dequeue(output)) {
            ++count;
        } else {
            if (!running.load(std::memory_order_relaxed)) {
                while (buffer.dequeue(output)) ++count;
                break;
            }
            std::this_thread::yield();
        }
    }
    total_consumed.fetch_add(count, std::memory_order_relaxed);
}

// ── Main ──────────────────────────────────────────────────────────────────────
int main() {
    std::cout << "Buffer capacity : " << BUFFER_CAPACITY << "\n";
    std::cout << "Producer threads: " << NUM_PRODUCERS   << "\n";
    std::cout << "Run duration    : " << RUN_DURATION.count() << "s\n";
    std::cout << "Starting benchmark...\n\n";

    ConcurrentRingBuffer buffer(BUFFER_CAPACITY);
    std::thread consumer(consumer_thread, std::ref(buffer));

    auto start = std::chrono::high_resolution_clock::now();

    std::vector<std::thread> producers;
    for (int i = 0; i < NUM_PRODUCERS; ++i)
        producers.emplace_back(producer_thread, std::ref(buffer), (uint32_t)i);

    std::this_thread::sleep_for(RUN_DURATION);
    running.store(false, std::memory_order_relaxed);

    for (auto& t : producers) t.join();
    consumer.join();

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end - start;

    uint64_t consumed = total_consumed.load(std::memory_order_relaxed);
    std::cout << "Duration    : " << elapsed.count() << " s\n";
    std::cout << "Consumed    : " << consumed << " items\n";
    std::cout << "Throughput  : "
              << (double)consumed / elapsed.count() / 1e6
              << " M ops/sec\n";
    return 0;
}

