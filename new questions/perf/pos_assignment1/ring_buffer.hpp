#pragma once
#include <atomic>
#include <cstring>
#include <memory>
#include <vector>
#include <thread>
#include <new>        // For std::hardware_destructive_interference_size
#include <stdexcept>   // <-- ADD THIS FOR std::invalid_argument

struct LogEntry {
    uint64_t timestamp;
    uint32_t thread_id;
    char payload[32];
};

class ConcurrentRingBuffer {
private:
    struct BufferSlot {
        std::atomic<bool> is_ready{false};
        LogEntry entry;
    };

#ifdef __cpp_lib_hardware_interference_size
    static constexpr size_t CacheLineSize = std::hardware_destructive_interference_size;
#else
    static constexpr size_t CacheLineSize = 64; 
#endif

    alignas(CacheLineSize) std::atomic<size_t> head_{0};
    alignas(CacheLineSize) std::atomic<size_t> tail_{0};
    
    const size_t capacity_;
    const size_t mask_; 
    BufferSlot* const storage_;

public:
    explicit ConcurrentRingBuffer(size_t capacity) 
        : capacity_(capacity)
        , mask_(capacity - 1)
        , storage_(new BufferSlot[capacity]) 
    {
        if ((capacity & mask_) != 0 || capacity == 0) {
            throw std::invalid_argument("Capacity must be a power of 2 for fast bitwise masking.");
        }
    }

    ~ConcurrentRingBuffer() {
        delete[] storage_;
    }

    bool enqueue(uint64_t ts, uint32_t tid, const char* data) {
        size_t current_tail = tail_.load(std::memory_order_relaxed);
        
        while (true) {
            size_t current_head = head_.load(std::memory_order_acquire);
            
            if (current_tail - current_head >= capacity_) {
                return false; 
            }
            
            if (tail_.compare_exchange_weak(current_tail, current_tail + 1, 
                                            std::memory_order_release, 
                                            std::memory_order_relaxed)) {
                break;
            }
        }

        size_t index = current_tail & mask_; 
        
        storage_[index].entry.timestamp = ts;
        storage_[index].entry.thread_id = tid;
        
        std::strncpy(storage_[index].entry.payload, data, sizeof(storage_[index].entry.payload) - 1);
        storage_[index].entry.payload[sizeof(storage_[index].entry.payload) - 1] = '\0';

        storage_[index].is_ready.store(true, std::memory_order_release);
        return true;
    }

    bool dequeue(LogEntry& out_entry) {
        size_t current_head = head_.load(std::memory_order_relaxed);
        size_t current_tail = tail_.load(std::memory_order_acquire);

        if (current_head == current_tail) {
            return false; 
        }

        size_t index = current_head & mask_;

        while (!storage_[index].is_ready.load(std::memory_order_acquire)) {
            #if defined(__x86_64__) || defined(_M_X64)
                __builtin_ia32_pause(); 
            #else
                std::this_thread::yield();
            #endif
        }

        out_entry.timestamp = storage_[index].entry.timestamp;
        out_entry.thread_id = storage_[index].entry.thread_id;
        std::memcpy(out_entry.payload, storage_[index].entry.payload, sizeof(out_entry.payload));

        storage_[index].is_ready.store(false, std::memory_order_relaxed);
        head_.store(current_head + 1, std::memory_order_release); 

        return true;
    }
};