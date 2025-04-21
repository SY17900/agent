cmake_minimum_required(VERSION 3.16)

project(agent)

option(BUILD_VERSION_BIG "Set to ON to build the BIG version, OFF for the SMALL/Default version." OFF)
set(APP_OUTPUT_DIR ${PROJECT_SOURCE_DIR}/build/bin)
aux_source_directory(src SRC_LIST)

add_executable(agent ${SRC_LIST})
target_include_directories(agent PRIVATE ${PROJECT_SOURCE_DIR}/include)
set_target_properties(agent PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${APP_OUTPUT_DIR})

if(BUILD_VERSION_BIG)
    message(STATUS "Configuring project '${PROJECT_NAME}' for BIG version build.")
    target_compile_definitions(agent PRIVATE VERSION_BIG)
    set_target_properties(agent PROPERTIES OUTPUT_NAME "${PROJECT_NAME}_big")
else()
    message(STATUS "Configuring project '${PROJECT_NAME}' for Default version build.")
    set_target_properties(agent PROPERTIES OUTPUT_NAME "${PROJECT_NAME}_small")
endif()