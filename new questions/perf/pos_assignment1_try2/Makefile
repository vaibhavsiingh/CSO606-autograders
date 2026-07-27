CXX      = g++
CXXFLAGS = -O3 -g -std=c++17 -pthread -march=native -Wno-interference-size

TARGET = ipc_bench
SRC    = main.cpp

all: $(TARGET)

$(TARGET): $(SRC) ring_buffer.hpp
	$(CXX) $(CXXFLAGS) $(SRC) -o $(TARGET)

clean:
	rm -f $(TARGET) perf.data perf.data.old

