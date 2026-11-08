vnxbox/
├── dashboard/                 # Django App quản trị chung
├── env/                       # Môi trường ảo Python
└── knowledge/                 # Core App Tri thức & AI Corporation
    ├── __pycache__/
    ├── agents/                # Thư mục chứa các LangGraph Multi-Agent
    │   ├── __init__.py
    │   ├── accounting_sub_graph.py   # Sub-Graph Phòng Kế Toán (Kế toán kho, tổng hợp, trưởng)
    │   ├── agent_factory.py          # Dynamic Agent Factory (Tự sinh chuyên viên mới)
    │   ├── audit_dept.py             # Sub-Graph Phòng Pháp Chế & Kiểm Toán Nội Bộ
    │   ├── ba_arbiter.py             # Phòng Trọng Tài BA (Tranh biện ngầm < 1s)
    │   ├── inventory_dept.py         # Sub-Graph Phòng Kho Vận & Định Mức Tuổi Vàng
    │   ├── pricing_dept.py           # Sub-Graph Phòng Kinh Doanh & Định Giá Động
    │   ├── qa_evaluator.py           # Phòng QA & Chấm Điểm RAGAS Evaluator
    │   ├── router_graph.py           # Ban Giám Đốc (Central Controller Router Graph)
    │   └── state.py                  # Định nghĩa Shared State cho LangGraph
    ├── migrations/
    ├── parsers/               # Thư mục xử lý tài liệu đa định dạng
    │   ├── __init__.py
    │   ├── docling_parser.py         # Bóc tách Layout nâng cao bằng IBM Docling
    │   ├── ocr_engine.py             # EasyOCR CPU Lazy Loading an toàn
    │   └── taxonomy_engine.py        # Auto-Taxonomy LLM & Context Header
    ├── __init__.py
    ├── admin.py
    ├── ai_services.py         # Kết nối Ollama / Local LLMs & Hardware Auto-Profiling
    ├── apps.py
    ├── chunker.py
    ├── file_parsers.py        # Router Ingestion chính điều phối các Parser
    ├── models.py
    ├── sandbox.py             # Secure Python Sandbox (Thực thi code an toàn)
    ├── tests.py
    ├── urls.py
    └── views.py


templates/
└── dashboard/
    ├── base_layout.html                 # Layout khung chính (Layout tổng)
    └── partials/
        ├── sidebar_nav.html             # Thanh menu chuyển tab bên trái
        ├── topbar_header.html           # Header trên cùng (Logo GIF, tiêu đề, badge offline)
        ├── chat_view.html               # Giao diện Cổng Chat Chính & Thinking Steps
        ├── knowledge_config_view.html   # Giao diện Quản trị Kho Tri Thức (Master-Detail)
        ├── upload_modal.html            # Modal nạp file mới
        └── recompile_modal.html         # Modal AI biên soạn lại tri thức