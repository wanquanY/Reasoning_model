from openai import OpenAI
import os
import json
import re
from datetime import datetime
from logger_config import logger
from tool_registry import registry
import web_search  # 导入web_search模块以触发工具注册

logger.info("初始化OpenAI客户端")
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

def get_system_prompt():
    current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    available_tools = registry.get_system_prompt_tools_section()
    output_format = registry.get_tool_output_format_section()
    
    return f"""你是一个专门负责工具调用的AI助手。当前时间是：{current_time}

你必须严格遵循以下规则：

1. 判断规则：
   - 对于需要实时信息的问题（如天气、新闻、股票等），必须使用工具调用
   - 对于普通问题（如打招呼、解释概念等），直接用自然语言回答

2. 可用工具：
{available_tools}

{output_format}"""

class ConversationManager:
    def __init__(self):
        self.system_memory = {
            "tool_calling": {"role": "system", "content": get_system_prompt()},
            "response_generation": {"role": "system", "content": "你是一个助手，请基于搜索结果生成简洁的回答，使用自然语言。"}
        }
        self.conversation_history = []
        self.working_memory = {}
    
    def get_tool_calling_messages(self):
        return [self.system_memory["tool_calling"]] + self.conversation_history[-5:]
    
    def get_response_messages(self, tool_result):
        return [
            self.system_memory["response_generation"],
            {"role": "user", "content": f"基于搜索结果生成回答。搜索结果：{json.dumps(tool_result, ensure_ascii=False)}"}
        ]
    
    def add_message(self, role, content):
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > 10:
            self.conversation_history.pop(0)

# 初始化对话管理器
conversation_manager = ConversationManager()

def process_stream_response(response):
    """处理流式响应"""
    reasoning_content = ""
    content = ""
    
    for chunk in response:
        logger.debug(f"接收到chunk数据: {chunk}")
        if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
            reasoning_content += chunk.choices[0].delta.reasoning_content
            logger.debug(f"推理内容更新: {chunk.choices[0].delta.reasoning_content}")
        else:
            content_chunk = chunk.choices[0].delta.content or ""
            content += content_chunk
            logger.debug(f"生成内容更新: {content_chunk}")
    
    return reasoning_content.strip(), content.strip()

# 主程序入口
if __name__ == "__main__":
    logger.info("=== 开始运行主程序 ===")
    
    # 初始化对话
    conversation_manager.add_message("user", "帮我整理最近的新闻资讯，我更关注AI相关的")
    
    # 更新系统提示词以获取最新时间
    conversation_manager.system_memory["tool_calling"]["content"] = get_system_prompt()
    
    logger.info("准备发送API请求")
    response = client.chat.completions.create(
        model="ep-20250209134650-d8pgv",
        messages=conversation_manager.get_tool_calling_messages(),
        stream=True,
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    logger.info("开始接收流式响应")
    print("-" * 50)

    reasoning_content, content = process_stream_response(response)

    print("\n" + "-" * 50)
    logger.info("流式响应接收完成，开始处理最终结果...")
    logger.info(f"完整的推理内容: {reasoning_content}")
    logger.info(f"完整的生成内容: {content}")

    if content:
        try:
            logger.debug("开始处理响应内容")
            processed_content = content.strip()
            processed_content = re.sub(r'[\u0000-\u001F\u0080-\u009F]', '', processed_content)

            try:
                response_json = json.loads(processed_content)
                logger.debug(f"解析到的JSON结构: {json.dumps(response_json, ensure_ascii=False)}")

                if response_json.get("is_tool_call"):
                    if "thought" not in response_json:
                        logger.error("响应缺少必需的'thought'字段")
                        raise ValueError("Invalid response format: missing 'thought' field")

                    if "tool_calls" not in response_json:
                        logger.error("响应缺少必需的'tool_calls'字段")
                        raise ValueError("Invalid response format: missing 'tool_calls' field")

                    logger.info(f"模型思考过程: {response_json['thought']}")

                    for tool_call in response_json["tool_calls"]:
                        if "name" not in tool_call or "parameters" not in tool_call:
                            logger.error("工具调用格式错误")
                            continue

                        logger.info(f"执行工具调用: {tool_call['name']}")
                        tool_result = registry.execute_tool(tool_call["name"], tool_call["parameters"])
                        
                        if tool_result and not tool_result.get("error"):
                            conversation_manager.add_message("user", f"基于搜索结果生成回答。搜索结果：{json.dumps(tool_result, ensure_ascii=False)}")

                            logger.info("发送最终请求生成答案")
                            final_response = client.chat.completions.create(
                                model="ep-20250209134650-d8pgv",
                                messages=conversation_manager.get_response_messages(tool_result),
                                stream=True,
                                temperature=0.1
                            )
                            
                            final_reasoning, final_answer = process_stream_response(final_response)
                            if final_reasoning:
                                logger.info(f"生成答案的推理过程: {final_reasoning}")
                            logger.debug("获取到最终答案")
                            print("\n最终答案:")
                            print(final_answer)
                        else:
                            logger.error(f"工具调用失败: {tool_result.get('error', '未知错误')}")
                else:
                    logger.info("模型返回自然语言回答")
                    print("\n回答:")
                    print(processed_content)

            except json.JSONDecodeError:
                logger.info("模型返回自然语言回答")
                print("\n回答:")
                print(processed_content)

        except Exception as e:
            logger.error(f"处理响应时发生错误: {str(e)}")

    logger.info("=== 程序运行结束 ===")