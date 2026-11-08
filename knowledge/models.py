# File path: knowledge/models.py
# Chú thích: Định nghĩa cơ sở dữ liệu ORM (Django Models) cho hệ thống vnxBox Enterprise.
# Bao gồm: Tri thức (KnowledgeChapter, KnowledgeFAQ, KnowledgeHistory), 
# Hệ thống Tập đoàn AI (CompanyDomain, DepartmentRegistry), Lịch sử chat (ChatSession, ChatMessage)
# và Nhật ký kiểm toán / Giám sát (AuditDebateLog, QAEvaluationLog).

from django.db import models
import uuid


class CompanyDomain(models.Model):
    """
    Bảng quản lý các Công ty con / Lĩnh vực nghiệp vụ lớn thuộc Tập đoàn vnxBox.
    VD: Công ty Đầu tư Xây dựng, Công ty Kinh doanh Vàng bạc, Công ty Logistics...
    """
    company_code = models.CharField(max_length=50, unique=True, db_index=True, help_text="Mã định danh công ty/lĩnh vực (VD: CONSTRUCTION, GOLD_RETAIL)")
    company_name = models.CharField(max_length=255, help_text="Tên hiển thị công ty/lĩnh vực (VD: Công ty CP Đầu tư Xây dựng vnxBox)")
    description = models.TextField(blank=True, null=True, help_text="Mô tả phạm vi hoạt động chuyên ngành")
    is_active = models.BooleanField(default=True, help_text="Trạng thái hoạt động trong tập đoàn")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.company_code}] {self.company_name}"


class DepartmentRegistry(models.Model):
    """
    Bảng quản lý Phòng ban & Nhân viên AI tự trị (Dynamic Agent Registry).
    Gán chặt nhiệm vụ, trách nhiệm pháp lý, System Prompt và Toolset độc quyền.
    """
    company = models.ForeignKey(
        CompanyDomain,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='agents',
        help_text="Thuộc công ty/lĩnh vực nào trong tập đoàn"
    )
    department_code = models.CharField(max_length=100, db_index=True, help_text="Mã phòng ban (VD: LEGAL, ACCOUNTING, ESTIMATION)")
    agent_name = models.CharField(max_length=150, unique=True, help_text="Tên chức danh nhân viên AI (VD: Chief_Estimation_Engineer)")
    role_description = models.TextField(blank=True, null=True, help_text="Mô tả vai trò và chức năng chuyên môn")
    
    # Gán nhiệm vụ & Trách nhiệm gắn liền với nhân viên này
    responsibilities = models.TextField(blank=True, null=True, help_text="Trách nhiệm cụ thể (VD: Rà soát hợp đồng, Tính dự toán xây dựng)")
    kpi_rules = models.TextField(blank=True, null=True, help_text="Ràng buộc kỹ thuật: Cấm nhẩm số, Cấm cắt xén điều khoản, Ép dùng Sandbox")
    
    system_prompt = models.TextField(help_text="System prompt chuyên biệt định hình tư duy & quy tắc làm việc của nhân viên này")
    required_tools = models.JSONField(default=list, blank=True, help_text="Danh sách Toolset được cấp phép (Sandbox, GraphRAG, Docling OCR...)")
    is_active = models.BooleanField(default=True, db_index=True, help_text="Trạng thái sẵn sàng tiếp nhận công việc")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        comp_str = self.company.company_code if self.company else self.department_code
        return f"[{comp_str}] {self.agent_name} ({'Active' if self.is_active else 'Disabled'})"


class KnowledgeChapter(models.Model):
    """
    Bảng chính lưu trữ từng phân đoạn/điều khoản tri thức doanh nghiệp
    với cấu trúc định vị sâu (Công ty > Lĩnh vực > Nghiệp vụ > Chương > Điều > Mục).
    """
    company = models.ForeignKey(
        CompanyDomain,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='knowledge_chapters',
        help_text="Thuộc sở hữu của công ty/lĩnh vực nào"
    )
    title = models.CharField(max_length=255, help_text="Tiêu đề phân đoạn/điều khoản")
    source_file = models.CharField(max_length=255, blank=True, null=True, help_text="Tên file gốc nạp vào")
    sheet_name = models.CharField(max_length=100, blank=True, null=True, help_text="Tên Sheet nếu là file Excel")

    domain_name = models.CharField(max_length=100, db_index=True, help_text="Lĩnh vực nghiệp vụ lớn")
    sub_domain = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Nghiệp vụ chi tiết")
    chapter_code = models.CharField(max_length=50, blank=True, null=True, help_text="Mã chương")
    article_code = models.CharField(max_length=50, blank=True, null=True, help_text="Mã điều/mục")

    summary = models.TextField(blank=True, null=True, help_text="Tóm tắt ngắn gọn nội dung")
    content = models.TextField(help_text="Nội dung chi tiết của điều khoản/chương hoặc Markdown Table")
    
    status = models.CharField(
        max_length=50, 
        default="AUTO_APPROVED", 
        choices=[
            ("AUTO_APPROVED", "AI tự động duyệt"), 
            ("NEEDS_REVIEW", "Cần Admin kiểm tra"), 
            ("APPROVED", "Đã duyệt thủ công"),
        ],
        db_index=True,
        help_text="Trạng thái kiểm duyệt tri thức"
    )
    
    metadata = models.JSONField(default=dict, blank=True, help_text="Lưu trữ related_processes, formulas và thông tin mở rộng")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        source = f"[{self.source_file}" + (f" - {self.sheet_name}]" if self.sheet_name else "]")
        location = f"{self.chapter_code} > {self.article_code}" if self.chapter_code else "Tổng hợp"
        return f"{source} {self.domain_name} ({location}) - {self.title}"


class KnowledgeFAQ(models.Model):
    """
    Bảng lưu trữ các câu hỏi mẫu (Intent FAQ Variations) do AI tự sinh khi nạp tài liệu.
    """
    chapter = models.ForeignKey(
        KnowledgeChapter,
        on_delete=models.CASCADE,
        related_name='faq_variations',
        help_text="Liên kết đến chương/điều gốc"
    )
    question_variation = models.TextField(help_text="Câu hỏi mẫu thực tế")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FAQ [Chapter {self.chapter_id}]: {self.question_variation[:50]}..."


class KnowledgeHistory(models.Model):
    """
    Bảng quản lý lịch sử chỉnh sửa dài hạn (Full Versioning & Audit Trail) phục vụ so sánh diff và rollback.
    """
    chapter = models.ForeignKey(
        KnowledgeChapter, 
        on_delete=models.CASCADE, 
        related_name='histories',
        help_text="Liên kết đến chương tri thức gốc"
    )
    version = models.IntegerField(default=1, help_text="Số thứ tự phiên bản")
    content_before = models.TextField(help_text="Nội dung trước khi sửa")
    content_after = models.TextField(help_text="Nội dung sau khi sửa")
    prompt_instruction = models.TextField(blank=True, null=True, help_text="Prompt hoặc lý do thay đổi")
    created_by = models.CharField(max_length=100, blank=True, null=True, help_text="Người thực hiện hoặc AI")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chapter {self.chapter_id} v{self.version} ({self.created_at})"


class ChatSession(models.Model):
    """
    Quản lý phiên hội thoại của người dùng để lưu vết ngữ cảnh.
    """
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    title = models.CharField(max_length=255, default="Phiên chat mới", help_text="Tiêu đề gợi nhớ phiên chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.session_id} - {self.title}"


class ChatMessage(models.Model):
    """
    Lưu trữ chi tiết các tin nhắn trong phiên chat.
    Hỗ trợ metadata tương tác (Like/Dislike/Heart) và cờ phục vụ Supervised Learning.
    """
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="Thuộc phiên chat nào"
    )
    sender = models.CharField(
        max_length=20,
        choices=[("user", "Người dùng"), ("ai", "Trợ lý AI")],
        help_text="Ai là người gửi tin nhắn"
    )
    text = models.TextField(help_text="Nội dung tin nhắn")
    
    # Metadata chứa citations, sandbox_execution, reactions (like/dislike/love) và user_feedback_note
    metadata = models.JSONField(default=dict, blank=True, help_text="Lưu citations, sandbox_execution, reactions và phản hồi người dùng")
    
    # Cờ đánh dấu phục vụ Supervised Learning (RLHF/RLAIF & Fine-tuning) khi tin nhắn bị Dislike
    needs_supervised_learning = models.BooleanField(default=False, db_index=True, help_text="Đánh dấu tin nhắn cần Admin/QA kiểm duyệt tự sửa lỗi")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender.upper()}] {self.text[:40]}..."


class AuditDebateLog(models.Model):
    """
    Nhật ký ghi vết tranh biện ngầm (< 1s) giữa các AI Agents do Phòng Trọng tài BA quản lý.
    """
    session = models.ForeignKey(
        ChatSession, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='debate_logs',
        help_text="Liên kết phiên chat"
    )
    user_query = models.TextField(help_text="Câu hỏi gốc từ người dùng")
    draft_response = models.TextField(help_text="Đáp án sơ thảo của nhân viên (Drafting Agent)")
    critic_feedback = models.TextField(blank=True, null=True, help_text="Phản biện từ Trọng tài BA")
    refine_action = models.TextField(blank=True, null=True, help_text="Hành động gọt giũa và chỉnh sửa (Refiner Agent)")
    is_conflict_detected = models.BooleanField(default=False, help_text="Phát hiện mâu thuẫn logic")
    admin_approval_required = models.BooleanField(default=False, help_text="Cờ yêu cầu Admin can thiệp")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Xung đột" if self.is_conflict_detected else "Đồng nhất"
        return f"DebateLog #{self.id} - Trạng thái: {status} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class QAEvaluationLog(models.Model):
    """
    Nhật ký chấm điểm tự động (Synthetic QA & RAGAS Evaluator) của Phòng QA.
    """
    session = models.ForeignKey(
        ChatSession, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='qa_logs',
        help_text="Liên kết phiên chat"
    )
    final_answer = models.TextField(help_text="Đáp án hoàn thiện xuất màn hình")
    qa_score = models.FloatField(default=0.0, help_text="Điểm chất lượng tổng hợp (0.0 - 10.0)")
    faithfulness_score = models.FloatField(default=0.0, help_text="Điểm trung thực với tài liệu gốc (0.0 - 1.0)")
    relevance_score = models.FloatField(default=0.0, help_text="Điểm độ liên quan đến câu hỏi (0.0 - 1.0)")
    passed = models.BooleanField(default=True, help_text="Đạt chuẩn xuất màn hình (Score >= 8.5)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status_text = 'PASSED' if self.passed else 'REJECTED'
        return f"QA Log #{self.id} - Score: {self.qa_score}/10 ({status_text})"

# File path: knowledge/models.py (Bổ sung model quản trị giao việc)

class AgentDirectiveLog(models.Model):
    """
    Bảng Nhật ký Chỉ đạo & Giao việc (AgentDirectiveLog)
    """
    STATUS_CHOICES = [
        ('PENDING_ADMIN', 'Chờ Admin duyệt'),
        ('APPLIED', 'Đã áp dụng vào Agent'),
        ('REJECTED', 'Admin từ chối'),
    ]

    message = models.ForeignKey('ChatMessage', on_delete=models.CASCADE, related_name='directives')
    source_feedback = models.TextField(verbose_name="Ý kiến người dùng")
    ba_analysis = models.TextField(verbose_name="BA Phân tích nguyên nhân")
    target_agent_code = models.CharField(max_length=100, verbose_name="Nhân sự AI nhận việc")
    directive_content = models.TextField(verbose_name="Nội dung Thư chỉ đạo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='APPLIED')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vnxbox_agent_directive_log'
        ordering = ['-created_at']