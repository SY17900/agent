#include "db_interface.h"
#include <iostream>
#include <sstream>
#include <algorithm>
#include <locale>
#include <codecvt>
#include <string>
#include <iomanip>

DBInterface::DBInterface() {
    initializeSampleData();
    std::cout << std::endl << "In-memory restaurant database initialized with " << restaurants_.size() << " entries." << std::endl;
}

void DBInterface::initializeSampleData() {
    restaurants_ = {
        {{"name", "猪肉饺子馆"}, {"description", "手工制作的猪肉馅饺子，口味多样。"}},
        {{"name", "猪肉荣"}, {"description", "主打猪肉料理，招牌菜是红烧肉和糖醋里脊。"}},
        {{"name", "川味小厨"}, {"description", "正宗四川风味，以麻辣口味为主，特色菜有辣子鸡和麻婆豆腐。"}},
        {{"name", "老北京炸酱面馆"}, {"description", "提供地道的北京炸酱面，还有各种老北京小吃。"}},
        {{"name", "意式风情餐厅"}, {"description", "浪漫的意大利餐厅，提供各种意大利面、披萨和牛排。"}},
        {{"name", "通心粉先生"}, {"description", "各种口味的通心粉是本店特色，也有少量其他西式简餐。"}},
        {{"name", "辣味海鲜"}, {"description", "以各种香辣口味的海鲜为主打，适合喜欢重口味的食客。"}},
        {{"name", "素食主义"}, {"description", "提供各种健康美味的素食菜肴。"}},
        {{"name", "麻辣烫专门店"}, {"description", "自选食材的麻辣烫，可以根据喜好选择辣度。"}},
    };
}

std::vector<std::string> DBInterface::executeQuery(const std::string& query_string) {
    std::vector<std::string> results;
    std::vector<DbRow> filtered_data = restaurants_;
    std::cout << "Filtering in-memory restaurant data based on query: \"" << query_string << "\"" << std::endl;

    std::stringstream ss(query_string);
    std::string keyword;
    std::vector<std::string> keywords;
    while (std::getline(ss, keyword, ',')) {
        size_t first = keyword.find_first_not_of(" ");
        if (std::string::npos == first) {
            keyword = "";
        } else {
            size_t last = keyword.find_last_not_of(" ");
            keyword = keyword.substr(first, (last - first + 1));
        }
        if (!keyword.empty() && keyword.front() == '"') {
            keyword.erase(0, 1);
        }
        if (!keyword.empty() && keyword.back() == '"') {
            keyword.erase(keyword.length() - 1, 1);
        }
        if (!keyword.empty()) {
            keywords.push_back(keyword);
        }
    }

    if (!keywords.empty()) {
        DbTable temp_data;
        for (const auto& restaurant : filtered_data) {
            for (const auto& kw : keywords) {
                bool keyword_found_in_restaurant = false;
                for (const auto& pair : restaurant) {
                    if (pair.second.find(kw) != std::string::npos) {
                        keyword_found_in_restaurant = true;
                        break;
                    }
                }
                if (keyword_found_in_restaurant) {
                    temp_data.push_back(restaurant);
                    break;
                }
            }
        }
        filtered_data = temp_data;
    } else {
        std::cout << "No keywords provided in the query." << std::endl;
    }

    std::vector<std::string> headers = {"name"};

    for (const auto& restaurant : filtered_data) {
        for (const std::string& header : headers) {
            auto it = restaurant.find(header);
            if (it != restaurant.end()) {
                results.push_back(it->second);
            } else {
                results.push_back("N/A");
            }
        }
    }

    std::cout << "Filtering complete. Found " << filtered_data.size() << " matching entries." << std::endl;
    return results;
}