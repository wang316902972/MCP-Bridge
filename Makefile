.PHONY: help test test-all test-unit test-integration test-ddg test-fast test-coverage test-verbose lint format clean install-dev run-docker stop-docker

# 默认目标
help:
	@echo "MCP-Bridge 测试命令:"
	@echo ""
	@echo "测试命令:"
	@echo "  make test           - 运行所有测试"
	@echo "  make test-all       - 运行所有测试 (包括外部服务)"
	@echo "  make test-unit      - 只运行单元测试"
	@echo "  make test-integration - 只运行集成测试"
	@echo "  make test-ddg       - 只运行 DuckDuckGo 测试"
	@echo "  make test-fast      - 快速测试 (跳过外部服务)"
	@echo "  make test-coverage  - 生成覆盖率报告"
	@echo "  make test-verbose   - 详细输出测试"
	@echo ""
	@echo "开发命令:"
	@echo "  make lint          - 代码检查"
	@echo "  make format        - 代码格式化"
	@echo "  make clean         - 清理临时文件"
	@echo "  make install-dev   - 安装开发依赖"
	@echo ""
	@echo "Docker 命令:"
	@echo "  make run-docker    - 启动 Docker 服务"
	@echo "  make stop-docker   - 停止 Docker 服务"
	@echo ""

# 安装测试依赖
install-dev:
	@echo "安装测试依赖..."
	pip install -r tests/requirements.txt
	@echo "✅ 依赖安装完成"

# 运行所有测试
test:
	@echo "运行所有测试..."
	python tests/run_tests.py

# 运行所有测试 (包括外部服务)
test-all:
	@echo "运行所有测试 (包括外部服务)..."
	python tests/run_tests.py --integration

# 只运行单元测试
test-unit:
	@echo "运行单元测试..."
	python tests/run_tests.py --unit

# 只运行集成测试
test-integration:
	@echo "运行集成测试..."
	python tests/run_tests.py --integration

# 只运行 DuckDuckGo 测试
test-ddg:
	@echo "运行 DuckDuckGo 测试..."
	python tests/run_tests.py --duckduckgo

# 快速测试 (跳过外部服务)
test-fast:
	@echo "运行快速测试..."
	python tests/run_tests.py --fast

# 生成覆盖率报告
test-coverage:
	@echo "生成覆盖率报告..."
	python tests/run_tests.py --coverage
	@echo "✅ 覆盖率报告已生成: htmlcov/index.html"

# 详细输出测试
test-verbose:
	@echo "运行测试 (详细输出)..."
	python tests/run_tests.py --verbose

# 代码检查
lint:
	@echo "运行代码检查..."
	ruff check mcp_bridge/
	ruff check tests/
	@echo "✅ 代码检查完成"

# 代码格式化
format:
	@echo "格式化代码..."
	ruff format mcp_bridge/
	ruff format tests/
	@echo "✅ 代码格式化完成"

# 清理临时文件
clean:
	@echo "清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "✅ 清理完成"

# 启动 Docker 服务
run-docker:
	@echo "启动 Docker 服务..."
	docker compose -f docker-compose.duckduckgo.yml up -d --build
	@echo "✅ Docker 服务已启动"
	@echo "等待服务启动..."
	sleep 5
	@echo "✅ 服务就绪"

# 停止 Docker 服务
stop-docker:
	@echo "停止 Docker 服务..."
	docker compose -f docker-compose.duckduckgo.yml down
	@echo "✅ Docker 服务已停止"
