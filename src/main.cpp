#include "config.h"
#include "user_preferences.h"
#include "llm_interface.h"
#include "db_interface.h"
#include <iostream>
#include <string>
#include <vector>
#include <stdexcept>

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " \"<user command>\"" << std::endl;
        return 1;
    }
    std::string user_command = argv[1];
    std::cout << "Received command: " << user_command << std::endl;

    try {
        UserPreferences prefs;
        if (!prefs.loadFromFile(config::PREFERENCES_FILE_PATH)) {
            std::cerr << "Warning: Could not load user preferences. Proceeding without them." << std::endl;
        }
        std::string prefs_string = prefs.getPreferencesAsString();

# ifdef VERSION_BIG
        LLMInterface llm(config::LLM_EXECUTABLE_PATH, config::BIG_MODEL_PATH);
# else
        LLMInterface llm(config::LLM_EXECUTABLE_PATH, config::SMALL_MODEL_PATH);
# endif
        
        std::string query_string;
        try {
            query_string = llm.generateQuery(user_command, prefs_string);
            if (query_string.empty()) {
                std::cerr << "LLM did not return a valid query string. Aborting." << std::endl;
                return 1;
            }
        } catch (const LLMError& e) {
            std::cerr << "Error interacting with LLM: " << e.what() << std::endl;
            return 1;
        }

        DBInterface db;
        std::vector<std::vector<std::string>> results;
        try {
            results = db.executeQuery(query_string);
        } catch (const DatabaseError& e) {
            std::cerr << "In-memory data filtering failed: " << e.what() << std::endl;
            return 1;
        } catch (const std::exception& e) {
            std::cerr << "Error during data processing: " << e.what() << std::endl;
            return 1;
        }

        std::cout << "\n--- Query Results ---" << std::endl;
        if (results.empty()) {
            std::cout << "(No results found)" << std::endl;
        } else {
            for (const auto& row : results) {
                for (size_t i = 0; i < row.size(); ++i) {
                    std::cout << row[i];
                    if (i < row.size() - 1) {
                        std::cout << "\t";
                    }
                }
                std::cout << std::endl;
            }
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