import sys
import os
from flow import create_text_to_sql_flow


def run_text_to_sql(natural_query, max_debug_retries=3):
    
    shared = {
        "natural_query": natural_query,
        "max_debug_attempts": max_debug_retries,
        "debug_attempts": 0,
        "final_result": None,
        "final_error": None,
        "final_columns": [],
        "generated_sql": "" 
    }

    print(f"\n=== Starting Chatbot ===")
    print(f"Query: '{natural_query}'")
    print("=" * 30)

    flow = create_text_to_sql_flow()
    flow.run(shared)

    if shared.get("final_error"):
        return f"Lỗi: {shared['final_error']}"
    elif shared.get("final_result") is not None:
        return (
            shared["final_result"], 
            shared.get("final_columns"), 
            shared.get("generated_sql")
        )
    else:
        return "Không có kết quả."

if __name__ == "__main__":
    question = "Dự án nào có giá trị lớn nhất?"
    print(run_text_to_sql(question))