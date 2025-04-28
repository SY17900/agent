import json
import asyncio
import os
import datetime
from typing import List, Dict, Any, Tuple, Set, Optional
from contextlib import AsyncExitStack

from openai import OpenAI
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import helper
import config

load_dotenv("/home/sy/agent/data/.env")

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.client = OpenAI()

    async def connect_to_server(self):
        server_params = StdioServerParameters(
            command='uv',
            args=['run', '/home/sy/agent/src/python/order_helper.py'],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params))
        stdio, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write))

        await self.session.initialize()

    async def process_query(self, query: str) -> str:
        system_prompt = (
            "你是一个非常智能的外卖点单助手，你善于使用精妙但是简洁的语言响应用户的请求"
            "你可以并且仅可以调用两种外部函数：db_search和similarity_calc来辅助自己的工作"
            "在所有你认为有必要的时候，都建议你先调用合适的函数，再根据函数的返回结果进行工作"
            "我们已经根据用户的需求为他筛选出了一条他最有可能感兴趣的餐厅，你可以通过db_search函数得到这家餐厅的信息，\
                还可以通过similarity_calc函数得到这家餐厅是在哪些维度上与用户的偏好相匹配"
            "接下来你将得到这家餐厅的名称，然后你将根据上面两个函数的调用结果，为用户生成一则推荐词\
                需要介绍这家餐厅的信息，并且向用户说明为什么这可能是他最感兴趣的餐厅"
            "建议你调用两次函数，然后根据两次结果综合生成你的答案。"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # 获取mcp服务器工具列表
        response = await self.session.list_tools()
        # 生成function call的描述信息
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            }
        } for tool in response.tools]

        # print(available_tools)

        # 请求 deepseek，function call 的描述信息通过 tools 参数传入
        response = self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL"),
            messages=messages,
            tools=available_tools
        )

        # print(response.choices[0])

        # 处理返回的内容
        while True:
            content = response.choices[0]
            if content.finish_reason == "tool_calls":
                tool_call0 = content.message.tool_calls[0]
                tool_name0 = tool_call0.function.name
                tool_args0 = json.loads(tool_call0.function.arguments)

                tool_call1 = content.message.tool_calls[1]
                tool_name1 = tool_call1.function.name
                tool_args1 = json.loads(tool_call1.function.arguments)

                # 执行工具
                result0 = await self.session.call_tool(tool_name0, tool_args0)
                print(f"\n\n[Calling tool {tool_name0} with args {tool_args0}]\nresult = {result0}\n\n")

                result1 = await self.session.call_tool(tool_name1, tool_args1)
                print(f"\n\n[Calling tool {tool_name1} with args {tool_args1}]\nresult = {result1}\n\n")

                # 将deepseek返回的调用哪个工具数据和工具执行完成后的数据都存入messages中
                messages.append(content.message.model_dump())
                messages.append({
                    "role": "tool",
                    "content": result0.content[0].text,
                    "tool_call_id": tool_call0.id,
                })
                messages.append({
                    "role": "tool",
                    "content": result1.content[0].text,
                    "tool_call_id": tool_call1.id,
                })

                # 将上面的结果再返回给deepseek用于生产最终的结果
                response = self.client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL"),
                    messages=messages,
                )
            else:
                return response.choices[0].message.content

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
    
# --- Synchronous main function ---
def main():
    """Synchronous main function to run the client for a single query."""
    client = MCPClient()

    import sys
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python your_ranking_script.py <comma_separated_names_string>\n")
        sys.exit(1)
    comma_separated_names_string = sys.argv[1]

    all_restaurants_data = helper.load_json_data(config.RESTAURANTS_FILE)
    if all_restaurants_data is None or not isinstance(all_restaurants_data, list):
        sys.stderr.write("Failed to load valid restaurant data. Exiting.\n")
        sys.exit(1)

    user_profile_data = helper.load_json_data(config.USER_PROFILE_FILE)

    restaurant_names_to_rank: List[str] = []
    if comma_separated_names_string:
        restaurant_names_to_rank = comma_separated_names_string.split(',')

    ranked_results = helper.perform_ranking(restaurant_names_to_rank, all_restaurants_data, user_profile_data)

    # Define an async function to run the core async logic
    async def run_single_query() -> str:
        try:
            # Connect to the server
            await client.connect_to_server()
            query = ranked_results[0][1].get("name")
            return await client.process_query(query)

        except Exception as e:
            import traceback
            print("\nAn unexpected error occurred:")
            traceback.print_exc()
        finally:
            # Ensure cleanup happens
            await client.cleanup()

    # Run the async function using asyncio.run()
    try:
        response = asyncio.run(run_single_query())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")

    selected_restaurant_data: Optional[Dict[str, Any]] = None # 使用Optional类型提示
    
    if ranked_results:
        print("\n--- Ranked Restaurants ---")
        for i, (score, restaurant) in enumerate(ranked_results):
            # 显示序号、餐厅名字和相似度得分
            print(f"{i+1}. {restaurant.get('name', 'Unknown')} (Similarity: {score:.4f})")

        print(response)

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
        current_history = helper.load_json_data(config.HISTORY_FILE)
        current_history.append(history_record)
        helper.save_json_data(current_history, config.HISTORY_FILE)

        print("\nOrder placed successfully!")
        print(f"Your order for {selected_restaurant_data.get('name', 'Unknown')} has been recorded in history.")

        # 7. 读取history文件，根据记录重新计算并生成用户画像
        print("Recalculating user profile based on order history...")
        helper.update_user_profile_from_history(all_restaurants_data)

        sys.exit(0) # 程序正常结束

    else:
        # 如果没有排序结果
        print("\nNo restaurants found matching your criteria.")
        # 尽管没有点餐，仍然可以根据历史记录更新画像（基于可能存在的历史记录）
        print("\nAttempting to update user profile from existing history...")
        helper.update_user_profile_from_history(all_restaurants_data)
        print("\nProgram finished.")
        sys.exit(0)

if __name__ == "__main__":
    main()