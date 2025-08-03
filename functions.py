# Expense Processing Functions and Data
"""
Helper functions for expense validation, reimbursement calculation, 
policy checking, and data formatting.
"""

import re
from datetime import datetime
from typing import List, Dict, Any

# Chính sách chi phí công ty (Cơ sở tri thức)
EXPENSE_POLICIES = {
    "receipts": [
        "Hóa đơn được yêu cầu cho TẤT CẢ chi phí trên 500.000 VNĐ",
        "Hóa đơn điện tử và ảnh chụp được chấp nhận",
        "Hóa đơn gốc phải được giữ lại để kiểm toán",
        "Hóa đơn bị mất cần có sự phê duyệt của quản lý và giải trình"
    ],
    "meals": [
        "Chi phí ăn uống được hoàn trả tối đa 1.000.000 VNĐ/ngày cho công tác trong nước",
        "Giới hạn ăn uống công tác quốc tế là 1.500.000 VNĐ/ngày",
        "Rượu bia không được hoàn trả trừ khi tiếp khách hàng",
        "Ăn uống nhóm cần có danh sách người tham dự và mục đích kinh doanh"
    ],
    "travel": [
        "Chi phí đi lại phải được quản lý phê duyệt trước",
        "Đặt vé máy bay hạng phổ thông cho chuyến bay dưới 6 giờ",
        "Giá phòng khách sạn không vượt quá 4.000.000 VNĐ/đêm trừ khi ở thành phố chi phí cao",
        "Thuê xe cần có lý do kinh doanh nếu có phương tiện khác"
    ],
    "transportation": [
        "Chi phí taxi/Grab được hoàn trả đầy đủ với mục đích kinh doanh",
        "Tỷ lệ hoàn trả xăng xe là 3.000 VNĐ/km",
        "Phí đậu xe tại địa điểm kinh doanh được hoàn trả",
        "Sử dụng xe cá nhân cần ghi chỉ số công tơ mét"
    ],
    "office_supplies": [
        "Đồ dùng văn phòng tối đa 2.000.000 VNĐ/tháng mỗi nhân viên",
        "Mua hàng số lượng lớn cần phê duyệt quản lý",
        "Thiết bị văn phòng tại nhà cần phê duyệt phòng IT",
        "Giấy phép phần mềm phải được phòng bảo mật IT phê duyệt"
    ],
    "deadlines": [
        "Báo cáo chi phí phải được nộp trong vòng 30 ngày kể từ ngày phát sinh chi phí",
        "Báo cáo hàng tháng đến hạn vào ngày 5 của tháng tiếp theo",
        "Nộp trễ có thể dẫn đến chậm thanh toán",
        "Hạn cuối năm là ngày 31 tháng 12 - không có ngoại lệ"
    ]
}

# Danh mục chi phí mẫu với giới hạn và quy tắc
EXPENSE_CATEGORIES = {
    "meals": {"daily_limit": 1000000, "international_limit": 1500000, "requires_receipt": True},
    "travel": {"requires_approval": True, "flight_class": "phổ thông", "hotel_limit": 4000000},
    "taxi": {"fully_reimbursable": True, "requires_purpose": True},
    "mileage": {"rate_per_km": 3000, "requires_odometer": True},
    "office_supplies": {"monthly_limit": 2000000, "bulk_requires_approval": True},
    "parking": {"fully_reimbursable": True, "requires_receipt": True},
    "phone": {"monthly_limit": 1000000, "requires_business_use": True},
    "internet": {"monthly_limit": 2000000, "home_office_only": True}
}

# Các mẫu báo cáo chi phí để kiểm tra
MOCK_EXPENSE_REPORTS = [
    {"employee_id": "NV123", "date": "2025-07-20", "category": "meals", "amount": 900000, "description": "Ăn trưa với khách hàng", "has_receipt": True},
    {"employee_id": "NV123", "date": "2025-07-21", "category": "taxi", "amount": 350000, "description": "Từ sân bay đến khách sạn", "has_receipt": True},
    {"employee_id": "NV123", "date": "2025-07-22", "category": "travel", "amount": 12000000, "description": "Vé máy bay đi hội nghị", "has_receipt": True},
    {"employee_id": "NV456", "date": "2025-07-18", "category": "meals", "amount": 1500000, "description": "Tiệc tối nhóm", "has_receipt": False},
    {"employee_id": "NV456", "date": "2025-07-19", "category": "office_supplies", "amount": 1800000, "description": "Hộp mực máy in", "has_receipt": True},
    {"employee_id": "NV789", "date": "2025-07-15", "category": "mileage", "amount": 450000, "description": "Thăm khách hàng - 150 km", "has_receipt": False}
]

# Các câu hỏi thường gặp của người dùng để kiểm tra
SAMPLE_USER_QUERIES = [
    "Giới hạn chi phí ăn uống là bao nhiều?",
    "Tôi có cần hóa đơn cho chuyến đi taxi không?",
    "Làm thế nào để nộp chi phí xăng xe?",
    "Hạn chót nộp báo cáo chi phí là khi nào?",
    "Tôi có thể chi tiêu cho rượu bia không?",
    "Giới hạn khách sạn cho công tác là bao nhiều?",
    "Tôi có thể chi bao nhiều cho đồ dùng văn phòng?",
    "Tính toán hoàn tiền cho chi phí của tôi",
    "Tôi mất hóa đơn, phải làm gì?",
    "Tôi cần những giấy tờ gì cho chi phí đi lại?"
]

# FAQs và Knowledge Base mở rộng cho chatbot
GENERAL_FAQS = [
    {
        "question": "Làm thế nào để đăng nhập vào hệ thống báo cáo chi phí?",
        "answer": "Bạn có thể đăng nhập bằng tài khoản công ty của mình. Nếu quên mật khẩu, liên hệ IT Support để được hỗ trợ reset.",
        "category": "system_access",
        "keywords": ["đăng nhập", "login", "tài khoản", "mật khẩu", "password"]
    },
    {
        "question": "Tôi có thể nộp báo cáo chi phí bằng mobile app không?",
        "answer": "Có, công ty có mobile app để nộp báo cáo chi phí. Bạn có thể tải app 'Company Expense' từ App Store hoặc Play Store.",
        "category": "mobile_app",
        "keywords": ["mobile", "app", "điện thoại", "smartphone", "ứng dụng"]
    },
    {
        "question": "Quy trình phê duyệt chi phí như thế nào?",
        "answer": "Chi phí dưới 5 triệu: Manager trực tiếp phê duyệt. Chi phí 5-20 triệu: Cần phê duyệt từ Department Head. Trên 20 triệu: Cần phê duyệt từ Director.",
        "category": "approval_process",
        "keywords": ["phê duyệt", "approval", "quy trình", "manager", "director"]
    },
    {
        "question": "Thời gian xử lý hoàn trả thường là bao lâu?",
        "answer": "Sau khi được phê duyệt, chi phí sẽ được hoàn trả trong vòng 5-7 ngày làm việc thông qua chuyển khoản ngân hàng.",
        "category": "reimbursement_timing",
        "keywords": ["hoàn trả", "thời gian", "ngân hàng", "chuyển khoản", "reimbursement"]
    },
    {
        "question": "Tôi có thể chỉnh sửa báo cáo chi phí đã nộp không?",
        "answer": "Sau khi nộp, bạn chỉ có thể chỉnh sửa trong vòng 24 giờ. Sau đó cần liên hệ Finance Team để được hỗ trợ.",
        "category": "report_editing",
        "keywords": ["chỉnh sửa", "edit", "thay đổi", "modify", "24 giờ"]
    }
]

COMPANY_KNOWLEDGE_BASE = [
    {
        "topic": "Chính sách làm việc từ xa",
        "content": "Nhân viên có thể làm việc từ xa tối đa 3 ngày/tuần. Chi phí internet và điện thoại tại nhà được hỗ trợ một phần theo quy định.",
        "category": "work_from_home",
        "keywords": ["làm việc từ xa", "remote work", "internet", "điện thoại", "home office"]
    },
    {
        "topic": "Quy định về đào tạo và phát triển",
        "content": "Công ty hỗ trợ 100% chi phí đào tạo liên quan đến công việc. Nhân viên cần đăng ký trước và có xác nhận từ Manager.",
        "category": "training_development", 
        "keywords": ["đào tạo", "training", "course", "khóa học", "phát triển"]
    },
    {
        "topic": "Chính sách nghỉ phép",
        "content": "Nhân viên có 12 ngày phép năm cộng thêm 3 ngày phép cá nhân. Phép năm không được chuyển sang năm sau.",
        "category": "leave_policy",
        "keywords": ["nghỉ phép", "leave", "vacation", "ngày phép", "annual leave"]
    },
    {
        "topic": "Quy định bảo mật thông tin",
        "content": "Mọi thông tin công ty đều là bảo mật. Không được chia sẻ thông tin khách hàng ra bên ngoài. Vi phạm sẽ bị xử lý kỷ luật.",
        "category": "security_policy",
        "keywords": ["bảo mật", "security", "thông tin", "confidential", "khách hàng"]
    },
    {
        "topic": "Hỗ trợ IT và thiết bị",
        "content": "IT Support hoạt động 24/7. Có thể yêu cầu thiết bị mới qua portal hoặc liên hệ trực tiếp hotline 1900-xxxx.",
        "category": "it_support",
        "keywords": ["IT", "thiết bị", "equipment", "support", "hotline", "portal"]
    }
]

def calculate_reimbursement(expenses: List[Dict]) -> Dict[str, Any]:
    """
    Calculate total reimbursement amount based on company policies.
    
    Args:
        expenses: List of expense dictionaries with category, amount, and other details
        
    Returns:
        Dictionary with breakdown and total reimbursement
    """
    breakdown = []
    total_reimbursed = 0
    total_submitted = 0
    
    for expense in expenses:
        category = expense.get('category', '').lower()
        amount = float(expense.get('amount', 0))
        total_submitted += amount
        
        # Apply category-specific rules
        if category == 'meals':
            daily_limit = EXPENSE_CATEGORIES['meals']['daily_limit']
            reimbursed = min(amount, daily_limit)
            note = f"Giới hạn {daily_limit:,.0f} VNĐ/ngày" if amount > daily_limit else "Hoàn trả đầy đủ"
            
        elif category == 'taxi':
            reimbursed = amount
            note = "Hoàn trả đầy đủ"
            
        elif category == 'travel':
            reimbursed = amount
            note = "Hoàn trả đầy đủ (giả sử đã được phê duyệt)"
            
        elif category == 'mileage':
            # Trích xuất km từ mô tả hoặc tính toán
            description = expense.get('description', '')
            km_match = re.search(r'(\d+)\s*km', description.lower())
            if km_match:
                km = int(km_match.group(1))
                rate = EXPENSE_CATEGORIES['mileage']['rate_per_km']
                reimbursed = km * rate
                note = f"{km} km @ {rate:,.0f} VNĐ/km"
            else:
                reimbursed = amount
                note = "Tính toán thủ công - xác minh số km"
                
        elif category == 'office_supplies':
            monthly_limit = EXPENSE_CATEGORIES['office_supplies']['monthly_limit']
            reimbursed = min(amount, monthly_limit)
            note = f"Giới hạn {monthly_limit:,.0f} VNĐ/tháng" if amount > monthly_limit else "Hoàn trả đầy đủ"
            
        elif category == 'parking':
            reimbursed = amount
            note = "Hoàn trả đầy đủ"
            
        else:
            reimbursed = 0
            note = "Danh mục không được nhận dạng - cần xem xét thủ công"
        
        total_reimbursed += reimbursed
        
        breakdown.append({
            "category": expense.get('category'),
            "amount_submitted": amount,
            "amount_reimbursed": reimbursed,
            "note": note
        })
    
    return {
        "breakdown": breakdown,
        "total_submitted": total_submitted,
        "total_reimbursed": total_reimbursed,
        "savings": total_submitted - total_reimbursed
    }

def validate_expense(expense: Dict) -> Dict[str, Any]:
    """
    Validate an expense entry against company policies.
    
    Args:
        expense: Dictionary containing expense details
        
    Returns:
        Dictionary with validation results and warnings
    """
    warnings = []
    errors = []
    category = expense.get('category', '').lower()
    amount = float(expense.get('amount', 0))
    has_receipt = expense.get('has_receipt', False)
    date_str = expense.get('date', '')
    
    # Check receipt requirements
    if amount > 500000 and not has_receipt:
        errors.append(f"Yêu cầu hóa đơn cho chi phí trên 500.000 VNĐ (số tiền: {amount:,.0f} VNĐ)")
    
    # Check date validity (within 30 days)
    try:
        expense_date = datetime.strptime(date_str, '%Y-%m-%d')
        days_old = (datetime.now() - expense_date).days
        if days_old > 30:
            warnings.append(f"Chi phí đã {days_old} ngày tuổi - báo cáo nên được nộp trong vòng 30 ngày")
    except ValueError:
        errors.append("Định dạng ngày không hợp lệ - sử dụng YYYY-MM-DD")
    
    # Category-specific validations
    if category == 'meals' and amount > EXPENSE_CATEGORIES['meals']['daily_limit']:
        warnings.append(f"Chi phí ăn uống {amount:,.0f} VNĐ vượt quá giới hạn hàng ngày {EXPENSE_CATEGORIES['meals']['daily_limit']:,.0f} VNĐ")
    
    if category == 'travel':
        if not expense.get('pre_approved', False):
            warnings.append("Chi phí đi lại cần phê duyệt trước")
    
    if category == 'office_supplies' and amount > EXPENSE_CATEGORIES['office_supplies']['monthly_limit']:
        warnings.append(f"Chi phí văn phòng phẩm {amount:,.0f} VNĐ vượt quá giới hạn hàng tháng {EXPENSE_CATEGORIES['office_supplies']['monthly_limit']:,.0f} VNĐ")
    
    return {
        "is_valid": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "requires_manager_approval": len(errors) > 0 or ('travel' in category and not expense.get('pre_approved', False))
    }

def search_policies(query: str) -> List[str]:
    """
    Search expense policies based on user query.
    
    Args:
        query: User's question or search term
        
    Returns:
        List of relevant policy statements
    """
    query_lower = query.lower()
    relevant_policies = []
    
    # Map keywords to policy categories
    keyword_mapping = {
        'hóa đơn': 'receipts',
        'receipt': 'receipts',
        'ăn': 'meals',
        'meal': 'meals',
        'thức ăn': 'meals',
        'food': 'meals',
        'trưa': 'meals',
        'lunch': 'meals',
        'tối': 'meals',
        'dinner': 'meals',
        'đi lại': 'travel',
        'travel': 'travel',
        'máy bay': 'travel',
        'flight': 'travel',
        'khách sạn': 'travel',
        'hotel': 'travel',
        'taxi': 'transportation',
        'grab': 'transportation',
        'uber': 'transportation',
        'xăng': 'transportation',
        'mileage': 'transportation',
        'xe': 'transportation',
        'car': 'transportation',
        'văn phòng': 'office_supplies',
        'office': 'office_supplies',
        'phẩm': 'office_supplies',
        'supplies': 'office_supplies',
        'hạn': 'deadlines',
        'deadline': 'deadlines',
        'nộp': 'deadlines',
        'submit': 'deadlines',
        'due': 'deadlines'
    }
    
    # Find matching categories
    matched_categories = set()
    for keyword, category in keyword_mapping.items():
        if keyword in query_lower:
            matched_categories.add(category)
    
    # If no specific keywords found, search all policies
    if not matched_categories:
        matched_categories = set(EXPENSE_POLICIES.keys())
    
    # Collect relevant policies
    for category in matched_categories:
        if category in EXPENSE_POLICIES:
            relevant_policies.extend(EXPENSE_POLICIES[category])
    
    return relevant_policies[:5]  # Limit to top 5 most relevant

def format_expense_summary(expenses: List[Dict]) -> str:
    """
    Format a list of expenses into a readable summary.
    
    Args:
        expenses: List of expense dictionaries
        
    Returns:
        Formatted string summary
    """
    if not expenses:
        return "Không tìm thấy chi phí."
    
    summary = f"📊 **Tóm Tắt Chi Phí** ({len(expenses)} mục)\n\n"
    
    total = 0
    by_category = {}
    
    for expense in expenses:
        category = expense.get('category', 'Không xác định')
        amount = float(expense.get('amount', 0))
        total += amount
        
        if category not in by_category:
            by_category[category] = 0
        by_category[category] += amount
    
    # Category breakdown
    summary += "**Theo Danh Mục:**\n"
    for category, amount in sorted(by_category.items()):
        summary += f"  • {category.title()}: {amount:,.0f} VNĐ\n"
    
    summary += f"\n**Tổng Số Tiền:** {total:,.0f} VNĐ\n"
    
    return summary

# Define available functions for OpenAI to call
AVAILABLE_FUNCTIONS = {
    "calculate_reimbursement": calculate_reimbursement,
    "validate_expense": validate_expense,
    "search_policies": search_policies,
    "format_expense_summary": format_expense_summary
}

# Function schemas for OpenAI function calling
FUNCTION_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_reimbursement",
            "description": "Tính tổng số tiền hoàn trả từ danh sách chi phí dựa trên chính sách công ty",
            "parameters": {
                "type": "object",
                "properties": {
                    "expenses": {
                        "type": "array",
                        "description": "Danh sách các mục chi phí để tính hoàn trả",
                        "items": {
                            "type": "object",
                            "properties": {
                                "category": {
                                    "type": "string",
                                    "description": "Danh mục chi phí (meals, travel, taxi, mileage, office_supplies, parking, v.v.)"
                                },
                                "amount": {
                                    "type": "number",
                                    "description": "Số tiền chi phí tính bằng VNĐ"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Mô tả chi phí"
                                },
                                "date": {
                                    "type": "string",
                                    "description": "Ngày chi phí theo định dạng YYYY-MM-DD"
                                },
                                "has_receipt": {
                                    "type": "boolean",
                                    "description": "Có hóa đơn hay không"
                                }
                            },
                            "required": ["category", "amount"]
                        }
                    }
                },
                "required": ["expenses"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_expense",
            "description": "Xác thực một mục chi phí theo chính sách công ty và yêu cầu",
            "parameters": {
                "type": "object",
                "properties": {
                    "expense": {
                        "type": "object",
                        "description": "Expense entry to validate",
                        "properties": {
                            "category": {"type": "string"},
                            "amount": {"type": "number"},
                            "description": {"type": "string"},
                            "date": {"type": "string"},
                            "has_receipt": {"type": "boolean"},
                            "pre_approved": {"type": "boolean"}
                        },
                        "required": ["category", "amount"]
                    }
                },
                "required": ["expense"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_policies",
            "description": "Tìm kiếm chính sách chi phí công ty dựa trên truy vấn hoặc từ khóa",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query or keyword to find relevant expense policies"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "format_expense_summary",
            "description": "Định dạng danh sách chi phí thành tóm tắt dễ đọc với tổng số và danh mục",
            "parameters": {
                "type": "object",
                "properties": {
                    "expenses": {
                        "type": "array",
                        "description": "List of expenses to summarize",
                        "items": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string"},
                                "amount": {"type": "number"},
                                "description": {"type": "string"},
                                "date": {"type": "string"}
                            },
                            "required": ["category", "amount"]
                        }
                    }
                },
                "required": ["expenses"]
            }
        }
    }
]

def execute_function_call(function_name: str, arguments: Dict) -> Any:
    """
    Execute a function call from OpenAI with the given arguments.
    
    Args:
        function_name: Name of the function to call
        arguments: Dictionary of arguments to pass to the function
        
    Returns:
        Result of the function call
    """
    import json
    
    if function_name in AVAILABLE_FUNCTIONS:
        function = AVAILABLE_FUNCTIONS[function_name]
        try:
            # Extract arguments based on function signature
            if function_name == "calculate_reimbursement":
                return function(arguments["expenses"])
            elif function_name == "validate_expense":
                return function(arguments["expense"])
            elif function_name == "search_policies":
                return function(arguments["query"])
            elif function_name == "format_expense_summary":
                return function(arguments["expenses"])
            else:
                return {"error": f"Unknown function: {function_name}"}
        except Exception as e:
            return {"error": f"Error executing {function_name}: {str(e)}"}
    else:
        return {"error": f"Function {function_name} not available"}
