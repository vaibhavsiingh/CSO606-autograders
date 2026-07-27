#pragma once
#include <atomic>
#include <iostream>
#include <memory>
#include <string>
#include <vector>
#include <thread>
#include <cstdio>
#include <algorithm>

struct LogEntry {
    uint64_t timestamp;
    uint32_t thread_id;
    char payload[32];
    virtual ~LogEntry() = default;
};

class ConcurrentRingBuffer {
private:
    std::atomic<size_t> head_{0};
    std::atomic<size_t> tail_{0};
    size_t capacity_;
    LogEntry** storage_;

public:
    explicit ConcurrentRingBuffer(size_t capacity) : capacity_(capacity) {
        storage_ = new LogEntry*[capacity_];
        for (size_t i = 0; i < capacity_; ++i)
            storage_[i] = nullptr;
    }

    ~ConcurrentRingBuffer() {
        for (size_t i = 0; i < capacity_; ++i)
            delete storage_[i];
        delete[] storage_;
    }

    // Lock-free Multi-Producer Enqueue
    bool enqueue(uint64_t ts, uint32_t tid, const char* data) {
        size_t current_tail = tail_.load();

        while (true) {
            size_t current_head = head_.load();

            if (current_tail - current_head >= capacity_)
                return false;

            if (tail_.compare_exchange_weak(current_tail, current_tail + 1))
                break;
        }

        size_t index = current_tail % capacity_;

        LogEntry* entry = new LogEntry();
        entry->timestamp = ts;
        entry->thread_id = tid;
        std::snprintf(entry->payload, sizeof(entry->payload), "%s", data);

        storage_[index] = entry;
        return true;
    }

    // Single-Consumer Dequeue
    bool dequeue(LogEntry& out_entry) {
        size_t current_head = head_.load();
        size_t current_tail = tail_.load();

        if (current_head == current_tail)
            return false;

        size_t index = current_head % capacity_;

        while (storage_[index] == nullptr)
            std::this_thread::yield();

        LogEntry* slot = storage_[index];

        out_entry.timestamp = slot->timestamp;
        out_entry.thread_id = slot->thread_id;
        std::copy(slot->payload, slot->payload + 32, out_entry.payload);

        delete slot;
        storage_[index] = nullptr;
        head_.store(current_head + 1);

        return true;
    }
};

