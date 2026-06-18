"""
product_qa_skill.py — 商品问答技能

职责：回答商品材质、尺寸、参数、使用方法等问题。
      根据问题关键词返回不同方向的 mock 信息。
      后续接入本地商品知识库后替换此逻辑。
"""


def run_product_qa_skill(state: dict) -> dict:
    """执行商品问答，根据问题类型返回针对性信息。"""
    text = state.get("user_message", "") or ""
    product = _get_mock_product_info()

    # 根据问题关键词选择侧重点
    if any(w in text for w in ["码数", "尺码", "码", "大小", "尺寸"]):
        reply = (
            f"这款 {product['name']} 的尺码信息如下：\n"
            f"可选尺码：{product['size']}\n"
            f"版型为常规版，建议按平时尺码选购。\n"
            f"如果您不确定选哪个尺码，可以告诉我身高体重，我帮您参考。"
        )
    elif any(w in text for w in ["适合", "能穿", "可以穿", "推荐", "年龄段"]):
        reply = (
            f"这款 {product['name']} 设计为通用版型，不挑年龄，"
            f"适合{product['scene']}穿着。\n"
            f"材质：{product['material']}\n"
            f"特点：{'、'.join(product['features'])}\n"
            f"如果您有具体的场景或需求，可以再问我，我帮您进一步判断。"
        )
    elif any(w in text for w in ["材质", "面料", "什么料", "成分", "质量"]):
        reply = (
            f"这款 {product['name']} 的材质信息如下：\n"
            f"材质成分：{product['material']}\n"
            f"特点：{'、'.join(product['features'])}\n"
            f"此材质透气性良好，适合{product['scene']}穿着。"
        )
    elif any(w in text for w in ["怎么用", "怎么穿", "怎么洗", "保养", "清洗"]):
        reply = (
            f"这款 {product['name']} 的使用与保养建议：\n"
            f"建议手洗或轻柔机洗，避免漂白剂\n"
            f"适合{product['scene']}穿着，日常保养方便。"
        )
    else:
        reply = (
            f"您咨询的商品信息如下：\n"
            f"商品名称：{product['name']}\n"
            f"材质：{product['material']}\n"
            f"尺码：{product['size']}\n"
            f"特点：{'、'.join(product['features'])}\n"
            f"适用场景：{product['scene']}\n"
            f"如果您需要了解更多信息，欢迎继续咨询。"
        )

    return {
        "skill_result": {
            "action": "product_answer",
            "product_info": {
                "product_name": product["name"],
                "material": product["material"],
                "size": product["size"],
                "features": product["features"],
                "suitable_scene": product["scene"],
            },
            "message": reply,
        }
    }


def _get_mock_product_info() -> dict:
    """返回当前 mock 商品基础信息（后续接入 data/products.json）。"""
    return {
        "name": "UPF50+ 轻薄防晒衣",
        "material": "锦纶混纺 + 透气网眼",
        "size": "M/L/XL 可选",
        "features": ["轻薄", "透气", "UPF50+防晒", "防泼水"],
        "scene": "夏季通勤、骑行、户外活动、日常防晒",
    }
