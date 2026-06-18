"""
mock_multimodal_tool.py — Mock 多模态分析工具

职责：模拟多模态模型分析图片的能力。
      第一版不接真实多模态模型，只返回 mock 结果。
      注意：不判断真实图片内容，只用于验证流程完整性。
"""


def analyze_mock_image_with_text(
    user_message: str,
    image_url: str | None = None,
    image_base64: str | None = None,
) -> dict:
    """
    模拟多模态图文分析。

    第一版不判断真实图片内容，只根据 user_message 生成 mock 分析。
    目的是验证流程完整性，而不是做真实图片识别。

    Args:
        user_message: 用户输入的文本
        image_url: 图片 URL（可选）
        image_base64: 图片 base64（可选）

    Returns:
        dict: mock 分析结果，包含 visible_issue、combined_need、confidence
    """
    # 根据文本关键词生成不同 mock 结果，使流程可测试
    text = user_message or ""

    if "退" in text or "破" in text or "质量" in text:
        visible = "mock：疑似商品破损或用户关注图片细节"
        need = "mock：结合文字判断，用户可能在咨询售后/质量/退款问题"
    elif "装" in text or "安装" in text:
        visible = "mock：用户可能展示了安装位置或配件的图片"
        need = "mock：结合文字判断，用户可能咨询商品安装/使用方法"
    else:
        visible = "mock：用户上传了一张图片"
        need = f"mock：结合文字「{text}」进行综合分析"

    return {
        "visible_issue": visible,
        "combined_need": need,
        "confidence": 0.75,
        "is_mock": True,
    }
