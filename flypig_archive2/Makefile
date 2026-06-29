.PHONY: dev dev-backend dev-frontend stop docs docs-pdoc docs-vue lint test clean

# ── 开发模式 ──────────────────────────────────────────

dev: dev-backend dev-frontend    ## 同时启动后端 + 前端热加载

dev-backend:                    ## 后端热加载（Hypercorn --reload :8321）
	hypercorn backend.server:create_app --reload --bind 127.0.0.1:8321

dev-frontend:                   ## 前端 HMR（Vite :5173）
	cd frontend/static_vite && npm run dev

stop:                           ## 停止后端 + 前端
	@echo "手动关闭对应终端窗口或使用 kill <PID>"

# ── 文档 ──────────────────────────────────────────────

docs: docs-pdoc docs-vue       ## 生成全部 API 文档
	@echo "文档生成完成，运行 'make docs-serve' 预览"

docs-pdoc:                      ## pdoc 生成 Python API 文档
	python -m pdoc --output-dir ../docs/api-docs domain/

docs-vue:                     ## vue-docgen-api 生成 Vue 组件文档
	cd frontend/static_vite && node scripts/generate-vue-docs.cjs

docs-serve:                     ## 启动文档预览（热重载）
	python ../docs/serve_docs.py --port 8765 --watch

# ── 工具 ──────────────────────────────────────────────

lint:                           ## Ruff 代码检查
	ruff check .

lint-fix:                       ## Ruff 自动修复
	ruff check --fix .

test:                           ## 运行测试
	pytest

clean:                          ## 清理 pyc 缓存
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -type f -name "*.pyc" -delete 2>/dev/null; \
	echo "√ 已清理"

# ── 帮助 ──────────────────────────────────────────────

help:                           ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
