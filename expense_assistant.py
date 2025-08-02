# Trợ Lý Báo Cáo Chi Phí - Module Chính
"""
Trợ lý báo cáo chi phí được hỗ trợ AI với quản lý hội thoại,
gọi hàm và khả năng hướng dẫn chính sách.
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

class ExpenseAssistant:
    """
    Trợ lý báo cáo chi phí được hỗ trợ AI với quản lý hội thoại,
    gọi hàm và khả năng hướng dẫn chính sách.
    """
    
    def __init__(self, client, model="GPT-4o-mini"):
        self.client = client
        self.model = model
        self.conversation_history = []
        self.user_context = {}  # Store user-specific context
        
        # System prompt với ví dụ few-shot và chính sách công ty
        self.system_prompt = """Bạn là Trợ Lý Báo Cáo Chi Phí thông minh cho công ty chúng tôi. 
Vai trò của bạn là giúp nhân viên với báo cáo chi phí, câu hỏi chính sách và tính toán hoàn tiền.

TRÁCH NHIỆM CHÍNH:
1. Trả lời câu hỏi chính sách chi phí một cách chính xác
2. Giúp xác thực và tính toán hoàn tiền chi phí
3. Hướng dẫn người dùng qua quy trình nộp chi phí đúng cách
4. Cung cấp phản hồi rõ ràng, hữu ích và chuyên nghiệp

TÓM TẮT CHÍNH SÁCH CHI PHÍ CÔNG TY:
- Hóa đơn được yêu cầu cho chi phí trên 500.000 VNĐ
- Giới hạn ăn uống: 1.000.000 VNĐ/ngày trong nước, 1.500.000 VNĐ/ngày quốc tế
- Đi lại cần phê duyệt trước
- Văn phòng phẩm: giới hạn 2.000.000 VNĐ/tháng
- Báo cáo chi phí phải nộp trong vòng 30 ngày
- Tỷ lệ xăng xe: 3.000 VNĐ/km

PHONG CÁCH HỘI THOẠI:
- Thân thiện, chuyên nghiệp và hữu ích
- Đặt câu hỏi làm rõ khi cần
- Cung cấp hướng dẫn từng bước
- Sử dụng emoji phù hợp (📊, 💰, ✅, ❌, ⚠️)
- Luôn xác thực thông tin so với chính sách

GỌI HÀM:
Sử dụng các hàm có sẵn để:
- Tính toán hoàn tiền: calculate_reimbursement()
- Xác thực chi phí: validate_expense()
- Tìm kiếm chính sách: search_policies()
- Định dạng tóm tắt: format_expense_summary()

VÍ DỤ:
Người dùng: "Giới hạn chi phí ăn uống là bao nhiều?"
Trợ lý: "📋 Đối với ăn uống, chính sách công ty cho phép hoàn tiền tối đa 1.000.000 VNĐ mỗi ngày cho công tác trong nước và 1.500.000 VNĐ mỗi ngày cho công tác quốc tế. Rượu bia thường không được hoàn tiền trừ khi tiếp khách hàng. Bạn có cần giúp với chi phí ăn uống cụ thể nào không?"

Người dùng: "Tính hoàn tiền cho ăn trưa 900.000 VNĐ, taxi 400.000 VNĐ, văn phòng phẩm 2.400.000 VNĐ"
Trợ lý: [Sử dụng hàm calculate_reimbursement] "💰 Tôi đã tính toán hoàn tiền của bạn..."

Luôn hữu ích và chính xác với chính sách công ty."""

        # Khởi tạo hội thoại với system prompt
        self.conversation_history.append({
            "role": "system",
            "content": self.system_prompt
        })
    
    def add_user_message(self, message: str):
        """Thêm tin nhắn người dùng vào lịch sử hội thoại."""
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
    
    def add_assistant_message(self, message: str):
        """Thêm tin nhắn assistant vào lịch sử hội thoại."""
        self.conversation_history.append({
            "role": "assistant",
            "content": message
        })
    
    def add_function_result(self, function_name: str, result: Any):
        """Thêm kết quả gọi hàm vào lịch sử hội thoại."""
        self.conversation_history.append({
            "role": "function",
            "name": function_name,
            "content": json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
        })
    
    def get_conversation_summary(self) -> str:
        """Lấy tóm tắt cuộc hội thoại hiện tại."""
        user_messages = [msg for msg in self.conversation_history if msg["role"] == "user"]
        assistant_messages = [msg for msg in self.conversation_history if msg["role"] == "assistant"]
        
        return f"""📊 Tóm Tắt Hội Thoại:
• Tin nhắn người dùng: {len(user_messages)}
• Phản hồi trợ lý: {len(assistant_messages)}
• Tổng tin nhắn: {len(self.conversation_history)}
• Ngữ cảnh được bảo toàn: ✅"""
    
    def clear_conversation(self):
        """Xóa lịch sử hội thoại nhưng giữ system prompt."""
        self.conversation_history = [self.conversation_history[0]]  # Giữ system prompt
        self.user_context = {}
    
    def get_response(self, user_input: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Nhận phản hồi từ assistant với hỗ trợ gọi hàm.
        
        Args:
            user_input: Tin nhắn của người dùng
            max_retries: Số lần thử lại tối đa cho gọi hàm
            
        Returns:
            Dictionary với chi tiết phản hồi
        """
    
    def process_batch_requests(self, user_inputs: List[str], batch_size: int = 5) -> List[Dict[str, Any]]:
        """
        Xử lý nhiều request cùng lúc với batching để tối ưu hiệu suất.
        
        Args:
            user_inputs: Danh sách các tin nhắn từ người dùng
            batch_size: Kích thước batch cho mỗi lần xử lý
            
        Returns:
            Danh sách các phản hồi tương ứng
        """
        from functions import FUNCTION_SCHEMAS, execute_function_call
        import time
        
        results = []
        total_batches = (len(user_inputs) + batch_size - 1) // batch_size
        
        print(f"🔄 Xử lý {len(user_inputs)} requests với {total_batches} batch(es) (kích thước batch: {batch_size})")
        
        for batch_idx in range(0, len(user_inputs), batch_size):
            batch_inputs = user_inputs[batch_idx:batch_idx + batch_size]
            current_batch = batch_idx // batch_size + 1
            
            print(f"📦 Đang xử lý batch {current_batch}/{total_batches} ({len(batch_inputs)} requests)")
            start_time = time.time()
            
            batch_results = []
            
            for i, user_input in enumerate(batch_inputs):
                try:
                    # Tạo bản sao conversation history cho mỗi request trong batch
                    original_history = self.conversation_history.copy()
                    
                    # Add user message
                    temp_history = original_history + [{"role": "user", "content": user_input}]
                    
                    # Make API call
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=temp_history,
                        tools=FUNCTION_SCHEMAS,
                        tool_choice="auto",
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    message = response.choices[0].message
                    response_data = {
                        "input": user_input,
                        "content": message.content,
                        "tool_calls": [],
                        "function_results": [],
                        "total_tokens": response.usage.total_tokens if hasattr(response, 'usage') else 0,
                        "batch_index": current_batch,
                        "item_index": i + 1
                    }
                    
                    # Handle function calls nếu có
                    if message.tool_calls:
                        temp_history.append({
                            "role": "assistant",
                            "content": message.content,
                            "tool_calls": message.tool_calls
                        })
                        
                        for tool_call in message.tool_calls:
                            function_name = tool_call.function.name
                            function_args = json.loads(tool_call.function.arguments)
                            
                            # Execute function
                            function_result = execute_function_call(function_name, function_args)
                            
                            # Add function result
                            temp_history.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(function_result, ensure_ascii=False) if isinstance(function_result, dict) else str(function_result)
                            })
                            
                            response_data["tool_calls"].append({
                                "function": function_name,
                                "arguments": function_args,
                                "result": function_result
                            })
                        
                        # Get final response
                        final_response = self.client.chat.completions.create(
                            model=self.model,
                            messages=temp_history,
                            tools=FUNCTION_SCHEMAS,
                            tool_choice="auto",
                            temperature=0.7,
                            max_tokens=1000
                        )
                        
                        final_message = final_response.choices[0].message
                        response_data["content"] = final_message.content
                        response_data["total_tokens"] += final_response.usage.total_tokens if hasattr(final_response, 'usage') else 0
                    
                    batch_results.append(response_data)
                    
                except Exception as e:
                    error_response = {
                        "input": user_input,
                        "content": f"❌ Lỗi: {str(e)}",
                        "tool_calls": [],
                        "function_results": [],
                        "total_tokens": 0,
                        "batch_index": current_batch,
                        "item_index": i + 1,
                        "error": str(e)
                    }
                    batch_results.append(error_response)
            
            # Add delay giữa các batch để tránh rate limiting
            batch_time = time.time() - start_time
            print(f"   ✅ Hoàn thành batch {current_batch} trong {batch_time:.2f}s")
            
            if current_batch < total_batches:
                time.sleep(0.5)  # Nghỉ 0.5s giữa các batch
            
            results.extend(batch_results)
        
        # Tính toán thống kê tổng
        total_tokens = sum(r.get("total_tokens", 0) for r in results)
        successful_requests = len([r for r in results if "error" not in r])
        failed_requests = len(results) - successful_requests
        
        print(f"\n📊 KẾT QUẢ BATCH PROCESSING:")
        print(f"   • Tổng requests: {len(results)}")
        print(f"   • Thành công: {successful_requests}")
        print(f"   • Thất bại: {failed_requests}")
        print(f"   • Tổng tokens: {total_tokens:,}")
        print(f"   • Trung bình tokens/request: {total_tokens/len(results):.1f}")
        
        return results
    
    def process_expense_batch(self, expenses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Xử lý batch các chi phí để tính toán và xác thực hàng loạt.
        
        Args:
            expenses: Danh sách các chi phí cần xử lý
            
        Returns:
            Dictionary với kết quả xử lý tổng hợp
        """
        from functions import calculate_reimbursement, validate_expense, format_expense_summary
        
        print(f"💰 Xử lý batch {len(expenses)} chi phí...")
        
        # Tính toán hoàn trả cho tất cả chi phí
        reimbursement_result = calculate_reimbursement(expenses)
        
        # Xác thực từng chi phí
        validation_results = []
        for i, expense in enumerate(expenses):
            validation = validate_expense(expense)
            validation["expense_index"] = i + 1
            validation["expense"] = expense
            validation_results.append(validation)
        
        # Tạo tóm tắt
        summary = format_expense_summary(expenses)
        
        # Phân tích kết quả
        valid_expenses = [v for v in validation_results if v["is_valid"]]
        invalid_expenses = [v for v in validation_results if not v["is_valid"]]
        expenses_with_warnings = [v for v in validation_results if v["warnings"]]
        
        batch_result = {
            "total_expenses": len(expenses),
            "reimbursement_calculation": reimbursement_result,
            "validation_results": validation_results,
            "summary": summary,
            "statistics": {
                "valid_count": len(valid_expenses),
                "invalid_count": len(invalid_expenses),
                "warnings_count": len(expenses_with_warnings),
                "total_submitted": reimbursement_result["total_submitted"],
                "total_reimbursed": reimbursement_result["total_reimbursed"],
                "savings": reimbursement_result["savings"]
            }
        }
        
        print(f"   ✅ Hoàn thành: {len(valid_expenses)}/{len(expenses)} chi phí hợp lệ")
        print(f"   💰 Tổng hoàn trả: {reimbursement_result['total_reimbursed']:,.0f} VNĐ")
        
        return batch_result
        
    def get_response(self, user_input: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Nhận phản hồi từ assistant với hỗ trợ gọi hàm (method gốc cho single request).
        
        Args:
            user_input: Tin nhắn của người dùng
            max_retries: Số lần thử lại tối đa cho gọi hàm
            
        Returns:
            Dictionary với chi tiết phản hồi
        """
        from functions import FUNCTION_SCHEMAS, execute_function_call
        
        try:
            # Add user message to history
            self.add_user_message(user_input)
            
            # Make API call with function calling enabled
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                tools=FUNCTION_SCHEMAS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000
            )
            
            message = response.choices[0].message
            response_data = {
                "content": message.content,
                "tool_calls": [],
                "function_results": [],
                "total_tokens": response.usage.total_tokens if hasattr(response, 'usage') else 0
            }
            
            # Handle function calls
            if message.tool_calls:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": message.tool_calls
                })
                
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Execute function
                    function_result = execute_function_call(function_name, function_args)
                    
                    # Add function result to conversation
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(function_result, ensure_ascii=False) if isinstance(function_result, dict) else str(function_result)
                    })
                    
                    response_data["tool_calls"].append({
                        "function": function_name,
                        "arguments": function_args,
                        "result": function_result
                    })
                
                # Get final response after function calls
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.conversation_history,
                    tools=FUNCTION_SCHEMAS,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=1000
                )
                
                final_message = final_response.choices[0].message
                response_data["content"] = final_message.content
                response_data["total_tokens"] += final_response.usage.total_tokens if hasattr(final_response, 'usage') else 0
                
                # Add final response to history
                self.add_assistant_message(final_message.content)
            else:
                # No function calls, just add the response
                self.add_assistant_message(message.content)
            
            return response_data
            
        except Exception as e:
            error_msg = f"❌ Lỗi: {str(e)}"
            self.add_assistant_message(error_msg)
            return {
                "content": error_msg,
                "tool_calls": [],
                "function_results": [],
                "total_tokens": 0,
                "error": str(e)
            }
        from functions import FUNCTION_SCHEMAS, execute_function_call
        
        try:
            # Add user message to history
            self.add_user_message(user_input)
            
            # Make API call with function calling enabled
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                tools=FUNCTION_SCHEMAS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000
            )
            
            message = response.choices[0].message
            response_data = {
                "content": message.content,
                "tool_calls": [],
                "function_results": [],
                "total_tokens": response.usage.total_tokens if hasattr(response, 'usage') else 0
            }
            
            # Handle function calls
            if message.tool_calls:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": message.tool_calls
                })
                
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Execute function
                    function_result = execute_function_call(function_name, function_args)
                    
                    # Add function result to conversation
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(function_result, ensure_ascii=False) if isinstance(function_result, dict) else str(function_result)
                    })
                    
                    response_data["tool_calls"].append({
                        "function": function_name,
                        "arguments": function_args,
                        "result": function_result
                    })
                
                # Get final response after function calls
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.conversation_history,
                    tools=FUNCTION_SCHEMAS,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=1000
                )
                
                final_message = final_response.choices[0].message
                response_data["content"] = final_message.content
                response_data["total_tokens"] += final_response.usage.total_tokens if hasattr(final_response, 'usage') else 0
                
                # Add final response to history
                self.add_assistant_message(final_message.content)
            else:
                # No function calls, just add the response
                self.add_assistant_message(message.content)
            
            return response_data
            
        except Exception as e:
            error_msg = f"❌ Lỗi: {str(e)}"
            self.add_assistant_message(error_msg)
            return {
                "content": error_msg,
                "tool_calls": [],
                "function_results": [],
                "total_tokens": 0,
                "error": str(e)
            }

def create_client():
    """Tạo và trả về OpenAI client."""
    return OpenAI(
        base_url=os.getenv('OPENAI_BASE_URL'),
        api_key=os.getenv('OPENAI_API_KEY')
    )
