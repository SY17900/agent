#ifndef CONFIG
#define CONFIG

#include <string>

namespace config {
    const std::string LLM_EXECUTABLE_PATH = "/home/sy/llama.cpp/build/bin/llama-run";
    const std::string PREFERENCES_FILE_PATH = "/home/sy/agent/data/preferences.txt";
    const std::string PROMPT_FILE_PATH = "/home/sy/agent/data/prompt.txt";
    const std::string SMALL_MODEL_PATH = "/mnt/d/temps/qwen2.5-0.5b-instruct-q4_k_m.gguf";
    const std::string BIG_MODEL_PATH = "/mnt/d/temps/qwen2.5-3b-instruct-q4_k_m.gguf";
    const std::string PYTHON3_PATH = "/home/sy/agent/.venv/bin/python3";
    const std::string RANKER_SCRIPT_PATH = "/home/sy/agent/src/python/ranker.py";
    const std::string ICON_FILE_PATH = "/home/sy/agent/data/icon.txt";
}

#endif