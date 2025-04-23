#ifndef LLM_INTERFACE
#define LLM_INTERFACE

#include <string>
#include <stdexcept>

class LLMError : public std::runtime_error {
public:
    LLMError(const std::string& message) : std::runtime_error(message) {}
};

class LLMInterface {
public:
    LLMInterface(const std::string& llm_executable_path, const std::string& model_path);
    std::string generateQuery(const std::string& user_command);

private:
    std::string app_path_;
    std::string model_path_;
    std::string system_prompt_;
    std::string executeCommand(const std::string& command);
};

#endif