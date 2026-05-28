"""AI adapters. BudgetBot uses direct InvokeModel — no KB / no RAG.

Interface:
    categorize(description, amount, date) -> {"category": str, "confidence": "high|medium|low"}
"""
import json
import re
from typing import Any


CATEGORIES = [
    "Food", "Transport", "Shopping", "Utilities", "Entertainment",
    "Health", "Subscriptions", "Income", "Transfer", "Other",
]


CATEGORIZE_PROMPT = """You are an AI Money Coach. Categorize the following bank transaction into exactly one category.
Categories: {categories}

Rules:
1. If the description is a cryptic opaque code (e.g., "FT0024112501 ID:0001") with no obvious meaning, set category to "Other" and confidence to "low".
2. If it is ambiguous (e.g., "VINMART HCM 04" could be Food or Shopping), pick the most likely one and set confidence to "medium".
3. If it is clear (e.g., "NETFLIX"), set category and set confidence to "high".
4. If amount is positive and it's not a refund, it might be "Income".
5. If the description contains "REFUND", "Hoàn tiền", or "Reversal" and the amount is positive, DO NOT categorize as "Income". Set category to "Other" (or the original spending category) and confidence to "medium".

Examples:
Transaction: "AGODA REFUND"
Amount: 2000000
Date: 2026-04-06
Output: {{"category": "Other", "confidence": "medium"}}

Transaction: "T1908 GRAB CITY"
Amount: -50000
Date: 2026-04-05
Output: {{"category": "Transport", "confidence": "medium"}}

Transaction: "MACBOOK PRO 14 SHOPEE"
Amount: -35000000
Date: 2026-04-10
Output: {{"category": "Shopping", "confidence": "medium"}}

Transaction: "FT0024112501 ID:0001"
Amount: -250000
Date: 2026-04-12
Output: {{"category": "Other", "confidence": "low"}}

Transaction: "VINMART HCM 04"
Amount: -120000
Date: 2026-04-15
Output: {{"category": "Food", "confidence": "medium"}}

Transaction: "NETFLIX SUBSCRIPTION"
Amount: -250000
Date: 2026-04-20
Output: {{"category": "Subscriptions", "confidence": "high"}}

Transaction: "SALARY MAY"
Amount: 20000000
Date: 2026-04-30
Output: {{"category": "Income", "confidence": "high"}}

Now categorize this transaction:
Transaction: "{description}"
Amount: {amount}
Date: {date}

Respond with JSON only. No explanation.
"""


def _parse_json_response(text: str) -> dict:
    """Extract first JSON object from LLM response. Falls back to Other if invalid."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?|```$", "", text, flags=re.MULTILINE).strip()
    match = re.search(r"\{[^}]+\}", text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group())
            if obj.get("category") in CATEGORIES:
                return {
                    "category": obj["category"],
                    "confidence": obj.get("confidence", "medium"),
                }
        except json.JSONDecodeError:
            pass
    return {"category": "Other", "confidence": "low"}


class BedrockAI:
    def __init__(self, region: str, model_id: str):
        import boto3
        self.runtime = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id

    def categorize(self, description: str, amount: float, date: str, past_transactions: list = None) -> dict:
        # --- BƯỚC 1: HYBRID RULE-BASED (So khớp từ khóa nhanh offline) ---
        desc_lower = description.lower()
        for category, keywords in LocalAI.KEYWORDS.items():
            for kw in keywords:
                if kw in desc_lower:
                    # Khớp từ khóa chuẩn -> Gán ngay lập tức, độ tin cậy HIGH
                    return {"category": category, "confidence": "high"}

        # --- BƯỚC 2: GỌI BEDROCK AI NẾU GIAO DỊCH PHỨC TẠP / MƠ HỒ ---
        prompt = CATEGORIZE_PROMPT.format(
            categories=", ".join(CATEGORIES),
            description=description,
            amount=amount,
            date=date,
        )
        
        if past_transactions:
            dynamic_examples = "\nUSER'S PAST PREFERENCES (LEARN FROM THESE):\n"
            for t in past_transactions[:15]: # Use top 15 as examples
                dynamic_examples += f'Transaction: "{t.get("description", "")}"\nAmount: {t.get("amount", "")}\nDate: {t.get("date", "")}\nOutput: {{"category": "{t.get("category", "")}", "confidence": "high"}}\n\n'
            
            parts = prompt.split("Now categorize this transaction:")
            if len(parts) == 2:
                prompt = parts[0] + dynamic_examples + "Now categorize this transaction:" + parts[1]

        try:
            # Chờ phản hồi tối đa từ Bedrock, nếu quá tải hoặc lỗi sẽ kích hoạt fallback
            resp = self.runtime.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 100, "temperature": 0.0},
            )
            text = resp["output"]["message"]["content"][0]["text"]
            return _parse_json_response(text)
        except Exception as e:
            # --- BƯỚC 3: GRACEFUL FALLBACK NẾU BEDROCK BỊ TIMEOUT / LỖI ---
            import sys
            print(f"WARNING: Bedrock error triggered fallback to LocalAI: {e}", file=sys.stderr)
            
            # Dự phòng xuống LocalAI (Rule-based)
            local_ai = LocalAI()
            fallback_res = local_ai.categorize(description, amount, date)
            return {
                "category": fallback_res["category"],
                "confidence": "low-fallback"
            }


class LocalAI:
    """Rule-based categorizer. Keyword matching only. Use for development."""

    # Order matters: first match wins. Subscriptions BEFORE Entertainment so
    # "Netflix monthly subscription" → Subscriptions (subscription keyword fires).
    KEYWORDS = {
        "Income": ["salary", "deposit credit", "payroll", "incoming transfer"],
        "Transfer": ["transfer to", "transfer from", "moved to savings"],
        "Subscriptions": ["subscription", "netflix", "spotify", "openai", "chatgpt", "anthropic",
                          "claude", "github", "icloud", "google one"],
        "Food": ["restaurant", "cafe", "coffee", "starbucks", "highlands", "phở", "pho", "food",
                 "grab food", "shopee food", "lunch", "dinner", "bakery"],
        "Transport": ["grab", "uber", " be ", "xanh sm", "taxi", "metro", "bus", "petrol", "shell",
                      "vinfast", "fuel"],
        "Shopping": ["shopee", "lazada", "tiki", "amazon", "store", "mall", "vincom", "shop"],
        "Utilities": ["electric", "evn", "water", "internet", "viettel", "vnpt", "fpt", "utility"],
        "Entertainment": ["cinema", "cgv", "lotte cinema", "concert", "game"],
        "Health": ["pharmacy", "hospital", "clinic", "guardian", "long chau", "medlatec"],
    }

    def categorize(self, description: str, amount: float, date: str, past_transactions: list = None) -> dict:
        desc_lower = description.lower()
        for category, keywords in self.KEYWORDS.items():
            for kw in keywords:
                if kw in desc_lower:
                    return {"category": category, "confidence": "medium"}
        # Positive amount → income heuristic
        try:
            if float(amount) > 0:
                return {"category": "Income", "confidence": "low"}
        except (TypeError, ValueError):
            pass
        return {"category": "Other", "confidence": "low"}
