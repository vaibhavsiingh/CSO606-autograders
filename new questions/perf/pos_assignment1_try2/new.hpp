#pragma once
#include <atomic>
#include <iostream>
#include <memory>
#include <string>
#include <vector>
#include <thread>
#include <cstdio>
#include <algorithm>

// A polymorphic log entry. Looks clean and professional.
// HIDDEN FLAW 3: The virtual destructor forces vtable pointer storage inside each object.
// This prevents the compiler from using SIMD/vectorized copies and inflates each entry
// by one pointer width. Combined with dynamic allocation, it guarantees pointer chasing.
struct LogEntry {
    uint64_t timestamp;
    uint32_t thread_id;
    char payload[32];
    virtual ~LogEntry() = default;
};

class ConcurrentRingBuffer {
private:
    // HIDDEN FLAW 1: FALSE SHARING
    // head_ and tail_ are adjacent in memory. Each is 8 bytes.
    // Together they comfortably fit on ONE 64-byte cache line.
    // Producers write tail_; consumers write head_. Because they share a
    // cache line, every write by one side invalidates the other side's
    // cached copy via the MESI protocol — triggering expensive L3 round-trips
    // (HITM events) on every single enqueue and dequeue.
    std::atomic<size_t> head_{0};
    std::atomic<size_t> tail_{0};

    size_t capacity_;

    // HIDDEN FLAW 3 (continued): Array of raw pointers to heap objects.
    // Two-level indirection: first fetch the pointer, then chase it to
    // a random heap location for the actual data. Guaranteed L1 cache miss
    // on every read. Under 4 producer threads, the heap allocator also
    // contends on internal glibc mutexes, making this secretly NOT lock-free.
    LogEntry** storage_;

public:
    explicit ConcurrentRingBuffer(size_t capacity) : capacity_(capacity) {
        storage_ = new LogEntry*[capacity_];
        for (size_t i = 0; i < capacity_; ++i) {
            storage_[i] = nullptr;
        }
    }

    ~ConcurrentRingBuffer() {
        for (size_t i = 0; i < capacity_; ++i) {
            delete storage_[i];
        }
        delete[] storage_;
    }

    // Lock-free Multi-Producer Enqueue
    bool enqueue(uint64_t ts, uint32_t tid, const char* data) {
        // HIDDEN FLAW 2: IMPLICIT std::memory_order_seq_cst
        // Every atomic load/store/CAS below uses the default seq_cst ordering.
        // On x86_64 this compiles to a LOCK prefix or MFENCE instruction, which:
        //   (a) drains the CPU store buffer completely before proceeding
        //   (b) prevents any out-of-order execution across the barrier
        //   (c) serializes all cores observing this address globally
        // This is far stronger than needed. Acquire-Release semantics are sufficient
        // for a producer-consumer queue and carry no hardware fence overhead on x86.
        size_t current_tail = tail_.load(); // seq_cst

        while (true) {
            size_t current_head = head_.load(); // seq_cst

            if (current_tail - current_head >= capacity_) {
                return false; // Queue full
            }

            if (tail_.compare_exchange_weak(current_tail, current_tail + 1)) { // seq_cst
                break;
            }
        }

        // HIDDEN FLAW 3 (hot path): operator new inside the lock-free critical path.
        // glibc malloc acquires a per-arena spinlock under thread contention.
        // Even when it doesn't, it walks freelists — a non-deterministic latency spike
        // that completely undermines the latency goal of a lock-free design.
        // Additionally: size_t index = current_tail % capacity_ compiles to
        // a 64-bit integer division (divq on x86) which stalls the execution
        // unit for 30–90 cycles.
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
        size_t current_head = head_.load(); // seq_cst
        size_t current_tail = tail_.load(); // seq_cst

        if (current_head == current_tail) {
            return false; // Queue empty
        }

        size_t index = current_head % capacity_;

        // Spin until producer finishes writing the pointer
        while (storage_[index] == nullptr) {
            std::this_thread::yield();
        }
        LogEntry* slot = storage_[index];

        out_entry.timestamp = slot->timestamp;
        out_entry.thread_id = slot->thread_id;
        std::copy(slot->payload, slot->payload + 32, out_entry.payload);

        delete slot;
        storage_[index] = nullptr;
        head_.store(current_head + 1); // seq_cst

        return true;
    }
};