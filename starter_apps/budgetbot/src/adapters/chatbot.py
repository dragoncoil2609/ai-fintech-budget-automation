"""AI Chatbot adapter for personal money coaching."""
import json
import boto3
from typing import Any

CHATBOT_SYSTEM_PROMPT = """You are an AI Money Coach.
Your goal is to help the user understand their spending, provide budget recommendations, and set budget limits.
You will be provided with the user's recent transactions and their current budget limits (caps).

Rules:
1. When asked about spending, calculate the sum from the provided transactions and list the contributing items concisely.
2. When asked for budget recommendations, analyze their spending and suggest realistic limits.
3. If the user asks to set a budget, use the 'set_budget' tool.
4. Be friendly, professional, and concise.
5. IMPORTANT: When mentioning categories, you MUST use the exact Vietnamese names corresponding to the data:
   Food -> "Ăn uống", Transport -> "Di chuyển", Shopping -> "Mua sắm", Utilities -> "Tiện ích", Entertainment -> "Giải trí", Health -> "Sức khỏe", Subscriptions -> "Đăng ký", Income -> "Thu nhập", Transfer -> "Chuyển khoản", Other -> "Khác".
6. Format your response beautifully using Markdown (bolding important numbers, bullet points for lists, etc.).

Transactions context:
{transactions}

Current Budgets context:
{budgets}
"""

class ChatbotAI:
    def __init__(self, region: str, model_id: str):
        self.runtime = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id

    def chat(self, user_id: str, message: str, transactions: list, budgets: dict, userstore: Any) -> str:
        # Format transactions
        txns_str = "\n".join([f"- {t['date']}: {t['description']} ({t['amount']}) [{t['category']}]" for t in transactions])
        if not txns_str:
            txns_str = "No transactions found."
            
        # Format budgets
        budgets_str = "\n".join([f"- {k}: {v}" for k, v in budgets.items()])
        if not budgets_str:
            budgets_str = "No budgets set."

        system_text = CHATBOT_SYSTEM_PROMPT.format(transactions=txns_str, budgets=budgets_str)

        # Define the set_budget tool
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

        messages = [{"role": "user", "content": [{"text": message}]}]

        try:
            # 1. Send initial message
            response = self.runtime.converse(
                modelId=self.model_id,
                system=[{"text": system_text}],
                messages=messages,
                toolConfig=tool_config,
                inferenceConfig={"temperature": 0.3}
            )

            output_message = response["output"]["message"]
            messages.append(output_message)

            # 2. Check if a tool was called
            tool_calls = [c["toolUse"] for c in output_message["content"] if "toolUse" in c]
            
            if tool_calls:
                tool_results = []
                for tool_call in tool_calls:
                    if tool_call["name"] == "set_budget":
                        args = tool_call["input"]
                        category = args["category"]
                        amount = float(args["amount"])
                        
                        # Execute the tool
                        userstore.set_budget(user_id, category, amount)
                        
                        # Return result
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool_call["toolUseId"],
                                "content": [{"json": {"status": "success", "message": f"Budget for {category} set to {amount}"}}]
                            }
                        })
                
                # 3. Send tool results back to LLM for final answer
                messages.append({"role": "user", "content": tool_results})
                final_response = self.runtime.converse(
                    modelId=self.model_id,
                    system=[{"text": system_text}],
                    messages=messages,
                    toolConfig=tool_config,
                    inferenceConfig={"temperature": 0.3}
                )
                return final_response["output"]["message"]["content"][0]["text"]
            else:
                # No tool called, just return the text
                for content in output_message["content"]:
                    if "text" in content:
                        return content["text"]
                return "I couldn't process that."

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Oops! I encountered an error: {e}"
