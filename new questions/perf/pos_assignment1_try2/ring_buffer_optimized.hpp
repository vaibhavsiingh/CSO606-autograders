#pragma once
#include <atomic>
#include <cstring>
#include <stdexcept>
#include <thread>

// FIX 3: Removed virtual destructor.
// The vtable pointer added hidden per-object overhead and prevented the
// compiler from vectorizing copies. Now a plain POD struct.
struct LogEntry {
    uint64_t timestamp;
    uint32_t thread_id;
    char payload[32];
};

class ConcurrentRingBuffer {
private:
    // FIX 1: alignas(64) places head_ and tail_ on separate cache lines.
    // In the flawed version they were adjacent — one 64-byte cache line held
    // both. Every consumer write to head_ invalidated the producer's cached
    // copy of tail_ and vice versa (MESI HITM events).
    // Now each lives on its own line: writes to one cannot affect the other.
    alignas(64) std::atomic<size_t> head_{0};
    alignas(64) std::atomic<size_t> tail_{0};

    const size_t capacity_;
    const size_t mask_;      // capacity_ - 1, for fast bitwise index wrap

    // FIX 3: Flat pre-allocated array of LogEntry values (not pointers).
    // The flawed version stored LogEntry** — an array of pointers to heap
    // objects scattered across memory. Every dequeue chased a pointer to a
    // random heap address, guaranteed L1 miss.
    // Now all entries are contiguous. Sequential access is prefetcher-friendly
    // and there are zero heap allocations on the hot path.
    LogEntry* storage_;

    // Separate atomic flag array to signal slot readiness.
    // Needed because we removed the nullptr sentinel the flawed version used.
    std::atomic<bool>* ready_;

public:
    explicit ConcurrentRingBuffer(size_t capacity)
        : capacity_(capacity)
        , mask_(capacity - 1)
        , storage_(new LogEntry[capacity])
        , ready_(new std::atomic<bool>[capacity])
    {
        if (capacity == 0 || (capacity & mask_) != 0)
            throw std::invalid_argument("Capacity must be a non-zero power of 2.");
        for (size_t i = 0; i < capacity_; ++i)
            ready_[i].store(false, std::memory_order_relaxed);
    }

    ~ConcurrentRingBuffer() {
        delete[] storage_;
        delete[] ready_;
    }

    // Lock-free Multi-Producer Enqueue
    bool enqueue(uint64_t ts, uint32_t tid, const char* data) {
        // FIX 2: Explicit memory orders replace the implicit seq_cst defaults.
        // relaxed on tail_ load: we only need a recent value to start the CAS.
        // acquire on head_ load: syncs with consumer's release on head_ so we
        //   correctly observe freed slots.
        // release/relaxed on CAS: the release ensures our upcoming slot writes
        //   are visible to the consumer after it acquires the ready_ flag.
        size_t current_tail = tail_.load(std::memory_order_relaxed);

        while (true) {
            size_t current_head = head_.load(std::memory_order_acquire);

            if (current_tail - current_head >= capacity_)
                return false; // Queue full

            if (tail_.compare_exchange_weak(current_tail, current_tail + 1,
                                            std::memory_order_release,
                                            std::memory_order_relaxed))
                break;
        }

        // FIX 3 (bonus): & mask_ replaces % capacity_.
        // The modulo compiles to a 64-bit division (divq) — 30 to 90 cycles.
        // Bitwise AND is 1 cycle. Requires capacity to be a power of 2.
        size_t index = current_tail & mask_;

        // Write directly into contiguous pre-allocated memory. No heap call.
        storage_[index].timestamp = ts;
        storage_[index].thread_id = tid;
        std::strncpy(storage_[index].payload, data, sizeof(storage_[index].payload) - 1);
        storage_[index].payload[sizeof(storage_[index].payload) - 1] = '\0';

        // Publish: release store pairs with consumer's acquire load on ready_.
        ready_[index].store(true, std::memory_order_release);
        return true;
    }

    // Single-Consumer Dequeue
    bool dequeue(LogEntry& out_entry) {
        size_t current_head = head_.load(std::memory_order_relaxed);
        size_t current_tail = tail_.load(std::memory_order_acquire);

        if (current_head == current_tail)
            return false; // Queue empty

        size_t index = current_head & mask_;

        // Spin until producer has finished writing this slot.
        while (!ready_[index].load(std::memory_order_acquire)) {
#if defined(__x86_64__) || defined(_M_X64)
            __builtin_ia32_pause();
#else
            std::this_thread::yield();
#endif
        }

        out_entry.timestamp = storage_[index].timestamp;
        out_entry.thread_id = storage_[index].thread_id;
        std::memcpy(out_entry.payload, storage_[index].payload,
                    sizeof(out_entry.payload));

        // Reset flag for the next producer that wraps to this index.
        ready_[index].store(false, std::memory_order_relaxed);

        // Release: makes head_ advancement visible to producers.
        head_.store(current_head + 1, std::memory_order_release);
        return true;
    }
};