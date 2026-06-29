/**
 * FlyPig Chat Server — 原生 OpenAI SDK 驱动的 LLM 对话服务
 *
 * 职责：仅处理 POST /api/chat，使用 OpenAI SDK stream=true 逐 token 输出
 * 其他功能（配置/文件/终端）仍由 Python/Quart 处理
 *
 * 启动：node server.js（dev.py 自动管理）
 * 端口：8321（环境变量 CHAT_PORT）
 */
import express from 'express';
import OpenAI from 'openai';
import fs from 'fs';
import { load as yamlLoad } from 'js-yaml';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.CHAT_PORT || '8321';
const CONFIG_PATH = process.env.FLYPIG_CONFIG || path.resolve(__dirname, '..', '..', 'config.yaml');
const PYTHON_API = process.env.PYTHON_API_URL || 'http://127.0.0.1:8320';

const app = express();
app.use((req, res, next) => {
  if (req.method !== 'POST' && req.method !== 'PUT') return next();
  const chunks = [];
  req.on('data', c => chunks.push(c));
  req.on('end', () => {
    try { req.body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf-8')) : {}; }
    catch { req.body = {}; }
    next();
  });
});

// ── 模型注册表：从 Python 拉取 ──
let REGISTRY = {};
async function reloadRegistry() {
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 2000);
    const res = await fetch(`${PYTHON_API}/api/config`, { signal: ctrl.signal });
    const data = await res.json();
    for (const m of (data?.models || [])) {
      REGISTRY[m.name] = { provider: m.provider, baseURL: m.base_url, model: m.api_model, local: m.local || false };
    }
    console.log(`[chat-server] Registry: ${Object.keys(REGISTRY).length} models`);
  } catch (e) {
    console.error('[chat-server] Registry load failed:', e.message);
  }
}

// ── API Key ──
let cachedApiKeys = {};
function reloadKeys() {
  try { const d = yamlLoad(fs.readFileSync(CONFIG_PATH, 'utf-8')); cachedApiKeys = d?.api_keys || {}; }
  catch {}
}
reloadKeys();
setInterval(reloadKeys, 30_000);
const getKey = p => cachedApiKeys[p] || '';

// ── 消息格式转换 ──
function extractText(m) {
  if (m.content) return m.content;
  if (m.parts?.length) return m.parts.filter(p => p.type === 'text').map(p => p.text).join('');
  return '';
}

// ── POST /api/chat ──
app.post('/api/chat', async (req, res) => {
  try {
    const { messages, model: modelName } = req.body;
    if (!messages?.length) return res.status(400).json({ error: 'messages 不能为空' });
    if (!modelName) return res.status(400).json({ error: 'model 不能为空' });

    let reg = REGISTRY[modelName];
    if (!reg) { await reloadRegistry(); reg = REGISTRY[modelName]; }
    if (!reg) return res.status(400).json({ error: `未知模型: ${modelName}` });

    const isLocal = reg.local;
    const apiKey = isLocal ? '' : getKey(reg.provider);
    if (!apiKey && !isLocal) return res.status(400).json({ error: `模型 ${modelName} 未配置 API Key` });

    // 原生 OpenAI SDK — 真正的逐 token 流式
    const openai = new OpenAI({ baseURL: reg.baseURL, apiKey: apiKey || 'not-needed' });
    const simpleMessages = messages.map(m => ({ role: m.role || 'user', content: extractText(m) }));

    const stream = await openai.chat.completions.create({
      model: reg.model,
      messages: simpleMessages,
      stream: true,
    });

    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('X-Accel-Buffering', 'no');

    for await (const chunk of stream) {
      const delta = chunk.choices?.[0]?.delta?.content;
      if (delta) res.write(delta);
    }
    res.end();
  } catch (err) {
    console.error('[chat-server] Error:', err.message);
    if (!res.headersSent) res.status(500).json({ error: `服务错误: ${err.message.slice(0, 200)}` });
  }
});

// ── 启动 ──
async function start() {
  await reloadRegistry();
  setInterval(() => reloadRegistry().catch(() => {}), 60_000);
  app.listen(PORT, () => console.log(`[chat-server] AI SDK Chat Server running on :${PORT}`));
}
start();
