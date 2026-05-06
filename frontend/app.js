/**
 * RupeezyVoice — Frontend App
 * Handles chat, voice (Web Speech API), and lead management.
 */

const API = '';  // Same origin

let currentLeadId = null;
let conversationActive = false;
let recognition = null;
let synthesis = window.speechSynthesis;
let isRecording = false;
let ttsEnabled = true;

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    loadLeads();
    initSpeechRecognition();
});

function escapeHtml(str) {
    return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// --- Lead Management ---

async function addLead() {
    const name = document.getElementById('leadName').value.trim();
    const phone = document.getElementById('leadPhone').value.trim();
    const language = document.getElementById('leadLanguage').value;

    if (!name || !phone) {
        alert('Please enter name and phone');
        return;
    }

    const res = await fetch(`${API}/api/leads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, phone, language, source: 'manual' })
    });

    if (res.ok) {
        document.getElementById('leadName').value = '';
        document.getElementById('leadPhone').value = '';
        loadLeads();
    }
}

async function uploadCSV() {
    const csvText = document.getElementById('csvInput').value.trim();
    if (!csvText) {
        alert('Paste CSV data first');
        return;
    }

    const res = await fetch(`${API}/api/leads/csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ csv_text: csvText })
    });

    if (res.ok) {
        const data = await res.json();
        document.getElementById('csvInput').value = '';
        alert(`✅ ${data.count} leads uploaded!`);
        loadLeads();
    } else {
        alert('Error uploading CSV. Check format: name,phone,language');
    }
}

async function sendWhatsApp(leadId) {
    const res = await fetch(`${API}/api/whatsapp/send/${leadId}`, { method: 'POST' });
    if (res.ok) {
        const data = await res.json();
        // Open real wa.me link in new tab
        window.open(data.wa_url, '_blank');
    }
}

async function loadLeads() {
    const res = await fetch(`${API}/api/leads`);
    const data = await res.json();
    
    const container = document.getElementById('leadsList');
    container.innerHTML = '';

    data.leads.forEach(lead => {
        const el = document.createElement('div');
        el.className = `lead-item ${lead.id === currentLeadId ? 'active' : ''}`;
        const canCall = lead.status !== 'converted';
        const btnLabel = lead.status === 'in_progress' ? '▶ Resume' : 
                         lead.status === 'new' ? '📞 Start Call' : '🔄 Call Again';
        const showWhatsApp = lead.status !== 'new';
        el.innerHTML = `
            <div class="lead-name">${lead.name}</div>
            <div class="lead-meta">
                <span>📱 ${lead.phone}</span>
                <span class="status-badge ${lead.status}">${lead.status}</span>
                ${lead.score > 0 ? `<span>${lead.score}/100</span>` : ''}
            </div>
            <div style="display:flex; gap:6px; margin-top:8px;">
                ${canCall ? 
                    `<button class="start-btn" onclick="startCall(${lead.id}, '${escapeHtml(lead.name)}', '${lead.language}')">
                        ${btnLabel}
                    </button>` : ''
                }
                ${showWhatsApp ?
                    `<button class="start-btn" style="background:#25D366;" onclick="sendWhatsApp(${lead.id})">
                        💬 WhatsApp
                    </button>` : ''
                }
            </div>
        `;
        el.addEventListener('click', (e) => {
            if (e.target.tagName !== 'BUTTON') selectLead(lead);
        });
        container.appendChild(el);
    });
}

function selectLead(lead) {
    currentLeadId = lead.id;
    document.getElementById('chatLeadName').textContent = lead.name;
    document.getElementById('chatStatus').textContent = lead.status;
    document.getElementById('chatStatus').className = `status-badge ${lead.status}`;
    document.getElementById('langBadge').textContent = lead.language;
    loadLeads(); // refresh active state
}

// --- Conversation ---

async function startCall(leadId, leadName, language) {
    currentLeadId = leadId;
    conversationActive = true;

    // Update STT language for this lead
    updateRecognitionLanguage(language);

    // Update UI
    document.getElementById('chatLeadName').textContent = leadName;
    document.getElementById('chatStatus').textContent = 'in_progress';
    document.getElementById('chatStatus').className = 'status-badge in_progress';
    document.getElementById('langBadge').textContent = language;
    document.getElementById('endCallBtn').disabled = false;
    document.getElementById('messageInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('voiceBtn').disabled = false;

    // Clear messages
    const container = document.getElementById('messagesContainer');
    container.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';

    // Start conversation
    const res = await fetch(`${API}/api/conversation/start/${leadId}`, { method: 'POST' });
    const data = await res.json();

    container.innerHTML = '';
    
    if (data.messages) {
        data.messages.forEach(msg => addMessageToUI(msg.role, msg.content));
        // Speak the opening
        if (data.messages.length > 0 && ttsEnabled) {
            speak(data.messages[0].content, language);
        }
    }

    loadLeads();
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    if (!currentLeadId || !conversationActive) {
        document.getElementById('voiceStatus').textContent = 'Start a call first!';
        return;
    }

    input.value = '';
    addMessageToUI('user', message);
    showTyping();

    const res = await fetch(`${API}/api/conversation/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_id: currentLeadId, message })
    });

    hideTyping();

    if (res.ok) {
        const data = await res.json();
        addMessageToUI('assistant', data.reply);

        // Update language badge
        if (data.language_detected) {
            document.getElementById('langBadge').textContent = data.language_detected;
        }

        // Speak response
        if (ttsEnabled) {
            speak(data.reply, data.language_detected || 'english');
        }

        // Suggest ending call if hot signal detected
        if (data.suggest_end && !data.is_ended) {
            showEndSuggestion();
        }

        // If ended
        if (data.is_ended) {
            endCallUI();
            await showSummary();
        }
    }
}

async function endCall() {
    if (!currentLeadId) return;
    
    const res = await fetch(`${API}/api/conversation/end/${currentLeadId}`, { method: 'POST' });
    
    if (res.ok) {
        const data = await res.json();
        endCallUI();
        displaySummary(data);
    }
    
    loadLeads();
}

function endCallUI() {
    conversationActive = false;
    document.getElementById('endCallBtn').disabled = true;
    document.getElementById('messageInput').disabled = true;
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('voiceBtn').disabled = true;
    
    addMessageToUI('system', '📞 Call ended. Summary generated.');
}

async function showSummary() {
    const res = await fetch(`${API}/api/conversation/end/${currentLeadId}`, { method: 'POST' });
    if (res.ok) {
        const data = await res.json();
        displaySummary(data);
    }
}

function displaySummary(data) {
    const panel = document.getElementById('summaryPanel');
    const content = document.getElementById('summaryContent');
    const s = data.summary;
    
    content.innerHTML = `
        <div class="summary-item">
            <div class="summary-label">Status</div>
            <strong class="status-badge ${s.interest_score}">${s.interest_score.toUpperCase()}</strong>
            <span> — Score: ${s.score_numeric}/100</span>
        </div>
        <div class="summary-item">
            <div class="summary-label">Duration</div>
            ${Math.floor(s.duration_seconds / 60)}m ${s.duration_seconds % 60}s • ${s.messages_count} messages
        </div>
        <div class="summary-item">
            <div class="summary-label">Language</div>
            ${s.language_used}
        </div>
        <div class="summary-item">
            <div class="summary-label">Objections Raised</div>
            ${s.objections_raised.length > 0 ? s.objections_raised.join(', ') : 'None'}
        </div>
        <div class="summary-item">
            <div class="summary-label">Topics Covered</div>
            ${s.topics_covered.length > 0 ? s.topics_covered.join(', ') : '—'}
        </div>
        <div class="summary-item">
            <div class="summary-label">Recommended Action</div>
            ${s.recommended_action}
        </div>
        <div class="summary-item">
            <div class="summary-label">AI Summary</div>
            ${s.summary_text}
        </div>
        ${data.scoring_signals ? `
        <div class="summary-item">
            <div class="summary-label">Scoring Signals</div>
            <ul>${data.scoring_signals.map(s => `<li>${s}</li>`).join('')}</ul>
        </div>` : ''}
    `;
    
    panel.style.display = 'block';
}

function closeSummary() {
    document.getElementById('summaryPanel').style.display = 'none';
}

function showEndSuggestion() {
    // Don't show if already showing
    if (document.getElementById('endSuggestion')) return;
    
    const container = document.getElementById('messagesContainer');
    const el = document.createElement('div');
    el.id = 'endSuggestion';
    el.className = 'end-suggestion';
    el.innerHTML = `
        <span>🔥 Hot lead detected! End call to update dashboard?</span>
        <div>
            <button onclick="endCall(); this.parentElement.parentElement.remove();">✅ End & Save</button>
            <button onclick="this.parentElement.parentElement.remove();" style="background:#2f3336;">Continue</button>
        </div>
    `;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
}

// --- UI Helpers ---

function addMessageToUI(role, content) {
    const container = document.getElementById('messagesContainer');
    
    // Remove empty state
    const emptyState = container.querySelector('.empty-state');
    if (emptyState) emptyState.remove();
    
    const el = document.createElement('div');
    
    if (role === 'system') {
        el.className = 'message assistant';
        el.style.background = '#2f3336';
        el.style.fontStyle = 'italic';
    } else {
        el.className = `message ${role}`;
    }
    
    const ttsBtn = (role === 'assistant') 
        ? `<button class="tts-btn" onclick="speakThis(this)" title="Listen">🔊</button>` 
        : '';
    
    el.innerHTML = `
        <div class="msg-content">${content}</div>
        <div class="msg-footer">
            <span class="msg-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}</span>
            ${ttsBtn}
        </div>
    `;
    
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
}

function speakThis(btn) {
    const msgContent = btn.closest('.message').querySelector('.msg-content').textContent;
    if (!synthesis) return;
    synthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(msgContent);
    utterance.lang = LANG_CODES[currentLeadLanguage] || 'hi-IN';
    utterance.rate = 0.95;
    btn.textContent = '⏹️';
    utterance.onend = () => { btn.textContent = '🔊'; };
    utterance.onerror = () => { btn.textContent = '🔊'; };
    synthesis.speak(utterance);
}

function showTyping() {
    const container = document.getElementById('messagesContainer');
    const el = document.createElement('div');
    el.className = 'typing-indicator';
    el.id = 'typingIndicator';
    el.innerHTML = '<span></span><span></span><span></span>';
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
}

function hideTyping() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

function handleKeyPress(e) {
    if (e.key === 'Enter') sendMessage();
}

// --- Voice: Web Speech API ---

// Language to BCP-47 code mapping for Web Speech API
const LANG_CODES = {
    'english': 'en-IN',
    'hindi': 'hi-IN',
    'hinglish': 'hi-IN',
    'tamil': 'ta-IN',
    'telugu': 'te-IN',
    'marathi': 'mr-IN',
    'gujarati': 'gu-IN',
    'bengali': 'bn-IN'
};

let currentLeadLanguage = 'english';

function initSpeechRecognition() {
    // Just check browser support on load
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        document.getElementById('voiceBtn').title = 'Speech recognition not supported';
        document.getElementById('voiceBtn').disabled = true;
    }
}

function updateRecognitionLanguage(lang) {
    currentLeadLanguage = lang;
}

function toggleVoice() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

function startRecording() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    // Stop any ongoing TTS
    synthesis.cancel();
    
    // Create fresh instance every time
    recognition = new SpeechRecognition();
    recognition.lang = LANG_CODES[currentLeadLanguage] || 'hi-IN';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    let finalText = '';
    let silenceTimer = null;

    recognition.onresult = function(event) {
        let interim = '';
        finalText = '';
        for (let i = 0; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalText += event.results[i][0].transcript;
            } else {
                interim += event.results[i][0].transcript;
            }
        }
        document.getElementById('messageInput').value = finalText || interim;
        document.getElementById('voiceStatus').textContent = '🎤 Hearing you...';
        
        // Auto-stop after 2s of silence once we have a final result
        if (finalText) {
            clearTimeout(silenceTimer);
            silenceTimer = setTimeout(function() {
                try { recognition.stop(); } catch(e) {}
            }, 2000);
        }
    };

    recognition.onerror = function(event) {
        console.log('Mic event:', event.error);
        if (event.error === 'no-speech') {
            // Chrome kills session on no-speech — we'll restart in onend
            return;
        }
        if (event.error === 'aborted') return;
        isRecording = false;
        document.getElementById('voiceBtn').classList.remove('recording');
        document.getElementById('voiceStatus').textContent = 
            event.error === 'not-allowed' ? '❌ Allow mic in browser' :
            'Error: ' + event.error;
    };

    recognition.onend = function() {
        const text = document.getElementById('messageInput').value.trim();
        if (text) {
            // We got speech — send it
            isRecording = false;
            document.getElementById('voiceBtn').classList.remove('recording');
            document.getElementById('voiceStatus').textContent = '';
            setTimeout(function() { sendMessage(); }, 100);
        } else if (isRecording) {
            // No speech yet but user hasn't stopped — restart listening
            document.getElementById('voiceStatus').textContent = '🎤 Speak now...';
            setTimeout(function() {
                try { recognition.start(); } catch(e) {
                    console.error('Restart failed:', e);
                    isRecording = false;
                    document.getElementById('voiceBtn').classList.remove('recording');
                    document.getElementById('voiceStatus').textContent = '';
                }
            }, 300);
        } else {
            document.getElementById('voiceBtn').classList.remove('recording');
            document.getElementById('voiceStatus').textContent = '';
        }
    };

    // Start
    isRecording = true;
    document.getElementById('voiceBtn').classList.add('recording');
    document.getElementById('voiceStatus').textContent = '🎤 Speak now...';
    document.getElementById('messageInput').value = '';
    recognition.start();
}

function stopRecording() {
    isRecording = false;
    document.getElementById('voiceBtn').classList.remove('recording');
    document.getElementById('voiceStatus').textContent = '';
    if (recognition) {
        try { recognition.stop(); } catch(e) {}
    }
}

function speak(text, language) {
    if (!synthesis) return;
    synthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = LANG_CODES[language] || 'en-IN';
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    
    synthesis.speak(utterance);
}
