# poster_core.py
from PIL import Image, ImageFilter, ImageDraw

# ================= Configs =================
CANVAS_W = 1200
CANVAS_H = 1600
BG_COLOR = (0, 0, 0, 0)

# 阴影配置
SHADOW_CONFIG = {
    "radius": 15,
    "offset": (8, 8),
    "opacity": 80, # 0-255
    "color": (0, 0, 0) 
}

# 风格配置
STYLES = {
    # 5图：依然保留特有的海报风格 (偏下，留白稍大)
    "poster": {
        "margin": 50, 
        "v_ratio": 0.618,
        "mode": "poster"
    },
    # 6-10图：统一使用高密度风格 (极小间距，撑满画面)
    "dense": {
        "margin": 25, 
        "v_ratio": 0.5, 
        "mode": "dense"
    }
}

# ================= Helpers =================
def _resize_keeping_aspect(image, target_width=None, target_height=None):
    w, h = image.size
    aspect = w / h
    if target_width:
        new_w = int(target_width)
        new_h = int(new_w / aspect)
    elif target_height:
        new_h = int(target_height)
        new_w = int(new_h * aspect)
    else:
        return image
    return image.resize((new_w, new_h), Image.Resampling.LANCZOS)

def _generate_shadow(image_size):
    w, h = image_size
    r = SHADOW_CONFIG["radius"]
    padding = r * 3
    shadow_img = Image.new('RGBA', (w + padding*2, h + padding*2), (0,0,0,0))
    draw = ImageDraw.Draw(shadow_img)
    shrink = 2
    # Apply opacity
    color = SHADOW_CONFIG["color"] + (SHADOW_CONFIG["opacity"],)
    
    draw.rectangle(
        (padding + shrink, padding + shrink, padding + w - shrink, padding + h - shrink),
        fill=color
    )
    return shadow_img.filter(ImageFilter.GaussianBlur(r))

def _paste_with_shadow(canvas, img_obj, x, y):
    shadow = _generate_shadow(img_obj.size)
    r = SHADOW_CONFIG["radius"]
    off_x, off_y = SHADOW_CONFIG["offset"]
    padding = r * 3
    
    shadow_x = int(x - padding + off_x)
    shadow_y = int(y - padding + off_y)
    
    canvas.alpha_composite(shadow, dest=(shadow_x, shadow_y))
    canvas.alpha_composite(img_obj, dest=(int(x), int(y)))

def _calculate_max_dimensions(images, margin, layout_type):
    """核心算法：计算能塞进画布的最大图片宽度"""
    # 1. 宽度优先尝试
    max_w = (CANVAS_W - (margin * 3)) // 2
    current_w = max_w
    
    # 2. 模拟计算高度
    total_h = 0
    start_idx = 0
    
    # Top区域
    if layout_type == 'top_grid':
        main_w = (current_w * 2) + margin
        ratio = images[0].width / images[0].height
        total_h += int(main_w / ratio) + margin
        start_idx = 1
        
    # Grid区域
    grid_imgs = images[start_idx:]
    for i in range(0, len(grid_imgs), 2):
        img1 = grid_imgs[i]
        ratio1 = img1.width / img1.height
        row_h = int(current_w / ratio1)
        
        if i+1 < len(grid_imgs):
            img2 = grid_imgs[i+1]
            ratio2 = img2.width / img2.height
            row_h = max(row_h, int(current_w / ratio2))
            
        total_h += row_h
        if i + 2 < len(grid_imgs): total_h += margin
            
    # 3. 检查溢出并反推
    available_h = CANVAS_H - (margin * 2)
    if total_h <= available_h:
        return current_w
    else:
        scale = available_h / total_h
        return int(current_w * scale)

def _layout_engine(canvas, images, style, layout_type):
    margin = style["margin"]
    
    # 1. 计算尺寸
    grid_w = _calculate_max_dimensions(images, margin, layout_type)
    main_w = (grid_w * 2) + margin
    
    # 2. 缩放图片
    processed = []
    start_idx = 0
    if layout_type == 'top_grid':
        processed.append(_resize_keeping_aspect(images[0], target_width=main_w))
        start_idx = 1
    for img in images[start_idx:]:
        processed.append(_resize_keeping_aspect(img, target_width=grid_w))
        
    # 3. 计算实际高度
    total_h = 0
    row_heights = []
    
    curr = 0
    if layout_type == 'top_grid':
        total_h += processed[0].height + margin
        curr = 1
        
    grid_items = processed[curr:]
    for i in range(0, len(grid_items), 2):
        h = grid_items[i].height
        if i+1 < len(grid_items):
            h = max(h, grid_items[i+1].height)
        row_heights.append(h)
        total_h += h
        if i + 2 < len(grid_items): total_h += margin
            
    # 4. 绘制
    empty_space = CANVAS_H - total_h
    start_y = int(empty_space * style["v_ratio"])
    if start_y < margin: start_y = margin
    
    draw_y = start_y
    draw_idx = 0
    center_x = CANVAS_W // 2
    
    # 绘Top
    if layout_type == 'top_grid':
        img = processed[0]
        _paste_with_shadow(canvas, img, (CANVAS_W - img.width)//2, draw_y)
        draw_y += img.height + margin
        draw_idx = 1
        
    # 绘Grid
    grid_items = processed[draw_idx:]
    row_count = 0
    for i in range(0, len(grid_items), 2):
        left = grid_items[i]
        left_x = center_x - grid_w - (margin // 2)
        _paste_with_shadow(canvas, left, left_x, draw_y)
        
        if i+1 < len(grid_items):
            right = grid_items[i+1]
            right_x = center_x + (margin // 2)
            _paste_with_shadow(canvas, right, right_x, draw_y)
            
        draw_y += row_heights[row_count] + margin
        row_count += 1

# ================= Public API =================
def generate_poster_image(image_path_list, output_path):
    """
    对外接口：传入图片路径列表和保存路径，直接生成图片。
    """
    count = len(image_path_list)
    if count < 5:
        print("Error: 至少需要5张图片")
        return False

    try:
        # Load Images
        images = [Image.open(p).convert("RGBA") for p in image_path_list]
        canvas = Image.new('RGBA', (CANVAS_W, CANVAS_H), BG_COLOR)
        
        # 路由逻辑
        if count == 5:
            # 5张图：特例，使用 Poster 风格
            _layout_engine(canvas, images, STYLES["poster"], 'top_grid')
        else:
            # 6, 7, 8, 9, 10... 统统使用 Dense 风格
            style = STYLES["dense"]
            
            # 判断布局结构
            if count % 2 == 0: 
                mode = 'sym_grid' # 双数：纯网格
            else:
                mode = 'top_grid' # 单数：上大下小
                
            _layout_engine(canvas, images, style, mode)
            
        canvas.save(output_path, "PNG")
        return True
        
    except Exception as e:
        print(f"生成失败: {e}")
        return False