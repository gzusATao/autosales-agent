/**
 * Chat page controller.
 * Uses WebSocket streaming first, with the original HTTP endpoint as fallback.
 */

let sessionId = localStorage.getItem('chat_session_id') || '';
let customerId = localStorage.getItem('chat_customer_id') || '';
let isSending = false;
let thinkingTimer = null;

const INTENT_TITLES = {
  car_recommendation: '车型推荐结果',
  car_compare: '配置对比分析',
  loan_calculation: '分期试算方案',
  inventory_query: '库存查询结果',
  test_drive: '试驾预约确认',
  general_question: '需求确认',
  lead_save: '线索沉淀',
};

const INTENT_LABELS = {
  car_recommendation: '车型推荐',
  car_compare: '配置对比',
  loan_calculation: '分期试算',
  inventory_query: '库存查询',
  test_drive: '试驾预约',
  general_question: '需求确认',
  lead_save: '线索保存',
};

const THINKING_STEPS = [
  '识别购车意图',
  '读取客户记忆',
  '补全需求字段',
  '判断下一步动作',
  '调用业务工具',
  '组织销售回复',
  '更新客户画像',
];

const QUICK_MSGS = {
  'btn-recommend': '推荐几款20万以内的SUV',
  'btn-compare': '对比宋PLUS和锋兰达',
  'btn-loan': '月供多少？',
  'btn-inventory': '广州有现车吗？',
  'btn-drive': '预约试驾',
};

let messagesEl;
let inputEl;
let sendBtn;
let thinkingEl;
let thinkingText;

function initPage() {
  const sidebarHtml = renderSidebar('chat');
  const topbarHtml = renderTopbar('AI 销售对话');
  document.getElementById('app-root').insertAdjacentHTML('afterbegin', sidebarHtml);
  document.getElementById('topbar-placeholder').outerHTML = topbarHtml;

  messagesEl = document.getElementById('chat-messages');
  inputEl = document.getElementById('chat-input');
  sendBtn = document.getElementById('chat-send');
  thinkingEl = document.getElementById('agent-thinking');
  thinkingText = document.getElementById('thinking-text');

  hideGlobalThinking();

  sendBtn?.addEventListener('click', sendMessage);
  inputEl?.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  Object.entries(QUICK_MSGS).forEach(([id, message]) => {
    document.getElementById(id)?.addEventListener('click', () => {
      inputEl.value = message;
      sendMessage();
    });
  });
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || isSending) return;

  inputEl.value = '';
  setSending(true);
  addUserMessage(text);
  startGraphThinking();

  const streamMessage = createStreamingAgentMessage();

  try {
    const response = await streamChatMessage(text, streamMessage);
    finishStreamingAgentMessage(streamMessage, response);
    updateAgentPanel(response);
  } catch (error) {
    console.warn('WebSocket streaming failed, falling back to HTTP', error);
    try {
      const response = await api.chat(text, sessionId, customerId);
      syncSession(response);
      finishStreamingAgentMessage(streamMessage, response);
      updateAgentPanel(response);
    } catch (fallbackError) {
      console.error(fallbackError);
      finishStreamingAgentMessage(streamMessage, {
        reply: '这边暂时没有生成成功，您可以稍后再试一次。',
        current_intent: 'general_question',
        purchase_intent: {},
        tool_trace: [],
        missing_slots: [],
      });
      markGraphFailed();
    }
  } finally {
    stopGraphThinking();
    setSending(false);
    inputEl.focus();
  }
}

function streamChatMessage(text, streamMessage) {
  return new Promise((resolve, reject) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);
    let finished = false;

    const timeout = window.setTimeout(() => {
      if (!finished) {
        socket.close();
        reject(new Error('WebSocket timeout'));
      }
    }, 45000);

    socket.addEventListener('open', () => {
      socket.send(JSON.stringify({
        session_id: sessionId,
        customer_id: customerId,
        message: text,
      }));
    });

    socket.addEventListener('message', event => {
      const payload = JSON.parse(event.data);
      if (payload.type === 'start') {
        return;
      }
      if (payload.type === 'delta') {
        appendStreamingDelta(streamMessage, payload.content || '');
        return;
      }
      if (payload.type === 'done') {
        finished = true;
        window.clearTimeout(timeout);
        socket.close();
        syncSession(payload.data || {});
        resolve(payload.data || {});
        return;
      }
      if (payload.type === 'error') {
        finished = true;
        window.clearTimeout(timeout);
        socket.close();
        reject(new Error(payload.message || 'WebSocket error'));
      }
    });

    socket.addEventListener('error', () => {
      if (!finished) {
        finished = true;
        window.clearTimeout(timeout);
        reject(new Error('WebSocket connection error'));
      }
    });

    socket.addEventListener('close', () => {
      window.clearTimeout(timeout);
    });
  });
}

function syncSession(response) {
  if (response.session_id) {
    sessionId = response.session_id;
    localStorage.setItem('chat_session_id', sessionId);
  }
  if (response.customer_id) {
    customerId = response.customer_id;
    localStorage.setItem('chat_customer_id', customerId);
  }
}

function setSending(sending) {
  isSending = sending;
  sendBtn.disabled = sending;
  sendBtn.textContent = sending ? '生成中' : '发送';
}

function startGraphThinking() {
  let step = 0;
  resetGraphNodes();
  updateGraphNode(0, 'active');
  thinkingTimer = window.setInterval(() => {
    step = Math.min(step + 1, THINKING_STEPS.length - 1);
    updateGraphNode(step - 1, 'done');
    updateGraphNode(step, 'active');
  }, 650);
}

function stopGraphThinking() {
  if (thinkingTimer) {
    window.clearInterval(thinkingTimer);
    thinkingTimer = null;
  }
  document.querySelectorAll('.graph-node').forEach(node => {
    if (!node.classList.contains('failed')) node.className = 'graph-node done';
  });
  hideGlobalThinking();
}

function markGraphFailed() {
  document.querySelectorAll('.graph-node').forEach(node => {
    node.className = 'graph-node failed';
  });
}

function resetGraphNodes() {
  document.querySelectorAll('.graph-node').forEach(node => {
    node.className = 'graph-node pending';
  });
}

function updateGraphNode(index, status) {
  const nodes = document.querySelectorAll('.graph-node');
  if (nodes[index]) nodes[index].className = `graph-node ${status}`;
}

function hideGlobalThinking() {
  if (thinkingEl) thinkingEl.style.display = 'none';
  if (thinkingText) thinkingText.textContent = 'Agent 正在分析需求...';
}

function addUserMessage(text) {
  const div = document.createElement('div');
  div.className = 'message user';
  div.innerHTML = `
    <div class="message-avatar">U</div>
    <div class="message-content"><p>${escapeHtml(text)}</p></div>
  `;
  messagesEl.appendChild(div);
  scrollToBottom();
}

function createStreamingAgentMessage() {
  const div = document.createElement('div');
  div.className = 'message assistant is-streaming';
  div.innerHTML = `
    <div class="message-avatar assistant-avatar" aria-label="AI 智能销售"></div>
    <div class="message-content">
      <div class="msg-subtitle">正在思考</div>
      <div class="msg-body stream-body">
        <div class="stream-thinking" aria-live="polite">
          <span class="thinking-dot"></span>
          <span class="thinking-dot"></span>
          <span class="thinking-dot"></span>
          <span class="thinking-label">正在结合车型库和客户需求生成回复</span>
        </div>
      </div>
    </div>
  `;
  messagesEl.appendChild(div);
  scrollToBottom();

  return {
    root: div,
    subtitle: div.querySelector('.msg-subtitle'),
    body: div.querySelector('.stream-body'),
    text: '',
    hasFirstChunk: false,
  };
}

function appendStreamingDelta(streamMessage, delta) {
  if (!delta) return;
  if (!streamMessage.hasFirstChunk) {
    streamMessage.hasFirstChunk = true;
    streamMessage.subtitle.textContent = 'AI 回复生成中';
    streamMessage.body.innerHTML = '<p></p>';
  }
  streamMessage.text += delta;
  streamMessage.body.innerHTML = formatMessage(streamMessage.text);
  scrollToBottom();
}

function finishStreamingAgentMessage(streamMessage, response) {
  const reply = response.reply || streamMessage.text || '已收到，我再帮您继续分析。';
  streamMessage.root.classList.remove('is-streaming');
  streamMessage.subtitle.textContent = INTENT_TITLES[response.current_intent] || '销售顾问回复';
  streamMessage.body.innerHTML = formatMessage(reply);

  const summaryItems = buildSummaryItems(response);
  const oldSummary = streamMessage.root.querySelector('.msg-summary');
  if (oldSummary) oldSummary.remove();
  if (summaryItems.length) {
    streamMessage.body.insertAdjacentHTML('afterend', `
      <div class="msg-summary">
        <div class="msg-summary-title">本轮动作摘要</div>
        ${summaryItems.map(item => `<div class="msg-summary-item">${escapeHtml(item)}</div>`).join('')}
      </div>
    `);
  }
  scrollToBottom();
}

function buildSummaryItems(response) {
  const items = [];
  const title = INTENT_TITLES[response.current_intent] || response.current_intent;
  const intent = response.purchase_intent || {};
  const tools = response.tool_trace || [];
  const missing = response.missing_slots || [];

  if (title) items.push(`当前意图：${title}`);
  if (intent.budget) items.push(`预算：${intent.budget}`);
  if (intent.car_type) items.push(`车型：${intent.car_type}`);
  if (intent.energy_type) items.push(`能源：${intent.energy_type}`);
  if (tools.length) items.push(`调用工具：${tools.map(tool => tool.tool_name).join('、')}`);
  if (missing.length) items.push(`待补充：${missing.join('、')}`);
  return items;
}

function updateAgentPanel(response) {
  document.getElementById('panel-intent').innerHTML = response.current_intent
    ? `<span class="tag tag-blue">${INTENT_LABELS[response.current_intent] || response.current_intent}</span>`
    : '<span class="text-muted">等待识别...</span>';

  const stage = getStage(response.current_intent);
  document.getElementById('panel-stage').innerHTML = `<span class="tag ${stage.className}">${stage.label}</span>`;

  const purchaseIntent = response.purchase_intent || {};
  const slotLabels = {
    budget: '预算',
    car_type: '车型',
    energy_type: '能源',
    usage: '用途',
    purchase_time: '购车周期',
  };

  document.getElementById('panel-slots').innerHTML = Object.entries(slotLabels)
    .map(([key, label]) => `
      <div class="agent-field">
        <span class="label">${label}</span>
        <span class="value">${purchaseIntent[key] || '<span class="text-muted">待采集</span>'}</span>
      </div>
    `)
    .join('');

  const missing = response.missing_slots || [];
  document.getElementById('panel-missing').innerHTML = missing.length
    ? missing.map(slot => `<span class="tag tag-warm" style="margin:2px;">${slotLabels[slot] || slot}</span>`).join('')
    : '<span class="tag tag-success">已齐全</span>';

  const tools = response.tool_trace || [];
  document.getElementById('panel-tools').innerHTML = tools.length
    ? tools.map(tool => {
      const failed = Boolean(tool.output && tool.output.error);
      const statusText = failed ? '兜底' : '成功';
      const statusClass = failed ? 'tool-status failed' : 'tool-status';
      return `
      <div class="tool-timeline-item">
        <div class="tool-name">${escapeHtml(tool.tool_name)}<span class="${statusClass}">${statusText}</span></div>
        <div class="tool-io">参数: ${escapeHtml(Object.keys(tool.input || {}).slice(0, 3).join(', ') || '-')}</div>
        <div class="tool-io">结果: ${escapeHtml(JSON.stringify(tool.output || {}).slice(0, 90))}</div>
      </div>
    `;
    }).join('')
    : '<div class="text-muted" style="font-size:13px;">本轮未调用工具</div>';

  const profile = response.customer_profile || {};
  document.getElementById('panel-profile').innerHTML = Object.keys(profile).length
    ? `
      <div class="agent-field"><span class="label">预算</span><span class="value">${profile.budget || '-'}</span></div>
      <div class="agent-field"><span class="label">车型</span><span class="value">${profile.car_type || '-'}</span></div>
      <div class="agent-field"><span class="label">能源</span><span class="value">${profile.energy_type || '-'}</span></div>
      <div class="agent-field"><span class="label">关注点</span><span class="value">${(profile.concerns || []).join('、') || '-'}</span></div>
      <div class="agent-field"><span class="label">意向等级</span><span class="value">${profile.lead_level || '-'}</span></div>
    `
    : '<div class="text-muted" style="font-size:13px;">等待对话...</div>';
}

function getStage(intent) {
  const map = {
    car_recommendation: { label: '推荐车型', className: 'tag-warm' },
    car_compare: { label: '配置对比', className: 'tag-warm' },
    loan_calculation: { label: '分期方案', className: 'tag-warm' },
    inventory_query: { label: '库存查询', className: 'tag-warm' },
    test_drive: { label: '预约试驾', className: 'tag-hot' },
    lead_save: { label: '线索沉淀', className: 'tag-hot' },
    general_question: { label: '需求采集', className: 'tag-cold' },
  };
  return map[intent] || { label: '新对话', className: 'tag-cold' };
}

function escapeHtml(text = '') {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatMessage(text = '') {
  return '<p>' + escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>') + '</p>';
}

function scrollToBottom() {
  if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
}

document.addEventListener('DOMContentLoaded', initPage);
