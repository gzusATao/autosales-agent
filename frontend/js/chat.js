/**
 * Chat page controller.
 * Uses WebSocket streaming first, with the original HTTP endpoint as fallback.
 */

let sessionId = localStorage.getItem('chat_session_id') || '';
let customerId = localStorage.getItem('chat_customer_id') || '';
let isSending = false;
let thinkingTimer = null;
let lastUserMessage = '';
let feedbackTurnId = 0;
const feedbackTurns = new Map();

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

  ensureFeedbackModal();
  ensureLoanPickerModal();
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
  if (shouldOpenLoanPicker(text)) {
    openLoanPicker(text);
    return;
  }

  await sendResolvedMessage(text);
}

async function sendResolvedMessage(text) {
  inputEl.value = '';
  setSending(true);
  lastUserMessage = text;
  addUserMessage(text);
  startGraphThinking();

  const streamMessage = createStreamingAgentMessage(text);

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

function shouldOpenLoanPicker(text) {
  if (!/(分期|月供|贷款|按揭|首付)/.test(text)) return false;
  return !hasLoanDownPayment(text) || !hasLoanTerm(text);
}

function hasLoanDownPayment(text) {
  return /首付\s*\d+(?:\.\d+)?\s*(?:万|w|%)/i.test(text);
}

function hasLoanTerm(text) {
  return /(?:分期|贷款|贷|分)?\s*\d+\s*年|\d+\s*(?:期|个月|月)/i.test(text);
}

function ensureLoanPickerModal() {
  if (document.getElementById('loan-picker-modal')) return;
  document.body.insertAdjacentHTML('beforeend', `
    <div class="loan-picker-modal" id="loan-picker-modal" aria-hidden="true">
      <div class="loan-picker-card" role="dialog" aria-modal="true" aria-labelledby="loan-picker-title">
        <div class="loan-picker-head">
          <div>
            <strong id="loan-picker-title">选择分期方案</strong>
            <p>先补齐首付和期限，再为您试算月供。</p>
          </div>
          <button type="button" class="loan-picker-close" aria-label="关闭">×</button>
        </div>
        <div class="loan-picker-section" data-loan-section="down">
          <div class="loan-picker-label">首付比例</div>
          <div class="loan-picker-options" data-loan-group="down">
            <button type="button" data-value="20%">20%</button>
            <button type="button" data-value="30%" class="selected">30%</button>
            <button type="button" data-value="50%">50%</button>
            <button type="button" data-value="自定义">自定义</button>
          </div>
          <input class="loan-picker-custom" id="loan-custom-down" placeholder="例如：首付10万 或 40%" style="display:none;">
        </div>
        <div class="loan-picker-section" data-loan-section="term">
          <div class="loan-picker-label">分期期限</div>
          <div class="loan-picker-options" data-loan-group="term">
            <button type="button" data-value="12期">12期</button>
            <button type="button" data-value="24期">24期</button>
            <button type="button" data-value="36期" class="selected">36期</button>
            <button type="button" data-value="60期">60期</button>
          </div>
        </div>
        <div class="loan-picker-actions">
          <button type="button" class="btn btn-outline loan-picker-cancel">取消</button>
          <button type="button" class="btn btn-primary loan-picker-submit">开始试算</button>
        </div>
      </div>
    </div>
  `);

  document.querySelector('.loan-picker-close').addEventListener('click', closeLoanPicker);
  document.querySelector('.loan-picker-cancel').addEventListener('click', closeLoanPicker);
  document.querySelector('.loan-picker-submit').addEventListener('click', submitLoanPicker);
  document.querySelectorAll('.loan-picker-options button').forEach(button => {
    button.addEventListener('click', () => {
      const group = button.closest('.loan-picker-options');
      group.querySelectorAll('button').forEach(item => item.classList.remove('selected'));
      button.classList.add('selected');
      if (group.dataset.loanGroup === 'down') {
        document.getElementById('loan-custom-down').style.display = button.dataset.value === '自定义' ? 'block' : 'none';
      }
    });
  });
}

function openLoanPicker(text) {
  const modal = document.getElementById('loan-picker-modal');
  const hasDown = hasLoanDownPayment(text);
  const hasTerm = hasLoanTerm(text);
  modal.dataset.baseMessage = text;
  modal.dataset.hasDownPayment = hasDown ? 'true' : 'false';
  modal.dataset.hasTerm = hasTerm ? 'true' : 'false';
  modal.querySelector('[data-loan-section="down"]').style.display = hasDown ? 'none' : 'block';
  modal.querySelector('[data-loan-section="term"]').style.display = hasTerm ? 'none' : 'block';
  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
}

function closeLoanPicker() {
  const modal = document.getElementById('loan-picker-modal');
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
  modal.dataset.baseMessage = '';
  modal.dataset.hasDownPayment = '';
  modal.dataset.hasTerm = '';
}

function submitLoanPicker() {
  const modal = document.getElementById('loan-picker-modal');
  const baseMessage = modal.dataset.baseMessage || inputEl.value.trim() || '分期试算';
  const downButton = modal.querySelector('[data-loan-group="down"] .selected');
  const termButton = modal.querySelector('[data-loan-group="term"] .selected');
  const parts = [baseMessage];

  if (modal.dataset.hasDownPayment !== 'true') {
    let downText = downButton?.dataset.value || '30%';
    if (downText === '自定义') {
      downText = document.getElementById('loan-custom-down').value.trim();
      if (!downText) {
        document.getElementById('loan-custom-down').focus();
        return;
      }
    }
    if (!downText.startsWith('首付')) downText = `首付${downText}`;
    parts.push(downText);
  }

  if (modal.dataset.hasTerm !== 'true') {
    const termText = termButton?.dataset.value || '36期';
    parts.push(`分${termText}`);
  }

  const resolved = parts.join(' ');
  closeLoanPicker();
  sendResolvedMessage(resolved);
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

function createStreamingAgentMessage(question = '') {
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
    question,
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
  renderFeedbackControls(streamMessage, response, reply);
  scrollToBottom();
}

function renderFeedbackControls(streamMessage, response, reply) {
  const oldFeedback = streamMessage.root.querySelector('.feedback-actions');
  if (oldFeedback) oldFeedback.remove();

  const turnId = `turn-${Date.now()}-${++feedbackTurnId}`;
  const turn = {
    session_id: response.session_id || sessionId,
    customer_id: response.customer_id || customerId,
    question: streamMessage.question || lastUserMessage,
    answer: reply,
    intent: response.current_intent || '',
    tool_trace: response.tool_trace || [],
  };
  feedbackTurns.set(turnId, turn);

  streamMessage.root.querySelector('.message-content').insertAdjacentHTML('beforeend', `
    <div class="feedback-actions" data-turn-id="${turnId}">
      <span>本轮回答有帮助吗？</span>
      <button type="button" class="feedback-btn good" data-feedback-rating="good">满意</button>
      <button type="button" class="feedback-btn bad" data-feedback-rating="bad">不满意</button>
      <span class="feedback-status" aria-live="polite"></span>
    </div>
  `);

  const actions = streamMessage.root.querySelector('.feedback-actions');
  actions.querySelector('[data-feedback-rating="good"]').addEventListener('click', () => {
    submitFeedback(turnId, 'good', '');
  });
  actions.querySelector('[data-feedback-rating="bad"]').addEventListener('click', () => {
    openFeedbackModal(turnId);
  });
}

function ensureFeedbackModal() {
  if (document.getElementById('feedback-modal')) return;
  document.body.insertAdjacentHTML('beforeend', `
    <div class="feedback-modal" id="feedback-modal" aria-hidden="true">
      <div class="feedback-modal-card" role="dialog" aria-modal="true" aria-labelledby="feedback-modal-title">
        <div class="feedback-modal-head">
          <strong id="feedback-modal-title">不满意原因</strong>
          <button type="button" class="feedback-modal-close" aria-label="关闭">×</button>
        </div>
        <div class="feedback-reason-grid">
          ${['答非所问', '信息不准确', '没有查到资料', '推荐不合适', '功能出错', '其他'].map(reason => `
            <label><input type="radio" name="feedback-reason" value="${reason}"> ${reason}</label>
          `).join('')}
        </div>
        <textarea class="form-control feedback-note" id="feedback-note" placeholder="可以补充一句具体问题，方便后续优化"></textarea>
        <div class="feedback-modal-actions">
          <button type="button" class="btn btn-outline feedback-cancel">取消</button>
          <button type="button" class="btn btn-primary feedback-submit">提交反馈</button>
        </div>
      </div>
    </div>
  `);

  document.querySelector('.feedback-modal-close').addEventListener('click', closeFeedbackModal);
  document.querySelector('.feedback-cancel').addEventListener('click', closeFeedbackModal);
  document.querySelector('.feedback-submit').addEventListener('click', submitBadFeedbackFromModal);
}

function openFeedbackModal(turnId) {
  const modal = document.getElementById('feedback-modal');
  modal.dataset.turnId = turnId;
  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
  modal.querySelectorAll('input[name="feedback-reason"]').forEach(input => {
    input.checked = input.value === '答非所问';
  });
  document.getElementById('feedback-note').value = '';
}

function closeFeedbackModal() {
  const modal = document.getElementById('feedback-modal');
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
  modal.dataset.turnId = '';
}

function submitBadFeedbackFromModal() {
  const modal = document.getElementById('feedback-modal');
  const selected = modal.querySelector('input[name="feedback-reason"]:checked');
  const note = document.getElementById('feedback-note').value.trim();
  const reason = [selected?.value || '其他', note].filter(Boolean).join('：');
  submitFeedback(modal.dataset.turnId, 'bad', reason);
  closeFeedbackModal();
}

async function submitFeedback(turnId, rating, reason) {
  const turn = feedbackTurns.get(turnId);
  if (!turn) return;
  const actions = document.querySelector(`.feedback-actions[data-turn-id="${turnId}"]`);
  const status = actions?.querySelector('.feedback-status');
  const buttons = actions?.querySelectorAll('button') || [];
  buttons.forEach(button => { button.disabled = true; });
  if (status) status.textContent = '提交中...';

  try {
    await api.submitFeedback({
      ...turn,
      rating,
      reason,
      rag_chunks: [],
    });
    if (status) status.textContent = rating === 'good' ? '已记录满意反馈' : '已记录问题原因';
    feedbackTurns.delete(turnId);
  } catch (error) {
    console.error('Failed to submit feedback', error);
    buttons.forEach(button => { button.disabled = false; });
    if (status) status.textContent = '提交失败，请稍后重试';
  }
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
