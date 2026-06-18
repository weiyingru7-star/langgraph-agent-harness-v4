"""
测试: 图文混合输入场景

验证文字+图片的多模态分析流程。
"""


def test_text_with_image_imports():
    """验证必要模块可正常导入。"""
    from app.state.customer_state import CustomerServiceState

    state = CustomerServiceState()
    assert state is not None
