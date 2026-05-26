/* === 主数据AI助手 — 前端聊天逻辑 === */

const API_BASE = '';
let sessionId = '';
let isLoading = false;

// === DOM Refs ===
const messagesContainer = document.getElementById('messagesContainer');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const exampleList = document.getElementById('exampleList');
const llmModeEl = document.getElementById('llmMode');
const welcomeMessage = messagesContainer.querySelector('.welcome-message');

// === Init ===
async function init() {
  await loadHealth();
  await loadExamples();
  bindEvents();
}

async function loadHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    llmModeEl.textContent = data.llm_mode === 'deepseek' ? 'DeepSeek API' : '模拟模式';
  } catch {
    llmModeEl.textContent = '离线';
  }
}

async function loadExamples() {
  try {
    const res = await fetch('/api/examples');
    const data = await res.json();
    renderExamples(data.examples);
  } catch (e) {
    renderExamples(defaultExamples);
  }
}

const defaultExamples = [
  { label: '字段枚举查询（意图A）', text: '物料申请里"来源类型"字段有哪些枚举值？' },
  { label: '命名规范修改（意图A）', text: '申请被退回，原因是命名规范不符，我应该怎么改？' },
  { label: '实体状态查询（意图B）', text: '物料编码 PART-2024-001 现在的状态是什么？' },
  { label: '双库联动查询（意图C）', text: '物料 PART-2024-003 是冻结状态，还能发起采购申请吗？' },
  { label: '澄清反问（意图D）', text: '物料状态怎么查？' },
  { label: '实体不存在（边界测试）', text: '物料编码 FAKE-9999-XX 现在什么状态？' },
];

function renderExamples(examples) {
  exampleList.innerHTML = examples.map((ex, i) => {
    const tagClass = ['intent-a', 'intent-b', 'intent-c', 'intent-d'][i % 4];
    return `<div class="example-item" data-text="${escapeHtml(ex.text)}">
      <span class="tag tag-${tagClass}">${escapeHtml(ex.label)}</span>
      <div>${escapeHtml(ex.text)}</div>
    </div>`;
  }).join('');

  // Click event delegation
  exampleList.querySelectorAll('.example-item').forEach(item => {
    item.addEventListener('click', () => {
      const text = item.getAttribute('data-text');
      userInput.value = text;
      sendMessage();
    });
  });
}

function bindEvents() {
  sendBtn.addEventListener('click', sendMessage);
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  // Auto-resize textarea
  userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
  });
}

// === Send Message ===
async function sendMessage() {
  if (isLoading) return;
  const message = userInput.value.trim();
  if (!message) return;

  isLoading = true;
  sendBtn.disabled = true;

  // Remove welcome message
  if (welcomeMessage) {
    welcomeMessage.remove();
  }

  // Add user message
  addMessage('user', message, null);
  userInput.value = '';
  userInput.style.height = 'auto';

  // Add loading message
  const loadingMsg = addLoadingMessage();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    const data = await res.json();

    // Update session ID
    if (data.session_id) {
      sessionId = data.session_id;
    }

    // Remove loading, add AI response
    loadingMsg.remove();
    addMessage('assistant', data.message, data);
  } catch (err) {
    loadingMsg.remove();
    addMessage('assistant', '抱歉，服务暂时不可用，请稍后重试。', null);
  } finally {
    isLoading = false;
    sendBtn.disabled = false;
    userInput.focus();
  }
}

// === Render Messages ===
function addMessage(role, content, data) {
  const div = document.createElement('div');
  div.className = `message ${role}`;

  if (role === 'assistant') {
    // Intent badge
    if (data && data.intent) {
      const badge = document.createElement('span');
      badge.className = 'intent-badge';
      badge.className += getIntentClass(data.intent);
      badge.textContent = getIntentLabel(data.intent);
      div.appendChild(badge);
    }

    // Bad case indicator
    if (data && data.is_bad_case) {
      const bc = document.createElement('span');
      bc.className = 'intent-badge intent-d';
      bc.textContent = 'Bad Case';
      div.appendChild(bc);
    }
  }

  // Message content
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  contentDiv.innerHTML = formatMessageContent(content);
  div.appendChild(contentDiv);

  // Source cards
  if (data && data.sources && data.sources.length > 0) {
    const sourcesDiv = document.createElement('div');
    sourcesDiv.className = 'sources';
    data.sources.forEach(src => {
      const card = document.createElement('span');
      card.className = `source-card ${src.type}`;
      card.innerHTML = `<span class="source-icon">${src.type === 'knowledge' ? '📄' : '🗄️'}</span>`;
      if (src.type === 'knowledge') {
        card.innerHTML += `${src.doc} · ${src.section}`;
      } else {
        card.innerHTML += `MDM · ${src.entity_id} · ${src.query_time}`;
      }
      sourcesDiv.appendChild(card);
    });
    div.appendChild(sourcesDiv);
  }

  messagesContainer.appendChild(div);
  scrollToBottom();
  return div;
}

function addLoadingMessage() {
  const div = document.createElement('div');
  div.className = 'message assistant';
  const content = document.createElement('div');
  content.className = 'message-content';
  content.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';
  div.appendChild(content);
  messagesContainer.appendChild(div);
  scrollToBottom();
  return div;
}

// === Formatting ===
function formatMessageContent(text) {
  if (!text) return '';
  let html = marked.parse(text);
  html = html.replace(/【知识库】/g, '<span class="kb-highlight">【知识库】</span>');
  html = html.replace(/【MDM】/g, '<span class="mdm-highlight">【MDM】</span>');
  return html;
}

// === Intent Helpers ===
function getIntentClass(intent) {
  const map = {
    'Intent_Rule': 'intent-a',
    'Intent_Data': 'intent-b',
    'Intent_Dual': 'intent-c',
    'Intent_Clarify': 'intent-d',
  };
  return map[intent] || '';
}

function getIntentLabel(intent) {
  const map = {
    'Intent_Rule': '意图A：规则咨询',
    'Intent_Data': '意图B：数据查询',
    'Intent_Dual': '意图C：双库联动',
    'Intent_Clarify': '意图D：澄清',
  };
  return map[intent] || intent;
}

// === Utils ===
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function scrollToBottom() {
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// === Start ===
init();
