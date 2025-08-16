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
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS

from database import ExpenseDB
from expense_assistant import ExpenseAssistant, create_client
from functions import EXPENSE_POLICIES, MOCK_EXPENSE_REPORTS, SAMPLE_USER_QUERIES, calculate_reimbursement
from text_to_speech import text_to_speech as tts

# 🆕 RAG Integration
try:
    from rag_integration import get_rag_integration, is_rag_query
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# 🔧 Hybrid Memory Fix
try:
    from hybrid_memory_fix import RAGExpenseMemoryIntegration
    HYBRID_MEMORY_AVAILABLE = True
except ImportError:
    HYBRID_MEMORY_AVAILABLE = False

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

app = Flask(__name__)
app.secret_key = "expense_assistant_secret_key_2024"
CORS(app)

# Khởi tạo cơ sở dữ liệu
db = ExpenseDB()

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
        if HYBRID_MEMORY_AVAILABLE:
            if RAG_AVAILABLE:
                from rag_integration import get_rag_integration
                rag_integration = get_rag_integration()
                expense_memory_integration = RAGExpenseMemoryIntegration(rag_integration)
            else:
                expense_memory_integration = RAGExpenseMemoryIntegration()
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
        
        # Tạo expense session (legacy support)
        expense_session_id = None
        if expense_memory_integration:
            expense_session_id = expense_memory_integration.start_new_session()

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
    """Đăng nhập người dùng (chỉ cần account)."""
    data = request.get_json()
    account = data.get("account", "").strip()
    
    if not account:
        return jsonify({
            "success": False,
            "error": "Account không được để trống"
        }), 400
    
    try:
        if not USER_SESSION_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "User session system không khả dụng"
            }), 503
        
        # Login user và tạo session
        session_id, user_info = session_manager.login_user(account)
        
        # Khởi tạo expense memory
        initialize_expense_memory()
        
        # Tạo expense session (legacy support)
        expense_session_id = None
        if expense_memory_integration:
            expense_session_id = expense_memory_integration.start_new_session()
        
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
        return jsonify({
            "success": False,
            "error": f"Lỗi đăng nhập: {str(e)}"
        }), 500


@app.route("/api/logout", methods=["POST"])
def logout_user():
    """Đăng xuất người dùng."""
    data = request.get_json()
    session_id = data.get("session_id")
    
    if not session_id:
        return jsonify({
            "success": False,
            "error": "Session ID không được để trống"
        }), 400
    
    try:
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
    """Xử lý tin nhắn chat với User Session Manager và Smart Memory."""
    data = request.get_json()
    session_id = data.get("session_id")
    message = data.get("message", "").strip()

    # Validation
    if not session_id:
        return jsonify({"success": False, "error": "Session ID không được để trống"}), 400
    if not message:
        return jsonify({"success": False, "error": "Tin nhắn không được để trống"}), 400

    try:
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
        elif session_data.get("type") in ["guest_rag_with_smart_memory", "logged_in_rag_with_smart_memory", "rag_with_memory"] and "rag_integration" in session_data:
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


# 🆕 RAG API Endpoints - Workshop 4
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
            expense_memory_integration.start_new_session()
        
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
