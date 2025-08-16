# Ứng dụng Web Tối Ưu cho Trợ Lý Báo Cáo Chi Phí với Hybrid Memory
"""
Ứng dụng web Flask tối ưu hóa với hybrid memory integration
và tính năng reimbursement analysis hoàn chỉnh.
"""

import os
# 🔧 Fix OpenMP conflict - PHẢI ĐẶT TRƯỚC KHI IMPORT BẤT KỲ THƯ VIỆN NÀO
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import uuid
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS

from database import ExpenseDB
from expense_assistant import ExpenseAssistant, create_client
from functions import EXPENSE_POLICIES, MOCK_EXPENSE_REPORTS, SAMPLE_USER_QUERIES, calculate_reimbursement, validate_expense
from text_to_speech import text_to_speech as tts

# ========================================
# 🧠 ENHANCED MEMORY SYSTEM (INTEGRATED)
# ========================================

logger = logging.getLogger(__name__)

# Global enhanced memory store
ENHANCED_MEMORY_STORE = {
    "users": {},  # user_id -> {"expenses": [], "sessions": {}}
    "guest_sessions": {}  # session_id -> {"expenses": [], "created_at": datetime}
}

class EnhancedMemorySystem:
    """🧠 Enhanced Memory System integrated directly into web app"""
    
    def __init__(self, database=None):
        self.store = ENHANCED_MEMORY_STORE
        self.db = database  # ChromaDB instance for persistence
        logger.info("🧠 Enhanced Memory System initialized")
        
        # Load existing data from ChromaDB if available
        if self.db:
            self._load_all_data_from_chromadb()
    
    def _load_all_data_from_chromadb(self):
        """Load all user and session data from ChromaDB on startup"""
        try:
            if not self.db:
                logger.warning("⚠️ No database instance available for loading data")
                return
                
            # Load all users
            all_users = self.db.load_all_users()
            
            # Validate and update store
            for account, user_data in all_users.items():
                # Ensure user data has required structure
                if not isinstance(user_data, dict):
                    logger.warning(f"⚠️ Invalid user data structure for {account}")
                    continue
                    
                # Set defaults if missing
                if "expenses" not in user_data:
                    user_data["expenses"] = []
                if "sessions" not in user_data:
                    user_data["sessions"] = {}
                if "created_at" not in user_data:
                    user_data["created_at"] = datetime.now().isoformat()
                    
                self.store["users"][account] = user_data
            
            logger.info(f"🔄 Successfully loaded {len(all_users)} users from ChromaDB")
            
            # Note: Guest sessions are typically short-lived, so we don't restore them
            # But we could add this logic if needed
            
        except Exception as e:
            logger.error(f"❌ Error loading data from ChromaDB: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _save_user_to_chromadb(self, account: str):
        """Save user data to ChromaDB for persistence"""
        if not self.db:
            logger.warning("⚠️ No database instance available for saving user data")
            return False
            
        try:
            user_data = self.store["users"].get(account)
            if user_data:
                success = self.db.save_user_data(account, user_data)
                if success:
                    logger.info(f"✅ User data saved to ChromaDB: {account}")
                else:
                    logger.error(f"❌ Failed to save user data to ChromaDB: {account}")
                return success
            else:
                logger.warning(f"⚠️ No user data found for account: {account}")
            return False
        except Exception as e:
            logger.error(f"❌ Error saving user to ChromaDB: {str(e)}")
            return False
    
    def _save_guest_session_to_chromadb(self, session_id: str):
        """Save guest session to ChromaDB for persistence"""
        if not self.db:
            return False
            
        try:
            session_data = self.store["guest_sessions"].get(session_id)
            if session_data:
                return self.db.save_guest_session(session_id, session_data)
            return False
        except Exception as e:
            logger.error(f"❌ Error saving guest session to ChromaDB: {str(e)}")
            return False
    
    def safe_login_user(self, account: str) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        """Safe user login with expense context loading"""
        try:
            if not account or not account.strip():
                return None, None, "Account không được để trống"
            
            account = account.strip().lower()
            session_id = f"user_{account}_{uuid.uuid4().hex[:8]}"
            
            # Initialize user data if not exists
            if account not in self.store["users"]:
                self.store["users"][account] = {
                    "expenses": [],
                    "sessions": {},
                    "created_at": datetime.now().isoformat()
                }
            
            # Load expense summary
            user_data = self.store["users"][account]
            expense_summary = self._calculate_user_summary(account)
            
            # Create user info
            user_info = {
                'session_id': session_id,
                'user_type': 'logged_in',
                'account': account,
                'created_at': datetime.now(),
                'last_activity': datetime.now(),
                'expense_summary': expense_summary,
                'stats': {
                    'messages_count': 0,
                    'total_expenses': len(user_data["expenses"]),
                    'total_expense_amount': sum(exp.get('amount', 0) for exp in user_data["expenses"])
                }
            }
            
            # 💾 Auto-save user data to ChromaDB after login
            self._save_user_to_chromadb(account)
            
            logger.info(f"🔓 User logged in successfully: {account}")
            return session_id, user_info, None
            
        except Exception as e:
            error_msg = f"Lỗi đăng nhập: {str(e)}"
            logger.error(f"❌ Login error for {account}: {str(e)}")
            return None, None, error_msg
    
    def safe_logout_user(self, session_id: str) -> Tuple[bool, Optional[str]]:
        """Safe user logout with data persistence"""
        try:
            # Extract account from session_id if it's a user session
            account = None
            if session_id.startswith("user_"):
                parts = session_id.split("_")
                if len(parts) >= 2:
                    account = parts[1]
            
            if account and account in self.store["users"]:
                logger.info(f"🔒 User logged out successfully: {account}")
            else:
                logger.info(f"🔒 Session ended: {session_id}")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Lỗi đăng xuất: {str(e)}"
            logger.error(f"❌ Logout error: {str(e)}")
            return False, error_msg
    
    def safe_chat_endpoint(self, session_id: str, message: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Safe chat endpoint with enhanced memory integration"""
        try:
            # Parse session info
            account = None
            user_type = "guest"
            
            # Extract account from session_id if it's a user session
            if session_id.startswith("user_"):
                account_part = session_id.split("_")[1]
                if account_part and account_part in self.store["users"]:
                    account = account_part
                    user_type = "logged_in"
            
            # 1. Check for expense messages
            if self._is_expense_message(message):
                captured_expenses = self._extract_expenses_from_message(message)
                
                if captured_expenses:
                    # Validate and store expenses
                    validation_results = []
                    for expense in captured_expenses:
                        # Validate expense against policies
                        validation = self._validate_expense_with_policy(
                            expense, 
                            account=account if user_type == "logged_in" else None,
                            session_id=session_id if user_type != "logged_in" else None
                        )
                        validation_results.append(validation)
                        
                        # Store expense regardless of validation (but note issues)
                        if user_type == "logged_in" and account:
                            self._add_expense_to_user(account, expense)
                        else:
                            self._add_expense_to_guest(session_id, expense)
                    
                    # Get summary for response
                    if user_type == "logged_in" and account:
                        summary = self._calculate_user_summary(account)
                    else:
                        guest_expenses = self.store["guest_sessions"].get(session_id, {}).get("expenses", [])
                        summary = {
                            "total_expenses": len(guest_expenses),
                            "total_amount": sum(exp.get('amount', 0) for exp in guest_expenses)
                        }
                    
                    # Build response with validation info
                    if len(captured_expenses) == 1:
                        exp = captured_expenses[0]
                        validation = validation_results[0]
                        
                        response = f"✅ {exp.get('amount', 0):,.0f} VND - {exp.get('category', 'other').title()}"
                        response += f" (Ngày: {exp.get('date')})"
                        
                        # Add validation warnings
                        if validation.get('warnings'):
                            response += f"\n\n⚠️ CẢNH BÁO:\n"
                            for warning in validation['warnings']:
                                response += f"• {warning}\n"
                        
                        # Add reimbursement info for meals with limits
                        if exp.get('category') == 'meals':
                            if validation.get('daily_limit_exceeded'):
                                daily_total_reimbursable = validation.get('daily_reimbursable_total', 0)
                                response += f"\n💰 Tổng số tiền được hoàn trả hôm nay: {daily_total_reimbursable:,.0f} VND"
                            else:
                                # No limit exceeded, show full reimbursement
                                reimbursable = validation.get('current_expense_reimbursable', exp.get('amount', 0))
                                response += f"\n💰 Số tiền được hoàn trả: {reimbursable:,.0f} VND"
                        
                    else:
                        # Multiple expenses - show detailed breakdown
                        response = f"✅ {len(captured_expenses)} khoản chi phí đã được ghi nhận:\n\n"
                        
                        total_expense_amount = 0
                        any_warnings = False
                        
                        for i, (exp, validation) in enumerate(zip(captured_expenses, validation_results), 1):
                            amount = exp.get('amount', 0)
                            total_expense_amount += amount
                            expense_type = exp.get('expense_type', 'Chi phí')  # Use new expense_type field
                            
                            response += f"{i}. {expense_type}: {amount:,.0f} VND\n"
                            
                            if validation.get('warnings'):
                                any_warnings = True
                        
                        # Add summary warnings for multiple expenses 
                        if any_warnings:
                            # Check if daily limit exceeded for MEALS only
                            meals_total = sum(exp.get('amount', 0) for exp in captured_expenses 
                                            if exp.get('category') == 'meals')
                            if meals_total > 1000000:  # meals daily limit
                                response += f"\n⚠️ CẢNH BÁO:\n"
                                response += f"• 🍽️ Tổng chi phí ăn uống hôm nay: {meals_total:,.0f} VND vượt giới hạn 1,000,000 VND\n"
                                response += f"• Số tiền được hoàn trả (meals): 1,000,000 VND (giới hạn hàng ngày)\n"
                                response += f"• Số tiền vượt: {meals_total - 1000000:,.0f} VND\n"
                    
                    response += f"\n📊 Tổng: {summary['total_expenses']} khoản - {summary['total_amount']:,.0f} VND"
                    
                    # Check if this is also a policy question (hybrid case)
                    rag_keywords = ['chính sách', 'policy', 'quy định', 'hướng dẫn', 'giới hạn', 'limit', 
                                   'hóa đơn', 'invoice', 'thủ tục', 'procedure', 'how', 'làm thế nào',
                                   'thuộc vào', 'loại nào', 'được phép', 'có thể', 'phân loại']
                    
                    has_policy_question = any(keyword in message.lower() for keyword in rag_keywords)
                    
                    if has_policy_question and RAG_AVAILABLE:
                        # This is a HYBRID case: expense + policy question
                        try:
                            from rag_integration import get_rag_integration
                            rag_integration = get_rag_integration()
                            rag_response = rag_integration.get_rag_response(message, use_hybrid=True)
                            
                            if rag_response and rag_response.get("content"):
                                # Combine expense response + policy answer
                                response += f"\n\n📋 **Về chính sách:**\n{rag_response.get('content')}"
                                
                                return {
                                    "success": True,
                                    "response": response,
                                    "type": "hybrid_expense_policy",
                                    "rag_used": True,
                                    "sources": rag_response.get("sources", []),
                                    "expense_data": {
                                        "new_expenses": captured_expenses, 
                                        "summary": summary,
                                        "validation_results": validation_results
                                    },
                                    "memory_optimized": True,
                                    "user_type": user_type,
                                    "storage_type": "enhanced_memory"
                                }, None
                        except Exception as e:
                            logger.warning(f"RAG query failed in hybrid case: {str(e)}")
                    
                    # Regular expense response (no policy question)
                    
                    return {
                        "success": True,
                        "response": response,
                        "type": "expense_declaration",
                        "rag_used": False,
                        "expense_data": {
                            "new_expenses": captured_expenses, 
                            "summary": summary,
                            "validation_results": validation_results
                        },
                        "memory_optimized": True,
                        "user_type": user_type,
                        "storage_type": "enhanced_memory"
                    }, None
            
            # 2. Check for report requests
            if self._is_report_request(message):
                # Extract month filter from message
                month_filter = self._extract_month_filter(message)
                
                if user_type == "logged_in" and account:
                    # Get all expenses first
                    all_expenses = self.store["users"].get(account, {}).get("expenses", [])
                    
                    # Apply month filter if specified
                    filtered_expenses = self._filter_expenses_by_month(all_expenses, month_filter)
                    
                    # Generate context and summary with filtered data
                    expense_context = self._get_expense_context_with_filter(account=account, month_filter=month_filter)
                    summary = self._calculate_summary_from_expenses(filtered_expenses)
                else:
                    # Guest expenses
                    all_expenses = self.store["guest_sessions"].get(session_id, {}).get("expenses", [])
                    filtered_expenses = self._filter_expenses_by_month(all_expenses, month_filter)
                    
                    expense_context = self._get_expense_context_with_filter(session_id=session_id, month_filter=month_filter)
                    summary = self._calculate_summary_from_expenses(filtered_expenses)
                
                # Build report response
                if summary["total_expenses"] == 0:
                    if month_filter:
                        month_year = month_filter.replace('-', '/')
                        report = f"📊 Báo cáo chi phí tháng {month_year}:\n\nBạn chưa kê khai chi phí nào cho tháng này."
                    else:
                        report = "📊 Báo cáo chi phí:\n\nBạn chưa kê khai chi phí nào. Hãy bắt đầu kê khai để tôi có thể tạo báo cáo cho bạn!"
                else:
                    if month_filter:
                        month_year = month_filter.replace('-', '/')
                        report_title = f"📊 Báo cáo chi phí tháng {month_year}:"
                    else:
                        report_title = "📊 Báo cáo chi phí:"
                    
                    report = f"""{report_title}

{expense_context}

💰 Tổng chi phí: {summary['total_amount']:,.0f} VND
📋 Số khoản: {summary['total_expenses']} khoản chi phí"""
                
                return {
                    "success": True,
                    "response": report,
                    "type": "expense_report",
                    "rag_used": False,
                    "expense_data": {"summary": summary, "month_filter": month_filter},
                    "memory_optimized": True,
                    "user_type": user_type,
                    "storage_type": "enhanced_memory"
                }, None
            
            # 3. Check for RAG queries first before general AI response
            # Detect if this is a knowledge/policy query that should use RAG
            rag_keywords = ['chính sách', 'policy', 'quy định', 'hướng dẫn', 'giới hạn', 'limit', 
                           'hóa đơn', 'invoice', 'thủ tục', 'procedure', 'how', 'làm thế nào']
            
            should_use_rag = any(keyword in message.lower() for keyword in rag_keywords)
            
            if should_use_rag and RAG_AVAILABLE:
                try:
                    from rag_integration import get_rag_integration
                    rag_integration = get_rag_integration()
                    rag_response = rag_integration.get_rag_response(message, use_hybrid=True)
                    
                    if rag_response and rag_response.get("content"):
                        return {
                            "success": True,
                            "response": rag_response.get("content"),
                            "type": "rag_response",
                            "rag_used": True,
                            "sources": rag_response.get("sources", []),
                            "memory_optimized": True,
                            "user_type": user_type,
                            "storage_type": "enhanced_memory"
                        }, None
                except Exception as e:
                    logger.warning(f"RAG query failed, falling back to AI: {str(e)}")
            
            # 4. General AI response with context
            if user_type == "logged_in" and account:
                expense_context = self._get_expense_context(account=account)
                session_info = {"session_id": session_id, "account": account, "user_type": user_type}
            else:
                expense_context = self._get_expense_context(session_id=session_id)
                session_info = {"session_id": session_id, "user_type": user_type}
            
            ai_response = self._get_ai_response_with_context(message, expense_context, session_info)
            
            return {
                "success": True,
                "response": ai_response,
                "type": "ai_response",
                "rag_used": False,
                "memory_optimized": True,
                "user_type": user_type,
                "storage_type": "enhanced_memory",
                "expense_context_available": len(expense_context) > 50
            }, None
            
        except Exception as e:
            error_msg = f"Lỗi xử lý chat: {str(e)}"
            logger.error(f"❌ Chat error: {str(e)}")
            return None, error_msg
    
    def _validate_expense_with_policy(self, expense: Dict, account: str = None, session_id: str = None) -> Dict:
        """Validate expense against company policies and daily limits"""
        
        # Basic validation using functions.py
        validation_result = validate_expense(expense)
        
        # Additional daily limit validation for meals
        if expense.get('category') == 'meals':
            daily_limit = 1000000  # 1M VND per day
            expense_date = expense.get('date', datetime.now().strftime('%Y-%m-%d'))
            expense_amount = expense.get('amount', 0)
            
            # Get existing expenses for the same date
            existing_daily_total = 0
            if account:
                user_data = self.store["users"].get(account, {})
                user_expenses = user_data.get("expenses", [])
            else:
                guest_data = self.store["guest_sessions"].get(session_id, {})
                user_expenses = guest_data.get("expenses", [])
            
            # Calculate total for the same date and category
            for exp in user_expenses:
                if exp.get('date') == expense_date and exp.get('category') == 'meals':
                    existing_daily_total += exp.get('amount', 0)
            
            # Add current expense to daily total
            new_daily_total = existing_daily_total + expense_amount
            
            # Check daily limit
            if new_daily_total > daily_limit:
                excess_amount = new_daily_total - daily_limit
                validation_result['warnings'].append(
                    f"🍽️ Chi phí ăn uống ngày {expense_date} vượt giới hạn {daily_limit:,.0f} VND. "
                    f"Tổng: {new_daily_total:,.0f} VND (vượt {excess_amount:,.0f} VND). "
                    f"Chỉ hoàn trả tối đa {daily_limit:,.0f} VND/ngày."
                )
                validation_result['daily_limit_exceeded'] = True
                validation_result['excess_amount'] = excess_amount
                # Total reimbursable amount for the day (capped at daily limit)
                validation_result['daily_reimbursable_total'] = daily_limit
                # This specific expense's reimbursable portion
                validation_result['current_expense_reimbursable'] = min(expense_amount, daily_limit - existing_daily_total)
            else:
                # No limit exceeded, full amount reimbursable
                validation_result['daily_reimbursable_total'] = new_daily_total
                validation_result['current_expense_reimbursable'] = expense_amount
        
        return validation_result
    
    def _get_expense_date_from_message(self, message: str) -> str:
        """Extract date from natural language in message"""
        today = datetime.now()
        message_lower = message.lower()
        
        # First check for explicit date formats
        import re
        
        # Pattern for YYYY/MM/DD, YYYY-MM-DD
        date_patterns = [
            r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})',  # 2025/07/15 or 2025-07-15
            r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',  # 15/07/2025 or 15-07-2025
            r'ngày\s+(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})',  # ngày 2025/07/15
            r'ngày\s+(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',  # ngày 15/07/2025
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, message)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        # Determine if it's YYYY/MM/DD or DD/MM/YYYY format
                        if len(groups[0]) == 4:  # YYYY/MM/DD
                            year, month, day = groups
                        else:  # DD/MM/YYYY
                            day, month, year = groups
                        
                        # Validate and format
                        year = int(year)
                        month = int(month)
                        day = int(day)
                        
                        # Basic validation
                        if 1 <= month <= 12 and 1 <= day <= 31 and 2020 <= year <= 2030:
                            target_date = datetime(year, month, day)
                            return target_date.strftime('%Y-%m-%d')
                except (ValueError, IndexError):
                    continue
        
        # If no explicit date found, check for relative date patterns
        if 'hôm qua' in message_lower or 'yesterday' in message_lower:
            target_date = today - timedelta(days=1)
        elif 'hôm kia' in message_lower or 'day before yesterday' in message_lower:
            target_date = today - timedelta(days=2)
        elif 'tuần trước' in message_lower or 'last week' in message_lower:
            target_date = today - timedelta(days=7)
        elif 'tối qua' in message_lower:
            # "tối qua" could mean yesterday evening
            target_date = today - timedelta(days=1)
        elif 'sáng qua' in message_lower:
            # "sáng qua" could mean yesterday morning  
            target_date = today - timedelta(days=1)
        else:
            # Default to today
            target_date = today
            
        return target_date.strftime('%Y-%m-%d')
        """Get formatted expense context for AI prompts"""
        return self._get_expense_context(account=account, session_id=session_id)
    
    # Helper methods
    def _add_expense_to_user(self, account: str, expense_data: Dict) -> bool:
        """Add expense to user account"""
        try:
            if account not in self.store["users"]:
                self.store["users"][account] = {"expenses": [], "sessions": {}}
            
            expense_entry = {
                **expense_data,
                "id": f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
                "timestamp": datetime.now().isoformat()
            }
            
            self.store["users"][account]["expenses"].append(expense_entry)
            logger.info(f"💾 Added expense for {account}: {expense_data.get('amount', 0):,.0f} VND")
            
            # 💾 Auto-save to ChromaDB after adding expense
            self._save_user_to_chromadb(account)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding expense: {str(e)}")
            return False
    
    def _add_expense_to_guest(self, session_id: str, expense_data: Dict) -> bool:
        """Add expense to guest session"""
        try:
            if session_id not in self.store["guest_sessions"]:
                self.store["guest_sessions"][session_id] = {
                    "expenses": [],
                    "created_at": datetime.now().isoformat()
                }
            
            expense_entry = {
                **expense_data,
                "id": f"guest_exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
                "timestamp": datetime.now().isoformat()
            }
            
            self.store["guest_sessions"][session_id]["expenses"].append(expense_entry)
            logger.info(f"💾 Added guest expense for {session_id}: {expense_data.get('amount', 0):,.0f} VND")
            
            # 💾 Auto-save to ChromaDB after adding guest expense
            self._save_guest_session_to_chromadb(session_id)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding guest expense: {str(e)}")
            return False
    
    def _calculate_daily_reimbursements(self, expenses: List[Dict]) -> Dict:
        """Calculate reimbursements with proper daily limits"""
        
        # Group expenses by date and category
        daily_expenses = {}
        for exp in expenses:
            date = exp.get('date', datetime.now().strftime('%Y-%m-%d'))
            category = exp.get('category', 'other')
            
            if date not in daily_expenses:
                daily_expenses[date] = {}
            if category not in daily_expenses[date]:
                daily_expenses[date][category] = []
                
            daily_expenses[date][category].append(exp)
        
        # Calculate reimbursements with daily limits
        total_reimbursement = 0
        total_expenses = 0
        daily_breakdown = {}
        
        for date, categories in daily_expenses.items():
            daily_breakdown[date] = {}
            
            for category, day_expenses in categories.items():
                daily_total = sum(exp.get('amount', 0) for exp in day_expenses)
                total_expenses += daily_total
                
                # Apply daily limits
                if category == 'meals':
                    daily_limit = 1000000  # 1M VND per day for meals
                    reimbursable = min(daily_total, daily_limit)
                else:
                    reimbursable = daily_total  # No limit for other categories
                
                total_reimbursement += reimbursable
                daily_breakdown[date][category] = {
                    'total': daily_total,
                    'reimbursable': reimbursable,
                    'expenses': day_expenses,
                    'limit_exceeded': daily_total > daily_limit if category == 'meals' else False
                }
        
        return {
            'total_expenses': total_expenses,
            'total_reimbursement': total_reimbursement,
            'daily_breakdown': daily_breakdown,
            'savings_for_company': total_expenses - total_reimbursement
        }
    
    def _calculate_summary_from_expenses(self, expenses: List[Dict]) -> Dict:
        """Calculate summary from a list of expenses"""
        return {
            "total_expenses": len(expenses),
            "total_amount": sum(exp.get('amount', 0) for exp in expenses)
        }
    
    def _get_expense_context_with_filter(self, account: str = None, session_id: str = None, month_filter: str = None) -> str:
        """Generate expense context string with optional month filter"""
        try:
            expenses = []
            
            if account and account in self.store["users"]:
                expenses = self.store["users"][account]["expenses"]
            elif session_id and session_id in self.store["guest_sessions"]:
                expenses = self.store["guest_sessions"][session_id]["expenses"]
            
            # Apply month filter
            if month_filter:
                expenses = self._filter_expenses_by_month(expenses, month_filter)
            
            if not expenses:
                if month_filter:
                    month_year = month_filter.replace('-', '/')
                    return f"Không có chi phí nào trong tháng {month_year}."
                else:
                    return "Người dùng chưa kê khai chi phí nào."
            
            # Calculate proper reimbursements with daily limits
            reimbursement_data = self._calculate_daily_reimbursements(expenses)
            
            # Format context with accurate reimbursement info
            context_lines = []
            
            if month_filter:
                month_year = month_filter.replace('-', '/')
                context_lines.append(f"📊 TỔNG QUAN CHI PHÍ THÁNG {month_year}:")
            else:
                context_lines.append("📊 TỔNG QUAN CHI PHÍ ĐÃ KÊ KHAI:")
            
            context_lines.extend([
                f"• Tổng cộng: {len(expenses)} khoản chi phí",
                f"• Tổng chi phí: {reimbursement_data['total_expenses']:,.0f} VND",
                f"• Tổng hoàn trả: {reimbursement_data['total_reimbursement']:,.0f} VND",
                f"• Tiết kiệm cho công ty: {reimbursement_data['savings_for_company']:,.0f} VND",
                "",
                "📋 BREAKDOWN THEO NGÀY (VỚI GIỚI HẠN HOÀN TRẢ):"
            ])
            
            # Show daily breakdown with limits
            for date, categories in reimbursement_data['daily_breakdown'].items():
                context_lines.append(f"\n📅 {date}:")
                for category, data in categories.items():
                    total = data['total']
                    reimbursable = data['reimbursable']
                    limit_exceeded = data['limit_exceeded']
                    
                    if limit_exceeded:
                        context_lines.append(f"  • {category.title()}: {total:,.0f} VND → Hoàn trả: {reimbursable:,.0f} VND (giới hạn)")
                    else:
                        context_lines.append(f"  • {category.title()}: {total:,.0f} VND → Hoàn trả: {reimbursable:,.0f} VND")
            
            context_lines.extend([
                "",
                "⚠️ LƯU Ý: Chi phí ăn uống có giới hạn 1,000,000 VND/ngày.",
                "Các chi phí khác hoàn trả đầy đủ theo chính sách công ty."
            ])
            
            return "\n".join(context_lines)
            
        except Exception as e:
            logger.error(f"❌ Error generating expense context with filter: {str(e)}")
            return "Lỗi khi tải thông tin chi phí."
    
    def _get_expense_context(self, account: str = None, session_id: str = None) -> str:
        """Generate expense context string for AI prompts with proper reimbursement calculation"""
        try:
            expenses = []
            
            if account and account in self.store["users"]:
                expenses = self.store["users"][account]["expenses"]
            elif session_id and session_id in self.store["guest_sessions"]:
                expenses = self.store["guest_sessions"][session_id]["expenses"]
            
            if not expenses:
                return "Người dùng chưa kê khai chi phí nào."
            
            # Calculate proper reimbursements with daily limits
            reimbursement_data = self._calculate_daily_reimbursements(expenses)
            
            # Format context with accurate reimbursement info
            context_lines = [
                "📊 TỔNG QUAN CHI PHÍ ĐÃ KÊ KHAI:",
                f"• Tổng cộng: {len(expenses)} khoản chi phí",
                f"• Tổng chi phí: {reimbursement_data['total_expenses']:,.0f} VND",
                f"• Tổng hoàn trả: {reimbursement_data['total_reimbursement']:,.0f} VND",
                f"• Tiết kiệm cho công ty: {reimbursement_data['savings_for_company']:,.0f} VND",
                "",
                "📋 BREAKDOWN THEO NGÀY (VỚI GIỚI HẠN HOÀN TRẢ):"
            ]
            
            # Show daily breakdown with limits
            for date, categories in reimbursement_data['daily_breakdown'].items():
                context_lines.append(f"\n📅 {date}:")
                for category, data in categories.items():
                    total = data['total']
                    reimbursable = data['reimbursable']
                    limit_exceeded = data['limit_exceeded']
                    
                    if limit_exceeded:
                        context_lines.append(f"  • {category.title()}: {total:,.0f} VND → Hoàn trả: {reimbursable:,.0f} VND (giới hạn)")
                    else:
                        context_lines.append(f"  • {category.title()}: {total:,.0f} VND → Hoàn trả: {reimbursable:,.0f} VND")
            
            context_lines.extend([
                "",
                "⚠️ LƯU Ý: Chi phí ăn uống có giới hạn 1,000,000 VND/ngày.",
                "Các chi phí khác hoàn trả đầy đủ theo chính sách công ty."
            ])
            
            return "\n".join(context_lines)
            
        except Exception as e:
            logger.error(f"❌ Error generating expense context: {str(e)}")
            return "Lỗi khi tải thông tin chi phí."
    
    def _calculate_user_summary(self, account: str) -> Dict:
        """Calculate user expense summary"""
        if account not in self.store["users"]:
            return {"total_expenses": 0, "total_amount": 0}
        
        expenses = self.store["users"][account]["expenses"]
        return {
            "total_expenses": len(expenses),
            "total_amount": sum(exp.get('amount', 0) for exp in expenses)
        }
    
    def _is_expense_message(self, message: str) -> bool:
        """Check if message contains expense declaration"""
        expense_keywords = [
            'chi phí', 'chi tiêu', 'kê khai',
            'ăn', 'uống', 'taxi', 'xe', 'hotel', 'khách sạn',
            'văn phòng phẩm', 'cafe', 'cà phê', 'xăng',
            'sáng', 'trưa', 'tối', 'food'
        ]
        
        amount_patterns = [
            r'\d+\s*tr(?!\w)',  # 2tr
            r'\d+\s*triệu',     # 2 triệu  
            r'\d+\s*[ktKT]',    # 50k
            r'\d+\s*(nghìn)',   # 50 nghìn
            r'\d+\s*(vnd|đồng|VND)',  # 50000 VND
            r'\d{3,}',          # Numbers with 3+ digits
        ]
        
        message_lower = message.lower()
        has_keyword = any(keyword in message_lower for keyword in expense_keywords)
        has_amount = any(re.search(pattern, message_lower) for pattern in amount_patterns)
        
        return has_keyword and has_amount
    
    def _extract_expenses_from_message(self, message: str) -> List[Dict]:
        """Extract multiple expense information from message"""
        
        # Enhanced amount extraction - find ALL amounts with their positions
        amount_patterns = [
            (r'(\d+)\s*tr(?!\w)', 1000000),  # 2tr = 2000000 (triệu)
            (r'(\d+)\s*triệu', 1000000),     # 5 triệu = 5000000  
            (r'(\d+)\s*k(?!\w)', 1000),      # 50k = 50000
            (r'(\d+)\s*nghìn', 1000),        # 50 nghìn = 50000
            (r'(?<!\d[/\-])(\d{3,})(?![/\-]\d)', 1),  # 50000 = 50000 (but exclude dates like 2025/07/20)
        ]
        
        amounts_with_positions = []
        message_lower = message.lower()
        
        for pattern, multiplier in amount_patterns:
            for match in re.finditer(pattern, message_lower):
                try:
                    amount = int(match.group(1)) * multiplier
                    if 1000 <= amount <= 100000000:  # Reasonable range
                        amounts_with_positions.append({
                            'amount': amount,
                            'start': match.start(),
                            'end': match.end(),
                            'text': match.group(0)
                        })
                except ValueError:
                    continue
        
        # Remove duplicates and sort by position
        amounts_with_positions = sorted(amounts_with_positions, key=lambda x: x['start'])
        
        # Enhanced context parsing for multiple expenses
        expenses = []
        
        if not amounts_with_positions:
            return expenses
            
        # Extract date from message context
        expense_date = self._get_expense_date_from_message(message)
        
        # Expense category detection patterns (not just meals)
        category_patterns = [
            # Transportation
            (r'taxi|grab|xe\s*ôm|xe\s*om|đi\s*taxi|đi\s*grab', 'transportation', 'Taxi/Grab'),
            (r'xăng|gas|petrol|nhiên\s*liệu', 'transportation', 'Xăng xe'),
            (r'xe\s*bus|xe\s*buýt|bus', 'transportation', 'Xe bus'),
            (r'máy\s*bay|flight|vé\s*máy\s*bay', 'transportation', 'Máy bay'),
            
            # Meals (keep existing patterns but expand)
            (r'ăn\s*sáng', 'meals', 'Ăn sáng'),
            (r'sáng(?!\s*qua)', 'meals', 'Ăn sáng'),  # Avoid matching "sáng qua"
            (r'ăn\s*trưa', 'meals', 'Ăn trưa'), 
            (r'trưa', 'meals', 'Ăn trưa'),
            (r'ăn\s*tối', 'meals', 'Ăn tối'),
            (r'tối(?!\s*qua)', 'meals', 'Ăn tối'),  # Avoid matching "tối qua"
            (r'ăn\s*chiều', 'meals', 'Ăn chiều'),
            (r'chiều', 'meals', 'Ăn chiều'),
            (r'cà\s*phê|coffee|cafe', 'meals', 'Cà phê'),
            (r'nước|drink|đồ\s*uống', 'meals', 'Đồ uống'),
            
            # Office/Work
            (r'văn\s*phòng|office|công\s*việc', 'office', 'Văn phòng'),
            (r'meeting|họp', 'office', 'Meeting'),
            
            # Entertainment
            (r'giải\s*trí|entertainment|vui\s*chơi', 'entertainment', 'Giải trí'),
            (r'cinema|rạp|phim', 'entertainment', 'Xem phim'),
            
            # Other
            (r'khách\s*sạn|hotel', 'accommodation', 'Khách sạn'),
            (r'mua\s*sắm|shopping', 'shopping', 'Mua sắm'),
        ]
        
        # Try to match each amount with context
        for i, amount_info in enumerate(amounts_with_positions):
            amount = amount_info['amount']
            position = amount_info['start']
            
            # Look for context around this amount (before and after, but prioritize before)
            context_start = max(0, position - 100)  # Look further back for category
            context_end = min(len(message_lower), position + 20)   # Only look a little ahead
            context = message_lower[context_start:context_end]
            
            # Find the closest category before this amount
            category = 'meals'  # default category
            expense_type = 'Chi phí'  # default description
            best_distance = float('inf')
            
            for pattern, cat_name, cat_description in category_patterns:
                for match in re.finditer(pattern, context):
                    # Calculate distance from category word to amount position
                    cat_pos = context_start + match.start()
                    distance = abs(position - cat_pos)
                    
                    # Prefer category words that come BEFORE the amount
                    if cat_pos <= position and distance < best_distance:
                        category = cat_name
                        expense_type = cat_description
                        best_distance = distance
            
            # Generate description
            if len(amounts_with_positions) == 1:
                # Single expense - use full message
                description = message[:100]
            else:
                # Multiple expenses - create specific description based on detected type
                description = f"{expense_type} - {amount_info['text']}"
            
            # Create expense object
            expense_id = f"exp_{int(datetime.now().timestamp() * 1000)}_{i}"
            
            expenses.append({
                'id': expense_id,
                'amount': amount,
                'category': category,  # Use detected category
                'description': description,
                'timestamp': datetime.now().isoformat(),
                'date': expense_date,
                'has_receipt': False,
                'expense_type': expense_type  # Additional metadata
            })
        
        return expenses
    
    def _extract_month_filter(self, message: str) -> str:
        """Extract month filter from report request message"""
        message_lower = message.lower()
        
        # Month mapping
        month_patterns = {
            'tháng 1': '01', 'tháng 01': '01', 'january': '01', 'jan': '01',
            'tháng 2': '02', 'tháng 02': '02', 'february': '02', 'feb': '02',
            'tháng 3': '03', 'tháng 03': '03', 'march': '03', 'mar': '03',
            'tháng 4': '04', 'tháng 04': '04', 'april': '04', 'apr': '04',
            'tháng 5': '05', 'tháng 05': '05', 'may': '05',
            'tháng 6': '06', 'tháng 06': '06', 'june': '06', 'jun': '06',
            'tháng 7': '07', 'tháng 07': '07', 'july': '07', 'jul': '07',
            'tháng 8': '08', 'tháng 08': '08', 'august': '08', 'aug': '08',
            'tháng 9': '09', 'tháng 09': '09', 'september': '09', 'sep': '09',
            'tháng 10': '10', 'october': '10', 'oct': '10',
            'tháng 11': '11', 'november': '11', 'nov': '11',
            'tháng 12': '12', 'december': '12', 'dec': '12'
        }
        
        # Look for month patterns
        for pattern, month_num in month_patterns.items():
            if pattern in message_lower:
                current_year = datetime.now().year
                return f"{current_year}-{month_num}"
        
        # Check for numeric patterns like "7/2025" or "07/2025"
        import re
        month_year_pattern = r'(\d{1,2})[/\-](\d{4})'
        match = re.search(month_year_pattern, message)
        if match:
            month = match.group(1).zfill(2)
            year = match.group(2)
            return f"{year}-{month}"
        
        # Check for patterns like "2025-07"
        iso_pattern = r'(\d{4})[/\-](\d{1,2})'
        match = re.search(iso_pattern, message)
        if match:
            year = match.group(1)
            month = match.group(2).zfill(2)
            return f"{year}-{month}"
        
        return None  # No month filter found
    
    def _filter_expenses_by_month(self, expenses: List[Dict], month_filter: str) -> List[Dict]:
        """Filter expenses by month (YYYY-MM format)"""
        if not month_filter:
            return expenses
        
        filtered_expenses = []
        for expense in expenses:
            expense_date = expense.get('date', '')
            if expense_date.startswith(month_filter):
                filtered_expenses.append(expense)
        
        return filtered_expenses
    
    def _is_report_request(self, message: str) -> bool:
        """Check if message is requesting expense report (not policy questions)"""
        # Keywords indicating user wants to see their actual expense data/report
        report_keywords = [
            'thống kê chi phí', 'báo cáo chi phí của tôi', 'tổng kết chi phí', 'tổng hợp chi phí',
            'chi phí đã kê khai', 'đã chi', 'chi phí đã phát sinh',
            'tổng chi phí của tôi', 'bao nhiêu tiền đã chi', 'tính tổng chi phí',
            'xem chi phí', 'kiểm tra chi phí', 'danh sách chi phí'
        ]
        
        # Keywords indicating policy/procedure questions (should NOT trigger report)
        policy_keywords = [
            'hạn chốt', 'deadline', 'hạn nộp', 'khi nào nộp', 'thời hạn',
            'chính sách', 'quy định', 'làm thế nào', 'cách thức',
            'được phép', 'có thể', 'giới hạn', 'tối đa'
        ]
        
        message_lower = message.lower()
        
        # If it's clearly a policy question, don't treat as report request
        if any(keyword in message_lower for keyword in policy_keywords):
            return False
            
        # Check for report request keywords
        return any(keyword in message_lower for keyword in report_keywords)
    
    def _get_ai_response_with_context(self, message: str, expense_context: str, session_info: dict) -> str:
        """Get AI response with expense context"""
        try:
            # Try to use existing expense assistant
            client = create_client()
            assistant = ExpenseAssistant(client)
            
            # Enhanced prompt with expense context
            enhanced_prompt = f"""
Bạn là trợ lý báo cáo chi phí thông minh với hiểu biết chính xác về chính sách công ty.

CHÍNH SÁCH HOÀN TRẢ QUAN TRỌNG:
• Chi phí ăn uống: Giới hạn 1,000,000 VND/NGÀY (không phải tổng)
• Mỗi ngày được hoàn trả tối đa 1,000,000 VND cho tất cả bữa ăn trong ngày đó
• Các loại chi phí khác: Hoàn trả đầy đủ theo policy

THÔNG TIN CHI PHÍ HIỆN TẠI (ĐÃ ĐƯỢC TÍNH TOÁN CHÍNH XÁC):

{expense_context}

Người dùng hỏi: {message}

QUAN TRỌNG: Thông tin trên đã được tính toán chính xác với daily limits. 
Hãy dựa vào con số "Tổng hoàn trả" đã được tính sẵn, KHÔNG tự tính lại.
Trả lời một cách chính xác và thân thiện.
"""
            
            # ⚠️ get_response returns Dict, not string - need to extract content
            response_dict = assistant.get_response(enhanced_prompt, session_info.get('session_id', ''))
            
            # Extract string content from response dict
            if isinstance(response_dict, dict):
                response_content = response_dict.get('content') or response_dict.get('response') or str(response_dict)
            else:
                response_content = str(response_dict)
                
            logger.info(f"🤖 AI response generated: {len(response_content)} chars")
            return response_content
            
        except Exception as e:
            logger.error(f"❌ AI response error: {str(e)}")
            
            # Fallback response
            if "chưa kê khai chi phí nào" in expense_context:
                return "Tôi thấy bạn chưa kê khai chi phí nào. Hãy bắt đầu bằng cách cho tôi biết các chi phí của bạn nhé!"
            else:
                return f"Dựa trên thông tin chi phí của bạn:\n\n{expense_context[:300]}...\n\nBạn có muốn tôi hỗ trợ gì thêm về chi phí này không?"
    
    # Legacy compatibility methods for fallback code
    def start_new_session(self) -> str:
        """Legacy compatibility: start new session"""
        return f"expense_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def process_message(self, message: str) -> List[Dict]:
        """Legacy compatibility: process message for expense extraction"""
        if self._is_expense_message(message):
            return self._extract_expenses_from_message(message)
        return []
    
    def is_report_request(self, message: str) -> bool:
        """Legacy compatibility: check if message is report request"""
        return self._is_report_request(message)
    
    def get_report(self, format_type: str = "text") -> str:
        """Legacy compatibility: get expense report"""
        # For now, return a generic report - this is fallback code anyway
        return "📊 Báo cáo chi phí: Vui lòng sử dụng enhanced memory endpoints để có báo cáo chi tiết."
    
    def get_summary(self) -> Dict:
        """Legacy compatibility: get expense summary"""
        # Return empty summary for fallback compatibility
        return {"total_expenses": 0, "total_amount": 0}
    
    @property
    def hybrid_memory(self):
        """Legacy compatibility: fake hybrid_memory property"""
        class FakeHybridMemory:
            expense_store = {"current_expenses": []}
        return FakeHybridMemory()

# 🆕 RAG Integration
try:
    from rag_integration import get_rag_integration, is_rag_query
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# 🧠 Smart Conversation Memory
try:
    from smart_memory_integration import (
        SmartConversationMemory, 
        WebAppMemoryIntegration,
        create_smart_memory_for_session
    )
    SMART_MEMORY_AVAILABLE = True
except ImportError:
    SMART_MEMORY_AVAILABLE = False

# 🔐 User Session Management
try:
    from user_session_manager import UserSessionManager, session_manager
    USER_SESSION_AVAILABLE = True
except ImportError:
    USER_SESSION_AVAILABLE = False

# Note: Enhanced Memory is now integrated directly above
HYBRID_MEMORY_AVAILABLE = True  # Always available since integrated
print("✅ Enhanced Memory System loaded successfully (integrated)")

app = Flask(__name__)
app.secret_key = "expense_assistant_secret_key_2024"
CORS(app)

# Khởi tạo cơ sở dữ liệu
db = ExpenseDB()

# Initialize enhanced memory system với ChromaDB persistence
enhanced_memory = EnhancedMemorySystem(database=db)
ENHANCED_MEMORY_AVAILABLE = True

# Khởi tạo assistant - optional for compatibility
try:
    client = create_client()
    assistant = ExpenseAssistant(client, model="GPT-4o-mini")
except Exception:
    assistant = None

# Dictionary để lưu trữ các phiên chat với smart memory support
chat_sessions = {}

# Global expense memory integration
expense_memory_integration = None

def initialize_expense_memory():
    """Khởi tạo expense memory integration tối ưu"""
    global expense_memory_integration
    if expense_memory_integration is not None:
        return True
        
    try:
        # Enhanced memory system is always available (integrated)
        # No need for separate expense_memory_integration anymore
        # Enhanced memory handles all expense logic directly
        expense_memory_integration = enhanced_memory  # Use enhanced memory directly
        return True
    except Exception as e:
        print(f"❌ Failed to initialize expense memory: {e}")
        return False


@app.route("/")
def home():
    """Trang chủ của ứng dụng web."""
    return render_template("index.html")


@app.route("/api/start_session", methods=["POST"])
def start_session():
    """Bắt đầu phiên chat mới - Guest session (chưa đăng nhập)."""
    try:
        # Khởi tạo expense memory
        initialize_expense_memory()
        
        # 🔐 Create guest session with User Session Manager
        session_id = None
        if USER_SESSION_AVAILABLE:
            session_id = session_manager.create_guest_session()
        else:
            session_id = str(uuid.uuid4())
        
        # Tạo expense session (enhanced memory automatically handles sessions)
        expense_session_id = None
        if expense_memory_integration:
            # Enhanced memory system doesn't need explicit session start
            # Session is handled automatically based on session_id
            expense_session_id = f"expense_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 🧠 Smart memory đã được tích hợp trong User Session Manager
        smart_memory_stats = None
        if USER_SESSION_AVAILABLE:
            session_info = session_manager.get_session_info(session_id)
            if session_info:
                smart_memory_stats = session_info['stats']

        # Tạo session data tối ưu
        session_data = {
            "session_id": session_id,
            "expense_session_id": expense_session_id,
            "user_type": "guest",
            "account": None,
            "created_at": datetime.now().isoformat(),
            "message_count": 0,
            "type": "guest_session_with_smart_memory" if USER_SESSION_AVAILABLE else "guest_session",
            "rag_available": RAG_AVAILABLE,
            "hybrid_memory_available": HYBRID_MEMORY_AVAILABLE,
            "smart_memory_available": SMART_MEMORY_AVAILABLE,
            "user_session_available": USER_SESSION_AVAILABLE,
            "memory_stats": smart_memory_stats or {}
        }

        if RAG_AVAILABLE:
            from rag_integration import get_rag_integration
            session_data["rag_integration"] = get_rag_integration()
            session_data["type"] = "guest_rag_with_smart_memory"

        chat_sessions[session_id] = session_data

        return jsonify({
            "success": True,
            "session_id": session_id,
            "expense_session_id": expense_session_id,
            "user_type": "guest",
            "account": None,
            "message": "🚀 Guest session with Smart Memory ready!",
            "features": {
                "rag": RAG_AVAILABLE,
                "memory": HYBRID_MEMORY_AVAILABLE,
                "smart_memory": SMART_MEMORY_AVAILABLE,
                "user_session": USER_SESSION_AVAILABLE,
                "reimbursement": True
            },
            "memory_stats": smart_memory_stats or {}
        })
        
    except Exception as e:
        print(f"❌ Error in start_session: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Lỗi khởi tạo: {str(e)}"
        }), 500


# 🔐 User Authentication Endpoints

@app.route("/api/login", methods=["POST"])
def login_user():
    """Đăng nhập người dùng với enhanced error handling."""
    data = request.get_json()
    account = data.get("account", "").strip()
    
    if not account:
        return jsonify({
            "success": False,
            "error": "Account không được để trống"
        }), 400
    
    try:
        if ENHANCED_MEMORY_AVAILABLE:
            # Use simplified enhanced memory
            session_id, user_info, error = enhanced_memory.safe_login_user(account)
            
            if error:
                return jsonify({
                    "success": False,
                    "error": error
                }), 400
            
            # Get expense context for display
            expense_context = enhanced_memory.get_expense_context(account=account)
            
            return jsonify({
                "success": True,
                "session_id": session_id,
                "user_type": "logged_in",
                "account": account,
                "message": f"🔓 Welcome back, {account}! Your data has been loaded.",
                "features": {
                    "rag": RAG_AVAILABLE,
                    "memory": HYBRID_MEMORY_AVAILABLE,
                    "smart_memory": SMART_MEMORY_AVAILABLE,
                    "user_session": USER_SESSION_AVAILABLE,
                    "reimbursement": True,
                    "persistent_storage": True,
                    "enhanced_expense_tracking": True
                },
                "stats": user_info["stats"],
                "expense_summary": user_info.get("expense_summary", {}),
                "storage_info": {
                    "type": "enhanced_memory",
                    "persistent": True
                },
                "expense_context_preview": expense_context[:200] + "..." if len(expense_context) > 200 else expense_context
            })
        else:
            # Fallback to original implementation with better error handling
            if not USER_SESSION_AVAILABLE:
                return jsonify({
                    "success": False,
                    "error": "User session system không khả dụng"
                }), 503
            
            # Login user và tạo session
            session_id, user_info = session_manager.login_user(account)
            
            # Khởi tạo expense memory
            initialize_expense_memory()
            
            # Tạo expense session (enhanced memory automatically handles sessions)
            expense_session_id = None
            if expense_memory_integration:
                # Enhanced memory system doesn't need explicit session start
                expense_session_id = f"expense_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Tạo session data cho chat_sessions
            session_data = {
                "session_id": session_id,
                "expense_session_id": expense_session_id,
                "user_type": "logged_in",
                "account": account,
                "created_at": user_info["created_at"].isoformat(),
                "message_count": 0,
                "type": "logged_in_session_with_smart_memory",
                "rag_available": RAG_AVAILABLE,
                "hybrid_memory_available": HYBRID_MEMORY_AVAILABLE,
                "smart_memory_available": SMART_MEMORY_AVAILABLE,
                "user_session_available": USER_SESSION_AVAILABLE,
                "memory_stats": user_info["stats"]
            }
            
            if RAG_AVAILABLE:
                from rag_integration import get_rag_integration
                session_data["rag_integration"] = get_rag_integration()
                session_data["type"] = "logged_in_rag_with_smart_memory"
            
            chat_sessions[session_id] = session_data
            
            return jsonify({
                "success": True,
                "session_id": session_id,
                "expense_session_id": expense_session_id,
                "user_type": "logged_in",
                "account": account,
                "message": f"🔓 Welcome back, {account}! Your conversation history has been loaded.",
                "features": {
                    "rag": RAG_AVAILABLE,
                    "memory": HYBRID_MEMORY_AVAILABLE,
                    "smart_memory": SMART_MEMORY_AVAILABLE,
                    "user_session": USER_SESSION_AVAILABLE,
                    "reimbursement": True,
                    "persistent_storage": True
                },
                "memory_stats": user_info["stats"],
                "storage_info": {
                    "type": "chromadb",
                    "collection": user_info.get("collection_name"),
                    "persistent": True
                }
            })
            
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Lỗi đăng nhập: {str(e)}"
        }), 500


@app.route("/api/logout", methods=["POST"])
def logout_user():
    """Đăng xuất người dùng với enhanced cleanup."""
    data = request.get_json()
    session_id = data.get("session_id")
    
    if not session_id:
        return jsonify({
            "success": False,
            "error": "Session ID không được để trống"
        }), 400
    
    try:
        if ENHANCED_MEMORY_AVAILABLE:
            # Use simplified enhanced memory
            success, error = enhanced_memory.safe_logout_user(session_id)
            
            if not success:
                return jsonify({
                    "success": False,
                    "error": error
                }), 400
            
            # Clean up chat session
            if session_id in chat_sessions:
                del chat_sessions[session_id]
            
            return jsonify({
                "success": True,
                "message": "🔒 Đăng xuất thành công! Your data has been saved."
            })
        else:
            # Fallback to original implementation with better error handling
            if not USER_SESSION_AVAILABLE:
                return jsonify({
                    "success": False,
                    "error": "User session system không khả dụng"
                }), 503
            
            # Get session info before logout
            session_info = session_manager.get_session_info(session_id)
            if not session_info:
                return jsonify({
                    "success": False,
                    "error": "Session không tồn tại"
                }), 404
            
            account = session_info.get("account")
            user_type = session_info.get("user_type")
            
            # Logout from session manager
            if user_type == "logged_in":
                logout_success = session_manager.logout_user(session_id)
            else:
                logout_success = True  # Guest sessions don't need explicit logout
            
            # Remove from chat_sessions
            if session_id in chat_sessions:
                del chat_sessions[session_id]
            
            return jsonify({
                "success": True,
                "message": f"🔒 Logged out successfully" + (f" - {account}" if account else " (guest)"),
                "user_type": user_type,
                "account": account
            })
            
    except Exception as e:
        print(f"❌ Logout error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Lỗi đăng xuất: {str(e)}"
        }), 500


@app.route("/api/session_info/<session_id>", methods=["GET"])
def get_session_info(session_id):
    """Lấy thông tin phiên hiện tại."""
    try:
        if not USER_SESSION_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "User session system không khả dụng"
            }), 503
        
        session_info = session_manager.get_session_info(session_id)
        if not session_info:
            return jsonify({
                "success": False,
                "error": "Session không tồn tại"
            }), 404
        
        return jsonify({
            "success": True,
            "session_info": {
                "session_id": session_id,
                "user_type": session_info["user_type"],
                "account": session_info.get("account"),
                "created_at": session_info["created_at"].isoformat(),
                "last_activity": session_info["last_activity"].isoformat(),
                "stats": session_info["stats"]
            },
            "storage_info": {
                "type": "chromadb" if session_info["user_type"] == "logged_in" else "memory",
                "persistent": session_info["user_type"] == "logged_in"
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Lỗi lấy thông tin session: {str(e)}"
        }), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """Xử lý tin nhắn chat với Enhanced Memory & Expense Persistence."""
    data = request.get_json()
    session_id = data.get("session_id")
    message = data.get("message", "").strip()

    # Validation
    if not session_id:
        return jsonify({"success": False, "error": "Session ID không được để trống"}), 400
    if not message:
        return jsonify({"success": False, "error": "Tin nhắn không được để trống"}), 400

    try:
        if ENHANCED_MEMORY_AVAILABLE:
            # Use simplified enhanced memory
            response, error = enhanced_memory.safe_chat_endpoint(session_id, message)
            
            if error:
                return jsonify({"success": False, "error": error}), 400
            
            return jsonify(response)
        else:
            # Fallback to original implementation with better error handling
            # 🔐 Get session info from User Session Manager
            session_info = None
            if USER_SESSION_AVAILABLE:
                session_info = session_manager.get_session_info(session_id)
                if not session_info:
                    return jsonify({"success": False, "error": "Session không tồn tại hoặc đã hết hạn"}), 404
            
            # Fallback to legacy chat_sessions for backward compatibility
            session_data = chat_sessions.get(session_id)
            if not session_data and not session_info:
                return jsonify({"success": False, "error": "Phiên chat không hợp lệ"}), 400
            
            # 🧠 Process với User Session Manager Smart Memory
            conversation_result = None
            if USER_SESSION_AVAILABLE and session_info:
                # Add conversation turn to smart memory (will handle summarization automatically)
                # We'll add the assistant response after getting it from AI
                pass
            
            # Legacy smart memory support (fallback)
            elif session_data and session_data.get("smart_memory"):
                smart_memory = session_data["smart_memory"]
                
                # Add user message vào smart memory
                user_result = smart_memory.append({"role": "user", "content": message})
                
                # Get optimized context cho AI request
                ai_context = smart_memory.summarizer.get_conversation_context(smart_memory.session_id, max_summaries=2)
            
            # Khởi tạo expense memory nếu cần
            if expense_memory_integration is None:
                initialize_expense_memory()
            
            # 1. Xử lý capture chi phí
            captured_expenses = []
            if expense_memory_integration:
                try:
                    captured_expenses = expense_memory_integration.process_message(message) or []
                except Exception:
                    pass

            # 2. Kiểm tra yêu cầu báo cáo
            if expense_memory_integration and expense_memory_integration.is_report_request(message):
                report = expense_memory_integration.get_report()
                summary = expense_memory_integration.get_summary()
                
                # 🔐 Add conversation to User Session Manager
                if USER_SESSION_AVAILABLE and session_info:
                    conversation_result = session_manager.add_conversation_turn(session_id, message, report)
                
                # Legacy smart memory support
                elif session_data and session_data.get("smart_memory"):
                    session_data["smart_memory"].append({"role": "assistant", "content": report})
                    session_data["memory_stats"] = session_data["smart_memory"].get_stats()
                
                if session_data:
                    session_data["message_count"] += 1
                    
                return jsonify({
                    "success": True,
                    "response": report,
                    "type": "expense_report",
                    "expense_data": {"summary": summary},
                    "memory_optimized": True,
                    "smart_memory_stats": conversation_result.get("memory_stats") if conversation_result else session_data.get("memory_stats", {}),
                    "user_type": session_info.get("user_type") if session_info else "legacy",
                    "storage_type": "chromadb" if session_info and session_info.get("user_type") == "logged_in" else "memory"
                })

            # 3. Chi phí mới được kê khai
            elif captured_expenses:
                summary = expense_memory_integration.get_summary() if expense_memory_integration else {}
                
                # Tính hoàn trả
                reimbursement_info = ""
                try:
                    if captured_expenses:
                        expense_list = [{
                            'category': exp.get('category', 'other'),
                            'amount': exp.get('amount', 0),
                            'description': exp.get('description', ''),
                            'date': '2025-08-08',
                            'has_receipt': True
                        } for exp in captured_expenses]
                        
                        reimbursement_data = calculate_reimbursement(expense_list)
                        if reimbursement_data:
                            reimbursed = reimbursement_data.get('total_reimbursed', 0)
                            if reimbursed > 0:
                                reimbursement_info = f" (Hoàn trả: {reimbursed:,.0f} VND)"
                except Exception:
                    pass
                
                # Phản hồi gọn
                if len(captured_expenses) == 1:
                    ce = captured_expenses[0]
                    response = f"✅ {ce.get('amount', 0):,.0f} VND - {ce.get('category', 'other').title()}{reimbursement_info}"
                else:
                    response = f"✅ {len(captured_expenses)} khoản chi phí{reimbursement_info}"
                
                response += f"\n📊 Tổng: {summary.get('total_expenses', 0)} khoản - {summary.get('total_amount', 0):,.0f} VND"
                
                # 🔐 Add conversation to User Session Manager
                if USER_SESSION_AVAILABLE and session_info:
                    conversation_result = session_manager.add_conversation_turn(session_id, message, response)
                
                # Legacy smart memory support
                elif session_data and session_data.get("smart_memory"):
                    session_data["smart_memory"].append({"role": "assistant", "content": response})
                    session_data["memory_stats"] = session_data["smart_memory"].get_stats()
                
                if session_data:
                    session_data["message_count"] += 1
                    
                return jsonify({
                    "success": True,
                    "response": response,
                    "type": "expense_declaration",
                    "expense_data": {"new_expenses": captured_expenses, "summary": summary},
                    "memory_optimized": True,
                    "smart_memory_stats": conversation_result.get("memory_stats") if conversation_result else session_data.get("memory_stats", {}),
                    "user_type": session_info.get("user_type") if session_info else "legacy",
                    "storage_type": "chromadb" if session_info and session_info.get("user_type") == "logged_in" else "memory"
                })

            # 4. RAG query - check for both guest and logged-in RAG types
            elif session_data and session_data.get("type") in ["guest_rag_with_smart_memory", "logged_in_rag_with_smart_memory", "rag_with_memory"] and "rag_integration" in session_data:
                try:
                    print(f"🔍 Processing RAG query: {message[:50]}...")
                    rag_integration = session_data["rag_integration"]
                    rag_response = rag_integration.get_rag_response(message, use_hybrid=True)
                    print(f"✅ RAG response received: {len(rag_response.get('content', ''))} chars")
                    
                    # Add assistant response vào smart memory
                    if session_data.get("smart_memory"):
                        session_data["smart_memory"].append({"role": "assistant", "content": rag_response.get("content", "")})
                        session_data["memory_stats"] = session_data["smart_memory"].get_stats()
                    
                    session_data["message_count"] += 1
                    return jsonify({
                        "success": True,
                        "response": rag_response.get("content", "Không thể xử lý câu hỏi."),
                        "rag_used": True,
                        "sources": rag_response.get("sources", []),
                        "memory_optimized": True,
                        "smart_memory_stats": session_data.get("memory_stats", {}),
                        "type": "rag_response"
                    })
                except Exception as e:
                    print(f"❌ RAG Error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # Fallback to basic response instead of crashing
                    pass

            # 5. Basic response với smart memory
            basic_responses = {
                "chào": "Xin chào! Tôi có thể giúp bạn kê khai chi phí và tạo báo cáo.",
                "giúp": "Tôi có thể:\n• Kê khai chi phí\n• Tạo báo cáo\n• Tính hoàn trả"
            }
            
            response = "🤖 Trợ lý chi phí với Smart Memory sẵn sàng! Hãy kê khai chi phí hoặc yêu cầu báo cáo."
            for keyword, resp in basic_responses.items():
                if keyword in message.lower():
                    response = resp
                    break
            
            # 🔐 Add conversation to User Session Manager
            if USER_SESSION_AVAILABLE and session_info:
                conversation_result = session_manager.add_conversation_turn(session_id, message, response)
            
            # Legacy smart memory support
            elif session_data and session_data.get("smart_memory"):
                session_data["smart_memory"].append({"role": "assistant", "content": response})
                session_data["memory_stats"] = session_data["smart_memory"].get_stats()
            
            if session_data:
                session_data["message_count"] += 1
                
            return jsonify({
                "success": True,
                "response": response,
                "type": "basic_response",
                "memory_optimized": True,
                "smart_memory_stats": conversation_result.get("memory_stats") if conversation_result else session_data.get("memory_stats", {}),
                "user_type": session_info.get("user_type") if session_info else "legacy",
                "storage_type": "chromadb" if session_info and session_info.get("user_type") == "logged_in" else "memory"
            })

    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Lỗi xử lý: {str(e)}"}), 500


# ========================================
# 🧠 SMART MEMORY DASHBOARD ROUTES  
# ========================================

@app.route("/smart_memory/dashboard")
def smart_memory_dashboard():
    """Smart Memory Performance Dashboard"""
    return render_template("index.html")  # Sử dụng existing template với dashboard features


@app.route("/api/smart_memory/stats/<session_id>")
def get_smart_memory_stats(session_id: str):
    """API: Lấy thống kê smart memory cho session với User Session Manager"""
    try:
        # 🔐 Try User Session Manager first
        if USER_SESSION_AVAILABLE:
            session_info = session_manager.get_session_info(session_id)
            if session_info:
                return jsonify({
                    'success': True,
                    'stats': session_info['stats'],
                    'session_type': session_info['user_type'],
                    'account': session_info.get('account'),
                    'storage_type': 'chromadb' if session_info['user_type'] == 'logged_in' else 'memory',
                    'last_activity': session_info['last_activity'].isoformat()
                })
        
        # Fallback to legacy chat_sessions
        if session_id not in chat_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        session_data = chat_sessions[session_id]
        smart_memory = session_data.get('smart_memory')
        
        if not smart_memory:
            return jsonify({'success': False, 'error': 'Smart memory not available for this session'}), 400
        
        stats = smart_memory.get_stats()
        
        # Thêm thông tin chi tiết
        detailed_stats = {
            **stats,
            'session_info': {
                'session_id': session_id,
                'created_at': session_data.get('created_at'),
                'message_count': session_data.get('message_count', 0),
                'type': session_data.get('type')
            },
            'memory_efficiency': {
                'avg_tokens_per_message': stats.get('total_tokens_saved', 0) / max(1, stats.get('total_messages_processed', 1)),
                'summarization_frequency': stats.get('summaries_created', 0) / max(1, stats.get('total_messages_processed', 1)) * 100,
                'compression_ratio': f"{stats.get('efficiency_ratio', '0%')}"
            },
            'storage_type': 'memory'
        }
        
        return jsonify({
            'success': True,
            'stats': detailed_stats,
            'session_type': 'legacy',
            'storage_type': 'memory'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error getting stats: {str(e)}'}), 500


@app.route("/api/smart_memory/global_stats")
def get_global_smart_memory_stats():
    """API: Thống kê smart memory toàn cục với User Session Manager"""
    try:
        # 🔐 Get stats from User Session Manager
        if USER_SESSION_AVAILABLE:
            global_stats = session_manager.get_global_stats()
            return jsonify({
                'success': True,
                'global_stats': global_stats,
                'system_type': 'user_session_manager'
            })
        
        # Fallback to legacy system
        total_sessions = 0
        smart_memory_sessions = 0
        total_tokens_saved = 0
        total_summaries = 0
        total_messages = 0
        
        session_details = []
        
        for session_id, session_data in chat_sessions.items():
            total_sessions += 1
            
            smart_memory = session_data.get('smart_memory')
            if smart_memory:
                smart_memory_sessions += 1
                stats = smart_memory.get_stats()
                
                total_tokens_saved += stats.get('total_tokens_saved', 0)
                total_summaries += stats.get('summaries_created', 0)
                total_messages += stats.get('total_messages_processed', 0)
                
                session_details.append({
                    'session_id': session_id,
                    'created_at': session_data.get('created_at'),
                    'message_count': session_data.get('message_count', 0),
                    'tokens_saved': stats.get('total_tokens_saved', 0),
                    'summaries': stats.get('summaries_created', 0),
                    'efficiency': stats.get('efficiency_ratio', '0%')
                })
        
        # Tính toán metrics tổng quan
        avg_tokens_saved = total_tokens_saved / max(1, smart_memory_sessions)
        avg_summaries_per_session = total_summaries / max(1, smart_memory_sessions)
        
        global_stats = {
            'overview': {
                'total_sessions': total_sessions,
                'smart_memory_sessions': smart_memory_sessions,
                'adoption_rate': f"{(smart_memory_sessions / max(1, total_sessions)) * 100:.1f}%",
                'total_tokens_saved': total_tokens_saved,
                'total_summaries': total_summaries,
                'total_messages': total_messages
            },
            'performance': {
                'avg_tokens_saved_per_session': round(avg_tokens_saved, 2),
                'avg_summaries_per_session': round(avg_summaries_per_session, 2),
                'estimated_cost_savings': f"${(total_tokens_saved * 0.00001):.4f}",
                'memory_efficiency': f"{(total_tokens_saved / max(1, total_messages * 50)) * 100:.1f}%"
            },
            'sessions': sorted(session_details, key=lambda x: x['tokens_saved'], reverse=True)[:10]
        }
        
        return jsonify(global_stats)
        
    except Exception as e:
        return jsonify({'error': f'Failed to get global stats: {str(e)}'}), 500


@app.route("/api/smart_memory/optimize/<session_id>", methods=["POST"])
def optimize_smart_memory_session(session_id: str):
    """API: Force optimization cho session với User Session Manager"""
    try:
        # 🔐 Try User Session Manager first
        if USER_SESSION_AVAILABLE:
            session_info = session_manager.get_session_info(session_id)
            if session_info:
                # Optimize memory using User Session Manager
                optimization_result = session_manager.optimize_session_memory(session_id)
                
                # Get updated stats
                updated_session_info = session_manager.get_session_info(session_id)
                
                return jsonify({
                    'success': True,
                    'optimization_result': optimization_result,
                    'new_stats': updated_session_info['stats'],
                    'session_type': session_info['user_type'],
                    'storage_type': 'chromadb' if session_info['user_type'] == 'logged_in' else 'memory'
                })
        
        # Fallback to legacy system
        if session_id not in chat_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        session_data = chat_sessions[session_id]
        smart_memory = session_data.get('smart_memory')
        
        if not smart_memory:
            return jsonify({'success': False, 'error': 'Smart memory not available'}), 400
        
        # Force summarization nếu có đủ messages
        if smart_memory.session_id in smart_memory.summarizer.active_conversations:
            messages = smart_memory.summarizer.active_conversations[smart_memory.session_id]['messages']
            
            if len(messages) >= 3:  # Minimum for summarization
                result = smart_memory.summarizer.summarize_conversation_window(smart_memory.session_id)
                
                # Update session stats
                session_data['memory_stats'] = smart_memory.get_stats()
                
                return jsonify({
                    'success': True,
                    'optimization_result': result,
                    'new_stats': session_data['memory_stats'],
                    'session_type': 'legacy',
                    'storage_type': 'memory'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Not enough messages for optimization'
                })
        else:
            return jsonify({
                'success': False,
                'error': 'No active conversation found'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Optimization failed: {str(e)}'
        })


@app.route("/api/text-to-speech", methods=["POST"])
def text_to_speech_route():
    """Converts text to speech and returns the audio file."""
    data = request.get_json()
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"success": False, "error": "Text cannot be empty"}), 400

    try:
        output_filename = f"speech_{uuid.uuid4()}.wav"
        output_path = tts(text, output_filename)
        audio_url = f"/audio/{output_filename}"

        return jsonify({"success": True, "audio_url": audio_url})

    except Exception as e:
        return jsonify({"success": False, "error": f"Error generating speech: {str(e)}"}), 500


@app.route("/audio/<filename>")
def serve_audio(filename):
    """Serves the generated audio file."""
    return send_file(os.path.join("audio_chats", filename))


@app.route("/api/sample_questions")
def sample_questions():
    """Lấy danh sách câu hỏi mẫu."""
    return jsonify({"success": True, "questions": SAMPLE_USER_QUERIES})


@app.route("/api/system_info")
def system_info():
    """Thông tin hệ thống tối ưu."""
    # Expense memory status
    expense_status = {"available": False}
    if expense_memory_integration:
        try:
            summary = expense_memory_integration.get_summary()
            expense_status = {
                "available": True,
                "total_expenses": summary.get("total_expenses", 0),
                "total_amount": summary.get("total_amount", 0)
            }
        except Exception:
            pass
    
    return jsonify({
        "success": True,
        "info": {
            "policies": len(EXPENSE_POLICIES),
            "active_sessions": len(chat_sessions),
            "features": {
                "rag": RAG_AVAILABLE,
                "hybrid_memory": HYBRID_MEMORY_AVAILABLE,
                "reimbursement": True,
                "optimized": True
            },
            "expense_memory": expense_status
        }
    })


# 🆕 Enhanced Expense Memory Endpoints
@app.route("/api/expense_summary", methods=["GET"])
def get_expense_summary():
    """Get current expense session summary"""
    try:
        if expense_memory_integration is None:
            initialize_expense_memory()
            
        if expense_memory_integration is None:
            return jsonify({
                'success': False,
                'error': 'Expense memory not available'
            }), 503
        
        summary = expense_memory_integration.get_summary()
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Lỗi lấy thông tin: {str(e)}'
        }), 500


@app.route("/api/generate_report", methods=["POST"])
def generate_report():
    """Generate expense report on demand with reimbursement analysis"""
    try:
        if expense_memory_integration is None:
            initialize_expense_memory()
            
        if expense_memory_integration is None:
            return jsonify({
                'success': False,
                'error': 'Expense memory not available'
            }), 503
        
        data = request.get_json() or {}
        format_type = data.get('format', 'detailed')  # 'detailed' or 'summary'
        
        report = expense_memory_integration.get_report(format_type)
        summary = expense_memory_integration.get_summary()
        
        # Add reimbursement analysis
        reimbursement_data = None
        if expense_memory_integration.hybrid_memory.expense_store["current_expenses"]:
            try:
                # Convert expenses to format expected by calculate_reimbursement
                expense_list = []
                for exp in expense_memory_integration.hybrid_memory.expense_store["current_expenses"]:
                    expense_list.append({
                        'category': exp.get('category', 'other'),
                        'amount': exp.get('amount', 0),
                        'description': exp.get('description', ''),
                        'date': exp.get('timestamp', '2025-08-08')[:10],
                        'has_receipt': True  # Assume receipts for now
                    })
                
                reimbursement_data = calculate_reimbursement(expense_list)
            except Exception as e:
                print(f"⚠️ Reimbursement calculation error: {e}")
        
        return jsonify({
            'success': True,
            'report': report,
            'summary': summary,
            'reimbursement': reimbursement_data,
            'format': format_type
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Lỗi tạo báo cáo: {str(e)}'
        }), 500


@app.route("/api/reimbursement_analysis", methods=["GET"])
def get_reimbursement_analysis():
    """Get detailed reimbursement analysis for current expenses"""
    try:
        if expense_memory_integration is None:
            initialize_expense_memory()
            
        if expense_memory_integration is None:
            return jsonify({
                'success': False,
                'error': 'Expense memory not available'
            }), 503
        
        current_expenses = expense_memory_integration.hybrid_memory.expense_store["current_expenses"]
        
        if not current_expenses:
            return jsonify({
                'success': True,
                'message': 'Không có chi phí nào để phân tích',
                'reimbursement': None
            })
        
        # Convert expenses to format expected by calculate_reimbursement
        expense_list = []
        for exp in current_expenses:
            expense_list.append({
                'category': exp.get('category', 'other'),
                'amount': exp.get('amount', 0),
                'description': exp.get('description', ''),
                'date': exp.get('timestamp', '2025-08-08')[:10],
                'has_receipt': True  # Assume receipts for now
            })
        
        reimbursement_data = calculate_reimbursement(expense_list)
        
        return jsonify({
            'success': True,
            'reimbursement': reimbursement_data,
            'total_expenses': len(current_expenses),
            'analysis_date': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Lỗi phân tích hoàn trả: {str(e)}'
        }), 500


# 🆕 RAG API Endpoints - Workshop 5
@app.route("/api/rag/search", methods=["POST"])
def rag_search():
    """Search knowledge base using RAG system"""
    if not RAG_AVAILABLE:
        return jsonify({"success": False, "error": "RAG system not available"}), 503
    
    data = request.get_json()
    query = data.get("query", "").strip()
    limit = data.get("limit", 5)
    
    if not query:
        return jsonify({"success": False, "error": "Query cannot be empty"}), 400
    
    try:
        rag_integration = get_rag_integration()
        search_results = rag_integration.search_knowledge_base(query, limit)
        
        return jsonify({
            "success": True,
            "query": query,
            "results": search_results["results"],
            "total_found": search_results["total"],
            "limit": limit
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": f"Search failed: {str(e)}"}), 500


@app.route("/api/rag/query", methods=["POST"])
def rag_query():
    """Get RAG response for a query"""
    if not RAG_AVAILABLE:
        return jsonify({"success": False, "error": "RAG system not available"}), 503
    
    data = request.get_json()
    query = data.get("query", "").strip()
    use_hybrid = data.get("use_hybrid", True)
    
    if not query:
        return jsonify({"success": False, "error": "Query cannot be empty"}), 400
    
    try:
        rag_integration = get_rag_integration()
        rag_response = rag_integration.get_rag_response(query, use_hybrid)
        
        return jsonify({
            "success": True,
            "query": query,
            "response": rag_response["content"],
            "rag_used": rag_response.get("rag_used", False),
            "response_type": rag_response.get("response_type", "unknown"),
            "function_calling_used": rag_response.get("function_calling_used", False),
            "sources": rag_response.get("sources", [])
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": f"RAG query failed: {str(e)}"}), 500


@app.route("/api/rag/stats")
def rag_stats():
    """Get RAG system statistics"""
    if not RAG_AVAILABLE:
        return jsonify({"success": False, "error": "RAG system not available"}), 503
    
    try:
        rag_integration = get_rag_integration()
        stats = rag_integration.get_system_stats()
        
        return jsonify({
            "success": True,
            "stats": stats,
            "rag_available": rag_integration.is_rag_available()
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to get stats: {str(e)}"}), 500


@app.route("/api/clear_session", methods=["POST"])
def clear_session():
    """Xóa phiên chat."""
    data = request.get_json()
    session_id = data.get("session_id")

    if session_id and session_id in chat_sessions:
        # Reset expense memory if available
        if expense_memory_integration:
            # Enhanced memory system automatically manages sessions
            # No need to explicitly start new session
            pass
        
        chat_sessions[session_id]["message_count"] = 0
        return jsonify({"success": True, "message": "Phiên chat đã được xóa"})

    return jsonify({"success": False, "error": "Phiên chat không tồn tại"}), 400


@app.route("/api/session_stats/<session_id>")
def session_stats(session_id):
    """Lấy thống kê phiên chat."""
    if session_id in chat_sessions:
        session_data = chat_sessions[session_id]
        return jsonify({
            "success": True,
            "stats": {
                "created_at": session_data["created_at"],
                "message_count": session_data["message_count"],
                "type": session_data.get("type", "unknown"),
                "features": {
                    "rag": RAG_AVAILABLE,
                    "memory": HYBRID_MEMORY_AVAILABLE
                }
            }
        })

    return jsonify({"success": False, "error": "Phiên chat không tồn tại"}), 404


@app.errorhandler(404)
def not_found(error):
    """Xử lý lỗi 404."""
    return jsonify({"success": False, "error": "Không tìm thấy trang"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Xử lý lỗi 500."""
    return jsonify({"success": False, "error": "Lỗi máy chủ nội bộ"}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """
    🏥 System health check endpoint
    
    Returns comprehensive system health status and recommendations
    """
    try:
        # Database health check
        db = ExpenseDB()
        health_status = db.system_health_check()
        
        # Add application-level checks
        health_status["application"] = {
            "rag_available": RAG_AVAILABLE,
            "smart_memory_available": SMART_MEMORY_AVAILABLE,
            "user_sessions_available": USER_SESSION_AVAILABLE,
            "hybrid_memory_available": HYBRID_MEMORY_AVAILABLE
        }
        
        # System score calculation
        total_docs = health_status.get("total_documents", 0)
        app_features = sum([
            RAG_AVAILABLE, SMART_MEMORY_AVAILABLE, 
            USER_SESSION_AVAILABLE, HYBRID_MEMORY_AVAILABLE
        ])
        
        if health_status["overall_status"] == "excellent" and app_features >= 3:
            system_score = 9.0
        elif health_status["overall_status"] == "good" and app_features >= 2:
            system_score = 7.5
        elif health_status["overall_status"] == "fair":
            system_score = 6.0
        else:
            system_score = 4.0
            
        health_status["system_score"] = system_score
        health_status["grade"] = (
            "🟢 EXCELLENT" if system_score >= 8.5 else
            "🟡 GOOD" if system_score >= 7.0 else
            "🟠 FAIR" if system_score >= 6.0 else
            "🔴 NEEDS IMPROVEMENT"
        )
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            "overall_status": "error",
            "error": str(e),
            "system_score": 0.0,
            "grade": "🔴 SYSTEM ERROR"
        }), 500


@app.route("/api/stats", methods=["GET"])
def system_stats():
    """
    📊 Get system statistics
    """
    try:
        db = ExpenseDB()
        stats = db.get_system_stats()
        
        # Add session statistics if available
        if USER_SESSION_AVAILABLE and session_manager:
            session_stats = session_manager.get_session_stats()
            stats["sessions"] = session_stats
            
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/test_persistence", methods=["POST"])
def test_persistence():
    """🧪 Test ChromaDB persistence functionality"""
    try:
        data = request.get_json()
        test_account = data.get("account", "test_user")
        
        # Add test data
        test_data = {
            "expenses": [
                {
                    "id": "test_exp_001",
                    "amount": 50000,
                    "category": "food",
                    "description": "Test lunch expense",
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "sessions": {},
            "created_at": datetime.now().isoformat()
        }
        
        # Save to memory store
        enhanced_memory.store["users"][test_account] = test_data
        
        # Save to ChromaDB
        success = enhanced_memory._save_user_to_chromadb(test_account)
        
        # Try to load it back
        loaded_data = enhanced_memory.db.load_user_data(test_account)
        
        return jsonify({
            "success": True,
            "save_success": success,
            "loaded_data": loaded_data,
            "test_account": test_account,
            "message": "Test persistence completed successfully"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Test persistence failed"
        }), 500


if __name__ == "__main__":
    # Tạo thư mục cần thiết
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)

    print("🌐 Khởi động Trợ Lý Báo Cáo Chi Phí (Với Login System)...")
    print(f"   • RAG: {'✅' if RAG_AVAILABLE else '❌'}")
    print(f"   • Hybrid Memory: {'✅' if HYBRID_MEMORY_AVAILABLE else '❌'}")
    print(f"   • Smart Memory: {'✅' if SMART_MEMORY_AVAILABLE else '❌'}")
    print(f"   • User Sessions: {'✅' if USER_SESSION_AVAILABLE else '❌'}")
    print(f"   • Chính sách: {len(EXPENSE_POLICIES)} danh mục")
    print("🚀 Server: http://localhost:5000")
    print("🔐 Features:")
    print("   • Guest Mode: Memory-only storage")
    print("   • Login Mode: Persistent ChromaDB storage")
    print("   • Smart conversation summarization")

    # Khởi động Enhanced Expense Memory
    if HYBRID_MEMORY_AVAILABLE:
        initialize_expense_memory()

    app.run(debug=True, host="0.0.0.0", port=5000)
