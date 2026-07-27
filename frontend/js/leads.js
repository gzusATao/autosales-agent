/**
 * AutoSales Agent — 销售线索 CRM 管理页
 */

async function loadLeads() {
  const content = initLayout('销售线索', 'leads');
  content.innerHTML = `<div class="loading"><div class="spinner"></div><p>加载中...</p></div>`;

  try {
    const leads = await api.getLeads();

    const total = leads.length;
    const hot = leads.filter(l => l.lead_level === '高意向').length;
    const warm = leads.filter(l => l.lead_level === '中意向').length;
    const cold = leads.filter(l => l.lead_level === '低意向').length;

    content.innerHTML = `
      <!-- 统计 -->
      <div class="stats-grid">
        <div class="stat-card"><div class="stat-label">总线索数</div><div class="stat-value">${total}</div></div>
        <div class="stat-card"><div class="stat-label">高意向</div><div class="stat-value small" style="color:var(--red);">${hot}</div></div>
        <div class="stat-card"><div class="stat-label">中意向</div><div class="stat-value small" style="color:var(--orange);">${warm}</div></div>
        <div class="stat-card"><div class="stat-label">低意向 / 待跟进</div><div class="stat-value small">${cold}</div></div>
        <div class="stat-card"><div class="stat-label">今日新增</div><div class="stat-value small">0</div></div>
      </div>

      <!-- 表格 -->
      <div class="card">
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
                <th>跟进摘要</th>
                <th>最近联系</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              ${leads.length ? leads.map(l => `
                <tr>
                  <td><strong>${l.name || '未知'}</strong></td>
                  <td>${l.phone || '-'}</td>
                  <td>${l.budget || '-'}</td>
                  <td>${(l.intent_models || []).join('、') || '-'}</td>
                  <td>${l.purchase_time || '-'}</td>
                  <td><span class="tag ${l.lead_level === '高意向' ? 'tag-hot' : l.lead_level === '中意向' ? 'tag-warm' : 'tag-cold'}">${l.lead_level || '低意向'}</span></td>
                  <td style="max-width:180px;white-space:normal;">${l.follow_up_summary || '-'}</td>
                  <td>${l.last_contact_time ? new Date(l.last_contact_time).toLocaleString('zh-CN') : '-'}</td>
                  <td><button class="btn btn-sm btn-outline" onclick="showLeadDetail(${JSON.stringify(l).replace(/"/g, '&quot;')})">查看</button></td>
                </tr>
              `).join('') : `
                <tr><td colspan="9" style="text-align:center;padding:32px;color:var(--text-muted);">
                  暂无线索数据<br>
                  <div class="hint mt-1">通过销售对话页与客户沟通后自动生成线索</div>
                </td></tr>
              `}
            </tbody>
          </table>
        </div>
      </div>

      <!-- 抽屉详情 -->
      <div class="drawer-overlay" id="drawer-overlay" onclick="closeDrawer()"></div>
      <div class="drawer" id="drawer">
        <div class="drawer-header">
          <h3>线索详情</h3>
          <button class="drawer-close" onclick="closeDrawer()">${Icons.x}</button>
        </div>
        <div class="drawer-body" id="drawer-body"><div class="loading"><div class="spinner"></div></div></div>
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

function showLeadDetail(lead) {
  openDrawer();
  const body = document.getElementById('drawer-body');
  body.innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
      <div style="width:48px;height:48px;border-radius:50%;background:var(--bg-body);display:flex;align-items:center;justify-content:center;">${Icons.user}</div>
      <div>
        <div style="font-size:16px;font-weight:600;">${lead.name || '未知客户'}</div>
        <div class="text-muted text-sm">${lead.phone || ''}</div>
      </div>
      <div style="margin-left:auto;"><span class="tag ${lead.lead_level === '高意向' ? 'tag-hot' : lead.lead_level === '中意向' ? 'tag-warm' : 'tag-cold'}">${lead.lead_level || '低意向'}</span></div>
    </div>

    <div class="detail-grid">
      <div class="detail-item"><div class="label">预算</div><div class="value">${lead.budget || '-'}</div></div>
      <div class="detail-item"><div class="label">意向车型</div><div class="value">${(lead.intent_models || []).join('、') || '-'}</div></div>
      <div class="detail-item"><div class="label">购车周期</div><div class="value">${lead.purchase_time || '-'}</div></div>
      <div class="detail-item"><div class="label">最近联系</div><div class="value">${lead.last_contact_time ? new Date(lead.last_contact_time).toLocaleString('zh-CN') : '-'}</div></div>
    </div>

    <h4 style="font-size:14px;font-weight:600;margin:16px 0 8px;">跟进摘要</h4>
    <div class="card" style="border-color:var(--border-light);background:var(--bg-body);">
      <p style="font-size:13px;">${lead.follow_up_summary || '暂无跟进记录'}</p>
    </div>

    <h4 style="font-size:14px;font-weight:600;margin:16px 0 8px;">下一步建议</h4>
    <div class="card" style="border-color:var(--border-light);background:var(--bg-body);">
      <p style="font-size:13px;">${lead.lead_level === '高意向' ? '🎯 高意向客户，建议主动电话跟进，邀请到店试驾。可推送最新优惠政策和库存信息。' : lead.lead_level === '中意向' ? '📋 中意向客户，建议发送车型资料和用户口碑，保持微信/电话联系频率。' : '📌 低意向客户，需求尚不明确，建议继续采集购车预算和偏好信息。'}</p>
    </div>
  `;
}

loadLeads();
