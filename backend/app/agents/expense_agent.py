from __future__ import annotations

import json
import os
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.models.schemas import CategorizationResult, TransactionInput

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "expense_categorization_prompt.txt"


def run_expense_categorization(transactions: list[TransactionInput]) -> CategorizationResult:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_text),
            (
                "human",
                "Transactions to classify: {transactions}. Return one item for each row index.",
            ),
        ]
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=api_key,
        temperature=0,
    )
    chain = prompt | llm

    serializable_rows = [
        {
            "row_index": idx,
            "txn_date": txn.txn_date,
            "description": txn.description,
            "merchant": txn.merchant,
            "amount": txn.amount,
        }
        for idx, txn in enumerate(transactions)
    ]

    response = chain.invoke({"transactions": serializable_rows})
    response_text = getattr(response, "content", str(response)).strip()
    if response_text.startswith("```"):
        response_text = response_text.strip("`")
        if response_text.lower().startswith("json"):
            response_text = response_text[4:].strip()

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Expense Agent returned invalid JSON: {response_text}") from exc

    result = CategorizationResult.model_validate(payload)
    if len(result.items) != len(transactions):
        raise RuntimeError(
            "Expense Agent returned mismatched number of categorization rows."
        )
    return result
