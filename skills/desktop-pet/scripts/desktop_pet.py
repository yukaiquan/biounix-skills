#!/usr/bin/env python3
"""
Desktop Pet v4 - 像素风小猫 🐱
PIL 生成像素 sprite · 无边框透明 · BioUnix 通知集成

Usage:  python desktop_pet.py
Needs:  Python 3.6+, tkinter (built-in), Pillow
OS:     Windows (完美透明) / macOS (透明) / Linux (暂不支持)

Interactions:
  - Drag          : 拖拽移动
  - Double-click  : 互动（Meow~）
  - Right-click   : 菜单（测试通知/退出）

BioUnix 通知:
  Agent 写入 ~/.biounix/pet_notify.json → 宠物弹气泡 + 表情反应
  格式: {"type": "task_complete|task_failed|task_progress|info",
         "title": "...", "message": "...", "timestamp": 1234567890}

Author: liangxiaotian+BioUnix+GLM5.2
"""

import tkinter as tk
import platform
import sys
import os
import json
import time
import random
from PIL import Image, ImageTk


class DesktopPet:
    """桌面宠物（像素风小猫，跨平台透明窗口）"""

    W = 120
    H = 120
    SCALE = 5       # 像素放大倍数
    SPRITE = 24     # sprite 原始尺寸 24x24
    TICK = 120      # 动画帧间隔 ms
    NOTIFY_POLL = 2000
    NOTIFY_FILE = os.path.expanduser('~/.biounix/pet_notify.json')

    # 像素颜色调色板
    C_TRANS = (0, 0, 0, 0)       # 透明
    C_OUTLINE = (40, 40, 40, 255) # 黑色轮廓
    C_BODY = (255, 180, 80, 255)  # 橘色身体
    C_BODY_DK = (220, 140, 50, 255) # 深橘
    C_BELLY = (255, 230, 180, 255) # 浅黄肚子
    C_EYE = (40, 40, 40, 255)     # 眼睛黑
    C_EYE_HL = (255, 255, 255, 255) # 眼睛高光
    C_NOSE = (255, 130, 140, 255) # 粉鼻头
    C_INNER_EAR = (255, 180, 180, 255) # 耳朵内侧
    C_PAW = (255, 220, 160, 255)  # 爪子

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.os_name = platform.system()
        self.is_win = self.os_name == 'Windows'
        self.is_mac = self.os_name == 'Darwin'

        # 跨平台透明策略
        try:
            self.root.attributes('-topmost', True)
        except Exception:
            pass

        self.transparency = 'none'  # none / colorkey / alpha / mac

        if self.is_win:
            # Windows: -transparentcolor 原生支持，完美透明
            try:
                self.root.attributes('-transparentcolor', '#FF00FF')
                self.transparency = 'colorkey'
            except Exception:
                pass
        elif self.is_mac:
            # macOS: -transparent 属性
            try:
                self.root.attributes('-transparent', True)
                self.root.attributes('-alpha', 1.0)
                self.transparency = 'mac'
            except Exception:
                pass
        else:
            # Linux/WSLg: -transparentcolor 不支持，用 -alpha 半透明 fallback
            try:
                self.root.attributes('-alpha', 0.95)
                self.transparency = 'alpha'
            except Exception:
                pass

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.x = sw - self.W - 80
        self.y = sh - self.H - 100
        self.root.geometry(f'{self.W}x{self.H}+{self.x}+{self.y}')

        # Canvas 背景：Windows 用品红(透明key)，Linux 用深灰(半透明时不突兀)
        if self.transparency == 'colorkey':
            bg_color = '#FF00FF'
        elif self.transparency == 'alpha':
            bg_color = '#1a1a1a'  # 深灰，半透明后接近桌面
        else:
            bg_color = '#FF00FF'
        self.canvas = tk.Canvas(self.root, width=self.W, height=self.H,
                                bg=bg_color, highlightthickness=0)
        self.canvas.pack()

        # 生成所有帧的 sprite
        self.frames_normal = self._gen_frames_normal()
        self.frames_blink = self._gen_frames_blink()
        self.frames_happy = self._gen_frames_happy()
        self.frames_sad = self._gen_frames_sad()
        self._tk_frames = {}  # 缓存 ImageTk PhotoImage

        # 状态
        self.dragging = False
        self.frame_idx = 0
        self.anim_state = 'normal'  # normal / blink / happy / sad
        self.anim_timer = 0
        self.blink_t = random.randint(50, 150)
        self.off_x = 0
        self.off_y = 0

        # 通知
        self.last_notify_ts = 0
        self.notify_expr = ''
        self.notify_timer = 0

        # 事件
        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<B1-Motion>', self._on_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_release)
        self.canvas.bind('<Double-Button-1>', self._on_pet)
        self.canvas.bind('<Button-3>', self._on_right)
        self.canvas.bind('<Button-2>', self._on_right)

        self._animate()
        self._poll_notify()
        self._keep_on_top()
        self.root.mainloop()

    # ================================================================
    #  像素 sprite 生成
    # ================================================================
    def _make_sprite(self, draw_func):
        """用回调函数在 24x24 透明画布上画像素，返回 PIL Image"""
        img = Image.new('RGBA', (self.SPRITE, self.SPRITE), self.C_TRANS)
        px = img.load()
        draw_func(px)
        return img.resize((self.SPRITE * self.SCALE, self.SPRITE * self.SCALE),
                          Image.NEAREST)

    def _px(self, px, x, y, color):
        """安全设像素"""
        if 0 <= x < self.SPRITE and 0 <= y < self.SPRITE:
            px[x, y] = color

    def _rect(self, px, x0, y0, x1, y1, color):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                self._px(px, x, y, color)

    def _draw_cat_base(self, px, tail_offset=0):
        """画猫的基础身体（不含眼睛嘴巴），tail_offset 控制尾巴摆动"""
        # 耳朵 (尖三角)
        for dy in range(4):
            self._rect(px, 5 + dy, 4 - dy, 8 - dy, 4 - dy, self.C_OUTLINE)
            self._rect(px, 15 + dy, 4 - dy, 18 - dy, 4 - dy, self.C_OUTLINE)
        # 耳朵内侧
        self._rect(px, 7, 2, 8, 2, self.C_INNER_EAR)
        self._rect(px, 15, 2, 16, 2, self.C_INNER_EAR)
        # 头部轮廓顶
        self._rect(px, 5, 5, 18, 5, self.C_OUTLINE)
        # 身体轮廓左右
        for y in range(6, 19):
            self._px(px, 5, y, self.C_OUTLINE)
            self._px(px, 18, y, self.C_OUTLINE)
        # 底部
        self._rect(px, 5, 19, 18, 19, self.C_OUTLINE)
        # 身体填充
        self._rect(px, 6, 6, 17, 18, self.C_BODY)
        # 条纹（深橘）
        self._rect(px, 7, 7, 16, 7, self.C_BODY_DK)
        self._rect(px, 7, 11, 16, 11, self.C_BODY_DK)
        self._rect(px, 7, 15, 16, 15, self.C_BODY_DK)
        # 肚子（浅黄）
        self._rect(px, 9, 13, 14, 18, self.C_BELLY)
        # 尾巴 (右侧，根据 tail_offset 变化)
        tx = 19 + tail_offset
        for y in range(14, 18):
            self._px(px, tx, y, self.C_OUTLINE)
            self._px(px, tx + 1, y, self.C_BODY)
        self._px(px, tx, 13, self.C_OUTLINE)
        # 爪子
        self._rect(px, 7, 19, 9, 19, self.C_PAW)
        self._rect(px, 14, 19, 16, 19, self.C_PAW)

    def _draw_eyes_normal(self, px):
        self._rect(px, 8, 9, 10, 11, self.C_EYE)
        self._px(px, 9, 9, self.C_EYE_HL)
        self._rect(px, 13, 9, 15, 11, self.C_EYE)
        self._px(px, 14, 9, self.C_EYE_HL)

    def _draw_eyes_blink(self, px):
        self._rect(px, 8, 10, 10, 10, self.C_EYE)
        self._rect(px, 13, 10, 15, 10, self.C_EYE)

    def _draw_eyes_happy(self, px):
        self._px(px, 8, 11, self.C_EYE)
        self._px(px, 9, 10, self.C_EYE)
        self._px(px, 10, 11, self.C_EYE)
        self._px(px, 13, 11, self.C_EYE)
        self._px(px, 14, 10, self.C_EYE)
        self._px(px, 15, 11, self.C_EYE)

    def _draw_eyes_sad(self, px):
        self._px(px, 8, 9, self.C_EYE)
        self._px(px, 9, 10, self.C_EYE)
        self._px(px, 10, 11, self.C_EYE)
        self._px(px, 13, 9, self.C_EYE)
        self._px(px, 14, 10, self.C_EYE)
        self._px(px, 15, 11, self.C_EYE)

    def _draw_mouth_normal(self, px):
        self._px(px, 11, 14, self.C_NOSE)
        self._px(px, 12, 14, self.C_NOSE)
        self._px(px, 11, 15, self.C_OUTLINE)
        self._px(px, 12, 15, self.C_OUTLINE)

    def _draw_mouth_happy(self, px):
        self._px(px, 11, 14, self.C_NOSE)
        self._px(px, 12, 14, self.C_NOSE)
        self._px(px, 10, 15, self.C_OUTLINE)
        self._px(px, 11, 16, self.C_OUTLINE)
        self._px(px, 12, 16, self.C_OUTLINE)
        self._px(px, 13, 15, self.C_OUTLINE)

    def _draw_mouth_sad(self, px):
        self._px(px, 11, 14, self.C_NOSE)
        self._px(px, 12, 14, self.C_NOSE)
        self._px(px, 10, 16, self.C_OUTLINE)
        self._px(px, 11, 15, self.C_OUTLINE)
        self._px(px, 12, 15, self.C_OUTLINE)
        self._px(px, 13, 16, self.C_OUTLINE)

    def _gen_frames_normal(self):
        frames = []
        for i in range(4):
            tail = [0, 1, 0, -1][i]
            def draw(px, t=tail):
                self._draw_cat_base(px, tail_offset=t)
                self._draw_eyes_normal(px)
                self._draw_mouth_normal(px)
            frames.append(self._make_sprite(draw))
        return frames

    def _gen_frames_blink(self):
        def draw(px):
            self._draw_cat_base(px, tail_offset=0)
            self._draw_eyes_blink(px)
            self._draw_mouth_normal(px)
        return [self._make_sprite(draw)]

    def _gen_frames_happy(self):
        frames = []
        for i in range(2):
            tail = [0, 1][i]
            def draw(px, t=tail):
                self._draw_cat_base(px, tail_offset=t)
                self._draw_eyes_happy(px)
                self._draw_mouth_happy(px)
            frames.append(self._make_sprite(draw))
        return frames

    def _gen_frames_sad(self):
        def draw(px):
            self._draw_cat_base(px, tail_offset=-1)
            self._draw_eyes_sad(px)
            self._draw_mouth_sad(px)
        return [self._make_sprite(draw)]

    def _get_tk_frame(self, pil_img):
        key = id(pil_img)
        if key not in self._tk_frames:
            self._tk_frames[key] = ImageTk.PhotoImage(pil_img)
        return self._tk_frames[key]

    # ================================================================
    #  平台 & 置顶
    # ================================================================
    def _keep_on_top(self):
        if self.is_mac:
            try:
                self.root.lift()
                self.root.attributes('-topmost', True)
            except Exception:
                pass
        self.root.after(3000, self._keep_on_top)

    # ================================================================
    #  动画循环
    # ================================================================
    def _animate(self):
        self.anim_timer += 1
        if self.notify_timer > 0:
            self.notify_timer -= 1
            if self.notify_expr == 'happy':
                frames = self.frames_happy
            elif self.notify_expr == 'sad':
                frames = self.frames_sad
            else:
                frames = self.frames_normal
        elif self.anim_state == 'blink':
            frames = self.frames_blink
            if self.anim_timer > 3:
                self.anim_state = 'normal'
                self.anim_timer = 0
                self.blink_t = random.randint(50, 150)
        else:
            self.blink_t -= 1
            if self.blink_t <= 0:
                self.anim_state = 'blink'
                self.anim_timer = 0
            frames = self.frames_normal
        self.frame_idx = (self.frame_idx + 1) % len(frames)
        self.canvas.delete('all')
        tk_img = self._get_tk_frame(frames[self.frame_idx])
        self.canvas.create_image(self.W // 2, self.H // 2, image=tk_img)
        if not self.dragging and random.random() < 0.008:
            self._move(random.randint(-2, 2), random.randint(-1, 1))
        self.root.after(self.TICK, self._animate)

    def _move(self, dx, dy):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.x = max(0, min(sw - self.W, self.x + dx))
        self.y = max(0, min(sh - self.H, self.y + dy))
        self.root.geometry(f'{self.W}x{self.H}+{self.x}+{self.y}')

    # ================================================================
    #  通知集成
    # ================================================================
    def _poll_notify(self):
        try:
            if os.path.exists(self.NOTIFY_FILE):
                with open(self.NOTIFY_FILE, 'r') as f:
                    data = json.load(f)
                notifies = data if isinstance(data, list) else [data]
                for n in notifies:
                    ts = n.get('timestamp', 0)
                    if ts > self.last_notify_ts:
                        self._handle_notify(n)
                        self.last_notify_ts = max(self.last_notify_ts, ts)
                with open(self.NOTIFY_FILE, 'w') as f:
                    json.dump([], f)
        except (json.JSONDecodeError, IOError, KeyError):
            pass
        self.root.after(self.NOTIFY_POLL, self._poll_notify)

    def _handle_notify(self, notify):
        ntype = notify.get('type', 'info')
        title = notify.get('title', '')
        message = notify.get('message', '')
        if ntype == 'task_complete':
            self.notify_expr = 'happy'
            self.notify_timer = 30
            text = f'🎉 {title}' if title else '🎉 完成！'
        elif ntype == 'task_failed':
            self.notify_expr = 'sad'
            self.notify_timer = 30
            text = f'💔 {title}' if title else '💔 失败...'
        elif ntype == 'task_progress':
            self.notify_expr = 'normal'
            self.notify_timer = 15
            text = f'⏳ {message}' if message else '⏳ 进行中...'
        else:
            text = f'💬 {message}' if message else f'💬 {title}'
        self._bubble(text, duration=4000, width=180, is_notify=True)

    # ================================================================
    #  交互
    # ================================================================
    def _on_click(self, e):
        self.dragging = True
        self.off_x = e.x
        self.off_y = e.y

    def _on_drag(self, e):
        if self.dragging:
            self.x = self.root.winfo_pointerx() - self.off_x
            self.y = self.root.winfo_pointery() - self.off_y
            self.root.geometry(f'{self.W}x{self.H}+{self.x}+{self.y}')

    def _on_release(self, e):
        self.dragging = False

    def _on_pet(self, e):
        self.notify_expr = 'happy'
        self.notify_timer = 20
        self._bubble('Meow~ 🐱')

    def _on_right(self, e):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label='🔔 测试通知', command=self._test_notify)
        m.add_separator()
        m.add_command(label='❌ 退出', command=self._quit)
        m.post(e.x_root, e.y_root)

    def _test_notify(self):
        self._handle_notify({
            'type': 'task_complete',
            'title': '测试通知',
            'message': 'BioUnix 通知正常~',
            'timestamp': time.time()
        })

    def _quit(self):
        self.root.quit()

    # ================================================================
    #  气泡
    # ================================================================
    def _bubble(self, text, duration=2000, width=120, is_notify=False):
        b = tk.Toplevel(self.root)
        b.overrideredirect(True)
        b.attributes('-topmost', True)
        if self.transparency == 'colorkey':
            b.attributes('-transparentcolor', '#FF00FF')
            b.config(bg='#FF00FF')
        elif self.transparency == 'alpha':
            b.attributes('-alpha', 0.95)
        elif self.is_mac:
            try:
                b.attributes('-transparent', True)
            except Exception:
                pass
        bh = 30 if is_notify else 24
        bx = self.x + self.W // 2 - width // 2
        by = self.y - bh - 5
        b.geometry(f'{width}x{bh}+{bx}+{by}')
        bg_c = '#FFF8DC' if is_notify else 'white'
        fnt = ('Arial', 10, 'bold') if is_notify else ('Arial', 9)
        tk.Label(b, text=text, font=fnt, bg=bg_c, fg='#333',
                 relief='solid', bd=1, wraplength=width - 10
                 ).pack(fill='both', expand=True, padx=2, pady=2)
        b.after(duration, b.destroy)


# ================================================================
#  通知写入工具（供 Agent / 脚本调用）
# ================================================================
def send_notify(ntype, title='', message=''):
    """写入通知到 pet_notify.json，宠物会在下次轮询时读取。

    参数:
        ntype   : 'task_complete' | 'task_failed' | 'task_progress' | 'info'
        title   : 通知标题
        message : 通知内容
    """
    notify_dir = os.path.dirname(DesktopPet.NOTIFY_FILE)
    os.makedirs(notify_dir, exist_ok=True)
    notify = {'type': ntype, 'title': title, 'message': message, 'timestamp': time.time()}
    existing = []
    try:
        if os.path.exists(DesktopPet.NOTIFY_FILE):
            with open(DesktopPet.NOTIFY_FILE, 'r') as f:
                data = json.load(f)
                existing = data if isinstance(data, list) else [data]
    except (json.JSONDecodeError, IOError):
        pass
    existing.append(notify)
    with open(DesktopPet.NOTIFY_FILE, 'w') as f:
        json.dump(existing, f, ensure_ascii=False)


if __name__ == '__main__':
    _os = platform.system()
    if _os == 'Linux':
        print('⚠️  Desktop Pet 暂不支持 Linux/WSLg（透明窗口限制）', flush=True)
        print('   请在 Windows 或 macOS 上运行：python desktop_pet.py', flush=True)
        sys.exit(0)
    print('🐱 像素风小猫 v4 启动...', flush=True)
    print(f'   系统: {_os}', flush=True)
    print(f'   通知: {DesktopPet.NOTIFY_FILE}', flush=True)
    print('   右键→退出', flush=True)
    try:
        DesktopPet()
    except KeyboardInterrupt:
        print('\n拜拜~', flush=True)
        sys.exit(0)
