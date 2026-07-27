/**
 * AutoSales Agent — AI 销售对话页控制器
 */

let sessionId = localStorage.getItem('chat_session_id') || '';
let customerId = localStorage.getItem('chat_customer_id') || '';
let isSending = false;
let thinkingTimer = null;

const INTENT_TITLES = {
  'car_recommendation':'车型推荐结果','car_compare':'配置对比分析','loan_calculation':'分期试算方案',
  'inventory_query':'库存查询结果','test_drive':'试驾预约确认','general_question':'需求确认',
};

const THINKING_STEPS = [
  '正在识别意图...','正在读取客户记忆...','正在补全需求字段...',
  '正在路由决策...','正在调用业务工具...','正在生成销售回复...','正在更新客户画像...',
];

// DOM 缓存
let messagesEl, inputEl, sendBtn, thinkingEl, thinkingText;

// 快捷按钮消息映射
const QUICK_MSGS = {
  'btn-recommend': '推荐几款20万以内的SUV',
  'btn-compare': '对比宋PLUS和锋兰达',
  'btn-loan': '月供多少？',
  'btn-inventory': '广州有现车吗？',
  'btn-drive': '预约试驾',
};

function initPage() {
  // 注入侧边栏和顶栏
  const sidebarHtml = renderSidebar('chat');
  const topbarHtml = renderTopbar('AI 销售对话');
  document.getElementById('app-root').insertAdjacentHTML('afterbegin', sidebarHtml);
  document.getElementById('topbar-placeholder').outerHTML = topbarHtml;

  // 缓存 DOM
  messagesEl = document.getElementById('chat-messages');
  inputEl = document.getElementById('chat-input');
  sendBtn = document.getElementById('chat-send');
  thinkingEl = document.getElementById('agent-thinking');
  thinkingText = document.getElementById('thinking-text');

  // 绑定事件
  sendBtn?.addEventListener('click', sendMessage);
  inputEl?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  // 绑定快捷按钮
  Object.entries(QUICK_MSGS).forEach(([id, msg]) => {
    document.getElementById(id)?.addEventListener('click', () => {
      inputEl.value = msg;
      sendMessage();
    });
  });
}

// ─── 发送消息 ──────────────────────────────────
async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || isSending) return;
  inputEl.value = ''; isSending = true; sendBtn.disabled = true;

  addUserMessage(text);
  showThinking();

  try {
    const resp = await api.chat(text, sessionId, customerId);
    if (resp.session_id) { sessionId = resp.session_id; localStorage.setItem('chat_session_id', sessionId); }
    if (resp.customer_id) { customerId = resp.customer_id; localStorage.setItem('chat_customer_id', customerId); }
    hideThinking();
    addAgentMessage(resp);
    updateAgentPanel(resp);
  } catch (err) {
    hideThinking();
    addAgentMessage({ reply: '抱歉，系统遇到了一些问题，请稍后再试。' });
    console.error(err);
  } finally {
    isSending = false; sendBtn.disabled = false; inputEl.focus();
  }
}

// ─── 思维状态 ──────────────────────────────────
function showThinking() {
  thinkingEl.style.display = 'flex';
  thinkingText.textContent = 'Agent 正在分析需求...';
  let step = 0;
  updateGraphNode(0, 'active');
  thinkingTimer = setInterval(() => {
    step = (step + 1) % THINKING_STEPS.length;
    thinkingText.textContent = THINKING_STEPS[step];
    if (step > 0) updateGraphNode(step - 1, 'done');
    updateGraphNode(step, 'active');
  }, 700);
  scrollToBottom();
}

function hideThinking() {
  thinkingEl.style.display = 'none';
  if (thinkingTimer) { clearInterval(thinkingTimer); thinkingTimer = null; }
  document.querySelectorAll('.graph-node').forEach(n => { n.className = 'graph-node done'; });
}

function updateGraphNode(index, status) {
  const nodes = document.querySelectorAll('.graph-node');
  if (nodes[index]) nodes[index].className = `graph-node ${status}`;
}

// ─── 消息渲染 ──────────────────────────────────
function addUserMessage(text) {
  const div = document.createElement('div');
  div.className = 'message user';
  div.innerHTML = `<div class="message-avatar">U</div><div class="message-content"><p>${escapeHtml(text)}</p></div>`;
  messagesEl.appendChild(div);
  scrollToBottom();
}

function addAgentMessage(resp) {
  const div = document.createElement('div');
  div.className = 'message assistant';

  const title = INTENT_TITLES[resp.current_intent] || '销售顾问回复';
  const tools = resp.tool_trace || [];
  const intent = resp.purchase_intent || {};
  const missing = resp.missing_slots || [];

  let summaryItems = [];
  if (resp.current_intent) summaryItems.push(`当前意图：${title}`);
  if (intent.budget) summaryItems.push(`预算：${intent.budget}`);
  if (intent.car_type) summaryItems.push(`车型：${intent.car_type}`);
  if (intent.energy_type) summaryItems.push(`能源：${intent.energy_type}`);
  if (tools.length) summaryItems.push(`调用工具：${tools.map(t => t.tool_name).join('、')}`);
  if (missing.length) summaryItems.push(`待补充：${missing.join('、')}`);

  div.innerHTML = `
    <div class="message-avatar assistant-avatar" aria-label="AI 智能销售"></div>
    <div class="message-content">
      <div class="msg-subtitle">${title}</div>
      <div class="msg-body">${formatMessage(resp.reply)}</div>
      ${summaryItems.length ? `
        <div class="msg-summary">
          <div class="msg-summary-title">本轮动作摘要</div>
          ${summaryItems.map(s => `<div class="msg-summary-item">${s}</div>`).join('')}
        </div>
      ` : ''}
    </div>
  `;
  messagesEl.appendChild(div);
  scrollToBottom();
}

function escapeHtml(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function formatMessage(t) {
  return '<p>' + escapeHtml(t).replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>') + '</p>';
}

// ─── Agent 面板 ─────────────────────────────────
function updateAgentPanel(resp) {
  const il = {'car_recommendation':'车型推荐','car_compare':'配置对比','loan_calculation':'分期试算','inventory_query':'库存查询','test_drive':'试驾预约','general_question':'一般咨询'};
  document.getElementById('panel-intent').innerHTML = resp.current_intent ? `<span class="tag tag-blue">${il[resp.current_intent]||resp.current_intent}</span>` : '<span class="text-muted">等待识别...</span>';

  const sm = {'car_recommendation':{label:'推荐车型',cls:'tag-warm'},'car_compare':{label:'配置对比',cls:'tag-warm'},'loan_calculation':{label:'分期方案',cls:'tag-warm'},'inventory_query':{label:'库存查询',cls:'tag-warm'},'test_drive':{label:'预约试驾',cls:'tag-hot'},'general_question':{label:'需求采集',cls:'tag-cold'}};
  const s = sm[resp.current_intent]||{label:'新对话',cls:'tag-cold'};
  document.getElementById('panel-stage').innerHTML = `<span class="tag ${s.cls}">${s.label}</span>`;

  const pi = resp.purchase_intent||{};
  const sl = {budget:'预算',car_type:'车型',energy_type:'能源',usage:'用途',purchase_time:'购车周期'};
  document.getElementById('panel-slots').innerHTML = Object.entries(sl).map(([k,label])=>`<div class="agent-field"><span class="label">${label}</span><span class="value">${pi[k]||'<span class="text-muted">待采集</span>'}</span></div>`).join('');

  const miss = resp.missing_slots||[];
  document.getElementById('panel-missing').innerHTML = miss.length ? miss.map(s=>`<span class="tag tag-warm" style="margin:2px;">${sl[s]||s}</span>`).join('') : '<span class="tag tag-success">已齐全</span>';

  const tools = resp.tool_trace||[];
  document.getElementById('panel-tools').innerHTML = tools.length ? tools.map(t=>`
    <div class="tool-timeline-item">
      <div class="tool-name">${t.tool_name}<span class="tool-status">${Icons.check} 成功</span></div>
      <div class="tool-io" style="display:flex;justify-content:space-between;"><span>参数: ${Object.keys(t.input||{}).slice(0,3).join(', ')}</span><span class="text-muted" style="font-size:11px;">${t.timestamp?Math.round((Date.now()-new Date(t.timestamp).getTime())/1000)+'s前':''}</span></div>
      <div class="tool-io">结果: ${JSON.stringify(t.output).slice(0,80)}${JSON.stringify(t.output).length>80?'...':''}</div>
    </div>
  `).join('') : '<div class="text-muted" style="font-size:13px;">等待工具调用...</div>';

  const pf = resp.customer_profile||{};
  document.getElementById('panel-profile').innerHTML = Object.keys(pf).length ? `
    <div class="agent-field"><span class="label">预算</span><span class="value">${pf.budget||'-'}</span></div>
    <div class="agent-field"><span class="label">车型</span><span class="value">${pf.car_type||'-'}</span></div>
    <div class="agent-field"><span class="label">能源</span><span class="value">${pf.energy_type||'-'}</span></div>
    <div class="agent-field"><span class="label">关注点</span><span class="value">${(pf.concerns||[]).join('、')||'-'}</span></div>
    <div class="agent-field"><span class="label">意向等级</span><span class="value"><span class="tag ${pf.lead_level==='高意向'?'tag-hot':pf.lead_level==='中意向'?'tag-warm':'tag-cold'}">${pf.lead_level||'-'}</span></span></div>
  ` : '<div class="text-muted" style="font-size:13px;">等待对话...</div>';
}

function scrollToBottom() { if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight; }

document.addEventListener('DOMContentLoaded', initPage);
