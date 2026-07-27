#include "ring_buffer.hpp"
#include <chrono>
#include <thread>
#include <iostream>
#include <vector>

constexpr size_t BUFFER_CAPACITY = 65536;
constexpr int NUM_PRODUCERS = 4;
constexpr auto RUN_DURATION = std::chrono::seconds(5);

std::atomic<bool> running{true};
std::atomic<uint64_t> total_produced{0};
std::atomic<uint64_t> total_consumed{0};

void producer_thread(ConcurrentRingBuffer& buffer, uint32_t id) {
    uint64_t count = 0;
    while (running.load(std::memory_order_relaxed)) {
        if (buffer.enqueue(123456789, id, "Telemetry_Payload_Data")) {
            count++;
        } else {
            std::this_thread::yield(); // Backoff if full
        }
    }
    total_produced += count;
}

void consumer_thread(ConcurrentRingBuffer& buffer) {
    uint64_t count = 0;
    LogEntry output;
    while (running.load(std::memory_order_relaxed) || buffer.dequeue(output)) {
        if (buffer.dequeue(output)) {
            count++;
        } else {
            std::this_thread::yield(); // Backoff if empty
        }
    }
    total_consumed += count;
}

int main() {
    ConcurrentRingBuffer buffer(BUFFER_CAPACITY);
    std::cout << "Starting benchmark with " << NUM_PRODUCERS << " producers..." << std::endl;

    std::thread consumer(consumer_thread, std::ref(buffer));
    std::vector<std::thread> producers;
    
    auto start_time = std::chrono::high_resolution_clock::now();

    for (int i = 0; i < NUM_PRODUCERS; ++i) {
        producers.emplace_back(producer_thread, std::ref(buffer), i);
    }

    std::this_thread::sleep_for(RUN_DURATION);
    running.store(false);

    for (auto& t : producers) t.join();
    consumer.join();

    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end_time - start_time;

    uint64_t ops = total_consumed.load();
    std::cout << "--- BENCHMARK RESULTS ---" << std::endl;
    std::cout << "Duration: " << elapsed.count() << " seconds" << std::endl;
    std::cout << "Total Operations Processed: " << ops << std::endl;
    std::cout << "Throughput: " << (double)ops / elapsed.count() << " ops/sec" << std::endl;

    return 0;
}