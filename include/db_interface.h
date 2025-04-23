#ifndef DB_INTERFACE
#define DB_INTERFACE

#include <string>
#include <vector>
#include <map>
#include <stdexcept>

class DatabaseError : public std::runtime_error {
public:
    DatabaseError(const std::string& message) : std::runtime_error(message) {}
};

using DbRow = std::map<std::string, std::string>;
using DbTable = std::vector<DbRow>;

class DBInterface {
public:
    DBInterface();
    ~DBInterface() = default;
    std::vector<std::string> executeQuery(const std::string& query_string);

private:
    DbTable restaurants_;
    void initializeSampleData();
    DBInterface(const DBInterface&) = delete;
    DBInterface& operator=(const DBInterface&) = delete;
};

#endif