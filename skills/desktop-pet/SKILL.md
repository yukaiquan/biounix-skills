---
name: desktop-pet
description: 使用 PIL 生成 24×24 像素风小猫的桌面宠物，支持 Windows/macOS 透明无边框、拖拽移动、双击互动、右键菜单，并集成 BioUnix 通知轮询（任务完成→🎉、失败→💔、进度→⏳）。纯 Python 标准库 + Pillow，零外部依赖。当用户想要桌面宠物、像素猫、桌面通知指示器，或提到 desktop pet、像素风小猫、pet_notify 时触发。
triggers:
  - 桌面宠物
  - desktop pet
  - 像素猫
  - 像素风小猫
  - 通知集成
  - pet_notify
  - 桌面通知
  - BioUnix 通知
  - pixel cat
always_active: false
version: null
category: null
author: glm-5.2 + BioUnix
---
Pixel-art desktop pet (24×24 orange tabby cat) with transparency, drag-to-move, double-click interaction, right-click menu, and BioUnix notification polling. Pure Python stdlib + Pillow, zero external dependencies.

## Quick Start

1. Ensure Python 3.8+ and Pillow are installed: `pip install Pillow`
2. Run the pet: `python scripts/desktop_pet.py`
3. Verify the cat appears on screen — always-on-top, transparent background, animated tail (4-frame swing), random blink.

## Platform Behavior

- **Windows**: Uses `-transparentcolor` for pixel-perfect transparency. Verified working.
- **macOS**: Uses `-transparent` attribute. May require terminal accessibility permissions on first run.
- **Linux/WSLg**: Detected and exits with a friendly message. Transparency support is inconsistent across compositors, so Linux is disabled in this version.

## Interaction

- **Drag**: Click and hold to reposition the cat anywhere on screen.
- **Double-click**: Triggers a "Meow~" speech bubble.
- **Right-click**: Context menu with "Test Notification" and "Exit" options.

## BioUnix Notification Integration

The pet polls `~/.biounix/pet_notify.json` every 2 seconds. Write notification entries to this file to trigger mood changes:

- Task completed → 🎉 happy cat
- Task failed → 💔 sad cat  
- Progress update → ⏳ neutral

See [📋 Notification Integration](./references/notify_integration.md) for the JSON schema and usage examples.

## Customization

Edit `scripts/desktop_pet.py` to adjust:
- Sprite colors (orange tabby stripes, pink nose, eye size)
- Animation frames (tail swing speed, blink frequency)
- Notification poll interval
- Window size and initial position

## When to Use

Use this skill when the user wants a desktop companion, pixel pet, or visual notification indicator for BioUnix task completion. Also suitable as a lightweight always-on-top status monitor for long-running bioinformatics pipelines.