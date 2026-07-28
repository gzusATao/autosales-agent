const fs = require('fs');

const html = fs.readFileSync('frontend/chat.html', 'utf8');
const css = fs.readFileSync('frontend/css/style.css', 'utf8');
const layout = fs.readFileSync('frontend/js/layout.js', 'utf8');
const dashboard = fs.readFileSync('frontend/js/dashboard.js', 'utf8');
const chat = fs.readFileSync('frontend/js/chat.js', 'utf8');
const index = fs.readFileSync('frontend/index.html', 'utf8');
const apiJs = fs.readFileSync('frontend/js/api.js', 'utf8');
const dashboardHtml = fs.readFileSync('frontend/dashboard.html', 'utf8');
const favicon = fs.readFileSync('frontend/favicon.svg', 'utf8');
const carsJs = fs.readFileSync('frontend/js/cars.js', 'utf8');

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
assert(layout.includes('brandMark'), 'sidebar should use the custom brand mark');
assert(layout.includes('garage') || layout.includes('M4 18V9'), 'car library nav icon should look like a garage/library');
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
assert(apiJs.includes('uploadKnowledge'), 'frontend API should support adding knowledge documents');
assert(apiJs.includes('uploadKnowledgeFile'), 'frontend API should support uploading knowledge files');
assert(apiJs.includes("'/knowledge'"), 'frontend API should support listing knowledge documents');
assert(carsJs.includes('车型档案') && carsJs.includes('销售资料') && carsJs.includes('资料检索'), 'cars page should expose car profile and sales material tabs');
assert(carsJs.includes('api.uploadKnowledge'), 'cars page should upload knowledge documents');
assert(carsJs.includes('api.uploadKnowledgeFile'), 'cars page should upload PDF/TXT/Word/MD knowledge files');
assert(carsJs.includes('accept=".pdf,.txt,.docx,.md"'), 'knowledge upload should support common document formats');
assert(carsJs.includes('api.searchKnowledge'), 'cars page should test RAG retrieval');
assert(carsJs.includes('knowledge-workspace'), 'sales materials page should use a desktop workspace layout');
assert(carsJs.includes('knowledge-list-card'), 'sales materials list should be a first-class workspace panel');
assert(css.includes('grid-template-columns: minmax(320px, 420px) minmax(0, 1fr)'), 'sales materials layout should keep the list visible at 100 percent zoom');
assert(css.includes('max-height: calc(100dvh - var(--topbar-h) - 300px)'), 'sales materials list should scroll within the visible workspace');
assert(chat.includes('new WebSocket'), 'chat should use websocket streaming for AI replies');
assert(chat.includes('createStreamingAgentMessage'), 'chat should create an assistant bubble before streamed output arrives');
assert(css.includes('.stream-thinking'), 'assistant bubble should show a thinking animation before the first streamed chunk');
assert(css.includes('@keyframes thinking-dot'), 'thinking animation should have a stable pulse keyframe');
assert(css.includes('@media (max-width: 760px)'), 'mobile layout should have a dedicated phone breakpoint');
assert(css.includes('grid-template-columns: repeat(6, minmax(0, 1fr))'), 'mobile sidebar should become bottom navigation');
assert(css.includes('height: calc(100dvh - var(--topbar-h) - 84px)'), 'mobile chat should use dynamic viewport height');
assert(html.includes('href="/favicon.svg"'), 'chat page should include the branded favicon');
assert(dashboardHtml.includes('href="/favicon.svg"'), 'dashboard page should include the branded favicon');
assert(favicon.includes('aria-label="汽车销售顾问"'), 'favicon should be branded for the product');
assert(favicon.includes('M13 38h6l5-10'), 'favicon should read visually as a car outline');
assert(favicon.includes('fill="#22c55e"'), 'favicon should include the intelligent sales accent');

console.log('frontend layout checks passed');
