// File path: static/dashboard/js/dashboard.js
// Chú thích: Script quản lý toàn bộ logic Frontend Alpine.js cho vnxBox Enterprise.
// Tích hợp đầy đủ các hàm Ingestion (Nạp file), Chat Workspace, Recompile, Quản Trị Kho Tri Thức,
// và tiện ích Copy Bảng dữ liệu tự động.

document.addEventListener('alpine:init', () => {
    Alpine.data('knowledgeApp', () => ({
        currentView: 'chat',
        session_id: localStorage.getItem('vnxbox_session_id') || crypto.randomUUID(),
        chapters: [],
        selectedChapter: null,
        filterStatus: '',
        filterDomain: '',
        filterSubDomain: '',
        question: '',
        loading: false,
        isThinking: false,
        currentStepIndex: 0,

        // Mảng các bước tư duy động theo tiến trình thực tế của vnxBox 2026
        thinkingSteps: [
            "Đang khởi tạo kết nối Secure Sandbox...",
            "Đang phân tích ý định người dùng (Intent Routing)...",
            "Đang tra cứu Kho tri thức qua Hybrid Search (Vector + Metadata)...",
            "Đang trích xuất văn bản và ngữ cảnh quy định nội bộ...",
            "Đang thực thi mã tính toán an toàn & định dạng số học..."
        ],
        stepInterval: null,

        messages: [
            {
                sender: 'ai',
                text: 'Chào Vũ! Tôi là vnxBox Local AI Platform. Hệ thống đã sẵn sàng hỗ trợ tra cứu quy định và tính toán qua Secure Sandbox.',
                citations: [],
                sandbox_execution: null
            }
        ],

        // States cho Modal Nạp File & Ingestion
        showUploadModal: false,
        newDomain: '',
        newSubDomain: '',
        newRawText: '',
        selectedFile: null,
        ingesting: false,

        // States cho Modal Recompile & Quản Trị
        showRecompileModal: false,
        selectedChapterIdForRecompile: null,
        recompileInstruction: 'Hãy biên soạn, chuẩn hóa lại nội dung này mạch lạc, rõ ràng hơn.',
        recompiling: false,

        // ==========================================
        // HÀM AI BIÊN SOẠN LẠI TRI THỨC (RECOMPILE)
        // ==========================================
        async recompileWithAI() {
            if (!this.selectedChapter || this.recompiling) return;

            this.recompiling = true;
            try {
                let res = await fetch(`/api/chapters/${this.selectedChapter.id}/recompile_with_ai/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    },
                    body: JSON.stringify({
                        instruction: this.recompileInstruction
                    })
                });

                let data = await res.json();
                if (res.ok && data.success) {
                    alert("✨ AI đã biên soạn lại tri thức thành công và cập nhật phiên bản mới!");
                    this.showRecompileModal = false;
                    this.selectedChapter = data.data;
                    await this.fetchChapters();
                } else {
                    alert("⚠️ Lỗi biên soạn lại: " + (data.error || 'Không xác định'));
                }
            } catch (err) {
                console.error("Lỗi kết nối khi gọi AI Recompile:", err);
                alert("⚠️ Lỗi kết nối máy chủ khi yêu cầu AI biên soạn.");
            } finally {
                this.recompiling = false;
            }
        },

        // ==========================================
        // HÀM TIỆN ÍCH: COPY NỘI DUNG BẢNG VÀO CLIPBOARD
        // ==========================================
        async copyTableContent(elementOrText) {
            try {
                let textToCopy = '';
                if (typeof elementOrText === 'string') {
                    let el = document.getElementById(elementOrText);
                    textToCopy = el ? el.innerText : elementOrText;
                } else if (elementOrText instanceof HTMLElement) {
                    textToCopy = elementOrText.innerText;
                }

                await navigator.clipboard.writeText(textToCopy);
                alert("📋 Đã sao chép nội dung bảng vào bộ nhớ tạm thành công!");
            } catch (err) {
                console.error("Không thể copy:", err);
                alert("⚠️ Không thể sao chép nội dung.");
            }
        },

        async init() {
            localStorage.setItem('vnxbox_session_id', this.session_id);
            console.log("🚀 [DEBUG INIT] Khởi tạo ứng dụng, Session ID:", this.session_id);
            await this.fetchChapters();
            await this.fetchChatHistory();
            await this.scrollToBottom();
        },

        async fetchChatHistory() {
            try {
                let res = await fetch(`/api/chat/history/?session_id=${this.session_id}`);
                if (res.ok) {
                    let data = await res.json();
                    if (data.success && data.messages && data.messages.length > 0) {
                        this.messages = data.messages.map(m => ({
                            sender: m.sender,
                            text: m.text,
                            citations: m.metadata?.citations || [],
                            sandbox_execution: m.metadata?.sandbox || null
                        }));
                        await this.scrollToBottom();
                    }
                }
            } catch (err) {
                console.log("Lỗi tải lịch sử chat:", err);
            }
        },

        async scrollToBottom() {
            try {
                await this.$nextTick();
                await new Promise(resolve => setTimeout(resolve, 30));
                let container = this.$refs.chatContainer || document.querySelector('[x-ref="chatContainer"]');
                let anchor = this.$refs.bottomAnchor || document.querySelector('[x-ref="bottomAnchor"]');
                if (anchor) {
                    anchor.scrollIntoView({ behavior: 'auto', block: 'end' });
                }
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            } catch (err) {
                console.error("❌ Lỗi cuộn trang:", err);
            }
        },

        async sendMessage() {
            if (!this.question.trim() || this.loading || this.isThinking) return;
            let userQ = this.question;
            this.messages.push({ sender: 'user', text: userQ });
            this.question = '';
            this.loading = true;
            this.isThinking = true;
            this.currentStepIndex = 0;

            this.thinkingSteps = [
                `🔍 Đang phân tích câu hỏi: "${userQ.length > 25 ? userQ.substring(0, 25) + '...' : userQ}"`,
                "⚡ Đang định tuyến ý định (Intent Routing) & Quét Hybrid Search...",
                "📚 Đang trích xuất văn bản & ngữ cảnh luật định từ Kho tri thức...",
                "🛡️ Đang thực thi mã tính toán an toàn trong Secure Sandbox...",
                "✨ Đang tổng hợp kết quả chuẩn số học Việt Nam..."
            ];

            await this.scrollToBottom();

            this.stepInterval = setInterval(async () => {
                if (this.currentStepIndex < this.thinkingSteps.length - 2) {
                    this.currentStepIndex++;
                    await this.scrollToBottom();
                }
            }, 700);

            try {
                let res = await fetch('/api/chapters/chat_query/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    },
                    body: JSON.stringify({ question: userQ, session_id: this.session_id })
                });

                this.currentStepIndex = this.thinkingSteps.length - 1;
                await this.scrollToBottom();

                let data = await res.json();
                if (res.ok) {
                    this.messages.push({
                        sender: 'ai',
                        text: data.answer,
                        citations: data.citations || [],
                        sandbox_execution: data.sandbox_execution || null
                    });
                } else {
                    this.messages.push({ sender: 'ai', text: '⚠️ Lỗi hệ thống: ' + (data.error || 'Thất bại'), citations: [] });
                }
            } catch (err) {
                this.messages.push({ sender: 'ai', text: '⚠️ Lỗi kết nối máy chủ nội bộ.', citations: [] });
            } finally {
                clearInterval(this.stepInterval);
                this.isThinking = false;
                this.loading = false;
                await this.scrollToBottom();
            }
        },

        handleFileSelect(event) {
            if (event.target.files && event.target.files.length > 0) {
                this.selectedFile = event.target.files[0];
                console.log("📁 Đã chọn file:", this.selectedFile.name);
            }
        },

        async submitIngest() {
            if (this.ingesting) return;
            if (!this.selectedFile && !this.newRawText.trim()) {
                alert("Vui lòng chọn file tài liệu hoặc nhập văn bản thô để nạp vào hệ thống.");
                return;
            }

            this.ingesting = true;
            let formData = new FormData();
            if (this.selectedFile) {
                formData.append('file', this.selectedFile);
            }
            formData.append('domain_name', this.newDomain || 'Quy định chung');
            formData.append('sub_domain', this.newSubDomain || 'Nghiệp vụ chi tiết');
            formData.append('raw_text', this.newRawText || '');

            try {
                let res = await fetch('/api/chapters/ingest/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    },
                    body: formData
                });

                let data = await res.json();
                if (res.ok && data.success) {
                    alert("✅ Nạp tài liệu và phân tích Vector thành công!");
                    this.showUploadModal = false;
                    this.selectedFile = null;
                    this.newRawText = '';
                    this.newDomain = '';
                    this.newSubDomain = '';
                    await this.fetchChapters();
                } else {
                    alert("⚠️ Lỗi nạp tài liệu: " + (data.error || 'Không xác định'));
                }
            } catch (err) {
                console.error("Lỗi kết nối khi nạp file:", err);
                alert("⚠️ Lỗi kết nối máy chủ khi xử lý nạp file.");
            } finally {
                this.ingesting = false;
            }
        },

        async updateStatus(newStatus) {
            if (!this.selectedChapter) return;
            try {
                let res = await fetch(`/api/chapters/${this.selectedChapter.id}/`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    },
                    body: JSON.stringify({ status: newStatus })
                });
                if (res.ok) {
                    let updated = await res.json();
                    this.selectedChapter.status = updated.status || newStatus;
                    await this.fetchChapters();
                    alert("✅ Đã cập nhật trạng thái tài liệu thành công!");
                } else {
                    alert("⚠️ Không thể cập nhật trạng thái.");
                }
            } catch (err) {
                console.error("Lỗi cập nhật trạng thái:", err);
            }
        },

        get availableDomains() {
            let domains = {};
            this.chapters.forEach(c => {
                let dName = c.domain_name || 'Quy định chung';
                let sName = c.sub_domain || 'Chung';
                if (!domains[dName]) domains[dName] = new Set();
                domains[dName].add(sName);
            });
            let result = [];
            for (let d in domains) {
                result.push({ domain_name: d, sub_domains: Array.from(domains[d]) });
            }
            return result;
        },

        get filteredChapters() {
            return this.chapters.filter(c => {
                let matchStatus = !this.filterStatus || c.status === this.filterStatus;
                let matchDomain = !this.filterDomain || c.domain_name === this.filterDomain;
                let matchSubDomain = !this.filterSubDomain || c.sub_domain === this.filterSubDomain;
                return matchStatus && matchDomain && matchSubDomain;
            });
        },

        async fetchChapters() {
            try {
                let res = await fetch('/api/chapters/');
                let data = await res.json();
                this.chapters = data.results || data;
                if (this.chapters.length > 0 && !this.selectedChapter) {
                    this.selectedChapter = this.chapters[0];
                }
            } catch (err) {
                console.error("Lỗi tải chapters:", err);
            }
        },

        async jumpToEdit(chapterId) {
            if (!chapterId) return;
            let found = this.chapters.find(c => c.id === parseInt(chapterId));
            if (!found) {
                await this.fetchChapters();
                found = this.chapters.find(c => c.id === parseInt(chapterId));
            }
            if (found) {
                this.selectedChapter = found;
                this.currentView = 'config';
            }
        }
    }));

    Alpine.data('chatWidget', () => ({
        isOpen: false,
        session_id: localStorage.getItem('vnxbox_session_id') || crypto.randomUUID(),
        question: '',
        loading: false,
        messages: [{ sender: 'ai', text: 'Chào bạn! Tôi có thể hỗ trợ gì hôm nay?', citations: [] }],
        init() { }
    }));
});