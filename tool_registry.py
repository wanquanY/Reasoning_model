from typing import Dict, Callable, Any, Optional
import json
from logger_config import logger

class Tool:
    def __init__(self, name: str, description: str, parameters: Dict, handler: Callable, 
                 output_format: Optional[Dict] = None):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.output_format = output_format or {
            "type": "object",
            "properties": {
                "is_tool_call": {"type": "boolean", "const": True},
                "thought": {"type": "string"},
                "tool_calls": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "const": name},
                            "parameters": parameters
                        },
                        "required": ["name", "parameters"]
                    }
                }
            },
            "required": ["is_tool_call", "thought", "tool_calls"]
        }

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str, description: str, parameters: Dict, handler: Callable) -> None:
        """注册一个新工具"""
        self._tools[name] = Tool(name, description, parameters, handler)
        logger.info(f"工具 '{name}' 已注册")

    def get_tool(self, name: str) -> Tool:
        """获取工具实例"""
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, Dict]:
        """获取所有已注册工具的描述"""
        return {
            name: {
                "description": tool.description,
                "parameters": tool.parameters
            }
            for name, tool in self._tools.items()
        }

    def execute_tool(self, name: str, parameters: Dict) -> Dict:
        """执行工具调用"""
        tool = self.get_tool(name)
        if not tool:
            return {"error": f"未知的工具名称: {name}"}
        
        try:
            return tool.handler(parameters)
        except Exception as e:
            logger.error(f"工具 '{name}' 执行失败: {str(e)}")
            return {"error": f"工具执行失败: {str(e)}"}

    def get_system_prompt_tools_section(self) -> str:
        """生成系统提示词中的工具部分"""
        tools_info = []
        for name, tool in self._tools.items():
            # 生成参数描述
            param_desc = []
            for param_name, param_info in tool.parameters.get("properties", {}).items():
                required = param_name in tool.parameters.get("required", [])
                desc = param_info.get("description", "")
                param_desc.append(f"      - {param_name}: {desc} {'(必填)' if required else '(可选)'}")
            
            # 组合工具描述
            tools_info.append(f"""   - {name}:
     描述: {tool.description}
     参数:
{chr(10).join(param_desc)}""")
        
        return "\n".join(tools_info)

    def get_tool_output_format_section(self) -> str:
        """生成工具输出格式部分的提示词"""
        return """3. 工具调用时的输出格式（仅在需要实时信息时使用）：
   {
     "is_tool_call": true,
     "thought": "思考过程",
     "tool_calls": [
       {
         "name": "工具名称",
         "parameters": {
           // 根据工具定义提供必要的参数
         }
       }
     ]
   }

4. 普通回答时的输出格式：
   直接用自然语言回答，不需要任何特殊格式。

5. 示例：
   用户: "今天北京天气怎么样？"
   回答: {
     "is_tool_call": true,
     "thought": "需要查询实时天气信息",
     "tool_calls": [
       {
         "name": "web_search",
         "parameters": {
           "query": "北京实时天气"
         }
       }
     ]
   }"""

# 创建全局工具注册表实例
registry = ToolRegistry() 