#include "llm_interface.h"
#include "config.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <iostream>
#include <memory>
#include <array>
#include <string>

// Helper struct for popen/pclose RAII
struct PopenDeleter {
    void operator()(FILE* pipe) const {
        if (pipe) {
            // pclose returns the exit status of the command
            int status = pclose(pipe);
            // Optionally check status here, e.g., WEXITSTATUS(status)
            if (status == -1) {
                std::cerr << "Warning: pclose failed." << std::endl;
            } else if (WIFEXITED(status)) {
                int exit_code = WEXITSTATUS(status);
                if (exit_code != 0) {
                    std::cerr << "Warning: LLM process exited with status code: " << exit_code << std::endl;
                }
            } else if (WIFSIGNALED(status)) {
                std::cerr << "Warning: LLM process terminated by signal " << WTERMSIG(status) << std::endl;
            }
        }
    }
};
using unique_pipe_ptr = std::unique_ptr<FILE, PopenDeleter>;

LLMInterface::LLMInterface(const std::string& llm_executable_path, const std::string& model_path): 
    app_path_(llm_executable_path), model_path_(model_path) {
        std::ifstream file(config::PROMPT_FILE_PATH);
        if (!file.is_open()) {
            std::cerr << "Error: Could not open preferences file: " << config::PROMPT_FILE_PATH << std::endl;
        }

        std::stringstream buffer;
        buffer << file.rdbuf();
        system_prompt_ = buffer.str();
        file.close();
        std::cout << "Successfully loaded preferences from: " << config::PROMPT_FILE_PATH << std::endl;
    }

std::string LLMInterface::executeCommand(const std::string& command) {
    std::string result = "";
    std::array<char, 256> buffer;

    // 使用 popen 执行命令并读取其标准输出
    // " 2>&1" 可以选择性添加，用于捕获 stderr 到结果中，方便调试
    unique_pipe_ptr pipe(popen((command + " 2>&1").c_str(), "r"));
    if (!pipe) {
        throw LLMError("Failed to popen command: " + command);
    }

    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    // pclose is called automatically by unique_ptr's deleter (PopenDeleter)

    // 去除可能的尾部换行符
    if (!result.empty() && result.back() == '\n') {
        result.pop_back();
    }

    if (result.empty()) {
        std::cerr << "Warning: LLM command returned empty output." << std::endl;
    }

    return result;
}

std::string LLMInterface::generateQuery(const std::string& user_command, const std::string& preferences_info) {
    // 1. 合并用户指令和偏好信息为一个字符串
    std::string combined_input = system_prompt_ + "用户指令：" + user_command;
    if (!preferences_info.empty()) {
        combined_input += " 用户偏好：" + preferences_info;
    }

    // 2. 对合并后的字符串进行处理，确保可以安全地作为命令行参数传递
    //    最重要的是处理引号和特殊字符。一个简单（但不完美）的方法是用双引号包裹。
    //    需要转义输入字符串中的双引号。
    std::string escaped_input = "";
    escaped_input.reserve(combined_input.length() + 2); // 预留空间
    escaped_input += '"'; // 开头引号
    for (char c : combined_input) {
        if (c == '"' || c == '\\') { // 转义双引号和反斜杠
            escaped_input += '\\';
        }
        escaped_input += c;
    }
    escaped_input += '"'; // 结尾引号

    // 3. 构建完整的命令行
    //    假设 LLM 程序接受一个参数，该参数就是包含所有信息的字符串
    std::string full_command = app_path_ + " -m " + model_path_ + " " + escaped_input;
    std::cout << "Executing LLM command: " << full_command << std::endl; // Debug 输出，小心过长

    // 4. 执行命令并获取输出 (LLM生成的“查询”字符串)
    try {
        return executeCommand(full_command);
    } catch (const std::exception& e) {
        throw LLMError("LLM command execution failed: " + std::string(e.what()));
    }
}