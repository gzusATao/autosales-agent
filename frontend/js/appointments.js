/**
 * AutoSales Agent — 试驾预约页
 */

async function loadAppointments() {
  const content = initLayout('试驾预约', 'appointments');
  content.innerHTML = `<div class="loading"><div class="spinner"></div><p>加载中...</p></div>`;

  try {
    const apps = await api.getAppointments();

    const total = apps.length;
    const success = apps.filter(a => a.status === '预约成功').length;
    const pending = apps.filter(a => a.status === '待确认').length;

    content.innerHTML = `
      <!-- 统计 -->
      <div class="stats-grid">
        <div class="stat-card"><div class="stat-label">总预约</div><div class="stat-value small">${total}</div></div>
        <div class="stat-card"><div class="stat-label">已确认</div><div class="stat-value small" style="color:var(--green);">${success}</div></div>
        <div class="stat-card"><div class="stat-label">待确认</div><div class="stat-value small" style="color:var(--orange);">${pending}</div></div>
        <div class="stat-card"><div class="stat-label">已完成</div><div class="stat-value small">0</div></div>
      </div>

      <!-- 表格 -->
      <div class="card responsive-table-card">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>预约编号</th>
                <th>客户</th>
                <th>手机号</th>
                <th>车型</th>
                <th>门店</th>
                <th>预约时间</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              ${apps.length ? apps.map(a => `
                <tr>
                  <td><code style="font-size:12px;">${a.appointment_id}</code></td>
                  <td><strong>${a.customer_name || '未知'}</strong></td>
                  <td>${a.phone || '-'}</td>
                  <td>${a.brand || ''} ${a.model || ''}</td>
                  <td>${a.store_name}</td>
                  <td>${a.appointment_time}</td>
                  <td><span class="tag ${a.status === '预约成功' ? 'tag-success' : a.status === '已完成' ? 'tag-done' : a.status === '已取消' ? 'tag-cancel' : 'tag-pending'}">${a.status}</span></td>
                  <td>
                    <div class="btn-group">
                      <button class="btn btn-sm btn-ghost" ${a.status !== '预约成功' ? 'disabled' : ''}>确认</button>
                      <button class="btn btn-sm btn-ghost">改期</button>
                    </div>
                  </td>
                </tr>
              `).join('') : `
                <tr><td colspan="8" style="text-align:center;padding:32px;color:var(--text-muted);">
                  暂无试驾预约记录<br>
                  <div class="hint mt-1">通过销售对话页预约试驾后显示在此</div>
                </td></tr>
              `}
            </tbody>
          </table>
        </div>
        <div class="mobile-record-list">
          ${apps.length ? apps.map(a => `
            <article class="mobile-record-card">
              <div class="mobile-record-head">
                <div>
                  <div class="mobile-record-title">${a.customer_name || '未知客户'}</div>
                  <div class="mobile-record-subtitle">${a.phone || '未留电话'}</div>
                </div>
                <span class="tag ${a.status === '预约成功' ? 'tag-success' : a.status === '已完成' ? 'tag-done' : a.status === '已取消' ? 'tag-cancel' : 'tag-pending'}">${a.status}</span>
              </div>
              <div class="mobile-record-meta">
                <div><span>车型</span><strong>${a.brand || ''} ${a.model || ''}</strong></div>
                <div><span>门店</span><strong>${a.store_name || '-'}</strong></div>
              </div>
              <div class="mobile-record-line">
                <span>预约时间</span>
                <strong>${a.appointment_time || '-'}</strong>
              </div>
              <div class="btn-group mobile-record-action">
                <button class="btn btn-sm btn-ghost" ${a.status !== '预约成功' ? 'disabled' : ''}>确认</button>
                <button class="btn btn-sm btn-ghost">改期</button>
              </div>
            </article>
          `).join('') : `
            <div class="mobile-empty-card">
              暂无试驾预约记录
              <div class="hint mt-1">通过销售对话页预约试驾后显示在此</div>
            </div>
          `}
        </div>
      </div>
    `;
  } catch (e) {
    console.error(e);
    content.innerHTML = `<div class="empty-state"><p>加载失败</p></div>`;
  }
}

loadAppointments();
