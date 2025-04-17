#include "user_preferences.h"
#include <fstream>
#include <sstream>
#include <iostream>

bool UserPreferences::loadFromFile(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
        std::cerr << "Error: Could not open preferences file: " << filepath << std::endl;
        return false;
    }

    std::stringstream buffer;
    buffer << file.rdbuf();
    raw_preferences_data_ = buffer.str();
    file.close();

    std::cout << "Successfully loaded preferences from: " << filepath << std::endl;
    return true;
}

std::string UserPreferences::getPreferencesAsString() const {
    return raw_preferences_data_;
}