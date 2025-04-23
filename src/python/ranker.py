import json
import math
import os
import sys
import datetime
import numbers
from typing import List, Dict, Any, Tuple, Set, Optional

DATA_DIR = "/home/sy/agent/data"
RESTAURANTS_FILE = os.path.join(DATA_DIR, "restaurants_info.json")
USER_PROFILE_FILE = os.path.join(DATA_DIR, "user_profile.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

def load_json_data(filepath: str) -> Any:
    """从 JSON 文件读取数据"""
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}. Please make sure '{DATA_DIR}' directory and '{os.path.basename(filepath)}' exist.")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}. Please check the file format.")
        return None
    except Exception as e:
        print(f"An error occurred while reading {filepath}: {e}")
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
        # 理论上这里不应该发生，因为向量维度固定为5
        # 但作为健壮性检查，可以加上
        print("Warning: Vector dimensions mismatch.")
        return 0.0

    dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
    magnitude_vec1 = math.sqrt(sum(v1 * v1 for v1 in vec1))
    magnitude_vec2 = math.sqrt(sum(v2 * v2 for v2 in vec2))

    # 避免除以零的情况
    if magnitude_vec1 == 0 or magnitude_vec2 == 0:
        return 0.0
    else:
        # 加上一个极小值避免浮点数误差导致稍大于 1 或小于 -1
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

def _perform_ranking(restaurant_names_to_rank: List[str], all_restaurants: List[Dict[str, Any]], user_preference: Dict[str, float]) -> List[Tuple[float, Dict[str, Any]]]:
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
     # print(f"Loaded user preference vector: {preference_vector}", file=sys.stderr) # 打印到stderr

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

DEFAULT_USER_PROFILE = {
    "sweetness": 0.5,
    "spiciness": 0.5,
    "price": 0.5,
    "distance": 0.5,
    "rating": 0.5
}

def update_user_profile_from_history(all_restaurants: List[Dict[str, Any]]):
    """
    从历史记录文件中读取所有记录，根据指数衰减计算权重，重新生成用户画像 (5个属性维度)。
    并保存更新后的用户画像文件。
    """
    history_records = load_json_data(HISTORY_FILE)
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
             # sys.stderr.write(f"Info: Skipping history record from {order_date_str} due to zero or negative weight.\n") # 避免过多打印
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
    save_json_data(new_user_profile, USER_PROFILE_FILE)
    print(f"\nUser profile recalculated and saved to {USER_PROFILE_FILE}", file=sys.stderr)

if __name__ == "__main__":
    # 这个脚本期望接收一个命令行参数：包含餐厅名字列表的字符串 (逗号分隔)
    # 我们假设C++传递的是逗号分隔字符串
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python your_ranking_script.py <comma_separated_names_string>\n")
        sys.exit(1)

    # 获取命令行参数中的逗号分隔字符串
    comma_separated_names_string = sys.argv[1]

    # 1. 加载所有餐厅数据 (脚本启动时加载一次)
    all_restaurants_data = load_json_data(RESTAURANTS_FILE)
    if all_restaurants_data is None or not isinstance(all_restaurants_data, list):
        sys.stderr.write("Failed to load valid restaurant data. Exiting.\n")
        sys.exit(1)

    # 2. 加载唯一的用户画像数据 (脚本启动时加载一次)
    # load_json_data 已经处理了文件不存在或格式不正确的情况，返回 DEFAULT_USER_PROFILE
    user_profile_data = load_json_data(USER_PROFILE_FILE)
    # user_profile_data 保证是一个字典且包含5个key，不需要额外检查 None 或类型

    # 3. 分割字符串为Python列表
    restaurant_names_to_rank: List[str] = []
    if comma_separated_names_string: # 避免分割空字符串得到 ['']
         restaurant_names_to_rank = comma_separated_names_string.split(',')

    # 4. 执行排序逻辑
    # ranked_results 是一个 (相似度得分, 餐厅字典) 元组的列表
    ranked_results = _perform_ranking(restaurant_names_to_rank, all_restaurants_data, user_profile_data)

    # 5. 打印排序结果并进行交互式选择
    selected_restaurant_data: Optional[Dict[str, Any]] = None # 使用Optional类型提示
    if ranked_results:
        print("\n--- Ranked Restaurants ---")
        for i, (score, restaurant) in enumerate(ranked_results):
            # 显示序号、餐厅名字和相似度得分
            print(f"{i+1}. {restaurant.get('name', 'Unknown')} (Similarity: {score:.4f})")

        # 交互式选择
        while selected_restaurant_data is None:
            try:
                choice_str = input(f"Please select a restaurant by number (1-{len(ranked_results)}), or type 'q' to quit: ")
                if choice_str.lower() == 'q':
                     print("Order cancelled.")
                     sys.exit(0) # 用户选择退出

                choice = int(choice_str)
                if 1 <= choice <= len(ranked_results):
                    # 获取用户选择的餐厅数据 (字典)
                    # 序号是1-based，列表索引是0-based
                    selected_restaurant_data = ranked_results[choice - 1][1]
                    print(f"\nYou selected: {selected_restaurant_data.get('name', 'Unknown')}")
                else:
                    print("Invalid number. Please enter a number within the range.")
            except ValueError:
                print("Invalid input. Please enter a number or 'q'.")
            except Exception as e:
                print(f"An unexpected error occurred during selection: {e}")
                sys.exit(1) # 选择过程中发生未知错误

        # 6. 将点单记录写入历史文件
        order_date = datetime.date.today().isoformat()

        history_record = {
            "restaurant_name": selected_restaurant_data.get("name", "Unknown"),
            "order_date": order_date,
        }

        # 加载现有历史记录，添加新记录，然后保存
        current_history = load_json_data(HISTORY_FILE)
        # load_json_data 在文件不存在或格式错误时会返回 []，不需要额外检查
        current_history.append(history_record)
        save_json_data(current_history, HISTORY_FILE)

        print("\nOrder placed successfully!")
        print(f"Your order for {selected_restaurant_data.get('name', 'Unknown')} has been recorded in history.")

        # 7. 读取history文件，根据记录重新计算并生成用户画像
        print("\nRecalculating user profile based on order history...")
        # update_user_profile_from_history 现在只更新5个属性维度
        update_user_profile_from_history(all_restaurants_data)


        # 8. 打印更新后的用户画像并结束程序
        print("\n--- Updated User Profile ---", file=sys.stderr) # 打印到标准错误，与标准输出的排序结果区分
        # 重新加载以确认保存成功，load_json_data 保证返回有效画像或默认画像
        updated_profile = load_json_data(USER_PROFILE_FILE)
        # 使用json.dump打印到stderr，以便格式化显示
        json.dump(updated_profile, sys.stderr, ensure_ascii=False, indent=4)
        sys.stderr.write('\n')

        print("\nProgram finished.")
        sys.exit(0) # 程序正常结束

    else:
        # 如果没有排序结果
        print("\nNo restaurants found matching your criteria.")
        # 尽管没有点餐，仍然可以根据历史记录更新画像（基于可能存在的历史记录）
        print("\nAttempting to update user profile from existing history...")
        update_user_profile_from_history(all_restaurants_data)
        print("\nProgram finished.")
        sys.exit(0)