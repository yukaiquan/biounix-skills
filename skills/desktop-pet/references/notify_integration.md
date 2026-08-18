# BioUnix 通知集成指南

## 通知机制

桌面宠物通过**文件轮询**方式接收 BioUnix 通知：

```
Agent / 生信脚本  →  写入 ~/.biounix/pet_notify.json  →  宠物每 2 秒轮询  →  弹气泡 + 表情反应
```

## 通知文件格式

路径：`~/.biounix/pet_notify.json`

```json
[
  {
    "type": "task_complete",
    "title": "VCF 过滤完成",
    "message": "chr1A 处理完毕，保留 14595 个 SNP",
    "timestamp": 1697123456.789
  }
]
```

## 通知类型

| type | 图标 | 表情反应 |
|---|---|---|
| `task_complete` | 🎉 | 开心笑眼 |
| `task_failed` | 💔 | 难过垂眼 |
| `task_progress` | ⏳ | 正常 |
| `info` | 💬 | 正常 |

## Agent 发送通知

### 方式 1：Python 一行命令
```bash
python -c "import desktop_pet; desktop_pet.send_notify('task_complete', 'VCF过滤完成', 'chr1A 保留 14595 SNP')"
```

### 方式 2：直接写 JSON 文件
```bash
python -c "
import json, time
notify = {'type':'task_complete','title':'任务完成','message':'21条染色体全部过滤完毕','timestamp':time.time()}
with open('$HOME/.biounix/pet_notify.json','w') as f:
    json.dump([notify], f)
"
```

### 方式 3：在 bash 脚本末尾追加
```bash
echo '{"type":"task_complete","title":"VCF过滤完成","message":"21条染色体全部完成","timestamp":'$(date +%s)'}' > ~/.biounix/pet_notify.json
```

## 集成到 filter_21chr.sh

在脚本关键节点添加通知：
```bash
# Step 1 完成后
python -c "import desktop_pet; desktop_pet.send_notify('task_progress','Step 1 完成','Depth 过滤阶段完成')"

# 全部完成后
python -c "import desktop_pet; desktop_pet.send_notify('task_complete','全部完成','21条染色体合并完成')"

# 出错时
python -c "import desktop_pet; desktop_pet.send_notify('task_failed','任务失败','chr3D 处理出错')"
```
