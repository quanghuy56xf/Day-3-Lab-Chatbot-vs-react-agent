/**
 * VinHomes AI - Real Estate Agent Frontend Logic
 */

// ====== DOM Elements ======
const chatContainer = document.getElementById('chatContainer');
const messagesDiv = document.getElementById('messages');
const welcomeScreen = document.getElementById('welcomeScreen');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const clearChatBtn = document.getElementById('clearChatBtn');
const charCount = document.getElementById('charCount');
const responseTime = document.getElementById('responseTime');
const suggestionsContainer = document.getElementById('suggestionsContainer');
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');

// Stats elements
const statRequests = document.getElementById('statRequests');
const statTokens = document.getElementById('statTokens');
const statLatency = document.getElementById('statLatency');
const statCost = document.getElementById('statCost');
const modelName = document.getElementById('modelName');

let isLoading = false;
let messageCount = 0;
let currentMode = 'agent'; // 'agent' or 'chatbot'

// ====== Initialize ======
document.addEventListener('DOMContentLoaded', () => {
    loadSuggestions();
    setupEventListeners();
    autoResizeTextarea();
    setupModeToggle();
});

// ====== Event Listeners ======
function setupEventListeners() {
    // Send button
    sendBtn.addEventListener('click', sendMessage);

    // Enter to send (Shift+Enter for new line)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Character counter
    messageInput.addEventListener('input', () => {
        charCount.textContent = messageInput.value.length;
        autoResizeTextarea();
    });

    // Clear chat
    clearChatBtn.addEventListener('click', clearChat);

    // Feature cards on welcome screen
    document.querySelectorAll('.feature-card').forEach(card => {
        card.addEventListener('click', () => {
            const query = card.getAttribute('data-query');
            if (query) {
                messageInput.value = query;
                charCount.textContent = query.length;
                sendMessage();
            }
        });
    });

    // Mobile menu toggle
    menuToggle.addEventListener('click', toggleSidebar);

    // Click outside sidebar to close (mobile)
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
            if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('open');
                removeOverlay();
            }
        }
    });
}

// ====== Auto-resize Textarea ======
function autoResizeTextarea() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
}

// ====== Toggle Sidebar (Mobile) ======
function toggleSidebar() {
    sidebar.classList.toggle('open');
    if (sidebar.classList.contains('open')) {
        addOverlay();
    } else {
        removeOverlay();
    }
}

function addOverlay() {
    let overlay = document.querySelector('.sidebar-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay active';
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            removeOverlay();
        });
        document.body.appendChild(overlay);
    } else {
        overlay.classList.add('active');
    }
}

function removeOverlay() {
    const overlay = document.querySelector('.sidebar-overlay');
    if (overlay) overlay.classList.remove('active');
}

// ====== Send Message ======
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isLoading) return;

    // Hide welcome screen
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }

    // Show user message
    appendMessage('user', text);

    // Clear input
    messageInput.value = '';
    charCount.textContent = '0';
    autoResizeTextarea();

    // Show typing indicator
    const typingId = showTypingIndicator();

    // Disable input
    isLoading = true;
    sendBtn.disabled = true;
    responseTime.textContent = '⏳ Đang xử lý...';

    try {
        const startTime = Date.now();

        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, mode: currentMode })
        });

        const data = await res.json();
        const elapsed = Date.now() - startTime;

        // Remove typing indicator
        removeTypingIndicator(typingId);

        if (data.error) {
            appendMessage('bot', `⚠️ Lỗi: ${data.error}`, elapsed);
        } else {
            const modeLabel = data.mode === 'chatbot' ? '🤖 Chatbot' : '🧠 Agent';
            appendMessage('bot', data.answer, data.elapsed_ms || elapsed, modeLabel);
        }

        responseTime.textContent = `⚡ ${(data.elapsed_ms || elapsed).toLocaleString()}ms`;

        // Update stats
        updateStats();

    } catch (err) {
        removeTypingIndicator(typingId);
        appendMessage('bot', `❌ Không thể kết nối tới server: ${err.message}`);
        responseTime.textContent = '❌ Lỗi kết nối';
    } finally {
        isLoading = false;
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

// ====== Append Message ======
function appendMessage(role, text, elapsedMs, modeLabel) {
    messageCount++;
    const msg = document.createElement('div');
    msg.className = `message ${role}`;
    msg.id = `msg-${messageCount}`;

    const avatar = role === 'bot' ? '🏠' : '👤';
    const formattedText = role === 'bot' ? formatBotMessage(text) : escapeHtml(text);

    const timeStr = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
    const metaExtra = elapsedMs ? ` • ${(elapsedMs / 1000).toFixed(1)}s` : '';
    const modeBadge = modeLabel ? ` • ${modeLabel}` : '';

    msg.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div>
            <div class="message-content">${formattedText}</div>
            <div class="message-meta">
                <span>${timeStr}${metaExtra}${modeBadge}</span>
            </div>
        </div>
    `;

    messagesDiv.appendChild(msg);
    scrollToBottom();
}

// ====== Format Bot Message ======
function formatBotMessage(text) {
    if (!text) return '';

    // Pre-process: merge lines that have broken **bold** across line breaks
    // e.g. "**Căn 3PN\n**" → "**Căn 3PN**"
    text = text.replace(/\*\*([^*]*?)\n\*\*/g, '**$1**');
    text = text.replace(/\*\*\n([^*]*?)\*\*/g, '**$1**');

    // Split into lines for processing
    const lines = text.split('\n');
    let html = '';
    let cardFields = [];
    let sectionCounter = 0;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) {
            if (cardFields.length > 0) {
                html += buildPropertyCard(cardFields);
                cardFields = [];
            }
            continue;
        }

        // === SECTION HEADERS ===
        // Pattern: "1. Căn hộ 2 Phòng Ngủ (2PN):" or "**Căn 3 Phòng Ngủ (3PN)**"
        const sectionMatch = line.match(/^(\d+)\.\s+(.+?):\s*$/)
            || line.match(/^(\d+)\.\s+\*\*(.+?)\*\*\s*$/)
            || line.match(/^#{1,3}\s+(.+)$/);
        
        if (sectionMatch) {
            if (cardFields.length > 0) {
                html += buildPropertyCard(cardFields);
                cardFields = [];
            }
            const num = sectionMatch[1] || (++sectionCounter);
            const title = sectionMatch[2] || sectionMatch[1];
            html += `<div class="bot-section-header"><span class="section-num">${num}</span>${escapeHtml(title)}</div>`;
            continue;
        }

        // Bold-only lines as sub-headers: "**Căn 2 Phòng Ngủ (2PN)**"
        const boldHeaderMatch = line.match(/^\*\*(.+?)\*\*\s*$/);
        if (boldHeaderMatch) {
            if (cardFields.length > 0) {
                html += buildPropertyCard(cardFields);
                cardFields = [];
            }
            sectionCounter++;
            html += `<div class="bot-section-header"><span class="section-num">${sectionCounter}</span>${escapeHtml(boldHeaderMatch[1])}</div>`;
            continue;
        }

        // === PROPERTY FIELDS: "* Mã căn: ..." or "- Mã căn: ..." ===
        const fieldMatch = line.match(/^[\*\-•]\s+(.+?):\s*(.+)$/);
        if (fieldMatch) {
            const key = fieldMatch[1].trim();
            const val = fieldMatch[2].trim();
            if (key === 'Mã căn' && cardFields.length > 0) {
                html += buildPropertyCard(cardFields);
                cardFields = [];
            }
            cardFields.push({ key, val });
            continue;
        }

        // === NUMBERED LIST ITEMS: "1. **Mã căn ZR11606**..." ===
        const numberedMatch = line.match(/^(\d+)\.\s+\*\*(.+?)\*\*[:\s]*(.*)$/);
        if (numberedMatch) {
            if (cardFields.length > 0) {
                html += buildPropertyCard(cardFields);
                cardFields = [];
            }
            cardFields.push({ key: 'Mã căn', val: numberedMatch[2] });
            if (numberedMatch[3]) {
                // Try to parse remaining as "Diện tích: 40.9m², Giá: 3.2 tỷ..."
                const subFields = numberedMatch[3].split(/[,;|]/).map(s => s.trim()).filter(Boolean);
                for (const sf of subFields) {
                    const sfMatch = sf.match(/^(.+?):\s*(.+)$/);
                    if (sfMatch) {
                        cardFields.push({ key: sfMatch[1].trim(), val: sfMatch[2].trim() });
                    }
                }
            }
            continue;
        }

        // === STAT LINES: "Giá trung bình: 4.5 tỷ VND" (short key: value lines only) ===
        // Only match lines shorter than 80 chars to avoid grabbing paragraphs
        if (line.length < 80 && !line.startsWith('*') && !line.startsWith('-')) {
            const statMatch = line.match(/^([^:]{3,30}):\s*\*?\*?([\d.,]+\s*(?:tỷ|triệu)(?:\/m²)?(?:\s*VND)?)\*?\*?\s*\.?$/i)
                || line.match(/^([^:]{3,30})\s+(?:là|khoảng)\s+\*?\*?([\d.,]+\s*(?:tỷ|triệu)(?:\/m²)?(?:\s*VND)?)\*?\*?\s*\.?$/i);
            if (statMatch) {
                if (cardFields.length > 0) {
                    html += buildPropertyCard(cardFields);
                    cardFields = [];
                }
                const label = statMatch[1].replace(/\*\*/g, '').trim();
                const value = statMatch[2].replace(/\*\*/g, '').trim();
                html += `<div class="stat-line"><span class="stat-line-label">${escapeHtml(label)}</span><span class="stat-line-value">${escapeHtml(value)}</span></div>`;
                continue;
            }
        }

        // === INTRO LINES ===
        if (line.startsWith('Ví dụ') || line.startsWith('Dưới đây') || line.startsWith('*Lưu ý')) {
            if (cardFields.length > 0) {
                html += buildPropertyCard(cardFields);
                cardFields = [];
            }
            const cleanNote = line.replace(/^\*/, '').replace(/\*$/, '').trim();
            html += `<div class="bot-subtext">${escapeHtml(cleanNote)}</div>`;
            continue;
        }

        // === FLUSH PENDING CARD ===
        if (cardFields.length > 0) {
            html += buildPropertyCard(cardFields);
            cardFields = [];
        }

        // === NORMAL TEXT LINE ===
        let formatted = escapeHtml(line);

        // Bold: **text**
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Highlight prices: "4.8 tỷ" or "79 triệu/m²"
        formatted = formatted.replace(
            /(\d[\d.,]*)\s*(tỷ|triệu)(\/m²)?(\s*VND)?/gi,
            '<span class="price-highlight">$1 $2$3$4</span>'
        );

        // Highlight property IDs: (ID: X0435Q)
        formatted = formatted.replace(
            /\(ID:\s*([A-Z0-9]+)\)/g,
            '<span class="id-badge">$1</span>'
        );

        html += `<p class="bot-paragraph">${formatted}</p>`;
    }

    // Flush remaining card
    if (cardFields.length > 0) {
        html += buildPropertyCard(cardFields);
    }

    return html;
}

// ====== Build Property Card ======
function buildPropertyCard(fields) {
    if (!fields || fields.length === 0) return '';

    let cardId = '';
    let cardTitle = '';
    let price = '';
    let pricePerM2 = '';
    let area = '';
    let floor = '';
    let direction = '';
    let project = '';
    let type = '';
    let status = '';
    let otherFields = [];

    for (const f of fields) {
        const k = f.key.toLowerCase();
        if (k.includes('mã căn')) {
            // Extract ID from "ZR11606 (ID: X0435Q)"
            const idMatch = f.val.match(/\(ID:\s*([A-Z0-9]+)\)/i);
            cardId = idMatch ? idMatch[1] : '';
            cardTitle = f.val.replace(/\s*\(ID:.*?\)/, '').trim();
        } else if (k === 'giá' || k.includes('giá bán')) {
            // Parse price and price/m2 from "4.8 tỷ VND (79 triệu/m²)"
            const priceMatch = f.val.match(/([\d.,]+\s*tỷ)/i);
            const pm2Match = f.val.match(/\(([\d.,]+\s*triệu\/m²)\)/i);
            price = priceMatch ? priceMatch[1] : f.val;
            pricePerM2 = pm2Match ? pm2Match[1] : '';
        } else if (k.includes('diện tích')) {
            area = f.val;
        } else if (k.includes('tầng')) {
            // "Trung | Hướng: Tây Nam" combined
            const parts = f.val.split('|').map(p => p.trim());
            floor = parts[0] || f.val;
            if (parts[1]) {
                const dirMatch = parts[1].match(/Hướng:\s*(.+)/i);
                direction = dirMatch ? dirMatch[1].trim() : parts[1];
            }
        } else if (k.includes('hướng')) {
            direction = f.val;
        } else if (k.includes('dự án') || k.includes('phân khu')) {
            project = f.val;
        } else if (k.includes('loại')) {
            type = f.val;
        } else if (k.includes('trạng thái')) {
            status = f.val;
        } else {
            otherFields.push(f);
        }
    }

    // Build the card
    let statusClass = 'status-available';
    const statusLower = status.toLowerCase();
    if (statusLower.includes('đã bán')) statusClass = 'status-sold';
    else if (statusLower.includes('tạm dừng')) statusClass = 'status-paused';

    let html = `<div class="property-card">`;
    html += `<div class="prop-card-header">`;
    html += `<div class="prop-card-title">`;
    if (cardId) html += `<span class="prop-id">${escapeHtml(cardId)}</span>`;
    html += `<span class="prop-code">${escapeHtml(cardTitle)}</span>`;
    html += `</div>`;
    if (status) html += `<span class="prop-status ${statusClass}">${escapeHtml(status)}</span>`;
    html += `</div>`;

    // Info grid
    html += `<div class="prop-card-grid">`;
    if (project) html += `<div class="prop-field"><span class="prop-label">🏢 Dự án</span><span class="prop-value">${escapeHtml(project)}</span></div>`;
    if (type) html += `<div class="prop-field"><span class="prop-label">🏠 Loại</span><span class="prop-value">${escapeHtml(type)}</span></div>`;
    if (area) html += `<div class="prop-field"><span class="prop-label">📐 Diện tích</span><span class="prop-value">${escapeHtml(area)}</span></div>`;
    if (floor) html += `<div class="prop-field"><span class="prop-label">🏗️ Tầng</span><span class="prop-value">${escapeHtml(floor)}</span></div>`;
    if (direction) html += `<div class="prop-field"><span class="prop-label">🧭 Hướng</span><span class="prop-value">${escapeHtml(direction)}</span></div>`;

    // Other fields
    for (const f of otherFields) {
        html += `<div class="prop-field"><span class="prop-label">${escapeHtml(f.key)}</span><span class="prop-value">${escapeHtml(f.val)}</span></div>`;
    }
    html += `</div>`;

    // Price bar
    if (price) {
        html += `<div class="prop-price-bar">`;
        html += `<span class="prop-price">${escapeHtml(price)} VND</span>`;
        if (pricePerM2) html += `<span class="prop-price-m2">${escapeHtml(pricePerM2)}</span>`;
        html += `</div>`;
    }

    html += `</div>`;
    return html;
}

// ====== Escape HTML ======
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ====== Typing Indicator ======
function showTypingIndicator() {
    messageCount++;
    const id = `typing-${messageCount}`;
    const msg = document.createElement('div');
    msg.className = 'message bot';
    msg.id = id;
    msg.innerHTML = `
        <div class="message-avatar">🏠</div>
        <div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
    `;
    messagesDiv.appendChild(msg);
    scrollToBottom();
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ====== Scroll to Bottom ======
function scrollToBottom() {
    requestAnimationFrame(() => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    });
}

// ====== Clear Chat ======
function clearChat() {
    messagesDiv.innerHTML = '';
    messageCount = 0;
    responseTime.textContent = '';
    if (welcomeScreen) {
        welcomeScreen.style.display = 'flex';
    }
}

// ====== Load Suggestions ======
async function loadSuggestions() {
    try {
        const res = await fetch('/api/suggestions');
        const data = await res.json();

        suggestionsContainer.innerHTML = '';
        (data.suggestions || []).forEach(text => {
            const btn = document.createElement('button');
            btn.className = 'suggestion-btn';
            btn.textContent = text;
            btn.addEventListener('click', () => {
                messageInput.value = text;
                charCount.textContent = text.length;
                sendMessage();
                // Close sidebar on mobile
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('open');
                    removeOverlay();
                }
            });
            suggestionsContainer.appendChild(btn);
        });
    } catch (err) {
        console.warn('Could not load suggestions:', err);
    }
}

// ====== Update Stats ======
async function updateStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        statRequests.textContent = data.total_requests || 0;
        statTokens.textContent = formatNumber(data.total_tokens || 0);
        statLatency.textContent = `${(data.avg_latency_ms || 0).toLocaleString()}ms`;
        statCost.textContent = `$${(data.total_cost_usd || 0).toFixed(4)}`;

        if (data.model) {
            modelName.textContent = data.model;
        }
    } catch (err) {
        console.warn('Could not update stats:', err);
    }
}

// ====== Format Number ======
function formatNumber(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
}

// ====== Mode Toggle (Agent vs Chatbot) ======
function setupModeToggle() {
    const modeAgent = document.getElementById('modeAgent');
    const modeChatbot = document.getElementById('modeChatbot');

    if (!modeAgent || !modeChatbot) return;

    modeAgent.addEventListener('click', () => {
        currentMode = 'agent';
        modeAgent.classList.add('active');
        modeChatbot.classList.remove('active');
        messageInput.placeholder = 'Hỏi về căn hộ Vinhomes Ocean Park...';
    });

    modeChatbot.addEventListener('click', () => {
        currentMode = 'chatbot';
        modeChatbot.classList.add('active');
        modeAgent.classList.remove('active');
        messageInput.placeholder = '💬 Chế độ Chatbot (không dùng tools)...';
    });
}
