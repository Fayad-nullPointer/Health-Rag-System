const API        = '';
const token      = localStorage.getItem('token');
const userName   = localStorage.getItem('userName') || 'there';
const userCountry= localStorage.getItem('country')  || '';

if (!token) window.location.href = '/login';

let currentSessionId = null;
let isWaiting        = false;

document.getElementById('sidebarUserName').textContent = userName;
document.getElementById('sidebarCountry').textContent  = userCountry;
document.getElementById('welcomeTitle').textContent    = `Hello, ${userName.split(' ')[0]}`;

async function loadHistory() {
  try {
    const res  = await fetch(`${API}/sessions`, { headers: authHeaders() });
    const data = await res.json();
    renderSessions(data);
  } catch {}
}

function renderSessions(sessions) {
  const list = document.getElementById('sessionsList');
  list.innerHTML = '';
  sessions.forEach(s => {
    const el = document.createElement('div');
    el.className = 'session-item' + (s.session_id === currentSessionId ? ' active' : '');
    el.dataset.id = s.session_id;

    const date  = new Date(s.started_at).toLocaleDateString('en', { month:'short', day:'numeric' });
    const topic = (s.topics_discussed && s.topics_discussed.length) ? s.topics_discussed.join(', ') : 'Conversation';

    el.innerHTML = `
      <div class="session-topic">${topic}</div>
      <div class="session-meta">
        ${s.prior_crisis ? '<div class="crisis-dot"></div>' : ''}
        <span>${date}</span>
        <span>·</span>
        <span>${s.turn_count} turn${s.turn_count !== 1 ? 's' : ''}</span>
      </div>
    `;
    el.addEventListener('click', () => loadSession(s.session_id));
    list.appendChild(el);
  });
}

async function loadSession(sessionId) {
  currentSessionId = sessionId;
  document.getElementById('welcomeState').style.display = 'none';
  clearMessages();
  updateActiveSession();

  try {
    const res      = await fetch(`${API}/sessions/${sessionId}/messages`, { headers: authHeaders() });
    const messages = await res.json();
    messages.forEach(m => renderMessage(m.role, m.content, m.emotion, [], m.crisis_flag));
    scrollToBottom();
  } catch {}
}

document.getElementById('newChatBtn').addEventListener('click', () => {
  currentSessionId = null;
  clearMessages();
  document.getElementById('welcomeState').style.display = 'flex';
  document.getElementById('crisisBanner').classList.remove('show');
  updateActiveSession();
});

async function sendMessage(text) {
  if (!text.trim() || isWaiting) return;
  isWaiting = true;

  document.getElementById('welcomeState').style.display = 'none';
  document.getElementById('sendBtn').disabled = true;

  renderMessage('user', text, null, [], false);
  scrollToBottom();

  const typingEl = showTyping();

  try {
    const res = await fetch(`${API}/chat`, {
      method : 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body   : JSON.stringify({ message: text, session_id: currentSessionId }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error');

    typingEl.remove();
    currentSessionId = data.session_id;

    
    renderMessage('assistant', data.answer, data.emotion, data.sources, data.crisis_flag);

    if (data.crisis_flag && data.hotline) {
      showCrisisBanner(data.hotline);
    } else {
      document.getElementById('crisisBanner').classList.remove('show');
    }

    updateActiveSession();
    loadHistory();
    scrollToBottom();

  } catch (err) {
    typingEl.remove();
    renderMessage('assistant',
      "I'm here with you. I'm having a small technical moment — please try again in just a second.",
      null, [], false
    );
    scrollToBottom();
  }

  isWaiting = false;
  document.getElementById('sendBtn').disabled = false;
}

function renderMessage(role, content, emotion, sources, crisisFlag) {
  const area = document.getElementById('messagesArea');
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;

  const initials = role === 'user'
    ? (userName.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase())
    : '🌿';

  // معالجة وطباعة النصوص المقتبسة بشكل سليم بنسبة 100%
  const citationsHtml = (sources && sources.length)
    ? `<div class="citations">${sources.map(src => {
        const textToShow = src.excerpt ? src.excerpt : (typeof src === 'string' ? src : 'Clinical Insight');
        const similarityScore = src.similarity ? `Similarity: ${src.similarity}` : '';
        return `<span class="citation-tag" title="${similarityScore}">${textToShow}</span>`;
      }).join('')}</div>`
    : '';

  const formattedContent = content
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>');

  const now = new Date().toLocaleTimeString('en', { hour:'2-digit', minute:'2-digit' });

  wrapper.innerHTML = `
    <div class="avatar ${role === 'user' ? 'user-av' : 'bot-av'}">${initials}</div>
    <div>
      <div class="bubble"><p>${formattedContent}</p>${citationsHtml}</div>
      <div class="msg-time">${now}</div>
    </div>
  `;
  area.appendChild(wrapper);
}

function showTyping() {
  const area = document.getElementById('messagesArea');
  const el   = document.createElement('div');
  el.className = 'typing-indicator';
  el.innerHTML = `
    <div class="avatar bot-av">🌿</div>
    <div class="typing-dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
  `;
  area.appendChild(el);
  scrollToBottom();
  return el;
}

function showCrisisBanner(hotlineData) {
  const banner = document.getElementById('crisisBanner');
  const text   = document.getElementById('crisisHotlineText');
  
  if (hotlineData && hotlineData.number) {
    text.textContent = `Local Helpline: ${hotlineData.number} (${hotlineData.name || 'Emergency Support'})`;
  } else {
    text.textContent = `Please reach out to your local emergency services immediately.`;
  }
  banner.classList.add('show');
}

document.getElementById('crisisClose').addEventListener('click', () => {
  document.getElementById('crisisBanner').classList.remove('show');
});

const input  = document.getElementById('messageInput');
const sendBtn= document.getElementById('sendBtn');

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 140) + 'px';
});

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    const val = input.value.trim();
    if (val) {
      input.value = '';
      input.style.height = 'auto';
      sendMessage(val);
    }
  }
});

sendBtn.addEventListener('click', () => {
  const val = input.value.trim();
  if (val) {
    input.value = '';
    input.style.height = 'auto';
    sendMessage(val);
  }
});

function useStarter(btn) {
  sendMessage(btn.textContent);
}

function authHeaders() {
  return { 'Authorization': `Bearer ${token}` };
}

function clearMessages() {
  const area = document.getElementById('messagesArea');
  const messages = area.querySelectorAll('.message, .typing-indicator');
  messages.forEach(m => m.remove());
}

function scrollToBottom() {
  const area = document.getElementById('messagesArea');
  area.scrollTop = area.scrollHeight;
}

function updateActiveSession() {
  document.querySelectorAll('.session-item').forEach(el => {
    el.classList.toggle('active', el.dataset.id === currentSessionId);
  });
  document.getElementById('sessionInfoHeader').textContent = currentSessionId ? `Session active` : '';
}

document.getElementById('logoutBtn').addEventListener('click', () => {
  if (currentSessionId) {
    fetch(`${API}/sessions/${currentSessionId}`, {
      method: 'DELETE', headers: authHeaders()
    }).finally(() => {
      localStorage.clear();
      window.location.href = '/';
    });
  } else {
    localStorage.clear();
    window.location.href = '/';
  }
});

document.getElementById('mobileMenuBtn').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('open');
});

loadHistory();