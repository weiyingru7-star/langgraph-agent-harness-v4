"""
测试: 纯图片输入场景

验证用户只发图片时的处理逻辑。
"""


def test_image_only_imports():
    """验证必要模块可正常导入。"""
    from app.state.customer_state import CustomerServiceState

    state = CustomerServiceState()
    assert state is not None
