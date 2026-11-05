from django.db import models
import uuid


class KnowledgeChapter(models.Model):
    """
    Bảng chính lưu trữ từng phân đoạn/điều khoản tri thức doanh nghiệp
    với cấu trúc định vị sâu (Lĩnh vực > Nghiệp vụ > Chương > Điều > Mục).
    """
    title = models.CharField(max_length=255, help_text="Tiêu đề phân đoạn/điều khoản")
    
    # Định danh nguồn gốc file & sheet (Giải quyết bài toán tách file đa sheet)
    source_file = models.CharField(max_length=255, blank=True, null=True, help_text="Tên file gốc nạp vào (VD: Quy_che_vang.xlsx)")
    sheet_name = models.CharField(max_length=100, blank=True, null=True, help_text="Tên Sheet nếu là file Excel (VD: Dinh_muc_980)")

    # Cấu trúc phân cấp phục vụ lọc cứng & định vị sâu
    domain_name = models.CharField(max_length=100, db_index=True, help_text="Lĩnh vực nghiệp vụ lớn (VD: Thu đổi vàng)")
    sub_domain = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Nghiệp vụ chi tiết (VD: Thu mua vàng 24K)")
    chapter_code = models.CharField(max_length=50, blank=True, null=True, help_text="Mã chương (VD: Chương I)")
    article_code = models.CharField(max_length=50, blank=True, null=True, help_text="Mã điều/mục (VD: Điều 4 - Mục 1)")

    summary = models.TextField(blank=True, null=True, help_text="Tóm tắt ngắn gọn nội dung")
    content = models.TextField(help_text="Nội dung chi tiết của điều khoản/chương hoặc Markdown Table")
    
    status = models.CharField(
        max_length=50, 
        default="AUTO_APPROVED", 
        choices=[
            ("AUTO_APPROVED", "AI tự động duyệt"), 
            ("NEEDS_REVIEW", "Cần Admin kiểm tra (Mâu thuẫn/Mơ hồ)"), 
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
    Bảng riêng biệt lưu trữ các câu hỏi mẫu (Intent FAQ Variations) do AI tự sinh
    khi nạp tài liệu. Phục vụ cho bước Intent Routing (Lọc ý định người dùng trước khi tra cứu Vector).
    """
    chapter = models.ForeignKey(
        KnowledgeChapter,
        on_delete=models.CASCADE,
        related_name='faq_variations',
        help_text="Liên kết đến chương/điều gốc"
    )
    question_variation = models.TextField(help_text="Câu hỏi mẫu thực tế mà người dùng có thể hỏi")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FAQ [Chapter {self.chapter_id}]: {self.question_variation[:50]}..."


class KnowledgeHistory(models.Model):
    """
    Bảng quản lý lịch sử chỉnh sửa dài hạn (Full Versioning & Audit Trail)
    phục vụ đối soát, so sánh diff và rollback bất kỳ lúc nào.
    """
    chapter = models.ForeignKey(
        KnowledgeChapter, 
        on_delete=models.CASCADE, 
        related_name='histories',
        help_text="Liên kết đến chương tri thức gốc"
    )
    version = models.IntegerField(default=1, help_text="Số thứ tự phiên bản")
    content_before = models.TextField(help_text="Nội dung trước khi sửa/recompile")
    content_after = models.TextField(help_text="Nội dung sau khi sửa/recompile")
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
    Hệ thống sẽ query lấy ra tối đa 6-10 tin nhắn gần nhất của session này 
    để làm Sliding Window Memory cho AI.
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
    metadata = models.JSONField(default=dict, blank=True, help_text="Lưu citations, sandbox_execution kết quả nếu có")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']  # Đảm bảo sắp xếp theo thứ tự thời gian cũ -> mới

    def __str__(self):
        return f"[{self.sender.upper()}] {self.text[:40]}..."