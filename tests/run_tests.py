#!/usr/bin/env python3
"""
MCP-Bridge 测试运行脚本

运行方式:
    python tests/run_tests.py              # 运行所有测试
    python tests/run_tests.py --unit       # 只运行单元测试
    python tests/run_tests.py --integration # 只运行集成测试
    python tests/run_tests.py --duckduckgo # 只运行 DuckDuckGo 测试
    python tests/run_tests.py --fast       # 快速测试跳过外部服务
"""

import argparse
import subprocess
import sys
import os


def run_pytest(args: list[str]) -> int:
    """运行 pytest 命令"""
    cmd = ["python", "-m", "pytest", "-v", "--tb=short"] + args
    print(f"运行: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="MCP-Bridge 测试运行器")
    parser.add_argument("--unit", action="store_true", help="只运行单元测试")
    parser.add_argument("--integration", action="store_true", help="只运行集成测试")
    parser.add_argument("--duckduckgo", action="store_true", help="只运行 DuckDuckGo 测试")
    parser.add_argument("--fast", action="store_true", help="跳过需要外部服务的测试")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 构建 pytest 参数
    pytest_args = []

    # 测试目录
    pytest_args.append("tests/")

    # 标记过滤
    markers = []

    if args.unit:
        markers.append("unit")
    elif args.integration:
        markers.append("integration")
    elif args.duckduckgo:
        markers.append("duckduckgo")
    elif args.fast:
        markers.append("not external")

    if markers:
        pytest_args.append(f"-m {' and '.join(markers)}")

    # 覆盖率
    if args.coverage:
        pytest_args.extend([
            "--cov=mcp_bridge",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])

    # 详细输出
    if args.verbose:
        pytest_args.append("-vv")

    # 运行测试
    returncode = run_pytest(pytest_args)

    # 输出总结
    print("\n" + "="*60)
    if returncode == 0:
        print("✅ 所有测试通过!")
    else:
        print("❌ 测试失败")
        print(f"退出码: {returncode}")
    print("="*60 + "\n")

    return returncode


if __name__ == "__main__":
    sys.exit(main())
