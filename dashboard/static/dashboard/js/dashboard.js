// File path: static/dashboard/js/dashboard.js
// Chú thích: Script quản lý toàn bộ logic Frontend Alpine.js cho vnxBox Enterprise.
// Đã tích hợp đầy đủ Ingestion, Chat Workspace, Recompile, Copy Clipboard, Self-Learning Dislike Modal và Render Tức Thì (Instant UI Update).

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

        showDislikeModal: false,
        dislikeMessageId: null,
        dislikeNote: '',

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
                id: null, // Tin nhắn mặc định chào mừng không có ID cơ sở dữ liệu
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

        // States quan sát từng bước các tác nhân AI tranh biện, kiểm tra số học và chấm điểm QA
        selectedAuditMsg: null,

        // ==========================================
        // HÀM KHỞI TẠO (INIT)
        // ==========================================
        async init() {
            localStorage.setItem('vnxbox_session_id', this.session_id);
            console.log("🚀 [DEBUG INIT] Khởi tạo ứng dụng, Session ID:", this.session_id);
            await this.fetchChapters();
            await this.fetchChatHistory();
            await this.scrollToBottom();
        },

        // ==========================================
        // HÀM TẢI LỊCH SỬ CHAT & CHAPTERS
        // ==========================================
        async fetchChatHistory() {
            try {
                let res = await fetch(`/api/chat/history/?session_id=${this.session_id}`);
                if (res.ok) {
                    let data = await res.json();
                    if (data.success && data.messages && data.messages.length > 0) {
                        this.messages = data.messages.map(m => ({
                            id: m.id,
                            sender: m.sender,
                            text: m.text,
                            citations: m.metadata?.citations || [],
                            sandbox_execution: m.metadata?.sandbox || null,
                            qa_score: m.metadata?.qa_score || 9.5
                        }));
                        await this.scrollToBottom();
                    }
                }
            } catch (err) {
                console.log("Lỗi tải lịch sử chat:", err);
            }
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
        // ==========================================
        // HÀM GỬI TIN NHẮN CHAT (HOÀN TOÀN ĐỘNG - KHÔNG HARDCODE)
        // ==========================================
        async sendMessage() {
            if (!this.question.trim() || this.loading || this.isThinking) return;
            let userQ = this.question;

            // 1. Cập nhật mảng tin nhắn (Collection Reactivity)
            this.messages = [
                ...this.messages,
                {
                    id: null,
                    sender: 'user',
                    text: userQ
                }
            ];

            this.question = '';
            this.loading = true;
            this.isThinking = true;
            this.currentStepIndex = 0;

            // Hiển thị bước khởi tạo chung, chờ Backend định tuyến động
            this.thinkingSteps = [
                `🔍 [Agent Router]: Đang tiếp nhận và phân tích yêu cầu từ người dùng...`,
                `⚡ [System Core]: Đang kết nối phân hệ chuyên trách...`
            ];
            await this.$nextTick();
            await this.scrollToBottom();

            try {
                let res = await fetch('/api/chapters/chat_query/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    },
                    body: JSON.stringify({ question: userQ, session_id: this.session_id })
                });

                let data = await res.json();

                if (res.ok) {
                    // Nếu backend trả về các bước tư duy động, ta cập nhật vào giao diện
                    if (data.thinking_steps && data.thinking_steps.length > 0) {
                        this.thinkingSteps = data.thinking_steps;
                    }
                    this.currentStepIndex = this.thinkingSteps.length - 1;
                    await this.$nextTick();
                    await this.scrollToBottom();

                    // 2. Thêm câu trả lời của AI (Collection Reactivity Update)
                    this.messages = [
                        ...this.messages,
                        {
                            id: data.message_id,
                            sender: 'ai',
                            text: data.answer,
                            citations: data.citations || [],
                            sandbox_execution: data.sandbox_execution || null,
                            qa_score: data.qa_score || 9.5
                        }
                    ];
                } else {
                    this.messages = [
                        ...this.messages,
                        {
                            id: null,
                            sender: 'ai',
                            text: '⚠️ Lỗi hệ thống: ' + (data.error || 'Thất bại'),
                            citations: []
                        }
                    ];
                }
            } catch (err) {
                console.error("Lỗi chat query:", err);
                this.messages = [
                    ...this.messages,
                    {
                        id: null,
                        sender: 'ai',
                        text: '⚠️ Lỗi kết nối máy chủ nội bộ.',
                        citations: []
                    }
                ];
            } finally {
                clearInterval(this.stepInterval);
                this.isThinking = false;
                this.loading = false;

                await this.$nextTick();
                await this.scrollToBottom();
            }
        },

        // ==========================================
        // HÀM NẠP TÀI LIỆU & INGESTION
        // ==========================================
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

        // ==========================================
        // HÀM BIÊN SOẠN LẠI TRI THỨC (RECOMPILE) & LƯU
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

        async saveChapterChanges() {
            if (!this.selectedChapter || !this.selectedChapter.id) {
                alert("⚠️ Chưa chọn phân đoạn tri thức nào để lưu.");
                return;
            }
            try {
                let res = await fetch(`/api/chapters/${this.selectedChapter.id}/`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    },
                    body: JSON.stringify({
                        domain_name: this.selectedChapter.domain_name,
                        sub_domain: this.selectedChapter.sub_domain,
                        title: this.selectedChapter.title,
                        chapter_code: this.selectedChapter.chapter_code,
                        article_code: this.selectedChapter.article_code,
                        summary: this.selectedChapter.summary,
                        content: this.selectedChapter.content
                    })
                });

                let data = await res.json();
                if (res.ok) {
                    alert("✅ Đã cập nhật thành công! Hệ thống Vector DB đã tự động Re-index ngầm.");
                    await this.fetchChapters();
                } else {
                    alert("⚠️ Lỗi cập nhật: " + (data.error || 'Không xác định'));
                }
            } catch (err) {
                console.error("Lỗi kết nối khi lưu chapter:", err);
                alert("⚠️ Lỗi kết nối tới máy chủ.");
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

        // ==========================================
        // HÀM TIỆN ÍCH: COPY NỘI DUNG BẢNG VÀO CLIPBOARD
        // ==========================================
        copyTableContent(elementOrText) {
            let textToCopy = '';
            if (typeof elementOrText === 'string') {
                let el = document.getElementById(elementOrText);
                textToCopy = el ? el.innerText : elementOrText;
            } else if (elementOrText instanceof HTMLElement) {
                textToCopy = elementOrText.innerText;
            }

            if (!textToCopy) {
                alert("⚠️ Không có nội dung để sao chép.");
                return;
            }

            navigator.clipboard.writeText(textToCopy).then(() => {
                alert("📋 Đã sao chép toàn bộ nội dung bảng / markdown vào bộ nhớ tạm thành công!");
            }).catch(err => {
                console.error("Lỗi khi copy:", err);
                alert("⚠️ Không thể sao chép do giới hạn trình duyệt.");
            });
        },

        // ==========================================
        // CÁC HÀM GETTER & TƯƠNG TÁC KHÁC
        // ==========================================
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
        },

        reactMessage(index, type) {
            let msg = this.messages[index];
            if (!msg) return;

            if (!msg.reaction) {
                msg.reaction = type;
                if (type === 'love') msg.loves = (msg.loves || 0) + 1;
                if (type === 'like') msg.likes = (msg.likes || 0) + 1;
            } else if (msg.reaction === type) {
                if (type === 'love' && msg.loves > 0) msg.loves--;
                if (type === 'like' && msg.likes > 0) msg.likes--;
                msg.reaction = null;
            } else {
                if (msg.reaction === 'love' && msg.loves > 0) msg.loves--;
                if (msg.reaction === 'like' && msg.likes > 0) msg.likes--;

                msg.reaction = type;
                if (type === 'love') msg.loves = (msg.loves || 0) + 1;
                if (type === 'like') msg.likes = (msg.likes || 0) + 1;
            }
            console.log(`✨ [Self-Learning Feedback] Tin nhắn #${index} nhận phản hồi:`, type);
        },

        handleDislike(messageId) {
            if (!messageId || messageId === 'undefined' || isNaN(messageId)) {
                alert("⚠️ Tin nhắn này chưa được lưu định danh ID trên cơ sở dữ liệu. Vui lòng thử lại sau khi tin nhắn hoàn tất đồng bộ.");
                console.error("❌ Lỗi: messageId không hợp lệ:", messageId);
                return;
            }
            this.dislikeMessageId = messageId;
            this.dislikeNote = '';
            this.showDislikeModal = true;
        },

        async submitDislikeFeedback() {
            if (!this.dislikeNote.trim()) {
                alert("⚠️ Vui lòng mô tả vấn đề sai để AI tiến hành mổ xẻ và khắc phục.");
                return;
            }

            try {
                let res = await fetch(`/api/chat-interactions/${this.dislikeMessageId}/react_message/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    },
                    body: JSON.stringify({
                        reaction: 'dislike',
                        note: this.dislikeNote
                    })
                });

                let data = await res.json();
                if (res.ok && data.success) {
                    alert("🙏 Cảm ơn Vũ! AI BA đã tiếp nhận bức thư chỉ đạo, đang cập nhật lại định nghĩa (ví dụ: loại vàng 610) và tự động đối chiếu Re-index kho tri thức ngầm.");
                    this.showDislikeModal = false;
                    this.dislikeNote = '';
                    this.dislikeMessageId = null;
                } else {
                    alert("⚠️ Không thể gửi phản hồi: " + (data.error || 'Lỗi không xác định'));
                }
            } catch (err) {
                console.error("Lỗi kết nối khi gửi feedback dislike:", err);
                alert("⚠️ Lỗi kết nối tới máy chủ.");
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