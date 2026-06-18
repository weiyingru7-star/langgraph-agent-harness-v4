# 全链路一致性审计报告

> **Phase 10.4.2 · 审计文档**
> 排查目标：定位 Streamlit 前端测试中 Agent 频繁乱答的根因。

---

## 一、问题背景

Phase 10.4 Streamlit 集成测试中，Agent 频繁出现以下乱答现象：

1. 用户问"这个衣服是什么材质" → 回复"经典款运动鞋 / EVA 鞋底 / 39-44 码"
2. 用户问"有什么码数" → 回复"您好，我在的"（smalltalk 兜底）
3. 用户问"30岁适合吗" → 回复泛商品信息，未回答适合人群
4. 纯图片/图文场景曾走错推荐路线

---

## 二、审计方法

通过建立全链路 Trace 表，对 10 个测试场景逐一检查 14 个关键状态字段，定位乱答发生层。

```
审计层：
  前端 payload → State 初始化 → modality → intent → skill → reply
```

---

## 三、全链路 Trace 结论

| 场景 | intent | skill | reply 是否合理 | 问题层 |
|------|--------|-------|---------------|--------|
| A. 商品材质 | ✅ product_question | ✅ product_qa_skill | ✅（防晒衣，非运动鞋） | 已修复 |
| B. 商品尺码 | ⚠️ 原是 smalltalk | ⚠️ 原是 None | ❌ 回闲聊 | **分类层（关键词缺失）** |
| C. 年龄适合 | ✅ product_question | ✅ product_qa_skill | ⚠️ 泛模板无针对性 | **Skill 层（模板固定）** |
| D. 推荐 | ✅ recommendation | ✅ recommendation_skill | ✅ 保守说明 | 已修复 |
| E. 物流 | ✅ logistics_question | ✅ logistics_skill | ✅ | — |
| F. 退款 | ✅ refund_request | ✅ refund_skill | ✅（已触发转人工） | — |
| G. 投诉 | ✅ complaint | ✅ complaint_skill | ✅ | — |
| H. 纯图片 | ✅ image_only | ✅ None → image_clarification | ✅ | — |
| I. 图文售后 | ✅ text_with_image | ✅ refund_skill | ✅ | — |
| J. 闲聊 | ✅ smalltalk | ✅ None | ✅ | — |

---

## 四、前端 payload 检查结论

| 检查项 | 结果 |
|--------|------|
| image_url 默认是否为空字符串 | ✅ 是 |
| 普通按钮是否清空 image_url | ✅ 是（通过 `img_url = st.session_state.get("img_input", "")` 实时读取） |
| user_message 是否被 image_url 覆盖 | ✅ 否 |
| "图文"输入是否显示为"（图片）" | ✅ 否，有文字时显示文字 + 标注 |
| 是否有 last_payload 调试面板 | ✅ 有（"📤 本次请求体" expander） |
| 页面是否读取本次 response | ✅ 是 |
| API 地址是否固定 | ✅ `http://127.0.0.1:8003` |
| return_full_state 是否影响逻辑 | ✅ 否，仅控制 state 返回 |

**结论：** 前端 payload 无系统性污染。之前"你：（图片）"问题是由于 Streamlit `text_input` widget 跨 rerun 保持旧值的特性导致的偶发问题。

---

## 五、后端 state 流转检查结论

| 层 | 场景 | 结论 |
|----|------|------|
| `create_initial_state` | 所有 | ✅ 正确保留 user_message / image_url |
| `decide_modality` | 文本/图片/图文 | ✅ 正确区分 4 种模态 |
| `classify_intent` | "有什么码数" | ⚠️ **缺失关键词**："码数"、"尺码"未在 product_question 列表中 |
| `classify_intent` | "30岁适合吗" | ✅ "适合"命中 product_question |
| `route_to_skill` | image_only → image_clarification | ✅ |
| `generate_reply` | `need_human=True` | ✅ 转人工覆盖是预期行为 |

**已修复：** `classify_intent` 补充了"码数"、"码"、"尺码"、"颜色"、"款式"等关键词。

---

## 六、Skill / Mock 数据检查结论

| 问题 | 出现文件 | 状态 |
|------|---------|------|
| 硬编码"经典款运动鞋 / EVA 鞋底 / 39-44码" | `mock_product_tool.py` | ✅ **已修复** → UPF50+ 轻薄防晒衣 |
| product_qa 不看问题类型 | `product_qa_skill.py` | ✅ **已修复** → 根据关键词匹配不同回复（材质/尺码/适合/泛咨询） |
| recommendation 虚推商品 | `recommendation_skill.py` | ✅ **已修复** → 保守推荐说明 |
| smalltalk 被误用于商品咨询 | `classify_intent.py` | ✅ **已修复** → 通过补关键词解决 |
| "运动鞋"仍在 order mock | `mock_order_tool.py` | ✅ **已修复** |

---

## 七、Memory 污染检查结论

| 检查项 | 结果 |
|--------|------|
| conversation_memory 只保存最近一轮文字 | ✅ |
| 测试中使用 setup_function / setup_method 清理 | ✅ |
| 端到端测试使用独立 session_id | ✅ |
| 前端"新会话"生成新 session_id | ✅ |
| 前端"清空对话"不清后端 memory | ⚠️ 知道但可接受（每个 session 独立处理） |

**结论：** 测试中不存在 memory 污染。前端"清空对话"不清后端 memory 不构成问题，因为后端 memory 按 session_id 隔离。

---

## 八、已修复问题

| # | 问题 | 层 | 修复内容 |
|---|------|----|---------|
| 1 | Mock 商品硬编码"运动鞋" | Tool | `mock_product_tool.py` → 改为"UPF50+ 轻薄防晒衣" |
| 2 | Mock 订单含"运动鞋" | Tool | `mock_order_tool.py` → 同步更新 |
| 3 | product_qa 只返回固定模板 | Skill | `product_qa_skill.py` → 根据关键词分 5 种场景回复 |
| 4 | generate_reply 未使用 skill message | Node | `generate_reply.py` → `_product_qa_reply` 优先用 `message` 字段 |
| 5 | classify_intent 缺失"码数/尺码" | Node | `classify_intent.py` → 补关键词 |
| 6 | recommendation 虚假推荐 | Skill | `recommendation_skill.py` → 保守说明 |

---

## 九、暂未修复但进入后续阶段的问题

| 问题 | 计划 |
|------|------|
| 本地商品知识库 | Phase 10.5：`data/products.json` 替代 `mock_product_tool` |
| FAQ 知识库 | Phase 10.5：`data/faq.json` |
| `generate_reply` 对 `need_human=True` 的回复覆盖 | 当前为预期行为（情绪过激转人工） |
| 前端 `image_url` widget 跨 rerun 保留旧值 | 可通过"新会话"解决 |

---

## 十、新增测试列表

| 文件 | 数量 | 说明 |
|------|------|------|
| `tests/test_end_to_end_behavior.py` | 10 个 | 全链路行为审计测试 |

---

## 十一、pytest 结果

```
79 passed in 0.89s ✅
```

包含：原有 69 个 + 新增 10 个端到端测试。

---

## 十二、后续建议

1. **分类层**：后续接入 LLM 时 `classify_intent` 关键词规则直接替换为 LLM 调用
2. **Skill 层**：`product_qa_skill` 当前按关键词分段，接入本地知识库后直接从 JSON 查询
3. **回复层**：`generate_reply` 优先使用 skill 返回的 `message` 字段，这种做法正确，后续可以保持
4. **测试层**：端到端测试应随功能扩展持续增加
