# Expense Processing Functions and Data
"""
🏢 Hệ thống xử lý chi phí và chính sách công ty
Các function helper cho validation, tính toán hoàn trả, 
kiểm tra chính sách và format dữ liệu.

Author: Workshop Team
Date: August 2025
"""

import re
from datetime import datetime
from typing import List, Dict, Any

# 📋 CHÍNH SÁCH CHI PHÍ CÔNG TY (Company Expense Policies)
EXPENSE_POLICIES = {
    # 🧾 Quy định về hóa đơn và chứng từ
    "receipts": [
        "Hóa đơn được yêu cầu cho TẤT CẢ chi phí trên 500.000 VNĐ",
        "Hóa đơn điện tử và ảnh chụp được chấp nhận",
        "Hóa đơn gốc phải được giữ lại để kiểm toán",
        "Hóa đơn bị mất cần có sự phê duyệt của quản lý và giải trình",
        "Hóa đơn phải ghi rõ ngày, số tiền và tên nhà cung cấp",
        "Hóa đơn không hợp lệ sẽ bị từ chối hoàn trả",
        "Hóa đơn phải nộp cùng báo cáo chi phí",
        "Hóa đơn cho chi phí nhóm cần ghi rõ danh sách người tham dự",
        "Hóa đơn cho chi phí quốc tế phải chuyển đổi sang VNĐ theo tỷ giá công ty",
        "Hóa đơn cho chi phí taxi phải ghi rõ điểm đi và điểm đến"
    ],
    
    # 🍽️ Quy định về chi phí ăn uống
    "meals": [
        "Chi phí ăn uống được hoàn trả tối đa 1.000.000 VNĐ/ngày cho công tác trong nước",
        "Giới hạn ăn uống công tác quốc tế là 1.500.000 VNĐ/ngày",
        "Rượu bia không được hoàn trả trừ khi tiếp khách hàng",
        "Ăn uống nhóm cần có danh sách người tham dự và mục đích kinh doanh",
        "Chi phí ăn sáng chỉ được hoàn trả khi đi công tác qua đêm",
        "Chi phí ăn uống phải có hóa đơn hợp lệ",
        "Không hoàn trả chi phí ăn uống cho người thân hoặc bạn bè",
        "Chi phí ăn uống trong nội thành không được hoàn trả nếu không có lý do công việc",
        "Chi phí ăn uống vượt quá giới hạn cần phê duyệt quản lý",
        "Chi phí ăn uống cho sự kiện nội bộ cần có xác nhận phòng HR"
    ],
    
    # ✈️ Quy định về chi phí đi lại và công tác
    "travel": [
        "Chi phí đi lại phải được quản lý phê duyệt trước",
        "Đặt vé máy bay hạng phổ thông cho chuyến bay dưới 6 giờ",
        "Giá phòng khách sạn không vượt quá 4.000.000 VNĐ/đêm trừ khi ở thành phố chi phí cao",
        "Thuê xe cần có lý do kinh doanh nếu có phương tiện khác",
        "Chi phí di chuyển bằng tàu hỏa được hoàn trả theo giá vé phổ thông",
        "Chi phí đi lại quốc tế cần có phê duyệt phòng tài chính",
        "Chi phí visa và bảo hiểm du lịch được hoàn trả nếu đi công tác",
        "Chi phí di chuyển bằng xe cá nhân chỉ hoàn trả theo km quy định",
        "Chi phí đi lại phải ghi rõ mục đích chuyến đi",
        "Chi phí khách sạn phải có hóa đơn và xác nhận lưu trú"
    ],
    
    # 🚗 Quy định về chi phí di chuyển
    "transportation": [
        "Chi phí taxi/Grab được hoàn trả đầy đủ với mục đích kinh doanh",
        "Tỷ lệ hoàn trả xăng xe là 3.000 VNĐ/km",
        "Phí đậu xe tại địa điểm kinh doanh được hoàn trả",
        "Sử dụng xe cá nhân cần ghi chỉ số công tơ mét",
        "Chi phí gửi xe qua đêm chỉ hoàn trả nếu có lý do công việc",
        "Chi phí vận chuyển hàng hóa cần có hóa đơn vận chuyển",
        "Chi phí taxi ngoài giờ làm việc cần có xác nhận quản lý",
        "Chi phí thuê xe máy chỉ hoàn trả cho công tác ngoại tỉnh",
        "Chi phí cầu đường được hoàn trả nếu có hóa đơn",
        "Chi phí vận chuyển bằng xe công ty cần ghi rõ lộ trình"
    ],
    "office_supplies": [
        "Đồ dùng văn phòng tối đa 2.000.000 VNĐ/tháng mỗi nhân viên",
        "Mua hàng số lượng lớn cần phê duyệt quản lý",
        "Thiết bị văn phòng tại nhà cần phê duyệt phòng IT",
        "Giấy phép phần mềm phải được phòng bảo mật IT phê duyệt",
        "Chi phí mua máy tính, máy in cần có xác nhận phòng IT",
        "Chi phí sửa chữa thiết bị văn phòng cần hóa đơn và biên bản bàn giao",
        "Chi phí mua bàn ghế văn phòng chỉ hoàn trả cho phòng ban",
        "Chi phí văn phòng phẩm cho sự kiện cần xác nhận phòng HR",
        "Chi phí mua sách chuyên ngành được hoàn trả nếu liên quan công việc",
        "Chi phí mua vật tư tiêu hao phải ghi rõ mục đích sử dụng"
    ],
    "deadlines": [
        "Báo cáo chi phí phải được nộp trong vòng 30 ngày kể từ ngày phát sinh chi phí",
        "Báo cáo hàng tháng đến hạn vào ngày 5 của tháng tiếp theo",
        "Nộp trễ có thể dẫn đến chậm thanh toán",
        "Hạn cuối năm là ngày 31 tháng 12 - không có ngoại lệ",
        "Báo cáo chi phí quý phải nộp trước ngày 10 của tháng đầu quý tiếp theo",
        "Báo cáo chi phí bổ sung cần có lý do rõ ràng",
        "Báo cáo chi phí bị trả lại phải chỉnh sửa trong vòng 7 ngày",
        "Báo cáo chi phí cho công tác quốc tế phải nộp trong vòng 15 ngày sau khi về nước",
        "Báo cáo chi phí nhóm phải nộp kèm danh sách thành viên",
        "Báo cáo chi phí sự kiện phải nộp trong vòng 5 ngày sau sự kiện"
    ]
}

# 💰 CẤU HÌNH CHI PHÍ VÀ GIỚI HẠN (Expense Categories & Limits)
EXPENSE_CATEGORIES = {
    # 🍽️ Chi phí ăn uống
    "meals": {
        "daily_limit": 1000000,           # Giới hạn hàng ngày (VNĐ)
        "international_limit": 1500000,   # Giới hạn quốc tế (VNĐ)
        "requires_receipt": True,         # Yêu cầu hóa đơn
        "description": "Chi phí ăn uống công tác"
    },
    
    # ✈️ Chi phí đi lại
    "travel": {
        "requires_approval": True,        # Cần phê duyệt trước
        "flight_class": "phổ thông",     # Hạng vé máy bay
        "hotel_limit": 4000000,          # Giới hạn khách sạn/đêm
        "description": "Chi phí đi lại và lưu trú"
    },
    
    # 🚗 Chi phí taxi/di chuyển
    "taxi": {
        "fully_reimbursable": True,      # Hoàn trả đầy đủ
        "requires_purpose": True,        # Cần ghi rõ mục đích
        "description": "Chi phí taxi, Grab cho công việc"
    },
    
    # 🛣️ Chi phí xăng xe (theo km)
    "mileage": {
        "rate_per_km": 3000,            # Đơn giá/km (VNĐ)
        "requires_odometer": True,       # Yêu cầu ghi km
        "description": "Chi phí xăng xe cá nhân công tác"
    },
    
    # 📎 Văn phòng phẩm
    "office_supplies": {
        "monthly_limit": 2000000,        # Giới hạn hàng tháng
        "bulk_requires_approval": True,  # Mua số lượng lớn cần duyệt
        "description": "Đồ dùng văn phòng"
    },
    
    # 🅿️ Chi phí gửi xe
    "parking": {
        "fully_reimbursable": True,      # Hoàn trả đầy đủ
        "requires_receipt": True,        # Cần hóa đơn
        "description": "Chi phí gửi xe công tác"
    },
    
    # 📱 Chi phí điện thoại
    "phone": {
        "monthly_limit": 1000000,        # Giới hạn hàng tháng
        "requires_business_use": True,   # Phải dùng cho công việc
        "description": "Chi phí điện thoại công việc"
    },
    
    # 🌐 Chi phí internet
    "internet": {
        "monthly_limit": 2000000,        # Giới hạn hàng tháng
        "home_office_only": True,        # Chỉ cho home office
        "description": "Chi phí internet làm việc tại nhà"
    },
    
    # 📚 Chi phí đào tạo
    "training": {
        "max_per_year": 10000000,        # Tối đa/năm
        "requires_manager_approval": True, # Cần duyệt quản lý
        "description": "Chi phí đào tạo, khóa học"
    },
    
    # 🎪 Chi phí hội thảo
    "conference": {
        "max_per_event": 5000000,        # Tối đa/sự kiện
        "requires_manager_approval": True,
        "description": "Chi phí tham dự hội thảo, sự kiện"
    }
}

MOCK_EXPENSE_REPORTS = [
    {"employee_id": "NV123", "date": "2025-07-20", "category": "meals", "amount": 900000, "description": "Ăn trưa với khách hàng", "has_receipt": True},
    {"employee_id": "NV123", "date": "2025-07-21", "category": "taxi", "amount": 350000, "description": "Từ sân bay đến khách sạn", "has_receipt": True},
    {"employee_id": "NV123", "date": "2025-07-22", "category": "travel", "amount": 12000000, "description": "Vé máy bay đi hội nghị", "has_receipt": True},
    {"employee_id": "NV456", "date": "2025-07-18", "category": "meals", "amount": 1500000, "description": "Tiệc tối nhóm", "has_receipt": False},
    {"employee_id": "NV456", "date": "2025-07-19", "category": "office_supplies", "amount": 1800000, "description": "Hộp mực máy in", "has_receipt": True},
    {"employee_id": "NV789", "date": "2025-07-15", "category": "mileage", "amount": 450000, "description": "Thăm khách hàng - 150 km", "has_receipt": False},
    {"employee_id": "NV321", "date": "2025-07-23", "category": "parking", "amount": 50000, "description": "Phí đậu xe tại văn phòng", "has_receipt": True},
    {"employee_id": "NV654", "date": "2025-07-24", "category": "phone", "amount": 800000, "description": "Cước điện thoại tháng 7", "has_receipt": True},
    {"employee_id": "NV987", "date": "2025-07-25", "category": "internet", "amount": 1800000, "description": "Internet làm việc tại nhà", "has_receipt": True},
    {"employee_id": "NV111", "date": "2025-07-26", "category": "meals", "amount": 1200000, "description": "Ăn tối với đối tác", "has_receipt": True},
    {"employee_id": "NV222", "date": "2025-07-27", "category": "travel", "amount": 8000000, "description": "Khách sạn 2 đêm tại Đà Nẵng", "has_receipt": True},
    {"employee_id": "NV333", "date": "2025-07-28", "category": "office_supplies", "amount": 2500000, "description": "Mua giấy in số lượng lớn", "has_receipt": True},
    {"employee_id": "NV444", "date": "2025-07-29", "category": "taxi", "amount": 400000, "description": "Taxi đi họp khách hàng", "has_receipt": False},
    {"employee_id": "NV555", "date": "2025-07-30", "category": "mileage", "amount": 600000, "description": "Đi công tác - 200 km", "has_receipt": True},
    {"employee_id": "NV666", "date": "2025-07-31", "category": "meals", "amount": 700000, "description": "Ăn sáng nhóm dự án", "has_receipt": True},
    {"employee_id": "NV777", "date": "2025-08-01", "category": "parking", "amount": 70000, "description": "Phí đậu xe hội thảo", "has_receipt": False},
    {"employee_id": "NV888", "date": "2025-08-02", "category": "office_supplies", "amount": 500000, "description": "Bút, sổ tay cho phòng ban", "has_receipt": True},
    {"employee_id": "NV999", "date": "2025-08-03", "category": "travel", "amount": 15000000, "description": "Vé máy bay quốc tế", "has_receipt": True},
    {"employee_id": "NV101", "date": "2025-08-04", "category": "meals", "amount": 950000, "description": "Ăn trưa với đối tác Nhật", "has_receipt": True},
    {"employee_id": "NV202", "date": "2025-08-05", "category": "taxi", "amount": 250000, "description": "Taxi về nhà sau giờ làm", "has_receipt": False},
    {"employee_id": "NV303", "date": "2025-08-06", "category": "mileage", "amount": 90000, "description": "Đi gặp khách hàng - 30 km", "has_receipt": True},
    {"employee_id": "NV404", "date": "2025-08-07", "category": "office_supplies", "amount": 2100000, "description": "Mua máy tính cho phòng ban", "has_receipt": True},
    {"employee_id": "NV505", "date": "2025-08-08", "category": "meals", "amount": 1100000, "description": "Ăn tối nhóm phát triển sản phẩm", "has_receipt": True}
]

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
    "Tôi cần những giấy tờ gì cho chi phí đi lại?",
    "Chi phí internet làm việc tại nhà có được hoàn trả không?",
    "Tôi có thể nộp báo cáo chi phí qua điện thoại không?",
    "Có giới hạn cho chi phí điện thoại không?",
    "Chi phí đậu xe có cần hóa đơn không?",
    "Tôi có thể mua thiết bị văn phòng cho làm việc tại nhà không?",
    "Chi phí taxi về nhà sau giờ làm có được hoàn trả không?",
    "Tôi cần phê duyệt trước cho chi phí đi công tác không?",
    "Chi phí mua máy tính cho phòng ban có cần phê duyệt không?",
    "Thời gian xử lý hoàn trả là bao lâu?",
    "Tôi có thể chỉnh sửa báo cáo chi phí đã nộp không?"
]

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
    },
    {
        "question": "Chi phí internet làm việc tại nhà có được hoàn trả không?",
        "answer": "Có, chi phí internet tại nhà được hỗ trợ một phần theo quy định làm việc từ xa.",
        "category": "work_from_home",
        "keywords": ["internet", "home office", "làm việc từ xa"]
    },
    {
        "question": "Có giới hạn cho chi phí điện thoại không?",
        "answer": "Chi phí điện thoại được hoàn trả tối đa 1.000.000 VNĐ/tháng nếu sử dụng cho mục đích công việc.",
        "category": "phone_expense",
        "keywords": ["điện thoại", "phone", "giới hạn", "limit"]
    },
    {
        "question": "Chi phí đậu xe có cần hóa đơn không?",
        "answer": "Phí đậu xe tại địa điểm kinh doanh cần có hóa đơn để được hoàn trả.",
        "category": "parking_expense",
        "keywords": ["đậu xe", "parking", "hóa đơn", "receipt"]
    },
    {
        "question": "Tôi có thể mua thiết bị văn phòng cho làm việc tại nhà không?",
        "answer": "Thiết bị văn phòng tại nhà cần phê duyệt phòng IT trước khi mua.",
        "category": "office_supplies",
        "keywords": ["thiết bị", "văn phòng", "home office", "IT"]
    },
    {
        "question": "Chi phí taxi về nhà sau giờ làm có được hoàn trả không?",
        "answer": "Chi phí taxi về nhà chỉ được hoàn trả nếu có lý do công việc hoặc làm thêm ngoài giờ theo quy định.",
        "category": "taxi_expense",
        "keywords": ["taxi", "grab", "uber", "về nhà"]
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
    },
    {
        "topic": "Chính sách chi phí công tác quốc tế",
        "content": "Chi phí công tác quốc tế cần được phê duyệt trước và có giới hạn riêng cho ăn uống, khách sạn, di chuyển.",
        "category": "international_travel",
        "keywords": ["công tác quốc tế", "international", "travel", "phê duyệt"]
    },
    {
        "topic": "Quy định về làm thêm giờ",
        "content": "Nhân viên làm thêm giờ cần đăng ký trước với quản lý. Chi phí ăn uống và taxi ngoài giờ được hỗ trợ theo quy định.",
        "category": "overtime_policy",
        "keywords": ["làm thêm giờ", "overtime", "ăn uống", "taxi"]
    },
    {
        "topic": "Chính sách hỗ trợ gia đình",
        "content": "Công ty hỗ trợ một phần chi phí chăm sóc trẻ em cho nhân viên có con nhỏ dưới 6 tuổi.",
        "category": "family_support",
        "keywords": ["gia đình", "family", "trẻ em", "childcare", "hỗ trợ"]
    },
    {
        "topic": "Quy định về bảo hiểm sức khỏe",
        "content": "Nhân viên được công ty mua bảo hiểm sức khỏe toàn diện. Chi phí khám chữa bệnh ngoài danh mục cần phê duyệt.",
        "category": "health_insurance",
        "keywords": ["bảo hiểm", "health insurance", "khám bệnh", "sức khỏe"]
    },
    {
        "topic": "Chính sách thưởng hiệu suất",
        "content": "Thưởng hiệu suất được xét vào cuối năm dựa trên kết quả đánh giá KPI và đóng góp cá nhân.",
        "category": "performance_bonus",
        "keywords": ["thưởng", "bonus", "KPI", "hiệu suất", "performance"]
    }
]

def calculate_reimbursement(expenses: List[Dict]) -> Dict[str, Any]:
    """
    💰 Tính toán tổng số tiền hoàn trả dựa trên chính sách công ty
    
    Args:
        expenses: Danh sách dictionary chứa thông tin chi phí (category, amount, etc.)
        
    Returns:
        Dictionary chứa breakdown chi tiết và tổng tiền hoàn trả
    """
    breakdown = []              # Danh sách breakdown từng khoản
    total_reimbursed = 0       # Tổng tiền được hoàn trả
    total_submitted = 0        # Tổng tiền đã submit
    
    for expense in expenses:
        # 📋 Lấy thông tin cơ bản từ expense
        category = expense.get('category', '').lower()
        amount = float(expense.get('amount', 0))
        total_submitted += amount
        
        # 🔍 Áp dụng quy tắc theo từng danh mục
        if category == 'meals':
            # Chi phí ăn uống - có giới hạn hàng ngày
            daily_limit = EXPENSE_CATEGORIES['meals']['daily_limit']
            reimbursed = min(amount, daily_limit)
            note = f"Giới hạn {daily_limit:,.0f} VNĐ/ngày" if amount > daily_limit else "Hoàn trả đầy đủ"
            
        elif category == 'taxi':
            # Chi phí taxi - hoàn trả đầy đủ
            reimbursed = amount
            note = "Hoàn trả đầy đủ"
            
        elif category == 'travel':
            # Chi phí đi lại - hoàn trả đầy đủ (giả sử đã được phê duyệt)
            reimbursed = amount
            note = "Hoàn trả đầy đủ (giả sử đã được phê duyệt)"
            
        elif category == 'mileage':
            # Chi phí xăng xe - tính theo km
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
            # Văn phòng phẩm - có giới hạn hàng tháng
            monthly_limit = EXPENSE_CATEGORIES['office_supplies']['monthly_limit']
            reimbursed = min(amount, monthly_limit)
            note = f"Giới hạn {monthly_limit:,.0f} VNĐ/tháng" if amount > monthly_limit else "Hoàn trả đầy đủ"
            
        elif category == 'parking':
            # Chi phí gửi xe - hoàn trả đầy đủ
            reimbursed = amount
            note = "Hoàn trả đầy đủ"
            
        else:
            # Danh mục không nhận dạng được
            reimbursed = 0
            note = "Danh mục không được nhận dạng - cần xem xét thủ công"
        
        total_reimbursed += reimbursed
        
        # 📊 Thêm vào breakdown
        breakdown.append({
            "category": expense.get('category'),
            "amount_submitted": amount,
            "amount_reimbursed": reimbursed,
            "note": note
        })
    
    # 📈 Trả về kết quả tổng hợp
    return {
        "breakdown": breakdown,
        "total_submitted": total_submitted,
        "total_reimbursed": total_reimbursed,
        "savings": total_submitted - total_reimbursed  # Số tiền tiết kiệm cho công ty
    }

def validate_expense(expense: Dict) -> Dict[str, Any]:
    """
    🔍 Xác thực một mục chi phí theo chính sách công ty
    
    Args:
        expense: Dictionary chứa thông tin chi phí cần xác thực
        
    Returns:
        Dictionary chứa kết quả validation và cảnh báo
    """
    warnings = []    # Danh sách cảnh báo (không block nhưng cần lưu ý)
    errors = []      # Danh sách lỗi (block chi phí)
    
    # 📋 Lấy thông tin cơ bản
    category = expense.get('category', '').lower()
    amount = float(expense.get('amount', 0))
    has_receipt = expense.get('has_receipt', False)
    date_str = expense.get('date', '')
    
    # 🧾 Kiểm tra yêu cầu hóa đơn
    if amount > 500000 and not has_receipt:
        errors.append(f"⚠️ Yêu cầu hóa đơn cho chi phí trên 500.000 VNĐ (số tiền: {amount:,.0f} VNĐ)")
    
    # 📅 Kiểm tra tính hợp lệ của ngày (trong vòng 30 ngày)
    try:
        expense_date = datetime.strptime(date_str, '%Y-%m-%d')
        days_old = (datetime.now() - expense_date).days
        if days_old > 30:
            warnings.append(f"📆 Chi phí đã {days_old} ngày tuổi - báo cáo nên được nộp trong vòng 30 ngày")
    except ValueError:
        errors.append("❌ Định dạng ngày không hợp lệ - sử dụng YYYY-MM-DD")
    
    # 🔍 Validation theo từng danh mục
    if category == 'meals' and amount > EXPENSE_CATEGORIES['meals']['daily_limit']:
        warnings.append(f"🍽️ Chi phí ăn uống {amount:,.0f} VNĐ vượt quá giới hạn hàng ngày {EXPENSE_CATEGORIES['meals']['daily_limit']:,.0f} VNĐ")
    
    if category == 'travel':
        if not expense.get('pre_approved', False):
            warnings.append("✈️ Chi phí đi lại cần phê duyệt trước")
    
    if category == 'office_supplies' and amount > EXPENSE_CATEGORIES['office_supplies']['monthly_limit']:
        warnings.append(f"📎 Chi phí văn phòng phẩm {amount:,.0f} VNĐ vượt quá giới hạn hàng tháng {EXPENSE_CATEGORIES['office_supplies']['monthly_limit']:,.0f} VNĐ")
    
    # 📊 Trả về kết quả validation
    return {
        "is_valid": len(errors) == 0,                # True nếu không có lỗi
        "warnings": warnings,                         # Danh sách cảnh báo
        "errors": errors,                            # Danh sách lỗi
        "requires_manager_approval": len(errors) > 0 or ('travel' in category and not expense.get('pre_approved', False))
    }

def search_policies(query: str) -> List[str]:
    """
    🔍 Tìm kiếm chính sách chi phí dựa trên câu hỏi của user
    
    Args:
        query: Câu hỏi hoặc từ khóa tìm kiếm của user
        
    Returns:
        Danh sách các chính sách liên quan
    """
    query_lower = query.lower()
    relevant_policies = []
    
    # 🗂️ Mapping từ khóa với danh mục chính sách
    keyword_mapping = {
        # Từ khóa về hóa đơn
        'hóa đơn': 'receipts', 'receipt': 'receipts', 'bill': 'receipts',
        
        # Từ khóa về ăn uống
        'ăn': 'meals', 'meal': 'meals', 'thức ăn': 'meals', 'food': 'meals',
        'trưa': 'meals', 'lunch': 'meals', 'tối': 'meals', 'dinner': 'meals',
        'sáng': 'meals', 'breakfast': 'meals', 'rượu': 'meals', 'bia': 'meals',
        
        # Từ khóa về đi lại
        'đi lại': 'travel', 'travel': 'travel', 'công tác': 'travel',
        'máy bay': 'travel', 'flight': 'travel', 'khách sạn': 'travel', 'hotel': 'travel',
        
        # Từ khóa về di chuyển
        'taxi': 'transportation', 'grab': 'transportation', 'uber': 'transportation',
        'xăng': 'transportation', 'mileage': 'transportation', 'xe': 'transportation',
        
        # Từ khóa về văn phòng phẩm
        'văn phòng': 'office_supplies', 'office': 'office_supplies',
        'phẩm': 'office_supplies', 'supplies': 'office_supplies',
        
        # Từ khóa về deadline
        'hạn': 'deadlines', 'deadline': 'deadlines', 'nộp': 'deadlines', 'submit': 'deadlines'
    }
    
    # 🎯 Tìm các danh mục phù hợp
    matched_categories = set()
    for keyword, category in keyword_mapping.items():
        if keyword in query_lower:
            matched_categories.add(category)
    
    # 📂 Nếu không tìm thấy từ khóa cụ thể, tìm kiếm tất cả
    if not matched_categories:
        matched_categories = set(EXPENSE_POLICIES.keys())
    
    # 📋 Thu thập các chính sách liên quan
    for category in matched_categories:
        if category in EXPENSE_POLICIES:
            relevant_policies.extend(EXPENSE_POLICIES[category])
    
    return relevant_policies[:5]  # Giới hạn top 5 kết quả liên quan nhất

def format_expense_summary(expenses: List[Dict]) -> str:
    """
    📊 Format danh sách chi phí thành tóm tắt dễ đọc
    
    Args:
        expenses: Danh sách dictionary chứa thông tin chi phí
        
    Returns:
        String summary đã được format
    """
    if not expenses:
        return "❌ Không tìm thấy chi phí."
    
    summary = f"📊 **Tóm Tắt Chi Phí** ({len(expenses)} mục)\n\n"
    
    total = 0
    by_category = {}
    
    # 🔢 Tính toán tổng và phân theo danh mục
    for expense in expenses:
        category = expense.get('category', 'Không xác định')
        amount = float(expense.get('amount', 0))
        total += amount
        
        if category not in by_category:
            by_category[category] = 0
        by_category[category] += amount
    
    # 📈 Breakdown theo danh mục
    summary += "**📂 Theo Danh Mục:**\n"
    for category, amount in sorted(by_category.items()):
        summary += f"  • {category.title()}: {amount:,.0f} VNĐ\n"
    
    summary += f"\n💰 **Tổng Số Tiền:** {total:,.0f} VNĐ\n"
    
    return summary

# 🔧 CẤU HÌNH FUNCTION CALLING CHO OPENAI
# Dictionary chứa các function có thể gọi
AVAILABLE_FUNCTIONS = {
    "calculate_reimbursement": calculate_reimbursement,    # Tính hoàn trả
    "validate_expense": validate_expense,                  # Xác thực chi phí
    "search_policies": search_policies,                    # Tìm kiếm chính sách
    "format_expense_summary": format_expense_summary       # Format tóm tắt
}

# 📋 Schema cho OpenAI Function Calling
FUNCTION_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_reimbursement",
            "description": "💰 Tính tổng số tiền hoàn trả từ danh sách chi phí dựa trên chính sách công ty",
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
