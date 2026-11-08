# File path: knowledge/agents/viber_war_room_view.py
# Chú thích: Viber War Room View - Giao diện Web Dashboard điều hành Tập đoàn AI vnxBox Enterprise.

import json
from django.shortcuts import render
from django.http import JsonResponse
from .execution_dispatcher import ExecutionDispatcher
from .viber_test_generator import ViberTestGenerator
from .viber_docling_parser import ViberDoclingParser
from .viber_graph_rag import ViberGraphRAG


def viber_war_room_dashboard(request):
    """
    Render giao diện War Room trực quan cho Sếp quản lý các phòng ban AI.
    """
    return render(request, "knowledge/viber_war_room.html", {
        "title": "vnxBox Enterprise - AI War Room Dashboard"
    })





def api_run_corporation_trigger(request):
    if request.method == "POST":
        blueprint_text = "Hệ thống vnxBox Enterprise v2.6 - Web War Room Full Pipeline Triggered."
        
        # 1. Chạy chuỗi thực thi DAG Tasks
        results = ExecutionDispatcher.run_corporation_pipeline(blueprint_text)
        
        # 2. Bóc tách tài liệu qua Docling
        doc_result = ViberDoclingParser.parse_document("knowledge/management/commands/run_corporation.py")
        
        # 3. Lập chỉ mục đồ thị tri thức qua Neo4j GraphRAG
        graph_result = ViberGraphRAG.connect_and_index_graph(doc_result.get("extracted_markdown", ""))
        
        # 4. Sinh test case QA chuyên sâu
        test_report = ViberTestGenerator.generate_detailed_test_cases(
            feature_title="Hệ thống Tích hợp Toàn diện Docling & Neo4j GraphRAG",
            feature_specification="Xác thực luồng ingestion, lập chỉ mục đồ thị tri thức và quản lý tác vụ tự trị."
        )

        # Tổng hợp báo cáo hiển thị lên War Room
        combined_report = (
            f"=== BÁO CÁO BÓC TÁCH DOCLING ===\n{doc_result.get('extracted_markdown')}\n\n"
            f"=== BÁO CÁO ĐỒ THỊ TRI THỨC NEOMJ GRAPHRAG ===\n"
            f"- CSDL: {graph_result.get('database')}\n"
            f"- Thực thể đã lập chỉ mục: {graph_result.get('entities_indexed')}\n"
            f"- Mối quan hệ: {graph_result.get('relations_indexed')}\n"
            f"- Trạng thái: {graph_result.get('graph_summary')}\n\n"
            f"=== BỘ KỊCH BẢN KIỂM THỬ QA ===\n{test_report}"
        )

        return JsonResponse({
            "status": "success",
            "message": "Đã hoàn thành toàn bộ chuỗi Tập đoàn AI kết hợp Docling & GraphRAG!",
            "tasks": results,
            "test_report": combined_report
        })
    
    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)