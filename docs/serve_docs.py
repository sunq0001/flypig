"""
文档预览服务器：将 markdown 渲染 + 静态文件（pdoc/JSDoc）一锅端

用法:
  python serve_docs.py              # 端口 8765，无热重载
  python serve_docs.py --port 9999  # 自定义端口
  python serve_docs.py --watch      # 热重载模式（改 markdown 自动刷新）
"""
import argparse
import mimetypes
import os
import re
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

DOCS_DIR = Path(__file__).parent

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} - FlyPig 文档</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;display:flex;min-height:100vh;background:#f5f5f5}}
.sidebar{{width:280px;background:#1e1e2e;color:#cdd6f4;padding:20px;overflow-y:auto;flex-shrink:0}}
.sidebar h2{{font-size:16px;margin-bottom:16px;color:#cba6f7}}
.sidebar a{{display:block;padding:6px 12px;color:#a6adc8;text-decoration:none;font-size:14px;border-radius:4px;margin:2px 0}}
.sidebar a:hover,.sidebar a.active{{background:#313244;color:#cdd6f4}}
.sidebar .group{{margin-bottom:16px}}
.sidebar .group-title{{font-size:12px;text-transform:uppercase;color:#585b70;padding:4px 12px;margin-top:8px}}
.content{{flex:1;padding:40px;max-width:900px;background:#fff;min-height:100vh;line-height:1.7}}
.content h1{{font-size:28px;margin-bottom:16px;color:#1e1e2e;border-bottom:2px solid #cba6f7;padding-bottom:8px}}
.content h2{{font-size:22px;margin:24px 0 12px;color:#1e1e2e}}
.content h3{{font-size:18px;margin:20px 0 10px;color:#1e1e2e}}
.content p{{margin:8px 0;color:#333}}
.content code{{background:#f0f0f0;padding:2px 6px;border-radius:3px;font-size:13px}}
.content pre{{background:#1e1e2e;color:#cdd6f4;padding:16px;border-radius:8px;overflow-x:auto;margin:12px 0;font-size:13px}}
.content pre code{{background:none;padding:0;color:inherit}}
.content table{{border-collapse:collapse;width:100%;margin:12px 0}}
.content th,.content td{{border:1px solid #ddd;padding:8px 12px;text-align:left}}
.content th{{background:#f0f0f0}}
.content ul,.content ol{{padding-left:24px;margin:8px 0}}
.content li{{margin:4px 0}}
.content blockquote{{border-left:4px solid #cba6f7;padding:8px 16px;background:#f8f8ff;margin:12px 0;color:#555}}
.content hr{{border:none;border-top:1px solid #eee;margin:24px 0}}
</style></head><body>
<div class="sidebar"><h2>FlyPig 文档</h2>{sidebar}</div>
<div class="content">{content}</div>
</body></html>'''

SIDEBAR_ITEMS = [
    ("总览", [
        ("架构指南", "architecture-guide"),
        ("架构图", "architecture-diagram"),
        ("文件夹树", "folder-tree"),
    ]),
    ("设计文档", [
        ("前端架构", "frontend-arch"),
        ("后端模块", "backend-modules"),
        ("LangGraph 图", "langgraph-graph"),
        ("权限矩阵", "mode-matrix"),
        ("对抗体系", "adversarial-system"),
        ("数据流", "data-flow"),
        ("子进程", "subprocess"),
        ("MCP 能力", "mcp"),
        ("记忆与存储", "mem_convStore"),
        ("短期记忆", "short-term-memory"),
        ("技术栈", "tech-stack"),
    ]),
    ("API", [
        ("API 参考", "api-reference"),
    ]),
    ("演进", [
        ("迁移路线图", "migration-roadmap"),
    ]),
    ("代码生成", [
        ("Vue 组件文档", "api-docs-vue/components.md"),
        ("pdoc (Python 后端)", "/api-docs/"),
    ]),
]

def render_markdown(text):
    """极简 markdown 转 HTML"""
    lines = text.split('\n')
    html = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('```'):
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            html.append(f'<pre><code>{"<br>".join(code_lines)}</code></pre>')
            i += 1
            continue
        if line.startswith('###### '): html.append(f'<h6>{line[7:]}</h6>')
        elif line.startswith('##### '): html.append(f'<h5>{line[6:]}</h5>')
        elif line.startswith('#### '): html.append(f'<h4>{line[5:]}</h4>')
        elif line.startswith('### '): html.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('## '): html.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('# '): html.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('---'): html.append('<hr>')
        elif line.startswith('> '): html.append(f'<blockquote>{line[2:]}</blockquote>')
        elif line.strip() == '': html.append('<br>')
        else:
            content = re.sub(r'`([^`]+)`', r'<code>\1</code>', line)
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            html.append(f'<p>{content}</p>')
        i += 1
    return '\n'.join(html)

def make_sidebar(current=None):
    items = []
    for group, links in SIDEBAR_ITEMS:
        items.append(f'<div class="group-title">{group}</div>')
        for title, key in links:
            is_ext = key.startswith('/')
            href = key if is_ext else f'/{key}'
            active = ' active' if (not is_ext and key == current) else ''
            items.append(f'<a href="{href}" class="{active}">{title}</a>')
    return '\n'.join(items)

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class DocHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.strip('/').split('?')[0]
        # 静态文件：api-docs/
        if path == 'api-docs':
            file_path = DOCS_DIR / path / 'index.html'
            if file_path.exists():
                self._serve_file(file_path)
                return
        elif path.startswith('api-docs/') and not path.startswith('api-docs-vue/'):
            file_path = DOCS_DIR / path
            if file_path.exists() and file_path.is_file():
                self._serve_file(file_path)
                return
        # Markdown 文档渲染（docs_refactor/ 和 api-docs-vue/）
        if not path:
            path = 'architecture-guide'
        # 先试 docs_refactor/
        md_file = DOCS_DIR / 'docs_refactor' / f'{path}.md'
        if md_file.exists():
            text = md_file.read_text(encoding='utf-8')
            title_match = re.search(r'^#\s+(.+)', text)
            title = title_match.group(1) if title_match else path
            content = render_markdown(text)
            html = HTML_TEMPLATE.format(
                title=title, content=content,
                sidebar=make_sidebar(path)
            )
            self._send_html(html)
            return
        # 再试 api-docs-vue（Vue 组件文档）
        if path.startswith('api-docs-vue/'):
            vue_md = DOCS_DIR / path
            if vue_md.exists() and vue_md.is_file() and vue_md.suffix == '.md':
                text = vue_md.read_text(encoding='utf-8')
                title_match = re.search(r'^#\s+(.+)', text)
                title = title_match.group(1) if title_match else path
                content = render_markdown(text)
                html = HTML_TEMPLATE.format(
                    title=title, content=content,
                    sidebar=make_sidebar('api-docs-vue/components')
                )
                self._send_html(html)
                return
        self._send_404()

    def _serve_file(self, file_path):
        mime, _ = mimetypes.guess_type(str(file_path))
        self.send_response(200)
        self.send_header('Content-Type', mime or 'application/octet-stream')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def _send_html(self, html):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _send_404(self):
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(b'Not Found')

    def log_message(self, format, *args):
        print(f"[docs] {self.client_address[0]} - {args[0]} {args[1]}")

def run(port=8765):
    server = ThreadingHTTPServer(('0.0.0.0', port), DocHandler)
    print(f'FlyPig 文档服务: http://localhost:{port}/')
    print(f'按 Ctrl+C 停止服务')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止')
        server.server_close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FlyPig 文档预览服务')
    parser.add_argument('--port', type=int, default=8765, help='端口（默认 8765）')
    parser.add_argument('--watch', action='store_true', help='热重载模式（改 markdown 自动刷新）')
    args = parser.parse_args()

    if args.watch:
        from watchfiles import run_process
        watch_dirs = [str(DOCS_DIR / 'docs_refactor'), str(DOCS_DIR)]
        print(f'热重载模式: 监听 {watch_dirs}')
        run_process(*watch_dirs, target=run, args=(args.port,))
    else:
        run(args.port)
