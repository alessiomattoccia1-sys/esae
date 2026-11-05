cmake_minimum_required(VERSION 3.20)
project(esae_sensor_demo LANGUAGES C CXX)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
add_executable(sensor_demo src/main.c src/sensor.c src/data.c src/diagnostics.c src/comm.c src/resource.cpp)
target_include_directories(sensor_demo PRIVATE include)
# Build this owned demo manually only. ESAE never executes repository CMake/Make.
