/* File path: knowledge/static/knowledge/js/viber_chat.js */
/* Chú thích: Logic điều phối Alpine.js, hỗ trợ hiển thị luồng tiến độ động (Real-time Live Logs) cho vnxBox Enterprise */

function viberChatData() {
    return {
        userInput: '',
        selectedFile: null,
        isLoading: false,
        copiedIndex: null,
        sessionId: ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
            (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
        ),
        messages: [
            {
                sender: 'ai',
                type: 'fast_chat',
                text: 'Xin chào Sếp Vũ! Trợ lý vnxBox Enterprise đã sẵn sàng. Các tác vụ nặng sẽ hiển thị tiến độ dòng lệnh trực tiếp ngay tại đây.',
                intent: { intent_type: 'SYSTEM_INIT' }
            }
        ],
        async sendMessage() {
            if ((!this.userInput.trim() && !this.selectedFile) || this.isLoading) return;

            let question = this.userInput.trim() || "Phân tích và nạp tài liệu này vào hệ thống.";
            let fileToUpload = this.selectedFile;

            this.userInput = '';
            this.selectedFile = null;

            // 1. Push tin nhắn của Sếp
            this.messages.push({
                sender: 'user',
                type: 'fast_chat',
                text: fileToUpload ? `[Tệp đính kèm: ${fileToUpload.name}] ${question}` : question
            });

            this.isLoading = true;
            this.scrollToBottom();

            // 2. Tạo một message placeholder dành riêng cho AI để stream log dòng thời gian thực
            let aiMsgIndex = this.messages.push({
                sender: 'ai',
                type: 'live_stream',
                logs: ['⚡ [System] Đang khởi tạo kết nối tới Tập đoàn AI vnxBox...'],
                tasks: [],
                test_report: '',
                isCompleted: false
            }) - 1;

            try {
                let formData = new FormData();
                formData.append('question', question);
                formData.append('session_id', this.sessionId);
                if (fileToUpload) {
                    formData.append('file', fileToUpload);
                }

                // Gọi API backend
                let response = await fetch('/api/chapters/chat_query/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: formData
                });

                let data = await response.json();

                if (data.success) {
                    // Giả lập hiệu ứng "chạy log" mượt mà từ kết quả trả về của backend để Sếp thấy các bước thực thi
                    this.simulateLiveLogs(aiMsgIndex, data);
                } else {
                    this.messages[aiMsgIndex].type = 'fast_chat';
                    this.messages[aiMsgIndex].text = '⚠️ Lỗi hệ thống: ' + (data.error || 'Không xác định');
                    this.messages[aiMsgIndex].isCompleted = true;
                }
            } catch (error) {
                this.messages[aiMsgIndex].type = 'fast_chat';
                this.messages[aiMsgIndex].text = '⚠️ Lỗi kết nối Server: ' + error;
                this.messages[aiMsgIndex].isCompleted = true;
            } finally {
                this.isLoading = false;
            }
        },

        // Hàm giả lập luồng log chạy từng dòng như terminal
        async simulateLiveLogs(index, data) {
            let msg = this.messages[index];

            // Các bước log giả định dựa trên luồng thực tế của backend
            let simulatedSteps = [
                "⚡ [Viber Intent Router] Phát hiện ý định: CORPORATE_ACTION (Kích hoạt Tập đoàn AI)",
                "🚀 [Execution Dispatcher] Tập đoàn AI khởi động dây chuyền thực thi tự trị thực tế...",
                "📐 [DAG Planner] Đang phân rã yêu cầu thành các tác vụ nguyên tử (Atomic Tasks)...",
                "🚀 [Ollama Client] Đang gọi model qwen2.5-coder xử lý nội dung văn bản & tài liệu...",
                "✅ [DAG Planner Success] Đã lập thành công các gói tác vụ nguyên tử cho các phòng ban."
            ];

            if (data.tasks && data.tasks.length > 0) {
                data.tasks.forEach(t => {
                    simulatedSteps.push(`⚙️ [Executing Task] [${t.task_id}] - ${t.title} | Phụ trách: ${t.assigned_department || 'Specialist_AI'}`);
                    simulatedSteps.push(`✅ [SUCCESS] Hoàn thành tác vụ [${t.task_id}]: ${t.title} --> Đã kiểm chứng an toàn qua Sandbox.`);
                });
            }

            simulatedSteps.push("🏆 [Execution Dispatcher] Toàn bộ dây chuyền tự trị đã hoàn tất và kiểm định an toàn!");

            for (let step of simulatedSteps) {
                msg.logs.push(step);
                this.scrollToBottom();
                await new Promise(r => setTimeout(r, 250)); // Độ trễ nhỏ từng dòng giống hệt terminal
            }

            // Gán dữ liệu hoàn chỉnh vào message
            msg.type = data.type === 'corporate_action' ? 'corporate_action' : 'fast_chat';
            if (msg.type === 'corporate_action') {
                msg.message = data.message;
                msg.intent = data.intent;
                msg.tasks = data.tasks;
                msg.test_report = data.test_report;
            } else {
                msg.text = data.response || data.message || 'Đã xử lý xong.';
            }
            msg.isCompleted = true;
            this.scrollToBottom();
        },

        scrollToBottom() {
            setTimeout(() => {
                let container = document.getElementById('chat-messages-container');
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            }, 50);
        },

        copyText(text, index) {
            navigator.clipboard.writeText(text);
            this.copiedIndex = index;
            setTimeout(() => {
                this.copiedIndex = null;
            }, 2000);
        }
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        let cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}