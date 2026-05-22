import json
from typing import Any, Dict

def format_answer(state: Dict[str, Any]) -> Dict[str, Any]:
    """Format the final answer based on the execution result or node action."""
    action = state.get("actual_action", "generate_sql")
    
    # Handle direct refusals/clarifications
    if action == "refuse_unsafe_sql":
        return {"final_answer": "متاسفانه امکان اجرای این درخواست به دلایل امنیتی وجود ندارد."}
    if action == "refuse_privacy":
        return {"final_answer": "متاسفانه به دلایل حفظ حریم خصوصی، امکان نمایش اطلاعات فردی وجود ندارد."}
    if action == "ask_clarification":
        return {"final_answer": "لطفاً سوال خود را شفاف‌تر بیان کنید تا بتوانم کوئری دقیقی بسازم."}
    if action == "fail_gracefully":
        return {"final_answer": "تلاش برای تولید پاسخ مناسب موفقیت‌آمیز نبود. لطفاً سوال خود را تغییر دهید."}
    if action == "answer_without_sql":
        return {"final_answer": "این یک سوال مشاوره‌ای/تعریفی است. سیستم در حال حاضر فقط تحلیل داده‌های جدولی را پشتیبانی می‌کند."}
    if action == "answer_chart_recommendation":
        return {"final_answer": "این سوال نیاز به پیشنهاد نمودار دارد. (تحلیل و نمودار پیشنهادی به زودی پشتیبانی می‌شود)"}
        
        
    execution_result = state.get("execution_result")
    
    if execution_result is None and not state.get("semantic_passed", True):
        # In base_nodes, if semantic_passed is False, execution failed. But here we don't always have it.
        # If execution_result is None, either it failed or it hasn't run.
        if action == "fail_gracefully":
            return {"final_answer": "تلاش برای تولید پاسخ مناسب موفقیت‌آمیز نبود. لطفاً سوال خود را تغییر دهید."}
        return {"final_answer": f"خطا در اجرای کوئری."}
        
    rows = execution_result if hasattr(execution_result, "__iter__") else (execution_result or [])
    if not rows:
        return {"final_answer": "داده‌ای یافت نشد."}
        
    # Format based on shape
    if len(rows) == 1 and len(rows[0]) == 1:
        val = list(rows[0].values())[0]
        # Check if float, format nicely
        if isinstance(val, float):
            val = round(val, 2)
        return {"final_answer": f"تحلیل انجام شد. مقدار محاسبه شده: {val}"}
        
    # Table format
    headers = list(rows[0].keys())
    markdown_table = "تحلیل انجام شد. نتیجه به شرح زیر است:\n\n"
    markdown_table += "| " + " | ".join(headers) + " |\n"
    markdown_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    
    for row in rows[:10]: # Limit to 10 rows for display
        markdown_table += "| " + " | ".join([str(round(row.get(h, ""), 2)) if isinstance(row.get(h, ""), float) else str(row.get(h, "")) for h in headers]) + " |\n"
        
    if len(rows) > 10:
        markdown_table += f"\n*نمایش ۱۰ ردیف از مجموع {len(rows)} ردیف.*\n"
        
    markdown_table += "\n**توجه:** این داده‌ها برای مقاصد پژوهشی است و کاربرد بالینی ندارد."
        
    return {"final_answer": markdown_table}
