"""
mock_multimodal_tool.py — Mock 多模态分析工具

职责: 模拟多模态模型分析图片的能力。
      第一版不接真实多模态模型，返回 mock 结果。
"""


def analyze_image(image_path: str, text_context: str = "") -> dict:
    """
    模拟分析图片内容。

    Args:
        image_path: 图片路径或 URL
        text_context: 相关联的文字上下文

    Returns:
        模拟的分析结果
    """
    # TODO: 后续阶段接入真实多模态模型
    return {
        "image_description": "这是一张示例图片的描述（mock 数据）",
        "has_product": True,
        "product_type": "示例商品类别",
        "message": "图片分析完成（mock 数据）",
    }
