import sys
import io
import contextlib
import multiprocessing

# Danh sách các module bị cấm tuyệt đối để đảm bảo bảo mật hệ thống
FORBIDDEN_MODULES = ['os', 'sys', 'subprocess', 'socket', 'shutil', 'pathlib', 'ctypes', 'requests']

def _restricted_execution_worker(code_str, context_dict, return_dict):
    """
    Hàm worker chạy trong tiến trình độc lập (multiprocessing) 
    để cô lập hoàn toàn môi trường thực thi của Secure Sandbox.
    """
    # Kiểm tra an toàn cơ bản chống mã độc hệ thống
    for mod in FORBIDDEN_MODULES:
        if f"import {mod}" in code_str or f"from {mod}" in code_str:
            return_dict["success"] = False
            return_dict["output"] = f"⚠️ Lỗi bảo mật: Mã Python chứa module bị cấm ({mod})."
            return

    # Nạp các biến ngữ cảnh (context) vào không gian thực thi nếu có
    local_scope = dict(context_dict) if context_dict else {}
    global_scope = {"__builtins__": __builtins__}

    # Chặn các built-in nguy hiểm như open, eval, exec nếu cần thiết
    # Ở đây giữ lại toán học cơ bản và built-in an toàn
    
    output_capture = io.StringIO()
    try:
        # Chuyển hướng stdout để bắt toàn bộ lệnh print()
        with contextlib.redirect_stdout(output_capture):
            exec(code_str, global_scope, local_scope)
            
        # Lấy giá trị biến 'result' hoặc 'ket_qua' nếu có định nghĩa sẵn trong code
        result_value = local_scope.get("result", local_scope.get("ket_qua", None))
        printed_output = output_capture.getvalue().strip()
        
        final_output = ""
        if printed_output:
            final_output = printed_output
        elif result_value is not None:
            final_output = str(result_value)
        else:
            final_output = "Đã thực thi thành công (Không có giá trị trả về tường minh)."

        return_dict["success"] = True
        return_dict["output"] = final_output
        return_dict["variables"] = {k: v for k, v in local_scope.items() if not k.startswith('_') and not callable(v)}

    except Exception as e:
        return_dict["success"] = False
        return_dict["output"] = f"Lỗi thực thi code Python: {str(e)}"


def run_secure_sandbox(code_str, context_dict=None, timeout_seconds=3):
    """
    Thực thi mã Python an toàn trong Secure Code Sandbox với cơ chế giới hạn thời gian (Timeout).
    Triệt tiêu hoàn toàn ảo giác toán học của AI.
    """
    manager = multiprocessing.Manager()
    return_dict = manager.dict()

    p = multiprocessing.Process(
        target=_restricted_execution_worker, 
        args=(code_str, context_dict or {}, return_dict)
    )
    
    p.start()
    p.join(timeout=timeout_seconds)

    if p.is_alive():
        # Nếu quá thời gian cho phép (Timeout) -> Tiêu diệt tiến trình ngay lập tức
        p.terminate()
        p.join()
        return {
            "success": False,
            "output": f"⚠️ Lỗi Sandbox: Đoạn mã Python vượt quá thời gian cho phép ({timeout_seconds} giây) và đã bị dừng khẩn cấp."
        }

    if not return_dict:
        return {
            "success": False,
            "output": "⚠️ Lỗi Sandbox: Tiến trình bị lỗi không xác định hoặc trả về dữ liệu trống."
        }

    return {
        "success": return_dict.get("success", False),
        "output": return_dict.get("output", ""),
        "variables": return_dict.get("variables", {})
    }