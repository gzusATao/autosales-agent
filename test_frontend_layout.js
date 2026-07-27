const fs = require('fs');

const html = fs.readFileSync('frontend/chat.html', 'utf8');
const css = fs.readFileSync('frontend/css/style.css', 'utf8');
const layout = fs.readFileSync('frontend/js/layout.js', 'utf8');
const dashboard = fs.readFileSync('frontend/js/dashboard.js', 'utf8');
const chat = fs.readFileSync('frontend/js/chat.js', 'utf8');
const index = fs.readFileSync('frontend/index.html', 'utf8');
const apiJs = fs.readFileSync('frontend/js/api.js', 'utf8');
const dashboardHtml = fs.readFileSync('frontend/dashboard.html', 'utf8');

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

assert(html.includes('chat-layout-new'), 'chat page should keep the workbench layout');
assert(html.includes('agent-panel'), 'chat page should keep the agent explanation panel');
assert(html.includes('panel-tools'), 'agent panel should expose tool calling trace');
assert(html.includes('panel-graph'), 'agent panel should expose LangGraph flow');
assert(css.includes('.chat-layout-new'), 'css should style the chat workbench layout');
assert(css.includes('.chat-main::before'), 'chat surface should have an enterprise header strip');
assert(css.includes('.agent-panel-section'), 'agent panel sections should be styled');
assert(css.includes('.tool-timeline-item'), 'tool calling trace items should be styled');
assert(css.includes('grid-template-columns: minmax(0, 1fr) 380px'), 'desktop layout should reserve a stable agent panel');
assert(css.includes('.stat-card .stat-label svg'), 'dashboard metric icons should have a scoped size');
assert(css.includes('.card-header svg'), 'dashboard card header icons should have a scoped size');
assert(layout.includes('<span>汽车销售顾问</span>'), 'sidebar brand should use the Chinese product name');
assert(layout.includes("label: '概览'"), 'dashboard nav label should be fully Chinese');
assert(layout.includes("href: '/dashboard.html'"), 'dashboard nav should open the real overview page');
assert(dashboard.includes("initLayout('概览'"), 'dashboard topbar title should be fully Chinese');
assert(!layout.includes('概览 Dashboard'), 'layout should not show mixed Chinese-English dashboard label');
assert(!dashboard.includes('概览 Dashboard'), 'dashboard should not show mixed Chinese-English title');
assert(css.includes('content: "AI 销售工作台"'), 'chat workbench strip should be Chinese');
assert(html.includes('message-avatar assistant-avatar'), 'initial assistant avatar should use the smart sales avatar class');
assert(chat.includes('message-avatar assistant-avatar'), 'dynamic assistant messages should use the smart sales avatar class');
assert(css.includes('.assistant-avatar::before'), 'smart sales avatar should be drawn with CSS');
assert(dashboard.includes('dashboard-side-stack'), 'dashboard right column should use a compact side stack');
assert(css.includes('.dashboard-side-stack'), 'dashboard side stack should be styled');
assert(css.includes('.dashboard-side-stack .card'), 'dashboard side cards should have compact spacing');
assert(index.includes('window.location.replace("/chat.html")'), 'root page should open the AI chat workspace by default');
assert(index.includes('http-equiv="refresh"'), 'root page should provide a non-JS fallback redirect to chat');
assert(dashboardHtml.includes('/js/dashboard.js'), 'overview page should load the dashboard script');
assert(layout.includes('id="model-badge"'), 'topbar model badge should be addressable');
assert(apiJs.includes('initModelBadge'), 'frontend should sync the model badge from the backend');
assert(apiJs.includes('/health'), 'frontend should read health status for provider display');

console.log('frontend layout checks passed');
