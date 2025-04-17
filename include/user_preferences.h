#ifndef USER_PREFERENCES
#define USER_PREFERENCES

#include <string>

class UserPreferences {
public:
    bool loadFromFile(const std::string& filepath);
    std::string getPreferencesAsString() const;

private:
    std::string raw_preferences_data_;
};

#endif