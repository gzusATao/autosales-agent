/**
 * AutoSales Agent — 后台统计页
 */

async function loadMetrics() {
  const content = initLayout('后台统计', 'metrics');
  content.innerHTML = `<div class="loading"><div class="spinner"></div><p>加载中...</p></div>`;

  try {
    const stats = await api.getAgentMetrics();
    const toolRows = Object.entries(stats.tool_counts || {});
    const failedToolRows = Object.entries(stats.failed_tool_counts || {});
    const reasonRows = Object.entries(stats.reason_counts || {});

    content.innerHTML = `
      <div class="metrics-hero">
        <div>
          <h1>Agent 运行统计</h1>
          <p>用于观察回答成功率、用户反馈、RAG 命中质量和工具调用稳定性。</p>
        </div>
        <button class="btn btn-outline" onclick="loadMetrics()">刷新</button>
      </div>

      <div class="stats-grid metrics-grid">
        ${metricCard('成功率', `${stats.success_rate}%`, `${stats.successful_runs}/${stats.total_runs} 轮正常`, 'ok')}
        ${metricCard('失败率', `${stats.failure_rate}%`, `${stats.failed_runs} 轮兜底或异常`, 'bad')}
        ${metricCard('平均响应时间', `${stats.average_response_time_ms}ms`, '后端完整处理耗时', 'time')}
        ${metricCard('满意率', `${stats.satisfaction_rate}%`, `${stats.satisfied}/${stats.feedback_total} 次满意`, 'ok')}
        ${metricCard('不满意率', `${stats.dissatisfaction_rate}%`, `${stats.unsatisfied} 次点踩`, 'warn')}
        ${metricCard('工具成功率', `${stats.tool_success_rate}%`, `${stats.tool_failure_total}/${stats.tool_call_total} 次工具失败`, 'time')}
      </div>

      <div class="metrics-panels">
        <section class="card metrics-card">
          <div class="card-header">
            <h3>RAG 维护信号</h3>
            <span class="tag tag-warm">${stats.rag_negative_count} 条负反馈</span>
          </div>
          <div class="metric-note">点踩中涉及 RAG 检索或资料片段的记录，用来补充车型资料、清理低相关 chunk。</div>
          ${renderBadFeedback(stats.recent_bad_feedback || [])}
        </section>

        <section class="card metrics-card">
          <div class="card-header">
            <h3>工具调用健康</h3>
            <span class="tag ${stats.tool_failure_total ? 'tag-warm' : 'tag-cold'}">${stats.tool_failure_total} 次失败</span>
          </div>
          ${renderKeyValueList(toolRows, '暂无工具调用记录')}
          ${failedToolRows.length ? `
            <div class="metric-subtitle">失败工具</div>
            ${renderKeyValueList(failedToolRows, '暂无失败工具')}
          ` : ''}
        </section>

        <section class="card metrics-card">
          <div class="card-header">
            <h3>点踩原因</h3>
            <span class="tag tag-cold">${stats.unsatisfied} 条</span>
          </div>
          ${renderKeyValueList(reasonRows, '暂无点踩原因')}
        </section>

        <section class="card metrics-card">
          <div class="card-header">
            <h3>最近异常</h3>
            <span class="tag tag-cold">${(stats.recent_failures || []).length} 条</span>
          </div>
          ${renderFailures(stats.recent_failures || [])}
        </section>
      </div>
    `;
  } catch (error) {
    console.error(error);
    content.innerHTML = `<div class="empty-state"><p>统计数据加载失败</p></div>`;
  }
}

function metricCard(label, value, hint, tone) {
  return `
    <div class="stat-card metric-stat ${tone}">
      <div class="stat-label">${label}</div>
      <div class="stat-value small">${value}</div>
      <div class="metric-hint">${hint}</div>
    </div>
  `;
}

function renderKeyValueList(rows, emptyText) {
  if (!rows.length) {
    return `<div class="empty-state compact">${emptyText}</div>`;
  }
  return `
    <div class="metric-list">
      ${rows.map(([name, count]) => `
        <div class="metric-row">
          <span>${escapeHtml(name || '未分类')}</span>
          <strong>${count}</strong>
        </div>
      `).join('')}
    </div>
  `;
}

function renderBadFeedback(rows) {
  if (!rows.length) {
    return `<div class="empty-state compact">暂无不满意反馈</div>`;
  }
  return `
    <div class="metric-table-list">
      ${rows.map(item => `
        <article class="metric-record">
          <div class="metric-record-head">
            <strong>${escapeHtml(item.reason || '未填写原因')}</strong>
            <span>${formatTime(item.created_at)}</span>
          </div>
          <p>${escapeHtml(item.question || '-')}</p>
          <div class="metric-tags">
            <span class="tag tag-cold">${escapeHtml(item.intent || 'unknown')}</span>
            ${(item.tool_names || []).map(name => `<span class="tag">${escapeHtml(name)}</span>`).join('')}
            ${(item.rag_chunks || []).length ? '<span class="tag tag-warm">RAG</span>' : ''}
          </div>
        </article>
      `).join('')}
    </div>
  `;
}

function renderFailures(rows) {
  if (!rows.length) {
    return `<div class="empty-state compact">暂无异常或兜底记录</div>`;
  }
  return `
    <div class="metric-table-list">
      ${rows.map(item => `
        <article class="metric-record">
          <div class="metric-record-head">
            <strong>${escapeHtml(item.error_type || 'fallback')}</strong>
            <span>${item.response_time_ms || 0}ms</span>
          </div>
          <p>${escapeHtml(item.question || '-')}</p>
          <div class="metric-tags">
            <span class="tag tag-cold">${escapeHtml(item.intent || 'unknown')}</span>
            ${(item.failed_tool_names || []).map(name => `<span class="tag tag-warm">${escapeHtml(name)}</span>`).join('')}
          </div>
        </article>
      `).join('')}
    </div>
  `;
}

function formatTime(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN');
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

document.addEventListener('DOMContentLoaded', loadMetrics);
