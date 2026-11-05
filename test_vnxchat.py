import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/chapters"

def test_1_ingest_raw():
    print("\n--- [TEST 1] Đang test Ingest văn bản thô (Tự động phân cấp, sinh FAQ & Auto-Approval) ---")
    payload = {
        "domain_name": "Thu đổi vàng",
        "scope": "Áp dụng toàn hệ thống",
        "raw_text": (
            "Chương I: Quy định thu đổi vàng trang sức.\n"
            "Điều 2: Chính sách thu mua và chiết khấu.\n"
            "1. Vàng 24K mua vào tính bằng 98% giá niêm yết thị trường.\n"
            "2. Khách hàng đổi sang mẫu mới được chiết khấu thêm 2% trên tổng giá trị giao dịch.\n"
            "Công thức tính giá trị thực nhận: gia_mua_vao = gia_niem_yet * 0.98; chiet_khau = gia_niem_yet * 0.02."
        )
    }
    response = requests.post(f"{BASE_URL}/ingest_raw/", json=payload)
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(response.text)
    return response.json()

def test_2_chat_query():
    print("\n--- [TEST 2] Đang test Chat Query & Intent Routing kết hợp trích dẫn sâu Chương/Điều ---")
    payload = {
        "domain_name": "Thu đổi vàng",
        "question": "Quy định thu đổi vàng 24K cũ lấy mẫu mới được tính toán tỷ lệ phần trăm như thế nào?"
    }
    response = requests.post(f"{BASE_URL}/chat_query/", json=payload)
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(response.text)

def test_3_run_sandbox_manual():
    print("\n--- [TEST 3] Đang test trực tiếp Secure Code Sandbox (Kiểm tra chặn timeout & tính toán chính xác) ---")
    payload = {
        "code": (
            "gia_niem_yet = 10000000\n"
            "gia_mua_vao = gia_niem_yet * 0.98\n"
            "chiet_khau = gia_niem_yet * 0.02\n"
            "ket_qua = gia_mua_vao + chiet_khau\n"
            "print(f'Tong gia tri thuc te: {ket_qua}')"
        ),
        "timeout": 3
    }
    response = requests.post(f"{BASE_URL}/run_sandbox/", json=payload)
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(response.text)

def test_4_ai_sandbox_integration():
    print("\n--- [TEST 4] Đang test Chat Query yêu cầu tính toán số học (Ép AI tự sinh Code Python chạy Sandbox) ---")
    payload = {
        "domain_name": "Thu đổi vàng",
        "question": "Tôi có vàng 24K giá trị niêm yết 10,000,000 VNĐ đem đổi sang mẫu mới thì thực nhận sau chiết khấu là bao nhiêu? Hãy tính toán chính xác."
    }
    response = requests.post(f"{BASE_URL}/chat_query/", json=payload)
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(response.text)

if __name__ == "__main__":
    print("=== BẮT ĐẦU CHẠY KIỂM THỬ HỆ THỐNG VNXCHAT ===")
    try:
        # Chạy lần lượt các kịch bản test
        test_1_ingest_raw()
        test_2_chat_query()
        test_3_run_sandbox_manual()
        test_4_ai_sandbox_integration()
        print("\n=== HOÀN TẤT KIỂM THỬ THÀNH CÔNG! ===")
    except requests.exceptions.ConnectionError:
        print("\n[LỖI]: Không thể kết nối tới server Django. Hãy chắc chắn anh đã chạy lệnh 'python manage.py runserver'!")