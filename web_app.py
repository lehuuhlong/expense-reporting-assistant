# Ứng dụng Web cho Trợ Lý Báo Cáo Chi Phí
"""
Ứng dụng web Flask cho chatbot trợ lý báo cáo chi phí
với giao diện thân thiện và tính năng chat thời gian thực.
"""

import asyncio
import concurrent.futures
import json
import os
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime
from queue import Empty, Queue

import torch
from flask import Flask, jsonify, render_template, request, send_file, session
from flask_cors import CORS
from transformers import AutoTokenizer, VitsModel

from cli import run_batch_chat, run_expense_batch_processing
from database import ExpenseDB
from expense_assistant import ExpenseAssistant, create_client
from functions import EXPENSE_POLICIES, MOCK_EXPENSE_REPORTS, SAMPLE_USER_QUERIES
from text_to_speech import text_to_speech as tts

app = Flask(__name__)
app.secret_key = "expense_assistant_secret_key_2024"
CORS(app)

# Khởi tạo cơ sở dữ liệu
db = ExpenseDB()

# 🆕 BATCHING SYSTEM FOR MULTIPLE USERS
class BatchingQueue:
    """Hệ thống batching tự động cho multiple users"""

    def __init__(self, batch_size=5, max_wait_time=2.0):
        self.batch_size = batch_size  # Số requests tối đa trong 1 batch
        self.max_wait_time = max_wait_time  # Thời gian chờ tối đa (giây)
        self.pending_requests = Queue()
        self.response_futures = {}
        self.is_running = False
        self.batch_thread = None
        self.stats = {
            "total_requests": 0,
            "total_batches": 0,
            "total_tokens_saved": 0,
            "average_batch_size": 0,
        }

    def start(self):
        """Khởi động batch processing thread"""
        if not self.is_running:
            self.is_running = True
            self.batch_thread = threading.Thread(
                target=self._batch_processor, daemon=True
            )
            self.batch_thread.start()
            print("🚀 Batch processing system started")

    def stop(self):
        """Dừng batch processing thread"""
        self.is_running = False
        if self.batch_thread:
            self.batch_thread.join()
            print("⏹️ Batch processing system stopped")

    def add_request(self, session_id, message, assistant):
        """Thêm request vào queue để batch processing"""
        request_id = str(uuid.uuid4())
        future = concurrent.futures.Future()

        request_data = {
            "id": request_id,
            "session_id": session_id,
            "message": message,
            "assistant": assistant,
            "timestamp": time.time(),
            "future": future,
        }

        self.pending_requests.put(request_data)
        self.response_futures[request_id] = future
        self.stats["total_requests"] += 1

        return future

    def _batch_processor(self):
        """Main batch processing loop"""
        while self.is_running:
            try:
                batch = self._collect_batch()
                if batch:
                    self._process_batch(batch)
                else:
                    time.sleep(0.1)  # Short sleep if no requests
            except Exception as e:
                print(f"❌ Batch processor error: {e}")
                time.sleep(1)

    def _collect_batch(self):
        """Thu thập requests để tạo batch"""
        batch = []
        deadline = time.time() + self.max_wait_time

        # Lấy request đầu tiên (blocking với timeout)
        try:
            first_request = self.pending_requests.get(timeout=1.0)
            batch.append(first_request)
        except Empty:
            return None

        # Thu thập thêm requests cho đến khi đạt batch_size hoặc timeout
        while len(batch) < self.batch_size and time.time() < deadline:
            try:
                remaining_time = max(0, deadline - time.time())
                request = self.pending_requests.get(timeout=remaining_time)
                batch.append(request)
            except Empty:
                break

        return batch

    def _process_batch(self, batch):
        """Xử lý một batch requests"""
        if not batch:
            return

        self.stats["total_batches"] += 1
        batch_size = len(batch)
        self.stats["average_batch_size"] = (
            self.stats["average_batch_size"] * (self.stats["total_batches"] - 1)
            + batch_size
        ) / self.stats["total_batches"]

        print(f"🔄 Processing batch of {batch_size} requests")

        try:
            # Nếu chỉ có 1 request, xử lý bình thường
            if batch_size == 1:
                self._process_single_request(batch[0])
            else:
                # Batch processing cho multiple requests
                self._process_multiple_requests(batch)

        except Exception as e:
            print(f"❌ Batch processing error: {e}")
            # Set error cho tất cả requests trong batch
            for req in batch:
                req["future"].set_exception(e)
                if req["id"] in self.response_futures:
                    del self.response_futures[req["id"]]

    def _process_single_request(self, request):
        """Xử lý single request"""
        try:
            assistant = request["assistant"]
            response = assistant.get_response(request["message"])

            request["future"].set_result(
                {
                    "success": True,
                    "response": response["content"],
                    "tokens_used": response.get("total_tokens", 0),
                    "function_calls": len(response.get("tool_calls", [])),
                    "function_details": response.get("tool_calls", []),
                    "batch_size": 1,
                    "batch_processing": False,
                }
            )

        except Exception as e:
            request["future"].set_exception(e)
        finally:
            if request["id"] in self.response_futures:
                del self.response_futures[request["id"]]

    def _process_multiple_requests(self, batch):
        """Xử lý multiple requests với batching optimization"""
        try:
            # Gom tất cả messages
            messages = [req["message"] for req in batch]

            # Sử dụng assistant từ request đầu tiên (có thể optimize thêm)
            primary_assistant = batch[0]["assistant"]

            # Batch processing
            batch_query = f"Xử lý batch {len(messages)} câu hỏi:\n"
            for i, msg in enumerate(messages, 1):
                batch_query += f"{i}. {msg}\n"

            batch_query += "\nVui lòng trả lời từng câu hỏi một cách ngắn gọn và có số thứ tự tương ứng."

            # Gọi API một lần cho cả batch
            response = primary_assistant.get_response(batch_query)

            # Parse response để chia cho từng request
            responses = self._parse_batch_response(response["content"], len(batch))

            # Estimate token savings
            estimated_single_tokens = len(batch) * 150  # Estimate
            actual_tokens = response.get("total_tokens", 0)
            tokens_saved = max(0, estimated_single_tokens - actual_tokens)
            self.stats["total_tokens_saved"] += tokens_saved

            # Set results cho từng request
            for i, req in enumerate(batch):
                individual_response = (
                    responses[i] if i < len(responses) else "Lỗi xử lý batch response"
                )

                req["future"].set_result(
                    {
                        "success": True,
                        "response": individual_response,
                        "tokens_used": actual_tokens // len(batch),  # Chia đều tokens
                        "function_calls": len(response.get("tool_calls", [])),
                        "function_details": response.get("tool_calls", []),
                        "batch_size": len(batch),
                        "batch_processing": True,
                        "tokens_saved": tokens_saved // len(batch),
                    }
                )

                if req["id"] in self.response_futures:
                    del self.response_futures[req["id"]]

        except Exception as e:
            # Set error cho tất cả requests
            for req in batch:
                req["future"].set_exception(e)
                if req["id"] in self.response_futures:
                    del self.response_futures[req["id"]]

    def _parse_batch_response(self, batch_response, expected_count):
        """Parse batch response thành individual responses"""
        responses = []

        # Try to split by numbers (1., 2., 3., etc.)
        import re

        parts = re.split(r"\n?\d+\.\s*", batch_response)

        # Remove empty first part if exists
        if parts and not parts[0].strip():
            parts = parts[1:]

        # If we don't get expected count, try other splitting methods
        if len(parts) != expected_count:
            # Try splitting by lines
            lines = [
                line.strip() for line in batch_response.split("\n") if line.strip()
            ]
            if len(lines) >= expected_count:
                parts = lines[:expected_count]
            else:
                # Fallback: repeat the whole response
                parts = [batch_response] * expected_count

        # Ensure we have enough responses
        while len(parts) < expected_count:
            parts.append("Không thể xử lý câu hỏi này trong batch.")

        return parts[:expected_count]

    def get_stats(self):
        """Lấy thống kê batching"""
        return self.stats.copy()


# Khởi tạo batching system
batching_queue = BatchingQueue(batch_size=5, max_wait_time=2.0)

# 🔧 BATCHING CONFIGURATION
ENABLE_AUTO_BATCHING = False  # Bật/tắt auto batching
BATCHING_CONFIG = {
    "batch_size": 5,  # Số requests tối đa trong 1 batch
    "max_wait_time": 2.0,  # Thời gian chờ tối đa (giây)
    "min_batch_size": 2,  # Số requests tối thiểu để trigger batch
}


# Khởi tạo assistant
try:
    client = create_client()
    assistant = ExpenseAssistant(client, model="GPT-4o-mini")
except Exception as e:
    print(f"Lỗi khởi tạo assistant: {e}")
    assistant = None

# Dictionary để lưu trữ các phiên chat
chat_sessions = {}


@app.route("/")
def home():
    """Trang chủ của ứng dụng web."""
    return render_template("index.html")


@app.route("/api/start_session", methods=["POST"])
def start_session():
    """Bắt đầu một phiên chat mới."""
    session_id = str(uuid.uuid4())

    # Tạo assistant mới cho phiên này
    if assistant:
        try:
            session_client = create_client()
            session_assistant = ExpenseAssistant(session_client, model="GPT-4o-mini")
            chat_sessions[session_id] = {
                "assistant": session_assistant,
                "created_at": datetime.now().isoformat(),
                "message_count": 0,
            }

            return jsonify(
                {
                    "success": True,
                    "session_id": session_id,
                    "message": "Phiên chat đã được tạo thành công!",
                }
            )
        except Exception as e:
            return (
                jsonify({"success": False, "error": f"Lỗi tạo phiên chat: {str(e)}"}),
                500,
            )
    else:
        return jsonify({"success": False, "error": "Assistant chưa được khởi tạo"}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """Xử lý tin nhắn chat với auto-batching."""
    data = request.get_json()
    session_id = data.get("session_id")
    message = data.get("message", "").strip()

    if not session_id or session_id not in chat_sessions:
        return jsonify({"success": False, "error": "Phiên chat không hợp lệ"}), 400

    if not message:
        return jsonify({"success": False, "error": "Tin nhắn không được để trống"}), 400

    try:
        session_assistant = chat_sessions[session_id]["assistant"]

        # Bước 1: Tìm kiếm trong imported data từ setup_db.py
        try:
            imported_collection = db.client.get_collection("imported_data")
            if imported_collection:
                # Tìm kiếm trong dữ liệu đã import
                import_results = imported_collection.query(
                    query_texts=[message],
                    n_results=2,  # Lấy 2 kết quả phù hợp nhất
                    where={"type": {"$in": ["policy", "expense_rule", "guideline"]}}  # Lọc theo loại dữ liệu
                )
                
                # Nếu tìm thấy kết quả phù hợp trong imported data
                if import_results and import_results['distances'][0] and min(import_results['distances'][0]) < 0.25:
                    imported_contexts = []
                    for i, doc in enumerate(import_results['documents'][0]):
                        meta = import_results['metadatas'][0][i]
                        imported_contexts.append(f"Thông tin từ {meta['type']}: {doc}")
                    
                    if imported_contexts:
                        message = f"Context từ dữ liệu có sẵn:\n{chr(10).join(imported_contexts)}\n\nCâu hỏi: {message}"
        except Exception as e:
            print(f"Warning: Không thể tìm trong imported data: {str(e)}")

        # Bước 2: Tìm kiếm trong lịch sử chat
        chat_history_collection = db.client.get_collection(name="chat_history")
        if chat_history_collection:
            # Tìm kiếm các tin nhắn tương tự
            results = chat_history_collection.query(
                query_texts=[message],
                n_results=3,  # Lấy 3 kết quả tương tự nhất
                where={"session_id": session_id}  # Lọc theo session hiện tại
            )
            
            # Nếu tìm thấy kết quả tương tự
            if results and results['distances'][0] and min(results['distances'][0]) < 0.3:  # Ngưỡng tương đồng
                similar_responses = []
                for i, doc in enumerate(results['documents'][0]):
                    if results['metadatas'][0][i]['role'] == 'assistant':
                        similar_responses.append(doc)
                
                # Thêm context từ lịch sử chat
                if similar_responses:
                    chat_context = "\n".join([f"Câu trả lời tương tự trước đây: {resp}" for resp in similar_responses])
                    if "Context từ dữ liệu có sẵn:" in message:
                        message += f"\n\nContext từ lịch sử chat:\n{chat_context}"
                    else:
                        message = f"Context từ lịch sử chat:\n{chat_context}\n\nCâu hỏi hiện tại: {message}"

        # Gửi tin nhắn đến assistant
        response = session_assistant.get_response(message)

        # Cập nhật số lượng tin nhắn
        chat_sessions[session_id]["message_count"] += 1

        # --- Lưu lịch sử chat vào ChromaDB ---
        chat_history_collection = db.client.get_or_create_collection(
            name="chat_history",
            embedding_function=db.embedding_fn,
            metadata={"description": "Lịch sử chat của user và assistant"},
        )
        chat_history_collection.add(
            documents=[message],
            ids=[f"{session_id}_user_{chat_sessions[session_id]['message_count']}"],
            metadatas=[{"session_id": session_id, "role": "user"}],
        )
        chat_history_collection.add(
            documents=[response["content"]],
            ids=[
                f"{session_id}_assistant_{chat_sessions[session_id]['message_count']}"
            ],
            metadatas=[{"session_id": session_id, "role": "assistant"}],
        )
        # --- Kết thúc lưu lịch sử ---

        # --- Tạo và lưu summary vào ChromaDB ---
        # Lấy summary (giả sử assistant có hàm get_conversation_summary)
        summary = session_assistant.get_conversation_summary()
        chat_summary_collection = db.client.get_or_create_collection(
            name="chat_summaries",
            embedding_function=db.embedding_fn,
            metadata={"description": "Tóm tắt hội thoại theo session"},
        )
        chat_summary_collection.add(
            documents=[summary],
            ids=[f"{session_id}_summary"],
            metadatas=[{"session_id": session_id, "type": "summary"}],
        )
        # --- Kết thúc lưu summary ---

        # 🆕 SỬ DỤNG BATCHING SYSTEM
        if ENABLE_AUTO_BATCHING:
            # Thêm request vào batching queue
            future = batching_queue.add_request(session_id, message, session_assistant)

            # Chờ kết quả từ batch processing
            result = future.result(timeout=10.0)  # 10s timeout

            # Cập nhật message count
            chat_sessions[session_id]["message_count"] += 1

            return jsonify(result)

        else:
            # Xử lý bình thường (không batching)
            response = session_assistant.get_response(message)

            # Cập nhật số lượng tin nhắn
            chat_sessions[session_id]["message_count"] += 1
            print(response["content"])
            return jsonify(
                {
                    "success": True,
                    "response": response["content"],
                    "function_calls": len(response.get("tool_calls", [])),
                    "tokens_used": response.get("total_tokens", 0),
                    "has_function_calls": len(response.get("tool_calls", [])) > 0,
                    "function_details": response.get("tool_calls", []),
                    "batch_processing": False,
                    "batch_size": 1,
                }
            )

    except concurrent.futures.TimeoutError:
        return (
            jsonify({"success": False, "error": "Timeout - Yêu cầu xử lý quá lâu"}),
            504,
        )

    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Lỗi xử lý tin nhắn: {str(e)}"}),
            500,
        )


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
        return (
            jsonify({"success": False, "error": f"Error generating speech: {str(e)}"}),
            500,
        )


@app.route("/audio/<filename>")
def serve_audio(filename):
    """Serves the generated audio file."""
    return send_file(os.path.join("audio_chats", filename))


@app.route("/api/batch_chat", methods=["POST"])
def batch_chat():
    """Xử lý batch chat với nhiều queries cùng lúc."""
    data = request.get_json()
    session_id = data.get("session_id")
    queries = data.get("queries", [])
    batch_size = data.get("batch_size", 3)

    if not session_id or session_id not in chat_sessions:
        return jsonify({"success": False, "error": "Phiên chat không hợp lệ"}), 400

    if not queries or not isinstance(queries, list):
        return (
            jsonify({"success": False, "error": "Danh sách queries không hợp lệ"}),
            400,
        )

    try:
        session_assistant = chat_sessions[session_id]["assistant"]

        # Thực hiện batch processing
        start_time = datetime.now()
        batch_results = []

        # Chia queries thành các batch nhỏ
        for i in range(0, len(queries), batch_size):
            batch_queries = queries[i : i + batch_size]

            # Xử lý parallel trong batch
            batch_responses = []
            for query in batch_queries:
                try:
                    response = session_assistant.get_response(query.strip())
                    batch_responses.append(
                        {
                            "query": query,
                            "response": response.get("content", ""),
                            "tokens_used": response.get("total_tokens", 0),
                            "function_calls": len(response.get("tool_calls", [])),
                            "success": True,
                        }
                    )
                except Exception as e:
                    batch_responses.append(
                        {"query": query, "error": str(e), "success": False}
                    )

            batch_results.extend(batch_responses)

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Cập nhật session stats
        chat_sessions[session_id]["message_count"] += len(queries)

        # Tính toán statistics
        successful_queries = [r for r in batch_results if r.get("success", False)]
        total_tokens = sum(r.get("tokens_used", 0) for r in successful_queries)
        total_function_calls = sum(
            r.get("function_calls", 0) for r in successful_queries
        )

        return jsonify(
            {
                "success": True,
                "batch_results": batch_results,
                "statistics": {
                    "total_queries": len(queries),
                    "successful_queries": len(successful_queries),
                    "failed_queries": len(queries) - len(successful_queries),
                    "total_tokens_used": total_tokens,
                    "total_function_calls": total_function_calls,
                    "processing_time_seconds": processing_time,
                    "average_time_per_query": (
                        processing_time / len(queries) if queries else 0
                    ),
                    "batch_size_used": batch_size,
                },
            }
        )

    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Lỗi xử lý batch chat: {str(e)}"}),
            500,
        )


@app.route("/api/batch_expense_processing", methods=["POST"])
def batch_expense_processing():
    """Xử lý batch expense processing."""
    data = request.get_json()
    expenses = data.get(
        "expenses", MOCK_EXPENSE_REPORTS
    )  # Sử dụng mock data nếu không có input

    try:
        start_time = datetime.now()

        # Sử dụng function từ cli module
        batch_result = run_expense_batch_processing()

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Thêm thông tin timing
        batch_result["processing_time_seconds"] = processing_time
        batch_result["expenses_processed"] = len(expenses)

        return jsonify({"success": True, "batch_result": batch_result})

    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Lỗi xử lý batch expense: {str(e)}"}),
            500,
        )


@app.route("/api/sample_questions")
def sample_questions():
    """Lấy danh sách câu hỏi mẫu."""
    return jsonify({"success": True, "questions": SAMPLE_USER_QUERIES})


@app.route("/api/batching_stats", methods=["GET"])
def get_batching_stats():
    """Lấy thống kê batching system."""
    try:
        stats = batching_queue.get_stats()
        queue_size = batching_queue.pending_requests.qsize()

        return jsonify(
            {
                "success": True,
                "stats": {
                    "enabled": ENABLE_AUTO_BATCHING,
                    "queue_size": queue_size,
                    "total_requests": stats["total_requests"],
                    "total_batches": stats["total_batches"],
                    "average_batch_size": round(stats["average_batch_size"], 2),
                    "total_tokens_saved": stats["total_tokens_saved"],
                    "config": BATCHING_CONFIG,
                    "is_running": batching_queue.is_running,
                },
            }
        )

    except Exception as e:
        return (
            jsonify(
                {"success": False, "error": f"Lỗi lấy thống kê batching: {str(e)}"}
            ),
            500,
        )


@app.route("/api/batching_control", methods=["POST"])
def control_batching():
    """Bật/tắt batching system."""
    try:
        data = request.get_json()
        action = data.get("action", "").lower()

        global ENABLE_AUTO_BATCHING

        if action == "enable":
            ENABLE_AUTO_BATCHING = True
            if not batching_queue.is_running:
                batching_queue.start()
            message = "Auto-batching đã được bật"

        elif action == "disable":
            ENABLE_AUTO_BATCHING = False
            message = "Auto-batching đã được tắt (queue vẫn chạy)"

        elif action == "restart":
            batching_queue.stop()
            time.sleep(0.5)
            batching_queue.start()
            message = "Batching queue đã được restart"

        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Action không hợp lệ. Sử dụng: enable, disable, restart",
                    }
                ),
                400,
            )

        return jsonify(
            {
                "success": True,
                "message": message,
                "enabled": ENABLE_AUTO_BATCHING,
                "running": batching_queue.is_running,
            }
        )

    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Lỗi điều khiển batching: {str(e)}"}),
            500,
        )


@app.route("/api/system_info")
def system_info():
    """Lấy thông tin hệ thống."""
    return jsonify(
        {
            "success": True,
            "info": {
                "total_policies": len(EXPENSE_POLICIES),
                "sample_expenses": len(MOCK_EXPENSE_REPORTS),
                "active_sessions": len(chat_sessions),
                "openai_connected": assistant is not None,
                "base_url": os.getenv("OPENAI_BASE_URL", "Chưa thiết lập"),
                "model": os.getenv("OPENAI_DEPLOYMENT", "GPT-4o-mini"),
                "batching_enabled": True,
                "features": {
                    "batch_chat": True,
                    "batch_expense_processing": True,
                    "parallel_processing": True,
                    "token_optimization": True,
                },
            },
        }
    )


@app.route("/api/clear_session", methods=["POST"])
def clear_session():
    """Xóa phiên chat."""
    data = request.get_json()
    session_id = data.get("session_id")

    if session_id and session_id in chat_sessions:
        chat_sessions[session_id]["assistant"].clear_conversation()
        chat_sessions[session_id]["message_count"] = 0

        return jsonify({"success": True, "message": "Phiên chat đã được xóa"})

    return jsonify({"success": False, "error": "Phiên chat không tồn tại"}), 400


@app.route("/api/session_stats/<session_id>")
def session_stats(session_id):
    """Lấy thống kê phiên chat."""
    if session_id in chat_sessions:
        session_data = chat_sessions[session_id]
        return jsonify(
            {
                "success": True,
                "stats": {
                    "created_at": session_data["created_at"],
                    "message_count": session_data["message_count"],
                    "conversation_summary": session_data[
                        "assistant"
                    ].get_conversation_summary(),
                },
            }
        )

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
    # Tạo thư mục templates nếu chưa có
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)

    print("🌐 Khởi động ứng dụng web Trợ Lý Báo Cáo Chi Phí...")
    print("📊 Trạng thái hệ thống:")
    print(f"   • Assistant: {'✅ Sẵn sàng' if assistant else '❌ Lỗi'}")
    print(f"   • Chính sách: {len(EXPENSE_POLICIES)} danh mục")
    print(f"   • Dữ liệu mẫu: {len(MOCK_EXPENSE_REPORTS)} chi phí")
    print(f"   🆕 Batching: ✅ Đã tích hợp")
    print(f"   🆕 Tính năng:")
    print(f"      • Batch Chat Processing")
    print(f"      • Batch Expense Processing")
    print(f"      • Token Usage Optimization")
    print("🚀 Mở trình duyệt và truy cập: http://localhost:5000")
    print("📋 API Endpoints:")
    print("   • POST /api/batch_chat - Xử lý nhiều chat queries")
    print("   • POST /api/batch_expense_processing - Batch expense processing")
    print("🆕 Auto-Batching Endpoints:")
    print("   • GET /api/batching_stats - Thống kê batching")
    print("   • POST /api/batching_control - Điều khiển batching")

    # 🚀 Khởi động Auto-Batching System
    if ENABLE_AUTO_BATCHING:
        batching_queue.start()
        print("✅ Auto-batching system started")

    try:
        app.run(debug=True, host="0.0.0.0", port=5000)
    finally:
        # Cleanup khi server dừng
        batching_queue.stop()
