if __name__ == "__main__":
    # 这个脚本期望接收一个命令行参数：包含餐厅名字列表的字符串 (逗号分隔)
    # 我们假设C++传递的是逗号分隔字符串
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python your_ranking_script.py <comma_separated_names_string>\n")
        sys.exit(1)

    # 获取命令行参数中的逗号分隔字符串
    comma_separated_names_string = sys.argv[1]

    # 1. 加载所有餐厅数据 (脚本启动时加载一次)
    all_restaurants_data = helper.load_json_data(RESTAURANTS_FILE)
    if all_restaurants_data is None or not isinstance(all_restaurants_data, list):
        sys.stderr.write("Failed to load valid restaurant data. Exiting.\n")
        sys.exit(1)

    # 2. 加载唯一的用户画像数据 (脚本启动时加载一次)
    # load_json_data 已经处理了文件不存在或格式不正确的情况，返回 DEFAULT_USER_PROFILE
    user_profile_data = helper.load_json_data(USER_PROFILE_FILE)
    # user_profile_data 保证是一个字典且包含5个key，不需要额外检查 None 或类型

    # 3. 分割字符串为Python列表
    restaurant_names_to_rank: List[str] = []
    if comma_separated_names_string: # 避免分割空字符串得到 ['']
         restaurant_names_to_rank = comma_separated_names_string.split(',')

    # 4. 执行排序逻辑
    # ranked_results 是一个 (相似度得分, 餐厅字典) 元组的列表
    ranked_results = helper.perform_ranking(restaurant_names_to_rank, all_restaurants_data, user_profile_data)

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
        current_history = helper.load_json_data(HISTORY_FILE)
        current_history.append(history_record)
        helper.save_json_data(current_history, HISTORY_FILE)

        print("\nOrder placed successfully!")
        print(f"Your order for {selected_restaurant_data.get('name', 'Unknown')} has been recorded in history.")

        # 7. 读取history文件，根据记录重新计算并生成用户画像
        print("Recalculating user profile based on order history...")
        update_user_profile_from_history(all_restaurants_data)

        sys.exit(0) # 程序正常结束

    else:
        # 如果没有排序结果
        print("\nNo restaurants found matching your criteria.")
        # 尽管没有点餐，仍然可以根据历史记录更新画像（基于可能存在的历史记录）
        print("\nAttempting to update user profile from existing history...")
        update_user_profile_from_history(all_restaurants_data)
        print("\nProgram finished.")
        sys.exit(0)