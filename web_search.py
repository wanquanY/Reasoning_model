import json
import http.client
from logger_config import logger
from tool_registry import registry

def web_search_handler(parameters: dict) -> dict:
    """Web搜索工具的处理函数"""
    query = parameters.get("query")
    if not query:
        error_msg = "缺少搜索查询词 (query) 参数"
        logger.error(error_msg)
        return {"error": error_msg}

    logger.debug(f"执行网络搜索，查询词: {query}")
    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({
        "q": query,
        "gl": "cn",
        "hl": "zh-cn",
        "num": 20
    })
    headers = {
        'X-API-KEY': '<google serper dev的API_KEY>',#替换成自己的key
        'Content-Type': 'application/json'
    }

    try:
        logger.debug("发送API请求到google.serper.dev")
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        data = res.read()
        search_results = data.decode("utf-8")

        try:
            logger.debug("解析搜索结果JSON")
            search_results_json = json.loads(search_results)
            organic_results = search_results_json.get("organic", [])
            extracted_results = []
            for result in organic_results:
                extracted_results.append({
                    "title": result.get("title"),
                    "link": result.get("link"),
                    "snippet": result.get("snippet")
                })

            logger.info(f"搜索成功完成，获取到 {len(extracted_results)} 条结果")
            return {"search_results": extracted_results}

        except json.JSONDecodeError as e:
            error_msg = f"搜索API返回结果JSON解析失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "raw_result": search_results}

    except Exception as e:
        error_msg = f"调用搜索API失败: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

# 注册web_search工具
registry.register(
    name="web_search",
    description="搜索互联网获取实时信息，适用于查询新闻、天气、股票等实时数据",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询词"
            }
        },
        "required": ["query"]
    },
    handler=web_search_handler
)