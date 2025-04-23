#include "config.h"
#include "llm_interface.h"
#include "db_interface.h"
#include <iostream>
#include <string>
#include <vector>
#include <stdexcept>
#include <cstdlib>
#include <sstream>
#include <fstream>

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " \"<user command>\"" << std::endl;
        return 1;
    }
    std::string user_command = argv[1];
    std::cout << "Received command: " << user_command << std::endl;

    std::ifstream icon_file(config::ICON_FILE_PATH);

    if (icon_file.is_open()) {
        std::string line;
        while (std::getline(icon_file, line)) {
            std::cout << line << std::endl;
        }
        icon_file.close();
    }

    try {
# ifdef VERSION_BIG
        LLMInterface llm(config::LLM_EXECUTABLE_PATH, config::BIG_MODEL_PATH);
# else
        LLMInterface llm(config::LLM_EXECUTABLE_PATH, config::SMALL_MODEL_PATH);
# endif
        
        std::string query_string;
        try {
            query_string = llm.generateQuery(user_command);
            if (query_string.empty()) {
                std::cerr << "LLM did not return a valid query string. Aborting." << std::endl;
                return 1;
            }
        } catch (const LLMError& e) {
            std::cerr << "Error interacting with LLM: " << e.what() << std::endl;
            return 1;
        }

        DBInterface db;
        std::vector<std::string> results;
        try {
            results = db.executeQuery(query_string);
        } catch (const DatabaseError& e) {
            std::cerr << "In-memory data filtering failed: " << e.what() << std::endl;
            return 1;
        } catch (const std::exception& e) {
            std::cerr << "Error during data processing: " << e.what() << std::endl;
            return 1;
        }

        std::stringstream comma_separated_ss;
        for (size_t i = 0; i < results.size(); ++i) {
            comma_separated_ss << results[i];
            if (i < results.size() - 1) {
                comma_separated_ss << ",";
            }
        }
        std::string comma_separated_string = comma_separated_ss.str();

        std::string ranker_command = config::PYTHON3_PATH;
        ranker_command += " ";
        ranker_command += config::RANKER_SCRIPT_PATH;
        ranker_command += " ";
        ranker_command += comma_separated_string;

        int system_return_code = std::system(ranker_command.c_str());

        if (system_return_code == 0) {
            std::cout << "\nGoodbye!" << std::endl;
        } else {
            std::cerr << "\nError: Python script execution failed with return code " << system_return_code << std::endl;
        }
    } catch (const std::exception& e) {
        std::cerr << "An unexpected error occurred: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "An unknown error occurred." << std::endl;
        return 1;
    }

    return 0;
}