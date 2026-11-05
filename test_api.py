import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/chapters"

def test_1_ingest_raw():
    print("\n--- [TEST 1] Đang test Ingest văn bản thô (Tự động duyệt / Auto-Approval) ---")
    payload = {
        "domain_name": "Thu đổi vàng",
        "scope": "Áp dụng toàn hệ thống",
        "raw_text": "Quy định thu đổi vàng cũ: Vàng 24K mua vào tính bằng 98% giá niêm yết thị trường. Khách hàng đổi sang mẫu mới được chiết khấu thêm 2% trên tổng giá trị giao dịch."
    }
    response = requests.post(f"{BASE_URL}/ingest_raw/", json=payload)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    return response.json()

def test_2_chat_query():
    print("\n--- [TEST 2] Đang test Chat Query & Hybrid Search kết hợp Sandbox tính toán ---")
    payload = {
        "domain_name": "Thu đổi vàng",
        "question": "Tôi có vàng 24K giá trị niêm yết 10,000,000 VNĐ đem đổi sang mẫu mới thì thực nhận hoặc tiền thanh toán sau chiết khấu là bao nhiêu? Hãy tính toán giúp tôi."
    }
    response = requests.post(f"{BASE_URL}/chat_query/", json=payload)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))

def test_3_run_sandbox_manual():
    print("\n--- [TEST 3] Đang test trực tiếp Secure Code Sandbox ---")
    payload = {
        "code": "gia_niem_yet = 10000000\ngia_mua_vao = gia_niem_yet * 0.98\nchiet_khau = gia_niem_yet * 0.02\nket_qua = gia_mua_vao + chiet_khau\nprint(f'Tong gia tri thuc te: {ket_qua}')",
        "timeout": 3
    }
    response = requests.post(f"{BASE_URL}/run_sandbox/", json=payload)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    print("=== BẮT ĐẦU CHẠY KIỂM THỬ HỆ THỐNG VNXCHAT ===")
    try:
        # Chạy lần lượt các kịch bản test
        test_1_ingest_raw()
        test_2_chat_query()
        test_3_run_sandbox_manual()
        print("\n=== HOÀN TẤT KIỂM THỬ THÀNH CÔNG! ===")
    except requests.exceptions.ConnectionError:
        print("\n[LỖI]: Không thể kết nối tới server Django. Hãy chắc chắn anh đã chạy lệnh 'python manage.py runserver'!")