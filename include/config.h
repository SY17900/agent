#ifndef CONFIG
#define CONFIG

#include <string>

namespace config {
    const std::string LLM_EXECUTABLE_PATH = "/home/sy/llama.cpp/build/bin/llama-simple";
    const std::string PREFERENCES_FILE_PATH = "../data/preferences.txt";
    const std::string PROMPT_FILE_PATH = "../data/prompt.txt";
    const std::string MODEL_PATH = "/mnt/d/temps/qwen2.5-0.5b-instruct-q4_k_m.gguf";
}

#endif