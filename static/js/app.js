// JavaScript cho Trợ Lý Báo Cáo Chi Phí
class ExpenseAssistantApp {
  constructor() {
    this.sessionId = null;
    this.messageCount = 0;
    this.isConnected = false;
    this.isProcessing = false;
    this.audioCache = {};
    this.currentAudio = null;
    this.smartMemoryStats = { tokensSaved: 0, summariesCount: 0, efficiency: '0%' };

    this.initializeApp();
    this.bindEvents();
    this.loadSampleQuestions();
  }

  async initializeApp() {
    try {
      await this.startNewSession();
      this.updateConnectionStatus('online', 'Đã kết nối');
      this.enableInput();
    } catch (error) {
      console.error('Lỗi khởi tạo ứng dụng:', error);
      this.updateConnectionStatus('offline', 'Lỗi kết nối');
      this.showError('Không thể kết nối đến máy chủ. Vui lòng thử lại.');
    }
  }

  bindEvents() {
    // Đảm bảo các elements tồn tại trước khi bind
    const bindIfExists = (id, event, handler) => {
      const element = document.getElementById(id);
      if (element) {
        element.addEventListener(event, handler);
        console.log(`✅ Event bound: ${id}`);
      } else {
        console.error(`❌ Element not found: ${id}`);
      }
    };

    // Form submit
    bindIfExists('chat-form', 'submit', (e) => {
      e.preventDefault();
      this.sendMessage();
    });

    // Clear chat button
    bindIfExists('clear-chat', 'click', () => {
      this.clearChat();
    });

    // New session button
    bindIfExists('new-session', 'click', () => {
      this.startNewSession();
    });

    // Optimize memory button  
    bindIfExists('optimize-memory', 'click', () => {
      this.optimizeMemory();
    });

    // Test RAG button
    bindIfExists('test-rag', 'click', () => {
      this.testRAG();
    });

    // 🧠 Smart Memory optimization button
    bindIfExists('optimize-memory', 'click', () => {
      this.optimizeMemory();
    });

    // Enter key in input
    bindIfExists('message-input', 'keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });
  }

  async startNewSession() {
    try {
      const response = await fetch('/api/start_session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success) {
        this.sessionId = data.session_id;
        this.messageCount = 0;
        this.isConnected = true;
        this.updateSessionStats();
        this.clearChatMessages();
        this.showWelcomeMessage();
        
        // Update Smart Memory status nếu có
        if (data.memory_stats) {
          this.updateSmartMemoryStats(data.memory_stats);
        }
        
        // Load smart memory stats for this session
        this.loadSmartMemoryStats();
        
        console.log('Phiên mới đã được tạo:', this.sessionId);
      } else {
        throw new Error(data.error);
      }
    } catch (error) {
      console.error('Lỗi tạo phiên mới:', error);
      throw error;
    }
  }

  async sendMessage() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();

    if (!message || this.isProcessing || !this.isConnected) {
      return;
    }

    this.isProcessing = true;
    this.disableInput();

    // Hiển thị tin nhắn người dùng
    this.displayMessage(message, 'user');
    messageInput.value = '';

    // Hiển thị typing indicator
    this.showTypingIndicator();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: this.sessionId,
          message: message,
        }),
      });

      const data = await response.json();

      // Ẩn typing indicator
      this.hideTypingIndicator();

      if (data.success) {
        // Hiển thị phản hồi từ assistant
        this.displayMessage(data.response, 'assistant', {
          function_calls: data.function_calls,
          tokens_used: data.tokens_used,
          function_details: data.function_details,
          batch_processing: data.batch_processing,
          batch_size: data.batch_size,
          tokens_saved: data.tokens_saved,
          knowledge_base_used: data.knowledge_base_used,
          has_audio: data.has_audio,
          audio_url: data.audio_url,
          audio_error: data.audio_error,
          // 🆕 RAG System info
          rag_used: data.rag_used,
          response_type: data.response_type,
          sources: data.sources
        });

        // Update RAG response counter if RAG was used
        if (data.rag_used) {
          this.updateRAGResponseCount();
        }

        // Update Smart Memory stats nếu có
        if (data.smart_memory_stats) {
          this.updateSmartMemoryStats(data.smart_memory_stats);
        }

        this.messageCount += 2; // User + Assistant
        this.updateSessionStats();
      } else {
        this.showError(data.error);
      }
    } catch (error) {
      this.hideTypingIndicator();
      console.error('Lỗi gửi tin nhắn:', error);
      this.showError('Lỗi kết nối. Vui lòng thử lại.');
    } finally {
      this.isProcessing = false;
      this.enableInput();
    }
  }

  displayMessage(content, sender, metadata = {}) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    let metaInfo = '';
    if (metadata.function_calls > 0) {
      metaInfo += `<div class="function-calls">
                <strong><i class="fas fa-cog me-1"></i>Đã sử dụng ${metadata.function_calls} chức năng</strong>`;

      if (metadata.function_details && metadata.function_details.length > 0) {
        metadata.function_details.forEach((detail) => {
          metaInfo += `<div class="function-call">🔧 ${detail.function}()</div>`;
        });
      }
      metaInfo += '</div>';
    }

    if (metadata.tokens_used) {
      metaInfo += `<div class="message-meta">
                <i class="fas fa-microchip me-1"></i>Tokens: ${metadata.tokens_used}
                ${metadata.function_calls > 0 ? ` | Chức năng: ${metadata.function_calls}` : ''}
                ${metadata.knowledge_base_used ? ` | 📚 Knowledge Base` : ''}
                ${metadata.batch_processing ? ` | 🚀 Batched (${metadata.batch_size})` : ''}
                ${metadata.tokens_saved ? ` | 💰 Saved: ${metadata.tokens_saved}` : ''}
            </div>`;
    }

    // Add audio controls if audio is available
    let audioControls = '';
    if (metadata.has_audio && metadata.audio_url) {
      audioControls = `<div class="audio-controls mt-2">
                <button class="btn btn-sm btn-outline-primary" onclick="app.playAudio('${metadata.audio_url}')">
                    <i class="fas fa-play me-1"></i>Nghe Audio
                </button>
                <button class="btn btn-sm btn-outline-secondary ms-1" onclick="app.downloadAudio('${metadata.audio_url}')">
                    <i class="fas fa-download me-1"></i>Tải về
                </button>
            </div>`;
    } else if (metadata.audio_error) {
      audioControls = `<div class="audio-error mt-2">
                <small class="text-muted">
                    <i class="fas fa-exclamation-triangle me-1"></i>Không thể tạo audio
                </small>
            </div>`;
    }

    const ttsButton =
      sender === 'assistant'
        ? `<button class="btn btn-sm btn-outline-primary tts-button" onclick="window.expenseApp.textToSpeech(this)">
                <i class="fas fa-volume-up"></i>
             </button>`
        : '';

    messageDiv.innerHTML = `
            <div class="message-content" data-text="${content}">
                ${this.formatMessage(content)}
                ${metaInfo}
                ${audioControls}
            </div>
            <div class="message-meta">
                <i class="fas fa-clock me-1"></i>${new Date().toLocaleTimeString('vi-VN')}
                ${ttsButton}
            </div>
        `;

    chatMessages.appendChild(messageDiv);
    this.scrollToBottom();
  }

  async textToSpeech(button) {
    const messageContent = button.closest('.message').querySelector('.message-content');
    const text = messageContent.dataset.text;

    if (!text) return;

    if (this.currentAudio) {
      const playingButton = this.currentAudio.button;
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;

      if (playingButton) {
        playingButton.disabled = false;
        playingButton.innerHTML = '<i class="fas fa-volume-up"></i>';
      }

      if (playingButton === button) {
        this.currentAudio = null;
        return;
      }
    }

    const play = (url) => {
      const audio = new Audio(url);
      audio.button = button;
      this.currentAudio = audio;

      audio.onended = () => {
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        if (this.currentAudio === audio) {
          this.currentAudio = null;
        }
      };

      audio.onerror = () => {
        this.showError('Error playing audio file.');
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        if (this.currentAudio === audio) {
          this.currentAudio = null;
        }
      };

      audio.play();
      button.innerHTML = '<i class="fas fa-stop"></i>';
    };

    if (this.audioCache[text]) {
      play(this.audioCache[text]);
    } else {
      button.disabled = true;
      button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
      try {
        const response = await fetch('/api/text-to-speech', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text }),
        });

        if (response.ok) {
          const data = await response.json();
          this.audioCache[text] = data.audio_url;
          button.disabled = false;
          play(data.audio_url);
        } else {
          this.showError('Failed to generate speech.');
          button.disabled = false;
          button.innerHTML = '<i class="fas fa-volume-up"></i>';
          this.currentAudio = null;
        }
      } catch (error) {
        this.showError('Error fetching audio.');
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-volume-up"></i>';
        this.currentAudio = null;
      }
    }
  }

  formatMessage(content) {
    // Chuyển đổi markdown cơ bản và emoji
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>')
      .replace(/💰/g, '💰')
      .replace(/📋/g, '📋')
      .replace(/✅/g, '✅')
      .replace(/❌/g, '❌')
      .replace(/⚠️/g, '⚠️');
  }

  showTypingIndicator() {
    const chatMessages = document.getElementById('chat-messages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = `
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
    chatMessages.appendChild(typingDiv);
    this.scrollToBottom();
  }

  hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
      typingIndicator.remove();
    }
  }

  async clearChat() {
    if (!this.sessionId) return;

    try {
      const response = await fetch('/api/clear_session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: this.sessionId,
        }),
      });

      const data = await response.json();

      if (data.success) {
        this.messageCount = 0;
        this.clearChatMessages();
        this.showWelcomeMessage();
        this.updateSessionStats();
        this.showSuccess('Cuộc trò chuyện đã được xóa');
      }
    } catch (error) {
      console.error('Lỗi xóa chat:', error);
      this.showError('Lỗi xóa cuộc trò chuyện');
    }
  }

  clearChatMessages() {
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.innerHTML = '';
  }

  showWelcomeMessage() {
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.innerHTML = `
            <div class="welcome-message text-center p-4">
                <i class="fas fa-robot fa-3x text-primary mb-3"></i>
                <h5>Chào mừng đến với Trợ Lý Báo Cáo Chi Phí!</h5>
                <p class="text-muted">Tôi có thể giúp bạn:</p>
                <ul class="list-unstyled">
                    <li>📋 Tìm hiểu chính sách chi phí công ty</li>
                    <li>💰 Tính toán hoàn tiền chi phí</li>
                    <li>✅ Kiểm tra tính hợp lệ của chi phí</li>
                    <li>📊 Tạo báo cáo chi phí</li>
                </ul>
                <p class="small text-muted">Bắt đầu bằng cách gõ câu hỏi hoặc chọn câu hỏi mẫu bên trái.</p>
            </div>
        `;
  }

  async loadSampleQuestions() {
    try {
      const response = await fetch('/api/sample_questions');
      const data = await response.json();

      if (data.success) {
        const container = document.getElementById('sample-questions');
        container.innerHTML = '';

        data.questions.slice(0, 6).forEach((question) => {
          const item = document.createElement('div');
          item.className = 'list-group-item';
          item.textContent = question;
          item.addEventListener('click', () => {
            document.getElementById('message-input').value = question;
            this.sendMessage();
          });
          container.appendChild(item);
        });
      }
    } catch (error) {
      console.error('Lỗi tải câu hỏi mẫu:', error);
    }
  }

  updateConnectionStatus(status, text) {
    const statusElement = document.getElementById('connection-status');
    const sessionStatusElement = document.getElementById('session-status');

    statusElement.className = `badge status-${status}`;
    statusElement.textContent = text;

    if (sessionStatusElement) {
      sessionStatusElement.className = `badge status-${status}`;
      sessionStatusElement.textContent = status === 'online' ? 'Đã kết nối' : 'Chưa kết nối';
    }
  }

  updateSessionStats() {
    document.getElementById('message-count').textContent = this.messageCount;
  }

  enableInput() {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');

    messageInput.disabled = false;
    sendButton.disabled = false;
    messageInput.focus();
  }

  disableInput() {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');

    messageInput.disabled = true;
    sendButton.disabled = true;
  }

  setProcessing(processing) {
    this.isProcessing = processing;

    if (processing) {
      this.disableInput();
      // Hiển thị loading modal
      const loadingModal = document.getElementById('loading-modal');
      if (loadingModal) {
        const modal = new bootstrap.Modal(loadingModal);
        modal.show();
      }
    } else {
      this.enableInput();
      // Ẩn loading modal
      const loadingModal = document.getElementById('loading-modal');
      if (loadingModal) {
        const modal = bootstrap.Modal.getInstance(loadingModal);
        if (modal) {
          modal.hide();
        }
      }
    }
  }

  scrollToBottom() {
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  showError(message) {
    this.showNotification(message, 'danger');
  }

  showSuccess(message) {
    this.showNotification(message, 'success');
  }

  showNotification(message, type) {
    // Tạo toast notification
    const toastContainer = document.createElement('div');
    toastContainer.className = 'position-fixed top-0 end-0 p-3';
    toastContainer.style.zIndex = '11';

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');

    toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast"></button>
            </div>
        `;

    toastContainer.appendChild(toast);
    document.body.appendChild(toastContainer);

    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    // Xóa toast sau khi ẩn
    toast.addEventListener('hidden.bs.toast', () => {
      document.body.removeChild(toastContainer);
    });
  }

  // New audio handling methods for enhanced chatbot
  playAudio(audioUrl) {
    this.playAudioFromUrl(audioUrl);
  }

  playAudioFromUrl(audioUrl) {
    try {
      // Stop current audio if playing
      if (this.currentAudio) {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
      }

      // Create new audio instance
      this.currentAudio = new Audio(audioUrl);
      
      // Add event listeners
      this.currentAudio.addEventListener('loadstart', () => {
        console.log('🔊 Loading audio...');
      });
      
      this.currentAudio.addEventListener('canplay', () => {
        console.log('✅ Audio ready to play');
      });
      
      this.currentAudio.addEventListener('ended', () => {
        console.log('🔇 Audio playback ended');
        this.currentAudio = null;
      });
      
      this.currentAudio.addEventListener('error', (e) => {
        console.error('❌ Audio error:', e);
        this.showError('Không thể phát audio');
      });

      // Play the audio
      this.currentAudio.play().catch(error => {
        console.error('Playback error:', error);
        this.showError('Không thể phát audio. Kiểm tra trình duyệt có cho phép auto-play.');
      });
      
    } catch (error) {
      console.error('Audio handling error:', error);
      this.showError('Lỗi xử lý audio');
    }
  }

  downloadAudio(audioUrl) {
    try {
      const link = document.createElement('a');
      link.href = audioUrl;
      link.download = audioUrl.split('/').pop();
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Download error:', error);
      this.showError('Không thể tải file audio');
    }
  }

  // 🆕 RAG System Methods - Workshop 4
  async loadRAGStatus() {
    try {
      const response = await fetch('/api/rag/stats');
      const data = await response.json();
      
      if (data.success) {
        this.updateRAGStatus(data.stats, data.rag_available);
      } else {
        this.updateRAGStatus(null, false);
      }
    } catch (error) {
      console.error('RAG status error:', error);
      this.updateRAGStatus(null, false);
    }
  }

  updateRAGStatus(stats, available) {
    const statusElement = document.getElementById('rag-system-status');
    const vectorCountElement = document.getElementById('vector-db-count');
    const functionCallingElement = document.getElementById('function-calling-status');
    const testButton = document.getElementById('test-rag');

    if (available && stats) {
      statusElement.textContent = 'Hoạt động';
      statusElement.className = 'badge bg-success';
      
      vectorCountElement.textContent = stats.vector_store_documents || 0;
      
      functionCallingElement.textContent = 'Có';
      functionCallingElement.className = 'badge bg-success';
      
      if (testButton) {
        testButton.disabled = false;
        testButton.onclick = () => this.testRAGSystem();
      }
    } else {
      statusElement.textContent = 'Không khả dụng';
      statusElement.className = 'badge bg-danger';
      
      vectorCountElement.textContent = '-';
      
      functionCallingElement.textContent = 'Không';
      functionCallingElement.className = 'badge bg-danger';
      
      if (testButton) {
        testButton.disabled = true;
      }
    }
  }

  async testRAGSystem() {
    const testQueries = [
      "Chính sách chi phí ăn uống như thế nào?",
      "Tôi có thể báo cáo chi phí gì?",
      "Giới hạn chi phí đi lại ra sao?"
    ];
    
    const randomQuery = testQueries[Math.floor(Math.random() * testQueries.length)];
    
    try {
      const response = await fetch('/api/rag/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: randomQuery,
          use_hybrid: true
        })
      });

      const data = await response.json();
      
      if (data.success) {
        this.addMessage('RAG Test Query: ' + randomQuery, 'user');
        this.addMessage(data.response, 'assistant');
        
        if (data.sources && data.sources.length > 0) {
          this.addMessage(`📚 Sources: ${data.sources.length} documents found`, 'system');
        }
      } else {
        this.showError('RAG test failed: ' + data.error);
      }
    } catch (error) {
      console.error('RAG test error:', error);
      this.showError('Không thể test RAG system');
    }
  }

  updateRAGResponseCount() {
    const countElement = document.getElementById('rag-response-count');
    if (countElement) {
      const currentCount = parseInt(countElement.textContent) || 0;
      countElement.textContent = currentCount + 1;
    }
  }

  // 🧠 Smart Memory Methods
  updateSmartMemoryStats(stats) {
    this.smartMemoryStats = {
      tokensSaved: stats.total_tokens_saved || 0,
      summariesCount: stats.summaries_created || 0,
      efficiency: stats.efficiency_ratio || '0%'
    };

    // Update UI elements
    const statusElement = document.getElementById('smart-memory-status');
    const tokensSavedElement = document.getElementById('tokens-saved');
    const summariesElement = document.getElementById('summaries-count');
    const efficiencyElement = document.getElementById('memory-efficiency');

    if (statusElement) {
      statusElement.textContent = 'Active';
      statusElement.className = 'badge bg-success';
    }

    if (tokensSavedElement) {
      tokensSavedElement.textContent = this.smartMemoryStats.tokensSaved.toLocaleString();
    }

    if (summariesElement) {
      summariesElement.textContent = this.smartMemoryStats.summariesCount;
    }

    if (efficiencyElement) {
      efficiencyElement.textContent = this.smartMemoryStats.efficiency;
    }

    // Enable optimize button if significant savings
    const optimizeButton = document.getElementById('optimize-memory');
    if (optimizeButton) {
      optimizeButton.disabled = this.smartMemoryStats.tokensSaved < 100;
    }
  }

  async optimizeMemory() {
    if (!this.sessionId) {
      this.showError('Không có phiên hoạt động để tối ưu');
      return;
    }

    try {
      const optimizeButton = document.getElementById('optimize-memory');
      if (optimizeButton) {
        optimizeButton.disabled = true;
        optimizeButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Optimizing...';
      }

      const response = await fetch(`/api/smart_memory/optimize/${this.sessionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success) {
        this.updateSmartMemoryStats(data.new_stats);
        this.showSuccess('Memory optimization completed successfully!');
        
        // Show optimization result
        if (data.optimization_result && data.optimization_result.tokens_saved > 0) {
          this.addMessage(`🧠 Memory optimized: ${data.optimization_result.tokens_saved} tokens saved`, 'system');
        }
      } else {
        this.showError(data.error);
      }
    } catch (error) {
      console.error('Memory optimization error:', error);
      this.showError('Memory optimization failed');
    } finally {
      const optimizeButton = document.getElementById('optimize-memory');
      if (optimizeButton) {
        optimizeButton.disabled = false;
        optimizeButton.innerHTML = '<i class="fas fa-compress me-1"></i>Optimize Memory';
      }
    }
  }

  async loadSmartMemoryStats() {
    if (!this.sessionId) return;

    try {
      const response = await fetch(`/api/smart_memory/stats/${this.sessionId}`);
      const data = await response.json();
      
      if (data.success && data.stats) {
        this.updateSmartMemoryStats(data.stats);
      }
    } catch (error) {
      console.error('Failed to load smart memory stats:', error);
    }
  }
}

// Khởi tạo ứng dụng khi DOM đã load
document.addEventListener('DOMContentLoaded', () => {
  const app = new ExpenseAssistantApp();

  // Load RAG status after app initialization
  setTimeout(() => {
    app.loadRAGStatus();
  }, 1000);

  // Debug trong console và global access
  window.expenseApp = app;
  window.app = app; // For easier access in HTML onclick handlers
  console.log('🚀 Trợ Lý Báo Cáo Chi Phí đã sẵn sàng!');
  console.log('🔊 Enhanced with TTS and Knowledge Base!');
  console.log('🧠 RAG System Integration - Workshop 4');
});
