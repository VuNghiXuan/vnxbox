# File path: make_logo.py
# Chú thích: Script Python tạo logo động GIF với Chú Bot Cam Đồng cử động mắt sinh động,
# dòng chữ slogan tự động hóa thông minh, chạy gõ chữ và nhấp nháy 5 lần.

import os
from PIL import Image, ImageDraw, ImageFont

def draw_copper_robot_icon(draw, x, y, size=42, frame_idx=0):
    """Vẽ chú bot cam đồng cử động mắt (chớp nháy, thay đổi độ sáng và biểu cảm liên tục)"""
    body_color = (205, 102, 38, 255)     # Cam đồng đậm
    gold_outline = (255, 215, 0, 255)    # Viền vàng Gold
    
    # Hiệu động mắt linh hoạt theo frame_idx (tạo cảm giác bot đang chớp nháy và quét dữ liệu)
    state = frame_idx % 6
    if state == 0:
        # Nhắm mắt chớp nhẹ
        eye_color = (16, 124, 65, 255)
        visor_fill = (30, 41, 59, 255)
    elif state == 3:
        # Sáng rực rỡ
        eye_color = (255, 255, 255, 255)
        visor_fill = (15, 23, 42, 255)
    else:
        # Xanh ngọc công nghệ cao đặc trưng
        eye_color = (52, 211, 153, 255)
        visor_fill = (15, 23, 42, 255)
    
    # 1. Thân / Cổ áo cơ khí
    draw.rounded_rectangle([x + 12, y + 28, x + size - 12, y + size], radius=4, fill=body_color)
    
    # 2. Đầu robot (Hình vuông bo tròn màu cam đồng, viền vàng Gold)
    draw.rounded_rectangle([x + 2, y + 6, x + size - 2, y + 28], radius=8, fill=body_color, outline=gold_outline, width=2)
    
    # 3. Kính visor màn hình mắt
    draw.rounded_rectangle([x + 6, y + 10, x + size - 6, y + 21], radius=4, fill=visor_fill)
    
    # Nếu không phải khung nhắm mắt, vẽ tròng mắt phát sáng
    if state != 0:
        draw.ellipse([x + 10, y + 13, x + 16, y + 19], fill=eye_color)
        draw.ellipse([x + size - 16, y + 13, x + size - 10, y + 19], fill=eye_color)
    else:
        # Vạch nhắm mắt
        draw.line([x + 10, y + 16, x + 16, y + 16], fill=eye_color, width=2)
        draw.line([x + size - 16, y + 16, x + size - 10, y + 16], fill=eye_color, width=2)
    
    # 4. Hai ăng-ten phát sóng trên đỉnh đầu (rung nhẹ theo frame)
    antenna_offset = 1 if (frame_idx % 2 == 0) else 0
    draw.line([x + 10, y + 6, x + 4 - antenna_offset, y - 2], fill=gold_outline, width=2)
    draw.ellipse([x + 2 - antenna_offset, y - 5, x + 6 - antenna_offset, y - 1], fill=gold_outline)
    
    draw.line([x + size - 10, y + 6, x + size - 4 + antenna_offset, y - 2], fill=gold_outline, width=2)
    draw.ellipse([x + size - 6 + antenna_offset, y - 5, x + size - 2 + antenna_offset, y - 1], fill=gold_outline)

def create_animated_logo():
    width, height = 480, 68
    frames = []
    
    bg_color = (15, 23, 42, 255)       # Slate-900 (Nền tối chuyên nghiệp)
    gold_color = (255, 215, 0, 255)    # Vàng Gold sang trọng cho tên chính
    
    try:
        font_main = ImageFont.truetype("arial.ttf", 22)
    except IOError:
        font_main = ImageFont.load_default()

    text_main = "vnxChat"
    # Slogan mới: Khẳng định khả năng tự động hóa mọi tác vụ thông minh
    text_tagline = " • Tự động hóa tác vụ thông minh"
    full_text = text_main + text_tagline
    
    # ----------------------------------------------------
    # GIAO ĐOẠN 1: Chạy chữ gõ phím mượt mà trên một dòng
    # ----------------------------------------------------
    total_steps = len(full_text) + 6
    for step in range(1, total_steps + 1):
        img = Image.new("RGBA", (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Viền khung kỹ thuật số
        draw.rounded_rectangle([4, 4, width - 4, height - 4], radius=10, outline=(238, 130, 48, 150), width=2)
        
        # Vẽ Chú Bot Cam Đồng bên trái (truyền frame_idx để mắt cử động liên tục)
        draw_copper_robot_icon(draw, x=16, y=13, size=42, frame_idx=step)
        
        # Cắt chuỗi hiển thị theo từng ký tự
        current_len = min(step, len(full_text))
        current_text = full_text[:current_len]
        
        # Vẽ chữ
        draw.text((70, 21), current_text, fill=gold_color, font=font_main)
        
        frames.append(img)

    # Dừng lại vài frame cho người dùng kịp đọc trọn vẹn câu slogan
    for _ in range(8):
        frames.append(frames[-1])

    # ----------------------------------------------------
    # GIAO ĐOẠN 2: Focus vào tên chính "vnxChat"
    # ----------------------------------------------------
    for f_idx in range(4):
        img = Image.new("RGBA", (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([4, 4, width - 4, height - 4], radius=10, outline=(238, 130, 48, 180), width=2)
        draw_copper_robot_icon(draw, x=16, y=13, size=42, frame_idx=f_idx)
        
        draw.text((70, 21), text_main, fill=gold_color, font=font_main)
        frames.append(img)

    # ----------------------------------------------------
    # GIAO ĐOẠN 3: Nhấp nháy sáng rực 5 lần liên tục
    # ----------------------------------------------------
    for blink_i in range(5):
        # Frame sáng chói (On)
        img_on = Image.new("RGBA", (width, height), bg_color)
        draw_on = ImageDraw.Draw(img_on)
        draw_on.rounded_rectangle([4, 4, width - 4, height - 4], radius=10, outline=(238, 130, 48, 255), width=2)
        draw_copper_robot_icon(draw_on, x=16, y=13, size=42, frame_idx=blink_i)
        draw_on.text((70, 21), text_main, fill=(255, 240, 100, 255), font=font_main)
        
        for _ in range(2):
            frames.append(img_on)
            
        # Frame trầm nhẹ (Off)
        img_off = Image.new("RGBA", (width, height), bg_color)
        draw_off = ImageDraw.Draw(img_off)
        draw_off.rounded_rectangle([4, 4, width - 4, height - 4], radius=10, outline=(238, 130, 48, 80), width=2)
        draw_copper_robot_icon(draw_off, x=16, y=13, size=42, frame_idx=blink_i + 1)
        draw_off.text((70, 21), text_main, fill=(180, 140, 0, 255), font=font_main)
        
        for _ in range(2):
            frames.append(img_off)

    # Lưu file GIF động
    output_path = "dashboard/static/dashboard/vuxuan_animated_logo.gif"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        optimize=True,
        duration=80,
        loop=0
    )
    print(f"✨ Đã tạo logo Bot cam đồng chớp mắt cử động thành công tại: {output_path}")

if __name__ == "__main__":
    create_animated_logo()