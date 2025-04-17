cmake_minimum_required(VERSION 3.16)

project(agent)
set(EXECUTABLE_OUTPUT_PATH ${PROJECT_SOURCE_DIR}/bin)
aux_source_directory(src SRC_LIST)
include_directories(include)
add_executable(agent ${SRC_LIST})