/**
 * FlyPig Chat Server — AI SDK 驱动的 LLM 对话服务
 * 使用 AI SDK v4 的 streamText API，输出标准 SSE 格式
 */
import express from 'express';
import { streamText } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
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

let cachedApiKeys = {};
function reloadKeys() {
  try { const d = yamlLoad(fs.readFileSync(CONFIG_PATH, 'utf-8')); cachedApiKeys = d?.api_keys || {}; }
  catch {}
}
reloadKeys();
setInterval(reloadKeys, 30_000);
const getKey = p => cachedApiKeys[p] || '';

function extractText(m) {
  if (m.content) return m.content;
  if (m.parts?.length) return m.parts.filter(p => p.type === 'text').map(p => p.text).join('');
  return '';
}

app.post('/api/chat', async (req, res) => {
  try {
    const { messages: rawMessages, model: modelName } = req.body;
    if (!rawMessages?.length) return res.status(400).json({ error: 'messages 不能为空' });
    if (!modelName) return res.status(400).json({ error: 'model 不能为空' });

    let reg = REGISTRY[modelName];
    if (!reg) { await reloadRegistry(); reg = REGISTRY[modelName]; }
    if (!reg) return res.status(400).json({ error: `未知模型: ${modelName}` });

    const isLocal = reg.local;
    const apiKey = isLocal ? '' : getKey(reg.provider);
    if (!apiKey && !isLocal) return res.status(400).json({ error: `模型 ${modelName} 未配置 API Key` });

    // 使用 AI SDK 的 streamText
    const openai = createOpenAI({ baseURL: reg.baseURL, apiKey: apiKey || 'not-needed' });
    const messages = rawMessages.map(m => ({ role: m.role || 'user', content: extractText(m) }));

    const result = streamText({
      model: openai(reg.model),
      messages,
      maxTokens: 500,
    });

    // ── 诊断: 拦截每个 SSE 写入块，记录时间戳 ──
    const origWrite = res.write.bind(res);
    let chunkIdx = 0;
    const tsStart = Date.now();
    console.log('[sse] === stream start ===');
    res.write = function (chunk, ...rest) {
      const ms = Date.now() - tsStart;
      const text = Buffer.isBuffer(chunk) ? chunk.toString('utf-8') : String(chunk);
      // 只记 data: 行，忽略空行
      const dataLines = text.split('\n').filter(l => l.startsWith('data:'));
      for (const line of dataLines) {
        const payload = line.replace('data: ', '').slice(0, 100);
        console.log(`[sse] +${ms}ms #${chunkIdx} ${payload}`);
        chunkIdx++;
      }
      return origWrite(chunk, ...rest);
    };

    // AI SDK v7: pipeUIMessageStreamToResponse 取代旧的 pipeDataStreamToResponse
    result.pipeUIMessageStreamToResponse(res, {
      headers: {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
      },
    });
  } catch (err) {
    console.error('[chat-server] Error:', err.message);
    if (!res.headersSent) res.status(500).json({ error: `服务错误: ${err.message.slice(0, 200)}` });
  }
});

async function start() {
  await reloadRegistry();
  setInterval(() => reloadRegistry().catch(() => {}), 60_000);
  app.listen(PORT, () => console.log(`[chat-server] AI SDK Chat Server running on :${PORT}`));
}
start();
