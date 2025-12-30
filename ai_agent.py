#!/usr/bin/env python3
import os
import json
import subprocess
import requests
import sys

# API配置
API_KEY = os.getenv("MIMO_API_KEY", "sk-xxxxx")  # 替换为你的API密钥
API_URL = "https://api.xiaomimimo.com/v1/chat/completions"
MODEL = "mimo-v2-flash"

# 定义工具
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "执行系统命令并返回输出结果",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的命令"
                    }
                },
                "required": ["command"]
            }
        }
    }
]

def execute_command(command: str) -> str:
    """执行系统命令"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout or result.stderr or "命令执行成功"
        return output[:2000]  # 限制输出长度
    except subprocess.TimeoutExpired:
        return "命令执行超时"
    except Exception as e:
        return f"错误: {str(e)}"

def call_api(messages: list) -> dict:
    """调用MiMo API"""
    headers = {
        "api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "max_completion_tokens": 1024,
        "temperature": 0.3,
        "top_p": 0.95,
        "stream": False
    }
    
    response = requests.post(API_URL, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def process_response(response: dict, messages: list):
    """处理API响应，执行tool如果需要"""
    choice = response["choices"][0]
    message = choice["message"]
    
    # 添加模型响应到消息历史
    messages.append({
        "role": "assistant",
        "content": message.get("content", ""),
        "tool_calls": message.get("tool_calls")
    })
    
    # 检查是否有tool调用
    if message.get("tool_calls"):
        tool_results = []
        for tool_call in message["tool_calls"]:
            func_name = tool_call["function"]["name"]
            func_args = json.loads(tool_call["function"]["arguments"])
            
            print(f"\n🔧 调用工具: {func_name}")
            print(f"   参数: {func_args}")
            
            if func_name == "execute_command":
                result = execute_command(func_args["command"])
                print(f"   结果: {result[:100]}...")
                tool_results.append({
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "name": func_name,
                    "content": result
                })
        
        # 添加tool结果到消息
        messages.extend(tool_results)
        
        # 递归调用API以获取最终回复
        response = call_api(messages)
        return process_response(response, messages)
    else:
        # 返回最终回复
        return message.get("content", "")

def main():
    """主循环"""
    print("🤖 AI命令执行Agent启动")
    print("输入 'exit' 退出\n")
    
    messages = [
        {
            "role": "system",
            "content": "你是一个AI助手，可以执行用户要求的系统命令。当用户要求执行命令时，使用execute_command工具来完成任务。"
        }
    ]
    
    while True:
        user_input = input("\n👤 你: ").strip()
        
        if user_input.lower() == "exit":
            print("再见!")
            break
        
        if not user_input:
            continue
        
        # 添加用户消息
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        try:
            response = call_api(messages)
            result = process_response(response, messages)
            print(f"\n🤖 AI: {result}")
        except Exception as e:
            print(f"\n❌ 错误: {str(e)}")
            messages.pop()  # 移除失败的消息

if __name__ == "__main__":
    main()
