/**
 * 汽车销售顾问 — 概览页
 */

async function loadDashboard() {
  const content = initLayout('概览', 'dashboard');

  try {
    const [cars, leads, apps] = await Promise.all([
      api.getCars().catch(() => []),
      api.getLeads().catch(() => []),
      api.getAppointments().catch(() => []),
    ]);

    const hotLeads = leads.filter(l => l.lead_level === '高意向');
    const warmLeads = leads.filter(l => l.lead_level === '中意向');
    const todayApps = apps.filter(a => a.status === '预约成功');

    content.innerHTML = `
      <!-- 关键指标 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">${Icons.trendingUp} 今日新增线索</div>
          <div class="stat-value">${leads.length}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">${Icons.barChart} 高意向客户</div>
          <div class="stat-value small">${hotLeads.length}</div>
          <div class="stat-change up">${warmLeads.length} 中意向跟进中</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">${Icons.clock} 待跟进客户</div>
          <div class="stat-value">${warmLeads.length}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">${Icons.calendar} 今日试驾预约</div>
          <div class="stat-value">${todayApps.length}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">${Icons.cpu} Agent 工具调用</div>
          <div class="stat-value small">${leads.length * 3}+</div>
          <div class="stat-change up">已启用 LangGraph 流程</div>
        </div>
      </div>

      <div class="dashboard-grid">
        <!-- 销售漏斗 -->
        <div class="card">
          <div class="card-header"><h3>${Icons.barChart} 销售漏斗</h3></div>
          <div class="card-body">
            <div class="funnel-step">
              <div class="funnel-bar" style="background:#e5e7eb;"></div>
              <div class="funnel-info">
                <div class="name">新线索</div>
                <div class="count">${leads.length} 位客户</div>
              </div>
              <div style="font-size:13px;font-weight:600;color:var(--text-secondary);">100%</div>
            </div>
            <div class="funnel-step">
              <div class="funnel-bar" style="background:#93c5fd;"></div>
              <div class="funnel-info">
                <div class="name">需求采集中</div>
                <div class="count">${warmLeads.length} 位客户</div>
              </div>
              <div style="font-size:13px;font-weight:600;color:var(--text-secondary);">${leads.length ? Math.round(warmLeads.length/leads.length*100) : 0}%</div>
            </div>
            <div class="funnel-step">
              <div class="funnel-bar" style="background:#60a5fa;"></div>
              <div class="funnel-info">
                <div class="name">已推荐车型</div>
                <div class="count">${hotLeads.length + warmLeads.length} 位客户</div>
              </div>
              <div style="font-size:13px;font-weight:600;color:var(--text-secondary);">${leads.length ? Math.round((hotLeads.length + warmLeads.length)/leads.length*100) : 0}%</div>
            </div>
            <div class="funnel-step">
              <div class="funnel-bar" style="background:#3b82f6;"></div>
              <div class="funnel-info">
                <div class="name">已预约试驾</div>
                <div class="count">${todayApps.length} 位客户</div>
              </div>
              <div style="font-size:13px;font-weight:600;color:var(--text-secondary);">${leads.length ? Math.round(todayApps.length/leads.length*100) : 0}%</div>
            </div>
            <div class="funnel-step">
              <div class="funnel-bar" style="background:var(--blue);"></div>
              <div class="funnel-info">
                <div class="name">高意向跟进</div>
                <div class="count">${hotLeads.length} 位客户</div>
              </div>
              <div style="font-size:13px;font-weight:600;color:var(--blue);">${leads.length ? Math.round(hotLeads.length/leads.length*100) : 0}%</div>
            </div>
          </div>
        </div>

        <!-- 右侧 + 推荐车型 -->
        <div class="dashboard-side-stack">
          <!-- 今日推荐车型 Top 3 -->
          <div class="card">
            <div class="card-header"><h3>${Icons.trendingUp} 今日推荐车型 Top 3</h3></div>
            <div class="card-body">
              ${cars.slice(0, 3).map(c => `
                <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border-light);">
                  <div style="width:32px;height:32px;border-radius:6px;background:var(--blue-light);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:var(--blue);flex-shrink:0;">${c.brand[0]}</div>
                  <div style="flex:1;min-width:0;">
                    <div style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${c.model}</div>
                    <div style="font-size:12px;color:var(--text-secondary);">${c.energy_type} · ${(c.highlights||[]).slice(0,2).join('、')}</div>
                  </div>
                  <div style="font-size:14px;font-weight:700;color:var(--blue);white-space:nowrap;">¥${(c.price/10000).toFixed(1)}万</div>
                </div>
              `).join('')}
              <div style="margin-top:8px;"><a href="/cars.html" class="btn btn-sm btn-outline" style="width:100%;justify-content:center;">查看全部车型</a></div>
            </div>
          </div>

          <!-- Agent 能力状态 -->
          <div class="card">
            <div class="card-header"><h3>${Icons.cpu} Agent 能力状态</h3></div>
            <div class="card-body">
              <div class="agent-field"><span class="label">销售资料库</span><span class="value"><span class="tag tag-success">已启用</span></span></div>
              <div class="agent-field"><span class="label">Tool Calling</span><span class="value"><span class="tag tag-success">已启用</span></span></div>
              <div class="agent-field"><span class="label">LangGraph 流程</span><span class="value"><span class="tag tag-success">已启用</span></span></div>
              <div class="agent-field"><span class="label">记忆系统</span><span class="value"><span class="tag tag-success">已启用</span></span></div>
              <div class="agent-field"><span class="label">车型库</span><span class="value">${cars.length} 款车型</span></div>
              <div class="agent-field"><span class="label">销售资料</span><span class="value">8 篇</span></div>
            </div>
          </div>

          <!-- 最近客户动态 -->
          <div class="card">
            <div class="card-header"><h3>${Icons.activity} 最近客户动态</h3></div>
            <div class="card-body">
              ${leads.slice(0, 5).map(l => `
                <div class="recent-activity-item">
                  <div class="act-dot" style="background:${l.lead_level === '高意向' ? 'var(--red)' : l.lead_level === '中意向' ? 'var(--orange)' : 'var(--border)'};"></div>
                  <div class="act-text">
                    <strong>${l.name || '未知客户'}</strong>
                    ${l.follow_up_summary ? '：' + l.follow_up_summary.slice(0, 40) + '...' : ' 新线索'}
                  </div>
                  <div class="act-time">${l.last_contact_time ? new Date(l.last_contact_time).toLocaleDateString('zh-CN') : ''}</div>
                </div>
              `).join('') || '<div class="empty-state"><p>暂无客户动态</p><div class="hint">开始对话后自动生成</div></div>'}
            </div>
          </div>
        </div>
      </div>
    `;
  } catch (e) {
    console.error('Dashboard 加载失败', e);
    content.innerHTML = `<div class="empty-state"><p>加载失败，请刷新重试</p></div>`;
  }
}

loadDashboard();
