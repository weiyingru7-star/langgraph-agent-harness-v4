"""
mock_multimodal_tool.py — Mock 多模态分析工具（Demo Provider）

⚠️ 此文件是 demo/mock 数据提供者，用于 analyze_multimodal 节点。
仍被 demo 链路使用，不可直接删除。
纯图片场景走 image_clarification，不调用此工具。
"""


def analyze_mock_image_with_text(
    user_message: str,
    image_url: str | None = None,
    image_base64: str | None = None,
) -> dict:
    """模拟多模态图文分析。"""
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
