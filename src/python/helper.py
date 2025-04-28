import json
import math
import os
import sys
import datetime
import numbers
from typing import List, Dict, Any, Tuple, Set, Optional
import config

DEFAULT_USER_PROFILE = {
    "sweetness": 0.5,
    "spiciness": 0.5,
    "price": 0.5,
    "distance": 0.5,
    "rating": 0.5
}

def load_json_data(filepath: str) -> Any:
    """
    从 JSON 文件读取数据。文件保证存在。
    如果读取的是 user_profile.json 且内容无效，则设置默认画像并覆盖文件。
    其他文件的读取逻辑不变。
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        sys.stderr.write(f"\nError: Decoding JSON from {filepath} failed. ")
        if filepath.endswith('user_profile.json'):
            sys.stderr.write("Overwriting with default user profile.\n")
            default_profile = DEFAULT_USER_PROFILE.copy()
            save_json_data(default_profile, filepath)
            return default_profile
        sys.stderr.write("Returning None.\n")
        return None
    except Exception as e:
        sys.stderr.write(f"An error occurred while reading {filepath}: {e}. ")
        if filepath.endswith('user_profile.json'):
            sys.stderr.write("Overwriting with default user profile.\n")
            default_profile = DEFAULT_USER_PROFILE.copy()
            save_json_data(default_profile, filepath)
            return default_profile
        sys.stderr.write("Returning None.\n")
        return None
    
def save_json_data(data: Any, filepath: str):
    """将数据保存到 JSON 文件"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4) # 使用indent=4格式化输出
    except Exception as e:
        sys.stderr.write(f"Error occurred while saving data to {filepath}: {e}\n")

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算两个向量之间的余弦相似度

    Args:
        vec1: 第一个向量 (List[float])
        vec2: 第二个向量 (List[float])

    Returns:
        余弦相似度得分 (float)，范围在 -1.0 到 1.0 之间。
        如果任一向量为零向量，返回 0.0。
    """
    if len(vec1) != len(vec2):
        print("Warning: Vector dimensions mismatch.")
        return 0.0

    dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
    magnitude_vec1 = math.sqrt(sum(v1 * v1 for v1 in vec1))
    magnitude_vec2 = math.sqrt(sum(v2 * v2 for v2 in vec2))

    if magnitude_vec1 == 0 or magnitude_vec2 == 0:
        return 0.0
    else:
        similarity = dot_product / (magnitude_vec1 * magnitude_vec2)
        return max(-1.0, min(1.0, similarity))
    
DECAY_LAMBDA = 0.05

def calculate_decay_weight(order_date_str: str) -> float:
    """
    计算订单日期的指数衰减权重。
    权重 = exp(-lambda * 距离今天的天数)
    """
    try:
        order_date = datetime.date.fromisoformat(order_date_str)
        today = datetime.date.today()
        days_ago = (today - order_date).days
        days_ago = max(0, days_ago)
        weight = math.exp(-DECAY_LAMBDA * days_ago)
        return weight
    except ValueError:
        sys.stderr.write(f"Warning: Invalid date format in history: {order_date_str}. Returning weight 0.\n")
        return 0.0
    except Exception as e:
        sys.stderr.write(f"Error calculating decay weight for {order_date_str}: {e}.\n")
        return 0.0
    
def perform_ranking(restaurant_names_to_rank: List[str], all_restaurants: List[Dict[str, Any]], user_preference: Dict[str, float]) -> List[Tuple[float, Dict[str, Any]]]:
    """
    根据用户画像，计算传入名字列表的餐厅与用户偏好的余弦相似度，并对这些餐厅进行排序。
    ... (函数内容不变) ...
    """
    if not all(key in user_preference for key in ["sweetness", "spiciness", "price", "distance", "rating"]):
        sys.stderr.write("Error: User profile data is invalid (missing keys).\n")
        return []

    preference_vector = [
        user_preference.get("sweetness", 0.5),
        user_preference.get("spiciness", 0.5),
        user_preference.get("price", 0.5),
        user_preference.get("distance", 0.5),
        user_preference.get("rating", 0.5)
    ]

    ranked_restaurants = []
    names_to_rank_set: Set[str] = set(restaurant_names_to_rank)

    for restaurant in all_restaurants:
        restaurant_name = restaurant.get("name")
        if restaurant_name and restaurant_name in names_to_rank_set:
            attributes = restaurant.get("attributes")
            if attributes:
                restaurant_vector = [
                    attributes.get("sweetness", 0.0),
                    attributes.get("spiciness", 0.0),
                    attributes.get("price", 0.0),
                    attributes.get("distance", 0.0),
                    attributes.get("rating", 0.0)
                ]
                similarity = cosine_similarity(preference_vector, restaurant_vector)
                ranked_restaurants.append((similarity, restaurant))
            else:
                sys.stderr.write(f"Warning: Restaurant '{restaurant_name}' has no 'attributes'. Giving default score 0.\n")
                ranked_restaurants.append((0.0, restaurant))

    ranked_restaurants.sort(key=lambda x: x[0], reverse=True)

    return ranked_restaurants

def update_user_profile_from_history(all_restaurants: List[Dict[str, Any]]):
    """
    从历史记录文件中读取所有记录，根据指数衰减计算权重，重新生成用户画像 (5个属性维度)。
    并保存更新后的用户画像文件。
    """
    history_records = load_json_data(config.HISTORY_FILE)
    # load_json_data 已经处理了文件不存在或格式错误的情况，返回 []

    # 找到所有餐厅数据，方便通过名字查找属性
    restaurant_lookup: Dict[str, Dict[str, Any]] = {r.get("name"): r for r in all_restaurants if r.get("name")}

    # 初始化用于累积加权属性总和和总权重的字典
    attribute_weighted_sums: Dict[str, float] = {key: 0.0 for key in DEFAULT_USER_PROFILE.keys()}
    total_weight_sum = 0.0

    # 遍历历史记录，计算加权属性总和和总权重
    for record in history_records:
        restaurant_name = record.get("restaurant_name")
        order_date_str = record.get("order_date")

        if not restaurant_name or not order_date_str:
            sys.stderr.write(f"Warning: Skipping invalid history record: {record}\n")
            continue

        weight = calculate_decay_weight(order_date_str)
        if weight <= 0:
             continue # 权重为0或负数（未来日期）则忽略

        # 查找订单对应的餐厅数据
        restaurant_data = restaurant_lookup.get(restaurant_name)

        if restaurant_data:
            attributes = restaurant_data.get("attributes", {})
            # 检查attributes是否是字典且包含所有必要键
            if isinstance(attributes, dict) and all(key in attributes for key in DEFAULT_USER_PROFILE.keys()):
                # 累积加权属性总和和总权重
                total_weight_sum += weight
                for attr_key in DEFAULT_USER_PROFILE.keys():
                    attr_value = attributes.get(attr_key, 0.0) # 获取餐厅该属性值
                    attribute_weighted_sums[attr_key] += attr_value * weight
            else:
                 sys.stderr.write(f"Warning: Restaurant '{restaurant_name}' data has invalid or missing attributes for profile update. Skipping.\n")

        else:
            sys.stderr.write(f"Warning: Restaurant '{restaurant_name}' from history not found in restaurant data. Skipping.\n")


    # 根据累积结果生成新的用户画像 (计算加权平均)
    new_user_profile: Dict[str, float] = {}
    if total_weight_sum > 0:
        # 如果有有效的历史记录，计算加权平均值作为新的画像得分
        for attr_key in DEFAULT_USER_PROFILE.keys():
            new_user_profile[attr_key] = attribute_weighted_sums[attr_key] / total_weight_sum
    else:
        # 如果没有有效的历史记录，使用默认画像
        sys.stderr.write("No valid history records with attributes found. Using default user profile.\n")
        new_user_profile = DEFAULT_USER_PROFILE.copy() # 使用copy避免修改默认字典


    # 保存重新计算后的用户画像
    save_json_data(new_user_profile, config.USER_PROFILE_FILE)
    print(f"User profile recalculated and saved to {config.USER_PROFILE_FILE}", file=sys.stderr)