#!/usr/bin/env python3
"""
scripts/run_eval.py — Agent Eval Runner

读取 evals/test_cases.jsonl，调用本地 Agent 图流程，
逐条验证关键字段，输出 Eval 报告。

用法：
    .venv/bin/python scripts/run_eval.py
    .venv/bin/python scripts/run_eval.py --verbose
    .venv/bin/python scripts/run_eval.py --output eval_report.json

环境变量：
    LLM_PROVIDER=mock|deepseek    默认 mock，不调用真实 API
    RAG_PROVIDER=tfidf|chroma     默认 tfidf
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# 将项目根目录加入 sys.path，确保可以 import app 模块
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from app.graph import run_graph
from app.state.customer_state import create_initial_state


def load_test_cases(path: str) -> list[dict]:
    """加载 JSONL 测试用例文件。"""
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def check_case(case: dict, state: dict) -> dict:
    """
    逐条验证 test case 的关键字段。

    检查项由 test_cases.jsonl 中声明的字段控制，每个 case 可独立配置：
    - expected_intent / expected_skill / expected_query_type
    - expected_product / expected_source_file / expected_modality
    - policy_decision / need_human
    - must_contain / must_not_contain（对 reply 做关键词检查）

    未在 case 中声明的字段不检查，保证每个 case 只验证自身关心的维度。
    """
    checks = []
    all_pass = True

    def _check(name: str, passed: bool, detail: str = ""):
        nonlocal all_pass
        if not passed:
            all_pass = False
        checks.append({"name": name, "pass": passed, "detail": detail})

    reply = state.get("reply") or ""

    # 1. 模态（仅 image_only case）
    expected_modality = case.get("expected_modality")
    if expected_modality is not None:
        actual = state.get("modality")
        _check("modality", actual == expected_modality,
               f"expected={expected_modality}, got={actual}")

    # 2. 意图
    expected_intent = case.get("expected_intent")
    if expected_intent is not None:
        actual = state.get("intent")
        _check("intent", actual == expected_intent,
               f"expected={expected_intent}, got={actual}")

    # 3. Skill
    expected_skill = case.get("expected_skill")
    if expected_skill is not None:
        actual = state.get("selected_skill")
        _check("skill", actual == expected_skill,
               f"expected={expected_skill}, got={actual}")

    # 4. Query Type（来自 skill_result）
    expected_qtype = case.get("expected_query_type")
    if expected_qtype is not None:
        skill_result = state.get("skill_result") or {}
        actual = skill_result.get("query_type")
        _check("query_type", actual == expected_qtype,
               f"expected={expected_qtype}, got={actual}")

    # 5. 商品名（来自 skill_result.matched_product.name）
    expected_product = case.get("expected_product")
    if expected_product is not None:
        skill_result = state.get("skill_result") or {}
        matched = skill_result.get("matched_product") or {}
        actual = matched.get("name")
        _check("product", actual == expected_product,
               f"expected={expected_product}, got={actual}")

    # 6. RAG 来源文件（来自 skill_result.evidence[].source_file）
    expected_source = case.get("expected_source_file")
    if expected_source is not None:
        skill_result = state.get("skill_result") or {}
        evidence = skill_result.get("evidence", [])
        source_files = [e.get("source_file") for e in evidence]
        matched = expected_source in source_files
        _check("evidence_source", matched,
               f"expected={expected_source}, got={source_files}")

    # 7. Policy Decision
    expected_policy = case.get("policy_decision")
    if expected_policy is not None:
        actual = state.get("policy_decision")
        _check("policy_decision", actual == expected_policy,
               f"expected={expected_policy}, got={actual}")

    # 8. need_human
    if "need_human" in case:
        actual = state.get("need_human")
        _check("need_human", actual == case["need_human"],
               f"expected={case['need_human']}, got={actual}")

    # 9. must_contain（reply 中必须包含的关键词）
    for kw in case.get("must_contain", []):
        passed = kw in reply
        _check(f"must_contain[{kw}]", passed,
               f"keyword='{kw}' not found in reply" if not passed else "")

    # 10. must_not_contain（reply 中禁止出现的关键词）
    for kw in case.get("must_not_contain", []):
        passed = kw not in reply
        _check(f"must_not_contain[{kw}]", passed,
               f"keyword='{kw}' unexpectedly found in reply" if not passed else "")

    return {"pass": all_pass, "checks": checks}


def run_eval(test_cases_path: str, verbose: bool = False) -> dict:
    """运行全部 Eval 测试用例，返回报告。"""
    cases = load_test_cases(test_cases_path)
    print(f"\n加载 {len(cases)} 条测试用例，开始逐条运行...\n")

    results = []
    passed_count = 0
    failed_count = 0

    for i, case in enumerate(cases):
        case_id = case["id"]
        msg = case.get("user_message", "")
        img = case.get("image_url")
        history = case.get("history", [])

        if verbose:
            display = msg or "(图片)"
            print(f"[{i+1}/{len(cases)}] {case_id}: {display}")

        # 构造初始 state
        state = create_initial_state(
            session_id=f"eval-{case_id}",
            user_message=msg,
            image_url=img or None,
        )
        if history:
            state["conversation_history"] = history

        # 运行完整 LangGraph 图流程
        try:
            t0 = time.time()
            final_state = run_graph(state)
            elapsed = time.time() - t0

            check_result = check_case(case, final_state)
            passed = check_result["pass"]

            result = {
                "id": case_id,
                "user_message": msg or "(图片)",
                "pass": passed,
                "checks": check_result["checks"],
                "checks_passed": sum(1 for c in check_result["checks"] if c["pass"]),
                "checks_total": len(check_result["checks"]),
                "elapsed": round(elapsed, 3),
                "actual_intent": final_state.get("intent"),
                "actual_skill": final_state.get("selected_skill"),
                "actual_policy": final_state.get("policy_decision"),
                "actual_need_human": final_state.get("need_human"),
                "reply_preview": (final_state.get("reply") or "")[:120],
            }

            if passed:
                passed_count += 1
                status = "✓ PASS"
            else:
                failed_count += 1
                status = "✗ FAIL"

            print(f"  {status} {case_id} ({elapsed:.2f}s)  "
                  f"checks={result['checks_passed']}/{result['checks_total']}")

            if not passed and verbose:
                for c in check_result["checks"]:
                    if not c["pass"]:
                        print(f"    → {c['name']}: {c['detail']}")

            results.append(result)

        except Exception as e:
            failed_count += 1
            results.append({
                "id": case_id,
                "user_message": msg or "(图片)",
                "pass": False,
                "error": str(e),
                "checks": [],
                "checks_passed": 0,
                "checks_total": 0,
                "elapsed": 0,
            })
            print(f"  ✗ ERROR {case_id}: {e}")

    # 汇总
    total = len(cases)
    rate = (passed_count / total * 100) if total else 0
    print(f"\n{'=' * 50}")
    print(f"[EVAL] 合计: {passed_count}/{total} 通过 ({rate:.1f}%)")
    print(f"{'=' * 50}")

    report = {
        "summary": {
            "total": total,
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate": round(rate, 1),
        },
        "config": {
            "llm_provider": os.getenv("LLM_PROVIDER", "mock"),
            "rag_provider": os.getenv("RAG_PROVIDER", "tfidf"),
        },
        "results": results,
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="LangGraph Agent Eval Runner")
    parser.add_argument(
        "--cases",
        default=str(_root / "evals" / "test_cases.jsonl"),
        help="测试用例 JSONL 文件路径（默认 evals/test_cases.jsonl）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示每条失败检查的详细信息",
    )
    parser.add_argument(
        "--output", "-o",
        default=str(_root / "evals" / "eval_report.json"),
        help="Eval 报告 JSON 输出路径（默认 evals/eval_report.json）",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("LangGraph Agent Eval Runner")
    print("=" * 50)
    print(f"  LLM Provider:  {os.getenv('LLM_PROVIDER', 'mock'):<12}  "
          f"(deepseek 需要 .env 配置)")
    print(f"  RAG Provider:  {os.getenv('RAG_PROVIDER', 'tfidf'):<12}  "
          f"(chroma 需要 data/chroma/)")
    print(f"  Test cases:    {args.cases}")
    print(f"  Report output: {args.output}")
    print()

    report = run_eval(args.cases, verbose=args.verbose)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n详细报告已写入: {args.output}")

    # 退出码：全部通过返回 0，有失败返回 1
    sys.exit(0 if report["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
