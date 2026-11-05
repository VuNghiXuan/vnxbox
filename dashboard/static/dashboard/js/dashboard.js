// ==========================================
// vnxBox Enterprise - Dashboard State Management
// ==========================================

function knowledgeApp() {
    return {
        // --- Navigation State ---
        currentView: 'chat', // 'chat' hoặc 'config'

        // --- Session ID for Sliding Window Memory ---
        session_id: null,

        // --- Knowledge Repository State ---
        chapters: [],
        selectedChapter: null,
        filterStatus: '',
        filterDomain: '',
        filterSubDomain: '',

        // --- Chat Workspace State ---
        question: '',
        loading: false,
        messages: [
            {
                sender: 'ai',
                text: 'Chào Vũ! Tôi là vnxBox Local AI Platform. Hệ thống đã sẵn sàng hỗ trợ tra cứu quy định và tính toán qua Secure Sandbox.',
                citations: [],
                sandbox_execution: null
            }
        ],

        // --- Modal Ingest (Upload & Raw Text) State ---
        showUploadModal: false,
        newDomain: '',
        newRawText: '',
        selectedFile: null,
        ingesting: false,

        // --- Modal AI Recompile State ---
        showRecompileModal: false,
        selectedChapterIdForRecompile: null,
        recompileInstruction: 'Hãy biên soạn, chuẩn hóa lại nội dung này mạch lạc, rõ ràng hơn.',
        recompiling: false,

        // --- Lifecycle Hooks ---
        async init() {
            // Khởi tạo hoặc lấy session_id từ localStorage để duy trì bộ nhớ ngắn hạn
            let savedSession = localStorage.getItem('vnxbox_session_id');
            if (!savedSession) {
                savedSession = crypto.randomUUID();
                localStorage.setItem('vnxbox_session_id', savedSession);
            }
            this.session_id = savedSession;

            await this.fetchChapters();
        },

        // --- Computed Getters ---
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

        // --- API Actions: Chapters Management ---
        async fetchChapters() {
            try {
                let res = await fetch('/api/chapters/');
                let data = await res.json();
                this.chapters = data.results || data;
                if (this.chapters.length > 0 && !this.selectedChapter) {
                    this.selectedChapter = this.chapters[0];
                }
            } catch (err) {
                console.error("Lỗi tải danh sách chapters:", err);
            }
        },

        jumpToConfigAndEdit(chapterId) {
            let found = this.chapters.find(c => c.id === parseInt(chapterId));
            if (found) {
                this.selectedChapter = found;
                this.currentView = 'config';
            }
        },

        // --- API Actions: Ingestion (File & Raw Text) ---
        handleFileSelect(event) {
            if (event.target.files.length > 0) {
                this.selectedFile = event.target.files[0];
            }
        },

        async submitIngest() {
            if ((!this.newRawText.trim() && !this.selectedFile) || this.ingesting) return;
            this.ingesting = true;

            let formData = new FormData();
            formData.append('domain_name', this.newDomain || 'Quy định chung');
            if (this.selectedFile) {
                formData.append('file', this.selectedFile);
            } else {
                formData.append('raw_text', this.newRawText);
            }

            try {
                let res = await fetch('/api/chapters/ingest_raw/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '' },
                    body: formData
                });
                let result = await res.json();
                if (res.ok) {
                    this.chapters.unshift(result.data);
                    this.selectedChapter = result.data;
                    this.showUploadModal = false;
                    this.newRawText = '';
                    this.newDomain = '';
                    this.selectedFile = null;
                    alert('Nạp và bóc tách tri thức thành công!');
                } else {
                    alert('Lỗi: ' + (result.error || 'Thất bại'));
                }
            } catch (err) {
                console.error("Lỗi kết nối khi ingest:", err);
                alert('Lỗi kết nối máy chủ.');
            } finally {
                this.ingesting = false;
            }
        },

        // --- API Actions: AI Recompile ---
        openRecompileModal() {
            if (this.selectedChapter) {
                this.selectedChapterIdForRecompile = this.selectedChapter.id;
            }
            this.showRecompileModal = true;
        },

        async recompileWithAI() {
            let targetId = this.selectedChapterIdForRecompile || (this.selectedChapter ? this.selectedChapter.id : null);
            if (!targetId || this.recompiling) return;

            this.recompiling = true;

            try {
                let res = await fetch(`/api/chapters/${targetId}/recompile_with_ai/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    },
                    body: JSON.stringify({ instruction: this.recompileInstruction })
                });
                let result = await res.json();
                if (res.ok && result.success) {
                    this.selectedChapter = result.data;
                    let idx = this.chapters.findIndex(c => c.id === result.data.id);
                    if (idx !== -1) {
                        this.chapters[idx] = result.data;
                    }
                    this.showRecompileModal = false;
                    alert('AI đã biên soạn lại tri thức thành công!');
                } else {
                    alert('Lỗi biên soạn: ' + (result.error || 'Không xác định'));
                }
            } catch (err) {
                console.error("Lỗi kết nối khi gọi AI recompile:", err);
                alert('Lỗi kết nối máy chủ.');
            } finally {
                this.recompiling = false;
            }
        },

        // --- API Actions: Chat Workspace Query (Đã gắn session_id) ---
        async sendQuery() {
            if (!this.question.trim() || this.loading) return;
            let userQ = this.question;
            this.messages.push({ sender: 'user', text: userQ });
            this.question = '';
            this.loading = true;

            try {
                let res = await fetch('/api/chapters/chat_query/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    },
                    body: JSON.stringify({
                        question: userQ,
                        session_id: this.session_id
                    })
                });
                let data = await res.json();
                if (res.ok) {
                    this.messages.push({
                        sender: 'ai',
                        text: data.answer,
                        citations: data.citations || [],
                        sandbox_execution: data.sandbox_execution || null
                    });
                } else {
                    this.messages.push({ sender: 'ai', text: 'Lỗi: ' + (data.error || 'Không xử lý được'), citations: [] });
                }
            } catch (err) {
                console.error("Lỗi truy vấn chat:", err);
                this.messages.push({ sender: 'ai', text: 'Lỗi kết nối máy chủ.', citations: [] });
            } finally {
                this.loading = false;
            }
        }
    }
}

// ==========================================
// Floating Chat Widget Controller
// ==========================================
function chatWidget() {
    return {
        isOpen: false,
        session_id: localStorage.getItem('vnxbox_session_id') || crypto.randomUUID(),
        question: '',
        loading: false,
        messages: [
            { sender: 'ai', text: 'Chào bạn! Tôi có thể hỗ trợ gì cho quy trình hoặc nghiệp vụ của bạn hôm nay?', citations: [] }
        ],
        async sendQuery() {
            if (!this.question.trim() || this.loading) return;
            let userQ = this.question;
            this.messages.push({ sender: 'user', text: userQ });
            this.question = '';
            this.loading = true;

            try {
                let res = await fetch('/api/chapters/chat_query/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    },
                    body: JSON.stringify({
                        question: userQ,
                        session_id: this.session_id
                    })
                });
                let data = await res.json();
                if (res.ok) {
                    this.messages.push({
                        sender: 'ai',
                        text: data.answer,
                        citations: data.citations || []
                    });
                } else {
                    this.messages.push({ sender: 'ai', text: 'Lỗi: ' + (data.error || 'Không thể kết nối API.'), citations: [] });
                }
            } catch (err) {
                console.error("Lỗi widget chat:", err);
                this.messages.push({ sender: 'ai', text: 'Lỗi hệ thống mạng hoặc máy chủ.', citations: [] });
            } finally {
                this.loading = false;
            }
        }
    }
}