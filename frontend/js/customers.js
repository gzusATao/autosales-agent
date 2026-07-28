/**
 * AutoSales Agent — 客户画像/线索详情页
 */

async function loadCustomers() {
  const content = initLayout('客户画像 / 线索详情', 'customers');
  content.innerHTML = `<div class="loading"><div class="spinner"></div><p>加载中...</p></div>`;

  try {
    const leads = await api.getLeads();

    if (!leads || leads.length === 0) {
      content.innerHTML = `<div class="empty-state"><p>暂无客户数据</p><div class="hint">请在销售对话页创建客户</div><a href="/chat.html" class="btn btn-primary mt-2">开始对话</a></div>`;
      return;
    }

    content.innerHTML = `
      <div class="card responsive-table-card">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>客户</th>
                <th>电话</th>
                <th>预算</th>
                <th>意向车型</th>
                <th>购车周期</th>
                <th>意向等级</th>
                <th>最近跟进摘要</th>
                <th>最近联系</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              ${leads.map(l => `
                <tr>
                  <td><strong>${l.name || '未知'}</strong></td>
                  <td>${l.phone || '-'}</td>
                  <td>${l.budget || '-'}</td>
                  <td>${(l.intent_models || []).join('、') || '-'}</td>
                  <td>${l.purchase_time || '-'}</td>
                  <td><span class="tag ${l.lead_level === '高意向' ? 'tag-hot' : l.lead_level === '中意向' ? 'tag-warm' : 'tag-cold'}">${l.lead_level || '低意向'}</span></td>
                  <td style="max-width:200px;white-space:normal;">${l.follow_up_summary || '-'}</td>
                  <td>${l.last_contact_time ? new Date(l.last_contact_time).toLocaleString('zh-CN') : '-'}</td>
                  <td><button class="btn btn-sm btn-outline" onclick="viewProfile(${l.id})">查看详情</button></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
        <div class="mobile-record-list">
          ${leads.map(l => `
            <article class="mobile-record-card">
              <div class="mobile-record-head">
                <div>
                  <div class="mobile-record-title">${l.name || '未知客户'}</div>
                  <div class="mobile-record-subtitle">${l.phone || '未留电话'}</div>
                </div>
                <span class="tag ${l.lead_level === '高意向' ? 'tag-hot' : l.lead_level === '中意向' ? 'tag-warm' : 'tag-cold'}">${l.lead_level || '低意向'}</span>
              </div>
              <div class="mobile-record-meta">
                <div><span>预算</span><strong>${l.budget || '-'}</strong></div>
                <div><span>购车周期</span><strong>${l.purchase_time || '-'}</strong></div>
              </div>
              <div class="mobile-record-line">
                <span>意向车型</span>
                <strong>${(l.intent_models || []).join('、') || '-'}</strong>
              </div>
              <p class="mobile-record-summary">${l.follow_up_summary || '暂无跟进摘要'}</p>
              <button class="btn btn-sm btn-outline mobile-record-action" onclick="viewProfile(${l.id})">查看详情</button>
            </article>
          `).join('')}
        </div>
      </div>

      <!-- 详情抽屉 -->
      <div class="drawer-overlay" id="drawer-overlay" onclick="closeDrawer()"></div>
      <div class="drawer" id="drawer">
        <div class="drawer-header">
          <h3>客户详情</h3>
          <button class="drawer-close" onclick="closeDrawer()">${Icons.x}</button>
        </div>
        <div class="drawer-body" id="drawer-body">
          <div class="loading"><div class="spinner"></div></div>
        </div>
      </div>
    `;
  } catch (e) {
    console.error(e);
    content.innerHTML = `<div class="empty-state"><p>加载失败</p></div>`;
  }
}

function openDrawer() {
  document.getElementById('drawer-overlay').classList.add('open');
  document.getElementById('drawer').classList.add('open');
}

function closeDrawer() {
  document.getElementById('drawer-overlay').classList.remove('open');
  document.getElementById('drawer').classList.remove('open');
}

async function viewProfile(id) {
  openDrawer();
  const body = document.getElementById('drawer-body');
  body.innerHTML = `<div class="loading"><div class="spinner"></div></div>`;

  try {
    const p = await api.getCustomerProfile(id);
    body.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
        <div style="width:48px;height:48px;border-radius:50%;background:var(--bg-body);display:flex;align-items:center;justify-content:center;font-weight:600;">${Icons.user}</div>
        <div>
          <div style="font-size:16px;font-weight:600;">${p.name || '未知客户'}</div>
          <div class="text-muted text-sm">${p.phone || ''} · ${p.city || ''}</div>
        </div>
        <div style="margin-left:auto;"><span class="tag ${p.lead_level === '高意向' ? 'tag-hot' : p.lead_level === '中意向' ? 'tag-warm' : 'tag-cold'}">${p.lead_level || '低意向'}</span></div>
      </div>

      <h4 style="font-size:14px;font-weight:600;margin-bottom:12px;">购车意向</h4>
      <div class="detail-grid">
        <div class="detail-item"><div class="label">预算</div><div class="value">${p.budget || '未采集'}</div></div>
        <div class="detail-item"><div class="label">车型偏好</div><div class="value">${p.car_type || '未采集'}</div></div>
        <div class="detail-item"><div class="label">能源偏好</div><div class="value">${p.energy_type || '未采集'}</div></div>
        <div class="detail-item"><div class="label">主要用途</div><div class="value">${p.usage || '未采集'}</div></div>
        <div class="detail-item"><div class="label">意向车型</div><div class="value">${(p.intent_models || []).join('、') || '未采集'}</div></div>
        <div class="detail-item"><div class="label">购车周期</div><div class="value">${p.purchase_time || '未采集'}</div></div>
      </div>

      <h4 style="font-size:14px;font-weight:600;margin:16px 0 12px;">关注点</h4>
      <div>${(p.concerns || []).length ? (p.concerns || []).map(c => `<span class="tag tag-blue" style="margin:2px;">${c}</span>`).join('') : '<span class="text-muted text-sm">暂无</span>'}</div>

      <h4 style="font-size:14px;font-weight:600;margin:16px 0 12px;">Agent 跟进摘要</h4>
      <div class="card" style="border-color:var(--border-light);background:var(--bg-body);">
        <p style="font-size:13px;line-height:1.6;">${p.follow_up_summary || '暂无跟进记录'}</p>
      </div>

      <h4 style="font-size:14px;font-weight:600;margin:16px 0 12px;">时间线</h4>
      <div class="timeline">
        <div class="timeline-item done">
          <div class="tl-title">最近联系</div>
          <div class="tl-desc">${p.updated_at ? new Date(p.updated_at).toLocaleString('zh-CN') : '-'}</div>
        </div>
        <div class="timeline-item">
          <div class="tl-title">下一步建议</div>
          <div class="tl-desc">${p.lead_level === '高意向' ? '主动跟进，邀请试驾' : p.lead_level === '中意向' ? '发送车型资料，保持联系' : '继续采集需求'}</div>
        </div>
      </div>
    `;
  } catch (e) {
    body.innerHTML = `<div class="empty-state"><p>加载客户详情失败</p></div>`;
  }
}

loadCustomers();
