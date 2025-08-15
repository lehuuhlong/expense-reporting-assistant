# Ứng dụng Web Tối Ưu cho Trợ Lý Báo Cáo Chi Phí với Hybrid Memory
"""
Ứng dụng web Flask tối ưu hóa với hybrid memory integration
và tính năng reimbursement analysis hoàn chỉnh.
"""

import json
import os
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
    """Bắt đầu phiên chat mới với RAG, Hybrid Memory và Smart Conversation Memory."""
    session_id = str(uuid.uuid4())

    try:
        # Khởi tạo expense memory
        initialize_expense_memory()
        
        # Tạo expense session
        expense_session_id = None
        if expense_memory_integration:
            expense_session_id = expense_memory_integration.start_new_session()

        # 🧠 Khởi tạo Smart Conversation Memory nếu available
        smart_memory = None
        if SMART_MEMORY_AVAILABLE and client:
            try:
                smart_memory = create_smart_memory_for_session(client, session_id)
            except Exception as e:
                print(f"⚠️ Smart memory initialization failed: {e}")

        # Tạo session data tối ưu với smart memory
        session_data = {
            "expense_session_id": expense_session_id,
            "created_at": datetime.now().isoformat(),
            "message_count": 0,
            "type": "optimized_session_with_smart_memory" if smart_memory else "optimized_session",
            "smart_memory": smart_memory,
            "memory_stats": smart_memory.get_stats() if smart_memory else {}
        }

        if RAG_AVAILABLE:
            from rag_integration import get_rag_integration
            session_data["rag_integration"] = get_rag_integration()
            session_data["type"] = "rag_with_memory"

        chat_sessions[session_id] = session_data

        return jsonify({
            "success": True,
            "session_id": session_id,
            "expense_session_id": expense_session_id,
            "message": "🚀 Phiên chat với Smart Memory đã sẵn sàng!",
            "features": {
                "rag": RAG_AVAILABLE,
                "memory": HYBRID_MEMORY_AVAILABLE,
                "smart_memory": smart_memory is not None,
                "reimbursement": True
            },
            "memory_stats": session_data.get("memory_stats", {})
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Lỗi khởi tạo: {str(e)}"
        }), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """Xử lý tin nhắn chat tối ưu với RAG và Hybrid Memory."""
    data = request.get_json()
    session_id = data.get("session_id")
    message = data.get("message", "").strip()

    # Validation
    if not session_id or session_id not in chat_sessions:
        return jsonify({"success": False, "error": "Phiên chat không hợp lệ"}), 400
    if not message:
        return jsonify({"success": False, "error": "Tin nhắn không được để trống"}), 400

    try:
        session_data = chat_sessions[session_id]
        
        # 🧠 Process với Smart Memory nếu available
        if session_data.get("smart_memory"):
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
            
            # Add assistant response vào smart memory
            if session_data.get("smart_memory"):
                session_data["smart_memory"].append({"role": "assistant", "content": report})
                session_data["memory_stats"] = session_data["smart_memory"].get_stats()
            
            session_data["message_count"] += 1
            return jsonify({
                "success": True,
                "response": report,
                "type": "expense_report",
                "expense_data": {"summary": summary},
                "memory_optimized": True,
                "smart_memory_stats": session_data.get("memory_stats", {})
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
            
            # Add assistant response vào smart memory
            if session_data.get("smart_memory"):
                session_data["smart_memory"].append({"role": "assistant", "content": response})
                session_data["memory_stats"] = session_data["smart_memory"].get_stats()
            
            session_data["message_count"] += 1
            return jsonify({
                "success": True,
                "response": response,
                "type": "expense_declaration",
                "expense_data": {"new_expenses": captured_expenses, "summary": summary},
                "memory_optimized": True,
                "smart_memory_stats": session_data.get("memory_stats", {})
            })

        # 4. RAG query
        elif session_data.get("type") == "rag_with_memory" and "rag_integration" in session_data:
            try:
                rag_integration = session_data["rag_integration"]
                rag_response = rag_integration.get_rag_response(message, use_hybrid=True)
                
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
                    "smart_memory_stats": session_data.get("memory_stats", {})
                })
            except Exception:
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
        
        # Add assistant response vào smart memory
        if session_data.get("smart_memory"):
            session_data["smart_memory"].append({"role": "assistant", "content": response})
            session_data["memory_stats"] = session_data["smart_memory"].get_stats()
        
        session_data["message_count"] += 1
        return jsonify({
            "success": True,
            "response": response,
            "type": "basic_response",
            "memory_optimized": True,
            "smart_memory_stats": session_data.get("memory_stats", {})
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
    """API: Lấy thống kê smart memory cho session"""
    if session_id not in chat_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_data = chat_sessions[session_id]
    smart_memory = session_data.get('smart_memory')
    
    if not smart_memory:
        return jsonify({'error': 'Smart memory not available for this session'}), 400
    
    try:
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
                'memory_utilization': len(smart_memory._conversation_history) / 10 * 100
            }
        }
        
        return jsonify(detailed_stats)
        
    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500


@app.route("/api/smart_memory/global_stats")
def get_global_smart_memory_stats():
    """API: Thống kê smart memory toàn cục"""
    try:
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
    """API: Force optimization cho session"""
    if session_id not in chat_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_data = chat_sessions[session_id]
    smart_memory = session_data.get('smart_memory')
    
    if not smart_memory:
        return jsonify({'error': 'Smart memory not available'}), 400
    
    try:
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
                    'new_stats': session_data['memory_stats']
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


if __name__ == "__main__":
    # Tạo thư mục cần thiết
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)

    print("🌐 Khởi động Trợ Lý Báo Cáo Chi Phí (Tối Ưu)...")
    print(f"   • RAG: {'✅' if RAG_AVAILABLE else '❌'}")
    print(f"   • Hybrid Memory: {'✅' if HYBRID_MEMORY_AVAILABLE else '❌'}")
    print(f"   • Chính sách: {len(EXPENSE_POLICIES)} danh mục")
    print("🚀 Server: http://localhost:5000")

    # Khởi động Enhanced Expense Memory
    if HYBRID_MEMORY_AVAILABLE:
        initialize_expense_memory()

    app.run(debug=True, host="0.0.0.0", port=5000)
