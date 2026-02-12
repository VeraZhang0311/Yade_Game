# Yade Game 后端 API 规范

> **Base URL**: `http://<server>:8000`
> **协议**: HTTP REST + WebSocket
> **数据格式**: JSON (UTF-8)

---

## 目录

1. [架构说明](#架构说明)
2. [玩家 Player](#1-玩家-player)
3. [关卡 Levels](#2-关卡-levels)
4. [闲聊 Chat](#3-闲聊-chat)
5. [好感度 Affinity](#4-好感度-affinity)
6. [好感度等级对照表](#好感度等级对照表)
7. [错误码](#错误码)
8. [前后端对齐要点](#前后端对齐要点)

---

## 架构说明

```
前端 (Unity + YarnSpinner)              后端 (FastAPI)
┌──────────────────────┐           ┌──────────────────────┐
│  .yarn 对话树文件     │           │  YAML: 选项→好感度映射 │
│  本地驱动对话推进      │           │  PostgreSQL: 玩家数据  │
│  遇到选项 → 调后端    │ ───HTTP──→│  Redis: 聊天上下文     │
│  完成关卡 → 调后端    │           │  LLM: 闲聊回复        │
│  闲聊 → WebSocket    │ ───WS───→ │                      │
└──────────────────────┘           └──────────────────────┘
```

**核心原则**：
- 对话树由前端 YarnSpinner 管理，后端**不存储**对话内容
- 前端在玩家做出选择时调 `POST /api/levels/choice`，后端记录并返回好感度变化
- 前端在关卡结束时调 `POST /api/levels/complete`，后端解锁下一关
- 前后端通过 `node_id` + `choice_id` 对齐（必须命名一致）

---

## 1. 玩家 Player

### 1.1 创建玩家

```
POST /api/player/
```

**Request Body**:
```json
{
  "name": "小明",        // 可选，默认 "Player"，1-100字符
  "nickname": "明明"     // 可选
}
```

**Response** `201`:
```json
{
  "id": 1,
  "name": "小明",
  "nickname": "明明",
  "current_level_id": "chapter_01",
  "max_unlocked_level": "chapter_01",
  "affinity_score": 0,
  "affinity_tier": "陌生人",
  "memory_facts": {},
  "bio": null,
  "created_at": "2026-02-12T10:00:00",
  "updated_at": "2026-02-12T10:00:00"
}
```

### 1.2 获取玩家信息

```
GET /api/player/{player_id}
```

**Response** `200`: 同上 PlayerState 格式

**Error** `404`: `{"detail": "Player not found"}`

### 1.3 更新玩家信息

```
PATCH /api/player/{player_id}
```

**Request Body**（所有字段可选，只传需要改的）:
```json
{
  "name": "新名字",
  "nickname": "新昵称",
  "bio": "个人简介"
}
```

**Response** `200`: PlayerState 格式

### 1.4 删除玩家

```
DELETE /api/player/{player_id}
```

**Response** `204`: 无内容

### 1.5 重置玩家进度

```
POST /api/player/{player_id}/reset
```

重置好感度、关卡进度、记忆，保留 name/nickname/bio。

**Response** `200`:
```json
{
  "message": "Progress reset successfully",
  "player": { /* PlayerState */ }
}
```

---

## 2. 关卡 Levels

### 2.1 获取关卡列表

```
GET /api/levels/?player_id={player_id}
```

返回所有关卡及当前玩家的解锁状态。

**Response** `200`:
```json
[
  {
    "id": "chapter_01",
    "title": "初次相遇",
    "order": 1,
    "is_unlocked": true
  },
  {
    "id": "chapter_02",
    "title": "市场风波",
    "order": 2,
    "is_unlocked": false
  }
]
```

### 2.2 提交选择

```
POST /api/levels/choice?player_id={player_id}
```

前端在 YarnSpinner 对话中遇到选择节点，玩家选择后调用此接口。

**Request Body**:
```json
{
  "level_id": "chapter_01",
  "node_id": "choice_3",       // 与 .yarn 文件中的选择节点 ID 一致
  "choice_id": "A"             // 玩家选择的选项 ID
}
```

**Response** `200`:
```json
{
  "affinity_delta": 3,         // 本次好感度变化
  "new_affinity_total": 5,     // 好感度新总分
  "affinity_tier": "陌生人"     // 当前好感度等级
}
```

**Error** `400`: `{"detail": "Invalid level, node, or choice ID"}`
**Error** `404`: `{"detail": "Player not found"}`

### 2.3 完成关卡

```
POST /api/levels/complete?player_id={player_id}
```

前端播放到关卡结局节点时调用此接口，后端解锁下一关。

**Request Body**:
```json
{
  "level_id": "chapter_01",
  "ending_node": "ending_good"   // 可选，标记到达了哪个结局
}
```

**Response** `200`:
```json
{
  "next_level_id": "chapter_02",  // 下一关 ID，最后一关为 null
  "unlocked": true,               // 是否解锁了新关卡
  "total_affinity": 5,
  "affinity_tier": "陌生人"
}
```

**Error** `404`: `{"detail": "Level not found"}` 或 `{"detail": "Player not found"}`

### 2.4 查询进度

```
GET /api/levels/progress?player_id={player_id}
```

**Response** `200`:
```json
{
  "current_level": "chapter_01",
  "unlocked_levels": ["chapter_01"],
  "total_affinity": 5,
  "affinity_tier": "陌生人"
}
```

---

## 3. 闲聊 Chat

### 3.1 WebSocket 实时聊天

```
WS /ws/chat/{player_id}
```

关卡之间的自由闲聊，后端通过 LLM 生成亚德的回复，流式推送。

**客户端发送**:
```json
{"type": "message", "content": "你好呀亚德！"}
```

**服务端流式回复**（多条）:
```json
{"type": "chunk", "content": "你"}
{"type": "chunk", "content": "好"}
{"type": "chunk", "content": "呀！"}
```

**流式结束标记**:
```json
{"type": "end"}
```

**错误**:
```json
{"type": "error", "content": "错误描述"}
```

**说明**:
- 连接后可反复发送消息，服务端每次流式回复
- 断开连接时，后端自动评估本次聊天质量并更新好感度
- 后端自动提取关键记忆存入玩家档案
- 亚德的回复风格会随好感度等级变化（好感度越高越亲近）

### 3.2 获取聊天记录

```
GET /api/chat/history/{player_id}?limit=50
```

**参数**: `limit` — 返回最近 N 条记录，默认 50

**Response** `200`:
```json
{
  "messages": [
    {"role": "user", "content": "你好呀亚德！"},
    {"role": "assistant", "content": "你好呀！好久不见，今天过得怎么样？"}
  ]
}
```

---

## 4. 好感度 Affinity

### 4.1 查询好感度

```
GET /api/affinity/{player_id}
```

**Response** `200`:
```json
{
  "score": 5,
  "level": "陌生人"
}
```

---

## 好感度等级对照表

| 分数区间 | 等级 | 说明 |
|---------|------|------|
| 0 ~ 19  | 陌生人 | 初始状态，亚德较为冷淡 |
| 20 ~ 39 | 认识   | 开始有基本交流 |
| 40 ~ 59 | 朋友   | 亚德愿意分享更多 |
| 60 ~ 79 | 好友   | 关系亲密，语气温暖 |
| 80 ~ 99 | 挚友   | 深度信任 |
| 100+    | 羁绊   | 最高等级 |

好感度来源：
1. **关卡选择**（`POST /api/levels/choice`）— 每个选项有固定 `affinity_delta`
2. **闲聊质量**（WebSocket 断开时自动评估）— LLM 根据对话深度、情感投入打分

---

## 错误码

| HTTP 状态码 | 含义 |
|------------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无返回体） |
| 400 | 请求参数错误（如无效的 node_id / choice_id） |
| 404 | 资源不存在（玩家/关卡） |
| 422 | 请求体格式错误（Pydantic 验证失败） |

所有错误返回格式：
```json
{"detail": "错误描述"}
```

---

## 前后端对齐要点

### node_id / choice_id 命名约定

后端 YAML（`chapter_01.yaml`）示例：
```yaml
choices:
  choice_1:          # ← node_id
    A:               # ← choice_id
      affinity_delta: 1
    B:
      affinity_delta: 0
    C:
      affinity_delta: -1
  choice_3:
    A:
      affinity_delta: 3
      is_major: true
```

前端 `.yarn` 文件中对应的选择节点必须使用**完全相同的** `node_id` 和 `choice_id`。

### 典型调用流程

```
1. 游戏启动
   POST /api/player/              → 创建玩家，拿到 player_id
   GET  /api/levels/?player_id=1  → 获取关卡列表和解锁状态

2. 进入关卡 (chapter_01)
   前端加载 .yarn 文件，本地推进对话
   遇到选择节点 → POST /api/levels/choice?player_id=1
                  body: {"level_id":"chapter_01","node_id":"choice_1","choice_id":"A"}
                  ← 返回好感度变化，前端可展示
   ...继续对话...
   到达结局节点 → POST /api/levels/complete?player_id=1
                  body: {"level_id":"chapter_01"}
                  ← 返回下一关信息

3. 关卡间闲聊
   WS /ws/chat/1
   发送: {"type":"message","content":"刚才的事情好有趣"}
   接收: {"type":"chunk","content":"是"} ...
   接收: {"type":"end"}
   断开连接 → 后端自动评估好感度

4. 查看状态
   GET /api/levels/progress?player_id=1
   GET /api/affinity/1
```
