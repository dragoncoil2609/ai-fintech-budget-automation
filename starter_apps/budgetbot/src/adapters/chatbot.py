"""AI Chatbot adapter for personal money coaching."""
import json
import boto3
from typing import Any

CHATBOT_SYSTEM_PROMPT = """You are an AI Money Coach.
Your goal is to help the user understand their spending, provide budget recommendations, and set budget limits.
You will be provided with the user's recent transactions, their current budget limits (caps), and a pre-calculated summary of their exact total spending per category.

Rules:
1. STRICT DOMAIN GUARDRAILS: You are a financial assistant. If the user asks about topics unrelated to personal finance, budgeting, saving, or their provided transactions (e.g., coding, general knowledge, politics), you MUST politely decline to answer and redirect them back to financial topics.
2. When asked about spending totals for a category, DO NOT calculate it yourself from the transactions list! Instead, look at the "Category Summary context" to get the exact total. Then, list the contributing items concisely from the Transactions list.
3. When asked for budget recommendations, analyze their spending and suggest realistic limits.
4. If the user asks to set a budget, use the 'set_budget' tool.
5. EMPTY DATA HANDLING: If the "Transactions context" says "No transactions found", warmly welcome the user and instruct them to upload their bank statement (CSV or PDF) using the upload area on the screen to get started. Do not apologize, just guide them enthusiastically.
6. Be friendly, professional, and concise.
7. IMPORTANT: When mentioning categories, you MUST use the exact Vietnamese names corresponding to the data:
   Food -> "Ăn uống", Transport -> "Di chuyển", Shopping -> "Mua sắm", Utilities -> "Tiện ích", Entertainment -> "Giải trí", Health -> "Sức khỏe", Subscriptions -> "Đăng ký", Income -> "Thu nhập", Transfer -> "Chuyển khoản", Other -> "Khác".
8. Format your response beautifully using Markdown (bolding important numbers, bullet points for lists, etc.).

Category Summary context (Use this for EXACT math totals!):
{summary}

Transactions context:
{transactions}

Current Budgets context:
{budgets}
"""

class ChatbotAI:
    def __init__(self, region: str, model_id: str):
        self.runtime = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id

    def chat(self, user_id: str, message: str, history: list, transactions: list, budgets: dict, summary: dict, userstore: Any):
        # Format transactions
        txns_str = "\n".join([f"- {t['date']}: {t['description']} ({t['amount']}) [{t['category']}]" for t in transactions])
        if not txns_str:
            txns_str = "No transactions found."
            
        # Format summary
        summary_str = "\n".join([f"- {k}: Total={v['total']} VND (Count={v['count']})" for k, v in summary.items()])
        if not summary_str:
            summary_str = "No summary data found."

        # Format budgets
        budgets_str = "\n".join([f"- {k}: {v}" for k, v in budgets.items()])
        if not budgets_str:
            budgets_str = "No budgets set."

        system_text = CHATBOT_SYSTEM_PROMPT.format(transactions=txns_str, budgets=budgets_str, summary=summary_str)

        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "set_budget",
                        "description": "Set a monthly budget cap for a specific category.",
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": {
                                    "category": {"type": "string", "description": "The spending category (e.g., Food, Shopping, Transport)"},
                                    "amount": {"type": "number", "description": "The budget limit amount"}
                                },
                                "required": ["category", "amount"]
                            }
                        }
                    }
                }
            ]
        }

        messages = []
        for msg in history:
            role = msg.get("role")
            text = msg.get("text", "")
            if role in ["user", "assistant"]:
                if messages and messages[-1]["role"] == role:
                    messages[-1]["content"][0]["text"] += "\n\n" + text
                else:
                    messages.append({"role": role, "content": [{"text": text}]})

        while messages and messages[0]["role"] != "user":
            messages.pop(0)

        if messages and messages[-1]["role"] == "user":
            messages[-1]["content"][0]["text"] += "\n\n" + message
        else:
            messages.append({"role": "user", "content": [{"text": message}]})

        def stream_generator():
            try:
                response = self.runtime.converse_stream(
                    modelId=self.model_id,
                    system=[{"text": system_text}],
                    messages=messages,
                    toolConfig=tool_config,
                    inferenceConfig={"temperature": 0.3}
                )

                tool_use_id = None
                tool_name = None
                tool_input_str = ""
                is_tool_call = False

                for event in response.get('stream', []):
                    if 'contentBlockStart' in event:
                        start = event['contentBlockStart'].get('start', {})
                        if 'toolUse' in start:
                            is_tool_call = True
                            tool = start['toolUse']
                            tool_use_id = tool['toolUseId']
                            tool_name = tool['name']
                            
                    elif 'contentBlockDelta' in event:
                        delta = event['contentBlockDelta'].get('delta', {})
                        if 'text' in delta:
                            yield delta['text']
                        elif 'toolUse' in delta:
                            tool_input_str += delta['toolUse']['input']

                if is_tool_call:
                    # Execute tool
                    tool_input = json.loads(tool_input_str)
                    if tool_name == "set_budget":
                        category = tool_input.get("category")
                        amount = float(tool_input.get("amount", 0))
                        userstore.set_budget(user_id, category, amount)
                        
                        tool_result = {
                            "toolResult": {
                                "toolUseId": tool_use_id,
                                "content": [{"json": {"status": "success", "message": f"Budget for {category} set to {amount}"}}]
                            }
                        }
                        
                        messages.append({
                            "role": "assistant",
                            "content": [{
                                "toolUse": {
                                    "toolUseId": tool_use_id,
                                    "name": tool_name,
                                    "input": tool_input
                                }
                            }]
                        })
                        messages.append({"role": "user", "content": [tool_result]})
                        
                        # Second call to get final answer
                        second_response = self.runtime.converse_stream(
                            modelId=self.model_id,
                            system=[{"text": system_text}],
                            messages=messages,
                            toolConfig=tool_config,
                            inferenceConfig={"temperature": 0.3}
                        )
                        for event in second_response.get('stream', []):
                            if 'contentBlockDelta' in event:
                                delta = event['contentBlockDelta'].get('delta', {})
                                if 'text' in delta:
                                    yield delta['text']

            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"\n\n[Error: {str(e)}]"

        return stream_generator()
