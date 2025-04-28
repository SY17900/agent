from mcp.server import FastMCP
import helper
import config

app = FastMCP('order_helper')

@app.tool()
async def db_search(query: str) -> str:
    """
    通过餐厅的名字，查找餐厅的介绍信息

    Args:
        query: 餐厅的名字

    Returns:
        一段中文句子，餐厅的介绍信息
    """
    all_restaurants_data = helper.load_json_data(config.RESTAURANTS_FILE)
    if all_restaurants_data is None or not isinstance(all_restaurants_data, list):
        return ""
    for record in all_restaurants_data:
        if record["name"] == query:
            return record["description"]
        
@app.tool()
async def similarity_calc(restaurant_name: str) -> str:
    """
    我们通过向量来标记一家餐厅的属性，它表示这家餐厅在这几个方面的得分比如：
    "attributes": {
        "sweetness": 0.1,
        "spiciness": 0.1,
        "price": 0.4,
        "distance": 0.3,
        "rating": 0.7
    }
    同时，我们也为用户记录了同样的属性，表示用户在这些方面的偏好
    我们设计了一个计算余弦相似度的算法来衡量一家餐厅与用户的匹配程度，算法如下：
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        dot_product = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
        magnitude_vec1 = math.sqrt(sum(v1 * v1 for v1 in vec1))
        magnitude_vec2 = math.sqrt(sum(v2 * v2 for v2 in vec2))

        if magnitude_vec1 == 0 or magnitude_vec2 == 0:
            return 0.0
        else:
            similarity = dot_product / (magnitude_vec1 * magnitude_vec2)
            return max(-1.0, min(1.0, similarity))
    
    这个函数通过餐厅的名字，计算出这家餐厅与用户在这五个维度上的余弦相似度
    这可以作为“这家餐厅在哪些方面和用户的偏好比较符合”的参考

    Args:
        restaurant_name: 餐厅的名字

    Returns:
        一个字符串，记录了每一个维度的相似度
    """
    all_restaurants_data = helper.load_json_data(config.RESTAURANTS_FILE)
    user_profile_data = helper.load_json_data(config.USER_PROFILE_FILE)
    for restaurant in all_restaurants_data:
        if restaurant["name"] == restaurant_name:
            similarities = {}
            for attr in ["sweetness", "spiciness", "price", "distance", "rating"]:
                vec1 = [restaurant["attributes"][attr]]
                vec2 = [user_profile_data[attr]]
                sim = helper.cosine_similarity(vec1, vec2)
                similarities[attr] = sim
            sorted_similarities = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            return sorted_similarities
    return None
        
if __name__ == "__main__":
    app.run(transport='stdio')