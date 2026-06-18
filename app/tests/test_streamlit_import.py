"""Streamlit 页面导入测试（Phase 10.4）。"""


def test_streamlit_import():
    """验证 Streamlit 页面模块可以正常导入。"""
    from app.web import streamlit_app
    assert streamlit_app is not None
