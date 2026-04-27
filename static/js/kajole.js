/* ─────────────────────────────────────────────
   KAJOLE — Frontend JavaScript
   State machine, API calls, UI rendering
   ───────────────────────────────────────────── */

'use strict';

// ─── STATE ───
const STATE = {
  currentScreen: 'landing',
  currentView: 'today',
  user: null,
  todayMatch: null,
  aiLastCandidateId: null,
  conversations: {},
  activeConvId: null,
  deepsykeAnswers: {},
};

// ─── API BASE ───
const API = '/api';

// ═══════════════════════════════════════════
// SCREEN MANAGEMENT
// ═══════════════════════════════════════════
function showScreen(name, tab) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const screen = document.getElementById(`screen-${name}`);
  if (screen) screen.classList.add('active');
  STATE.currentScreen = name;

  if (name === 'auth' && tab) {
    switchAuthTab(tab);
  }
  if (name === 'app') {
    initApp();
  }
}

function switchAuthTab(tab) {
  document.getElementById('form-login').classList.toggle('hidden', tab !== 'login');
  document.getElementById('form-register').classList.toggle('hidden', tab !== 'register');
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-register').classList.toggle('active', tab === 'register');
}

// ═══════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════
function showLoading(text = 'One moment...') {
  document.getElementById('loading-overlay').classList.remove('hidden');
  document.getElementById('loading-text').textContent = text;
}

function hideLoading() {
  document.getElementById('loading-overlay').classList.add('hidden');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  const icons = { success: '✓', error: '✕', info: '✦' };
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || '✦'}</span> ${message}`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function showModal(title, body, actions = []) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = body;
  const actionsEl = document.getElementById('modal-actions');
  actionsEl.innerHTML = '';
  actions.forEach(a => {
    const btn = document.createElement('button');
    btn.className = `btn ${a.class || 'btn-ghost'}`;
    btn.textContent = a.label;
    if (typeof a.onclick === 'string') {
      btn.setAttribute('onclick', a.onclick);
    } else {
      btn.onclick = () => {
        closeModal();
        if (a.action) a.action();
      };
    }
    actionsEl.appendChild(btn);
  });
  document.getElementById('modal-overlay').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

// Close modal on backdrop click
document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
});

async function apiCall(endpoint, method = 'GET', data = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin'
  };
  if (data) opts.body = JSON.stringify(data);
  try {
    const resp = await fetch(`${API}${endpoint}`, opts);
    return await resp.json();
  } catch (err) {
    console.error('API error:', err);
    return { error: 'Network error' };
  }
}

function getInitials(name) {
  if (!name) return '?';
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' }).toUpperCase();
}

function todayDisplay() {
  return new Date().toLocaleDateString('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long'
  }).toUpperCase();
}

// ═══════════════════════════════════════════
// AUTH
// ═══════════════════════════════════════════
async function doLogin() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');

  if (!email || !password) {
    errEl.textContent = 'Please fill in all fields';
    errEl.classList.add('show');
    return;
  }

  showLoading('Signing you in...');
  const result = await apiCall('/auth/login', 'POST', { email, password });
  hideLoading();

  if (result.error) {
    errEl.textContent = result.error;
    errEl.classList.add('show');
    return;
  }

  errEl.classList.remove('show');
  STATE.user = result;

  if (!result.profile_complete) {
    showScreen('onboard');
    goOnboardStep(result.onboarding_step || 1);
  } else {
    showScreen('app');
  }
}

async function doRegister() {
  const name = document.getElementById('reg-name').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const errEl = document.getElementById('reg-error');

  if (!name || !email || !password) {
    errEl.textContent = 'Please fill in all fields';
    errEl.classList.add('show');
    return;
  }

  showLoading('Creating your account...');
  const result = await apiCall('/auth/register', 'POST', { name, email, password });
  hideLoading();

  if (result.error) {
    errEl.textContent = result.error;
    errEl.classList.add('show');
    return;
  }

  // Clear all old state and set fresh user
  STATE.user = null;
  STATE.currentMatch = null;
  STATE.profilePhotos = [];
  // Small delay to ensure cookie is set
  await new Promise(r => setTimeout(r, 100));
  // Fetch fresh user state from server
  const meResult = await apiCall('/auth/me');
  if (meResult.authenticated) {
    STATE.user = meResult.user;
  }
  showScreen('onboard');
  goOnboardStep(1);
}

// ═══════════════════════════════════════════
// ONBOARDING — STEP NAVIGATION
// ═══════════════════════════════════════════
function goOnboardStep(step) {
  // Hide all steps
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById(`onboard-step-${i}`);
    if (el) el.classList.add('hidden');
  }

  // Show target step
  const target = document.getElementById(`onboard-step-${step}`);
  if (target) target.classList.remove('hidden');

  // Update sidebar
  for (let i = 1; i <= 3; i++) {
    const sideItem = document.getElementById(`sidebar-step-${i}`);
    const dot = document.getElementById(`dot-${i}`);
    if (!sideItem) continue;
    sideItem.classList.remove('active', 'completed');
    if (i < step) {
      sideItem.classList.add('completed');
      dot.textContent = '✓';
    } else if (i === step) {
      sideItem.classList.add('active');
      dot.textContent = i;
    } else {
      dot.textContent = i;
    }
  }

  // Scroll to top of onboard main
  const main = document.getElementById('onboard-main');
  if (main) main.scrollTop = 0;
}

// Pre-populate onboarding form with existing user data
async function editProfile() {
  const result = await apiCall('/profile/me');
  if (result.error) {
    showScreen('onboard');
    goOnboardStep(1);
    return;
  }
  
  const u = result;
  
  // Populate Step 1 fields
  const setName = document.getElementById('s1-name');
  const setAge = document.getElementById('s1-age');
  const setDob = document.getElementById('s1-dob');
  const setGender = document.getElementById('s1-gender');
  const setCity = document.getElementById('s1-city');
  const setCountry = document.getElementById('s1-country');
  const setProfession = document.getElementById('s1-profession');
  const setEducation = document.getElementById('s1-education');
  const setBio = document.getElementById('s1-bio');
  const setReligion = document.getElementById('s1-religion');
  const setEthnicity = document.getElementById('s1-ethnicity');
  const setAttract = document.getElementById('s1-attract');
  const setIntel = document.getElementById('s1-intel');
  
  if (setName) setName.value = u.name || '';
  if (setAge) setAge.value = u.age || '';
  if (setDob) setDob.value = u.dob || '';
  if (setGender) setGender.value = u.gender || '';
  if (setCity) setCity.value = u.city || '';
  if (setCountry) setCountry.value = u.country || '';
  if (setProfession) setProfession.value = u.profession || '';
  if (setEducation) setEducation.value = u.education || '';
  if (setBio) setBio.value = u.bio || '';
  if (setReligion) setReligion.value = u.religion || '';
  if (setEthnicity) setEthnicity.value = u.ethnicity || '';
  if (setAttract) setAttract.value = u.attractiveness_self || 5;
  if (setIntel) setIntel.value = u.intellectual_self || 5;
  
  // Set orientation radio
  if (u.orientation) {
    const orientRadio = document.querySelector(`input[name="orientation"][value="${u.orientation}"]`);
    if (orientRadio) orientRadio.checked = true;
  }
  
  // Set social style radio
  if (u.social_style) {
    const socialRadio = document.querySelector(`input[name="social"][value="${u.social_style}"]`);
    if (socialRadio) socialRadio.checked = true;
  }
  
  // Set lifestyle checkboxes
  if (u.lifestyle && Array.isArray(u.lifestyle)) {
    u.lifestyle.forEach(val => {
      const cb = document.querySelector(`input[name="lifestyle"][value="${val}"]`);
      if (cb) cb.checked = true;
    });
  }
  
  // Populate Step 2 - Dealbreakers
  const dealbreakers = u.dealbreakers || [];
  dealbreakers.forEach(val => {
    const cb = document.querySelector(`input[name="dealbreaker"][value="${val}"]`);
    if (cb) cb.checked = true;
  });
  
  // Populate Step 2 - Importance sliders
  const importance = u.importance || {};
  ['distance', 'age_gap', 'religion', 'ethnicity'].forEach(key => {
    const slider = document.getElementById(`imp-${key}`);
    if (slider && importance[key] !== undefined) {
      slider.value = importance[key];
    }
  });
  
  // Load existing photos
  const photos = u.photos || [];
  if (photos.length > 0) {
    loadUserPhotos(photos);
  }
  
  // Show onboarding
  showScreen('onboard');
  goOnboardStep(1);
}

// ─── STEP 1 SUBMIT ───
async function submitStep1() {
  const name = document.getElementById('s1-name').value.trim();
  const age = document.getElementById('s1-age').value;
  const dob = document.getElementById('s1-dob').value;
  const gender = document.getElementById('s1-gender').value;
  const city = document.getElementById('s1-city').value.trim();
  const country = document.getElementById('s1-country').value.trim();
  const orientation = document.querySelector('input[name="orientation"]:checked')?.value;

  if (!name || !age || !dob || !gender || !city || !country || !orientation) {
    showToast('Please fill in all required fields', 'error');
    return;
  }

  const lifestyle = [...document.querySelectorAll('input[name="lifestyle"]:checked')].map(i => i.value);
  const social_style = document.querySelector('input[name="social"]:checked')?.value || 'ambivert';

  const data = {
    name, age: parseInt(age), dob, gender, city, country, orientation,
    profession: document.getElementById('s1-profession').value.trim(),
    education: document.getElementById('s1-education').value.trim(),
    bio: document.getElementById('s1-bio').value.trim(),
    religion: document.getElementById('s1-religion').value,
    ethnicity: document.getElementById('s1-ethnicity').value,
    lifestyle, social_style,
    attractiveness_self: document.getElementById('s1-attract').value,
    intellectual_self: document.getElementById('s1-intel').value,
  };

  showLoading('Saving your story...');
  const result = await apiCall('/profile/step1', 'POST', data);
  hideLoading();

  if (result.error) {
    showToast(result.error, 'error');
    return;
  }

  goOnboardStep(2);
}

// ─── STEP 2 SUBMIT ───
async function submitStep2() {
  const ageMin = document.getElementById('s2-age-min').value;
  const ageMax = document.getElementById('s2-age-max').value;
  const locPref = document.querySelector('input[name="loc-pref"]:checked')?.value || 'worldwide';
  const dealbreakers = [...document.querySelectorAll('input[name="dealbreaker"]:checked')].map(i => i.value);

  const data = {
    age_min: parseInt(ageMin),
    age_max: parseInt(ageMax),
    location_preference: locPref,
    religion: document.getElementById('s2-religion').value,
    ethnicity: document.getElementById('s2-ethnicity').value,
    attractiveness_min: parseInt(document.getElementById('s2-attract').value),
    partner_description: document.getElementById('s2-partner').value.trim(),
    dealbreakers
  };

  showLoading('Noting your preferences...');
  const result = await apiCall('/profile/step2', 'POST', data);
  hideLoading();

  if (result.error) {
    showToast(result.error, 'error');
    return;
  }

  goOnboardStep(3);
}

// ─── DEEPSYKE SCALE SELECTION ───
function selectScale(qName, value, el) {
  // Deselect others in same question
  el.closest('.deepsyke-scale').querySelectorAll('.scale-option').forEach(opt => {
    opt.classList.remove('selected');
  });
  el.classList.add('selected');
  STATE.deepsykeAnswers[qName] = value;
}

// ─── STEP 3 SUBMIT ───
async function submitStep3() {
  // Validate all 5 questions answered
  for (let i = 1; i <= 5; i++) {
    if (!STATE.deepsykeAnswers[`q${i}`]) {
      showToast(`Please answer question ${i}`, 'error');
      document.getElementById(`dq-${i}`).scrollIntoView({ behavior: 'smooth' });
      return;
    }
  }

  // Map answers to LOI indicators
  const ans = STATE.deepsykeAnswers;
  const data = {
    peace_with_self: parseInt(ans.q5),
    authenticity: parseInt(ans.q3),
    internal_validation: parseInt(ans.q3),
    relationship_stability: parseInt(ans.q4),
    decision_comfort: parseInt(ans.q1),
  };

  showLoading('Calculating your Deepsyke blueprint...');
  const result = await apiCall('/profile/step3', 'POST', data);
  hideLoading();

  if (result.error) {
    showToast(result.error, 'error');
    return;
  }

  // Show archetype reveal
  goOnboardStep(4);
  renderArchetypeReveal(result);
}

// ─── ARCHETYPE REVEAL ───
function renderArchetypeReveal(data) {
  const archetype = data.archetype || {};
  const typeName = data.natal_type || 'SD';
  const loi = data.loi_score || 50;

  const archetypeEmojis = {
    Magician: '✦', Mystic: '🌙', Knight: '⚔️', Maiden: '🌸',
    Warrior: '🔥', Queen: '👑', King: '♛', Huntress: '🏹'
  };

  const emoji = archetypeEmojis[archetype.name] || '✦';
  const bgColors = {
    SS: 'rgba(107,127,212,0.15)', SD: 'rgba(74,155,111,0.15)',
    DS: 'rgba(212,132,74,0.15)', DD: 'rgba(212,74,74,0.15)'
  };

  const loiLabel = loi >= 70 ? 'Highly Aligned' : loi >= 50 ? 'In Alignment' : 'Seeking Growth';

  const content = document.getElementById('archetype-reveal-content');
  content.innerHTML = `
    <div class="archetype-symbol" style="background: ${bgColors[typeName] || 'rgba(200,169,110,0.1)'};">
      ${emoji}
    </div>
    <div class="archetype-title">Your Deepsyke Blueprint</div>
    <div class="archetype-name">${archetype.title || 'The Guide'}</div>
    <p class="archetype-essence">"${archetype.essence || 'A unique force of nature'}"</p>
    <p class="archetype-desc">${archetype.description || ''}</p>

    <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;margin-bottom:2rem;">
      <div class="badge badge-gold">⚡ ${archetype.energy || 'Balanced'} Energy</div>
      <div class="badge badge-purple">🌊 ${archetype.element || 'Earth'} Element</div>
      <div class="badge badge-green" id="loi-badge">◉ ${loiLabel}</div>
    </div>

    <div style="max-width:300px;margin:0 auto 2rem;">
      <div class="loi-bar-wrap">
        <div class="loi-label">
          <span>Alignment (LOI)</span>
          <span style="color:var(--accent);">${loi}/100</span>
        </div>
        <div class="loi-bar">
          <div class="loi-fill" id="loi-fill-anim" style="width:0%"></div>
        </div>
      </div>
    </div>

    <p style="font-size:0.82rem;color:var(--text3);margin-bottom:2rem;max-width:400px;margin-left:auto;margin-right:auto;">
      Your first match arrives in your inbox tomorrow morning.
      No searching. No swiping. Just one perfectly calculated person —
      chosen by your psychology.
    </p>

    <button class="btn btn-primary btn-lg" onclick="enterApp()">
      ✦ Enter Kajole
    </button>
  `;

  // Animate LOI bar
  setTimeout(() => {
    const fill = document.getElementById('loi-fill-anim');
    if (fill) fill.style.width = `${loi}%`;
  }, 500);
}

async function enterApp() {
  // After onboarding complete, do a full page reload to get clean state from server
  // This ensures the correct user session is loaded fresh
  showLoading('Setting up your profile...');
  await new Promise(r => setTimeout(r, 500));
  window.location.reload();
}

// ═══════════════════════════════════════════
// BIO HELPER
// ═══════════════════════════════════════════
function toggleBioHelper() {
  const area = document.getElementById('bio-helper-area');
  area.classList.toggle('hidden');
}

async function generateBio() {
  const name = document.getElementById('s1-name').value.trim();
  const profession = document.getElementById('s1-profession').value.trim();
  const interests = document.getElementById('bio-interests').value.trim();
  const personality = document.getElementById('bio-personality').value.trim();

  if (!interests) {
    showToast('Add at least your interests first', 'error');
    return;
  }

  showLoading('Writing your story...');
  const result = await apiCall('/bio/generate', 'POST', {
    name, profession, interests,
    personality_note: personality,
    looking_for: document.getElementById('s2-partner')?.value || ''
  });
  hideLoading();

  if (result.error) {
    showToast('Could not generate bio right now', 'error');
    return;
  }

  const container = document.getElementById('bio-options');
  container.innerHTML = '';
  container.classList.remove('hidden');
  container.style.display = 'flex';

  (result.bios || []).forEach((bio, i) => {
    const card = document.createElement('div');
    card.className = 'card';
    card.style.cursor = 'pointer';
    card.style.transition = 'border-color 0.2s';
    card.innerHTML = `
      <p style="font-size:0.85rem;color:var(--text2);line-height:1.75;font-style:italic;">"${bio}"</p>
      <button class="btn btn-sm btn-surface" style="margin-top:0.75rem;" onclick="useBio(this)">Use this bio</button>
    `;
    card.dataset.bio = bio;
    container.appendChild(card);
  });
}

function useBio(btn) {
  const bio = btn.closest('.card').dataset.bio;
  document.getElementById('s1-bio').value = bio;
  document.getElementById('bio-helper-area').classList.add('hidden');
  showToast('Bio applied! ✓', 'success');
}

// ═══════════════════════════════════════════
// MAIN APP INIT
// ═══════════════════════════════════════════
async function initApp() {
  // Load user data
  const meResult = await apiCall('/auth/me');
  if (meResult.authenticated) {
    STATE.user = meResult.user;
    updateSidebarUser();
  }

  // Set today's date
  const dateEl = document.getElementById('today-date');
  if (dateEl) dateEl.textContent = todayDisplay();

  // Load today's match
  loadTodayMatch();
}

function updateSidebarUser() {
  if (!STATE.user) return;
  const initials = getInitials(STATE.user.name);
  const avatarEl = document.getElementById('sidebar-avatar');
  if (avatarEl) avatarEl.textContent = initials;
}

function switchView(view) {
  document.querySelectorAll('.app-view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.sidebar-nav-item').forEach(n => n.classList.remove('active'));

  const viewEl = document.getElementById(`view-${view}`);
  const navEl = document.getElementById(`nav-${view}`);

  if (viewEl) viewEl.classList.add('active');
  if (navEl) navEl.classList.add('active');

  STATE.currentView = view;

  // Load view data
  if (view === 'inbox') loadInbox();
  if (view === 'history') loadHistory();
  if (view === 'profile') loadProfile();
}

// ═══════════════════════════════════════════
// TODAY'S MATCH
// ═══════════════════════════════════════════
async function loadTodayMatch() {
  const container = document.getElementById('match-content');

  const result = await apiCall('/match/today');

  if (result.error) {
    container.innerHTML = renderMatchError(result.error);
    return;
  }

  if (!result.has_match) {
    container.innerHTML = renderWaitingState(result);
    startCountdown();
    return;
  }

  STATE.todayMatch = result;
  const candidate = result.candidate;
  STATE.aiLastCandidateId = candidate?.id;

  // Get AI insight async (non-blocking)
  if (candidate?.id) {
    loadMatchInsight(candidate.id);
  }

  container.innerHTML = renderMatchCard(candidate, result.match, result.already_sent_hi);
}

async function loadMatchInsight(candidateId) {
  const result = await apiCall('/ai/match_insight', 'POST', { candidate_id: candidateId });
  if (result.insight) {
    const insightEl = document.getElementById('match-insight-text');
    if (insightEl) {
      insightEl.textContent = result.insight;
      const compatEl = document.getElementById('match-compat-dynamic');
      if (compatEl && result.dynamic_name) {
        compatEl.textContent = result.dynamic_name;
      }
    }
  }
}

function renderMatchCard(candidate, matchRecord, alreadySentHi) {
  if (!candidate) return '<div class="empty-state"><div class="empty-icon">🌙</div><div class="empty-title">Your match is being found</div></div>';

  const compat = matchRecord?.compatibility || {};
  const score = compat.score || matchRecord?.compatibility_score || 75;
  const dynamic = compat.dynamic || 'Resonance';
  const initials = getInitials(candidate.name);
  const archetype = candidate.archetype || {};
  const archetypeName = archetype.title || archetype.name || 'The Guide';

  // Get photo - use first photo or fallback to initials
  const photos = candidate.photos || [];
  const photoHtml = photos.length > 0 
    ? `<img src="${photos[0]}" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;">` 
    : initials;

  const tags = [
    candidate.profession,
    candidate.city,
    ...(candidate.lifestyle || []).slice(0, 3)
  ].filter(Boolean);

  const hiButton = alreadySentHi
    ? `<button class="btn btn-surface" disabled>✓ Hi Sent</button>`
    : `<button class="btn btn-primary" onclick="sendHi('${candidate.id}')">Say Hi</button>`;

  const messageButton = alreadySentHi
    ? `<button class="btn btn-primary btn-message" onclick="openDirectMessage('${candidate.id}')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
        Message
      </button>`
    : '';

  return `
    <div class="match-card">
      <div class="match-card-hero">
        <div class="match-avatar-large">${photoHtml}</div>

        <div class="match-archetype-badge">${archetypeName}</div>

        <div class="match-card-compat">
          <div class="compat-score">${score}%</div>
          <div>
            <div class="compat-label">Compatibility</div>
            <div class="compat-dynamic" id="match-compat-dynamic">${dynamic}</div>
          </div>
        </div>
      </div>

      <div class="match-card-body">
        <div class="match-name">${candidate.name || 'Your Match'}</div>
        <div class="match-meta">
          <span>🎂 ${candidate.age}</span>
          ${candidate.city ? `<span>📍 ${candidate.city}${candidate.country ? ', ' + candidate.country : ''}</span>` : ''}
          ${candidate.religion && candidate.religion !== 'none' ? `<span>✦ ${capitalize(candidate.religion)}</span>` : ''}
        </div>

        ${candidate.bio ? `
        <div class="match-bio">${candidate.bio}</div>
        ` : ''}

        ${tags.length ? `
        <div class="match-tags">
          ${tags.map(t => `<span class="match-tag">${t}</span>`).join('')}
        </div>
        ` : ''}

        <div class="match-ai-insight">
          <div class="insight-label">✦ Deepsyke Insight</div>
          <div class="insight-text" id="match-insight-text">
            Analysing your psychological alignment...
          </div>
        </div>

        <div class="match-actions">
            ${hiButton}
            ${messageButton}
            <button class=\"btn btn-ghost\" onclick=\"switchView('ai')\">Ask AI about this match</button>
            <button class=\"btn btn-ghost\" onclick=\"openMatchFullProfile()\">View Full Profile</button>
        </div>
      </div>
    </div>

    <div style="text-align:center;margin-top:1.5rem;">
      <p style="font-size:0.78rem;color:var(--text3);font-family:var(--font-mono);letter-spacing:0.1em;">
        NEXT MATCH IN 24 HOURS · NO SWIPING · NO BROWSING
      </p>
    </div>
  `;
}

function renderWaitingState(data) {
  return `
    <div class="match-waiting">
      <div class="waiting-orb">✦</div>
      <div class="waiting-title">Your next match is coming</div>
      <p class="waiting-sub">The universe is finding someone extraordinary for you. One match per day — that's the deal.</p>

      <div class="countdown-display" id="countdown-display">
        <div class="countdown-block">
          <span class="countdown-num" id="cd-hours">--</span>
          <span class="countdown-label">Hours</span>
        </div>
        <div class="countdown-block">
          <span class="countdown-num" id="cd-minutes">--</span>
          <span class="countdown-label">Minutes</span>
        </div>
        <div class="countdown-block">
          <span class="countdown-num" id="cd-seconds">--</span>
          <span class="countdown-label">Seconds</span>
        </div>
      </div>

      <button class="btn btn-surface" onclick="switchView('ai')">✦ Talk to my AI companion</button>
    </div>
  `;
}

function renderMatchError(error) {
  return `
    <div class="empty-state">
      <div class="empty-icon">🔍</div>
      <div class="empty-title">No match found yet</div>
      <p class="empty-sub">${error}</p>
    </div>
  `;
}

function startCountdown() {
  function tick() {
    const now = new Date();
    const tomorrow9am = new Date(now);
    tomorrow9am.setHours(9, 0, 0, 0);
    if (now >= tomorrow9am) tomorrow9am.setDate(tomorrow9am.getDate() + 1);

    const diff = tomorrow9am - now;
    const hours = Math.floor(diff / 3600000);
    const mins = Math.floor((diff % 3600000) / 60000);
    const secs = Math.floor((diff % 60000) / 1000);

    const hEl = document.getElementById('cd-hours');
    const mEl = document.getElementById('cd-minutes');
    const sEl = document.getElementById('cd-seconds');
    if (hEl) hEl.textContent = String(hours).padStart(2, '0');
    if (mEl) mEl.textContent = String(mins).padStart(2, '0');
    if (sEl) sEl.textContent = String(secs).padStart(2, '0');
  }
  tick();
  setInterval(tick, 1000);
}

// ─── SEND HI ───
async function sendHi(candidateId) {
  showLoading('Sending your Hi...');
  const result = await apiCall('/match/send_hi', 'POST', {
    candidate_id: candidateId,
    message: 'Hi 👋'
  });
  hideLoading();

  if (result.error) {
    showToast(result.error, 'error');
    return;
  }

  showToast('Hi sent! ✓ The conversation has begun.', 'success');

  // Refresh match card
  loadTodayMatch();

  // Switch to inbox after delay
  setTimeout(() => switchView('inbox'), 1500);
}

// ═══════════════════════════════════════════════════════
// DIRECT MESSAGE — open conversation from match card
// ═══════════════════════════════════════════════════════
async function openDirectMessage(candidateId) {
  const userId = STATE.user?.id;
  if (!userId) return;

  // Build conv_id same way the server does: userId_candidateId
  const convId = `${userId}_${candidateId}`;

  // Get candidate data from current state
  const candidate = STATE.todayMatch?.candidate;

  // Switch to inbox view
  switchView('inbox');

  // Load inbox then open this conversation directly
  setTimeout(async () => {
    await loadInbox();
    if (candidate) {
      setTimeout(() => openConversation(convId, candidate), 350);
    }
  }, 250);
}


// ═══════════════════════════════════════════
// INBOX
// ═══════════════════════════════════════════
async function loadInbox() {
  const container = document.getElementById('inbox-content');
  const result = await apiCall('/matches/inbox');

  if (!result.conversations || result.conversations.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.4"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div>
        <div class="empty-title">No conversations yet</div>
        <p class="empty-sub">Say Hi to today's match to start a conversation.</p>
        <div style="margin-top:1.5rem;">
          <button class="btn btn-surface" onclick="switchView('today')">← Today's Match</button>
        </div>
      </div>
    `;
    return;
  }

  const convos = result.conversations;
  container.innerHTML = `
    <div class="conv-wrapper">
      <div class="conv-sidebar">
        <div class="conv-header">Conversations</div>
        <div class="inbox-list" id="inbox-list">
          ${convos.map(c => renderInboxItem(c)).join('')}
        </div>
      </div>
      <div class="conv-main" id="conv-main">
        <div class="empty-state" style="padding:3rem;">
          <div class="empty-icon"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.4"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div>
          <p class="empty-sub">Select a conversation</p>
        </div>
      </div>
    </div>
  `;

  // Don't auto-open - let user select conversation
}

function renderInboxItem(convo) {
  const c = convo.candidate || {};
  const lastMsg = convo.last_message;
  const initials = getInitials(c.name);
  const photos = c.photos || [];
  const avatarHtml = photos.length > 0 
    ? `<img src="${photos[0]}" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;">` 
    : initials;
  return `
    <div class="inbox-item" onclick="openConversation('${convo.conversation_id}', ${JSON.stringify(c).replace(/"/g, '"')})">
      <div class="inbox-avatar">${avatarHtml}</div>
      <div class="inbox-info">
        <div class="inbox-name">${c.name || 'Match'}</div>
        <div class="inbox-preview">${lastMsg ? lastMsg.text : 'Start the conversation...'}</div>
      </div>
      <div class="inbox-meta">
        <div class="inbox-date">${convo.match_date || ''}</div>
        <div style="font-size:0.72rem;color:var(--text3);">${convo.message_count} msg</div>
      </div>
    </div>
  `;
}

async function openConversation(convId, candidate) {
  STATE.activeConvId = convId;
  STATE.activeConvCandidate = typeof candidate === 'string' ? JSON.parse(candidate) : candidate;

  const result = await apiCall(`/messages/${convId}`);
  const messages = result.messages || [];

  const convMain = document.getElementById('conv-main');
  if (!convMain) return;

  const c = STATE.activeConvCandidate;
  const initials = getInitials(c.name);
  const photos = c.photos || [];
  const avatarHtml = photos.length > 0 
    ? `<img src="${photos[0]}" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;">` 
    : initials;

  convMain.innerHTML = `
    <div style="display:flex;flex-direction:column;height:100%;">
      <div style="padding:1rem 1.5rem;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:1rem;">
        <div class="inbox-avatar" style="width:40px;height:40px;font-size:1rem;">${avatarHtml}</div>
        <div>
          <div style="font-weight:500;">${c.name}</div>
          <div style="font-size:0.75rem;color:var(--text3);">${c.profession || ''} · ${c.city || ''}</div>
        </div>
      </div>

      <div class="conv-messages" id="conv-messages-${convId}">
        ${messages.length === 0
          ? '<div style="text-align:center;color:var(--text3);font-size:0.85rem;padding:2rem;">The conversation begins here.</div>'
          : messages.map(m => renderMessage(m)).join('')
        }
      </div>

      <div class="conv-input-area">
        <input class="conv-input" id="conv-input-${convId}"
          placeholder="Write something real..."
          onkeydown="if(event.key==='Enter')sendConvMessage('${convId}')">
        <button class="btn btn-primary btn-sm" onclick="sendConvMessage('${convId}')">Send →</button>
      </div>
    </div>
  `;

  // Scroll to bottom
  const msgArea = document.getElementById(`conv-messages-${convId}`);
  if (msgArea) msgArea.scrollTop = msgArea.scrollHeight;
  
  // Start polling for new messages every 3 seconds
  startMessagePolling(convId);
}

function renderMessage(msg) {
  const isUser = msg.sender_id === STATE.user?.id;
  const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '';
  return `
    <div class="ai-message ${isUser ? 'user' : 'ai'}" style="align-items:flex-end;">
      <div class="msg-bubble">
        ${msg.text}
        <div style="font-size:0.68rem;color:var(--text3);margin-top:0.3rem;text-align:${isUser?'right':'left'}">${time}</div>
      </div>
    </div>
  `;
}

// Message polling for real-time updates
let messagePollInterval = null;

function startMessagePolling(convId) {
  // Stop any existing polling
  stopMessagePolling();
  
  // Poll every 2 seconds for new messages
  messagePollInterval = setInterval(async () => {
    if (STATE.activeConvId !== convId) {
      stopMessagePolling();
      return;
    }
    
    const result = await apiCall(`/messages/${convId}`);
    if (result.messages) {
      const msgArea = document.getElementById(`conv-messages-${convId}`);
      if (msgArea) {
        const wasAtBottom = msgArea.scrollHeight - msgArea.scrollTop <= msgArea.clientHeight + 50;
        
        // Only update if messages changed
        const currentCount = msgArea.querySelectorAll('.ai-message').length;
        if (result.messages.length !== currentCount) {
          msgArea.innerHTML = result.messages.length === 0
            ? '<div style="text-align:center;color:var(--text3);font-size:0.85rem;padding:2rem;">The conversation begins here.</div>'
            : result.messages.map(m => renderMessage(m)).join('');
          
          // Auto-scroll if was at bottom
          if (wasAtBottom) {
            msgArea.scrollTop = msgArea.scrollHeight;
          }
        }
      }
    }
  }, 2000);
}

function stopMessagePolling() {
  if (messagePollInterval) {
    clearInterval(messagePollInterval);
    messagePollInterval = null;
  }
}

async function sendConvMessage(convId) {
  const input = document.getElementById(`conv-input-${convId}`);
  const text = input?.value.trim();
  if (!text) return;

  input.value = '';

  const result = await apiCall(`/messages/${convId}/send`, 'POST', { text });
  if (result.success) {
    // Immediately refresh messages
    const msgResult = await apiCall(`/messages/${convId}`);
    const msgArea = document.getElementById(`conv-messages-${convId}`);
    if (msgArea && msgResult.messages) {
      msgArea.innerHTML = msgResult.messages.length === 0
        ? '<div style="text-align:center;color:var(--text3);font-size:0.85rem;padding:2rem;">The conversation begins here.</div>'
        : msgResult.messages.map(m => renderMessage(m)).join('');
      msgArea.scrollTop = msgArea.scrollHeight;
    }
  }
}

// ═══════════════════════════════════════════
// MATCH HISTORY
// ═══════════════════════════════════════════
async function loadHistory() {
  const container = document.getElementById('history-content');
  const result = await apiCall('/matches/history');

  if (!result.matches || result.matches.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.4"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
        <div class="empty-title">Your story starts tomorrow</div>
        <p class="empty-sub">Your first match arrives every morning. Each one is a chapter.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="history-grid">
      ${result.matches.map(m => renderHistoryCard(m)).join('')}
    </div>
  `;
}

function renderHistoryCard(match) {
  const c = match.candidate || {};
  const compat = match.compatibility || {};
  const initials = getInitials(c.name);
  const statusLabels = {
    pending: '○ Passed',
    hi_sent: '● Hi Sent',
    conversation: '★ In Conversation',
    archived: '◌ Archived'
  };
  const statusClass = `status-${match.status || 'pending'}`;
  
  // Avatar: use photo if available, else gradient avatar
  const photos = c.photos || [];
  const avatarHtml = photos.length > 0
    ? `<img src="${photos[0]}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`
    : initials;
  
  // Store match data as JSON for click handler
  const matchJson = encodeURIComponent(JSON.stringify({candidate: c, compatibility: compat, status: match.status, match_date: match.match_date}));

  return `
    <div class="history-card" onclick="openCandidateProfile('${matchJson}')" style="cursor:pointer;">
      <div class="history-card-top">
        <div class="history-avatar">${avatarHtml}</div>
        <div>
          <div class="history-name">${c.name || 'Match'}</div>
          <div class="history-date">${formatDate(match.match_date)}</div>
        </div>
      </div>
      <div class="history-status ${statusClass}">${statusLabels[match.status] || '○ Passed'}</div>
      <div style="font-size:0.82rem;color:var(--text3);margin-bottom:0.5rem;">${c.profession || ''} · ${c.city || ''}</div>
      <div class="history-compat">${compat.score || '--'}%</div>
      <div style="font-size:0.72rem;color:var(--text3);font-family:var(--font-mono);">${compat.dynamic || 'Compatibility'}</div>
      <div style="font-size:0.72rem;color:var(--accent);margin-top:0.5rem;font-family:var(--font-mono);">TAP TO VIEW PROFILE →</div>
    </div>
  `;
}

// ═══════════════════════════════════════════════════════
// CANDIDATE PROFILE MODAL
// ═══════════════════════════════════════════════════════
function openCandidateProfile(encodedData) {
  const data = JSON.parse(decodeURIComponent(encodedData));
  const c = data.candidate || {};
  const compat = data.compatibility || {};
  
  const initials = getInitials(c.name);
  const photos = c.photos || [];
  const archetype = c.archetype || {};
  const archetypeName = archetype.title || archetype.name || '';
  
  // Photo/avatar display
  const photoHtml = photos.length > 0
    ? `<div style="width:120px;height:120px;border-radius:50%;overflow:hidden;margin:0 auto 1rem;border:3px solid var(--accent);">
        <img src="${photos[0]}" style="width:100%;height:100%;object-fit:cover;">
       </div>`
    : `<div style="width:120px;height:120px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent2,#8b5cf6));display:flex;align-items:center;justify-content:center;font-size:2.5rem;font-weight:700;color:white;margin:0 auto 1rem;">${initials}</div>`;

  const tags = [
    c.profession,
    c.city,
    ...(c.lifestyle || []).slice(0, 4)
  ].filter(Boolean);
  
  const compatSection = compat.score ? `
    <div style="background:var(--surface2,rgba(255,255,255,0.05));border-radius:12px;padding:1rem;margin:1rem 0;text-align:center;">
      <div style="font-size:2rem;font-weight:700;color:var(--accent);">${compat.score}%</div>
      <div style="font-size:0.75rem;color:var(--text3);font-family:var(--font-mono);letter-spacing:0.15em;">COMPATIBILITY · ${(compat.dynamic || 'resonance').toUpperCase()}</div>
      ${compat.description ? `<div style="font-size:0.85rem;color:var(--text2);margin-top:0.5rem;font-style:italic;">"${compat.description}"</div>` : ''}
    </div>` : '';
  
  const bioSection = c.bio ? `
    <div style="margin:1rem 0;">
      <div style="font-size:0.65rem;font-family:var(--font-mono);letter-spacing:0.2em;color:var(--accent);text-transform:uppercase;margin-bottom:0.4rem;">About</div>
      <div style="font-size:0.9rem;color:var(--text1);line-height:1.6;">${c.bio}</div>
    </div>` : '';
    
  const detailsSection = `
    <div style="margin:1rem 0;">
      <div style="font-size:0.65rem;font-family:var(--font-mono);letter-spacing:0.2em;color:var(--accent);text-transform:uppercase;margin-bottom:0.6rem;">Details</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
        ${c.age ? `<div style="font-size:0.82rem;color:var(--text2);">🎂 Age ${c.age}</div>` : ''}
        ${c.city ? `<div style="font-size:0.82rem;color:var(--text2);">📍 ${c.city}${c.country ? ', ' + c.country : ''}</div>` : ''}
        ${c.profession ? `<div style="font-size:0.82rem;color:var(--text2);">💼 ${c.profession}</div>` : ''}
        ${c.education ? `<div style="font-size:0.82rem;color:var(--text2);">🎓 ${c.education}</div>` : ''}
        ${c.religion && c.religion !== 'none' ? `<div style="font-size:0.82rem;color:var(--text2);">✦ ${c.religion}</div>` : ''}
        ${c.natal_type ? `<div style="font-size:0.82rem;color:var(--text2);">◈ ${c.natal_type} Type</div>` : ''}
      </div>
    </div>`;
    
  const tagsSection = tags.length ? `
    <div style="display:flex;flex-wrap:wrap;gap:0.4rem;margin:1rem 0;">
      ${tags.map(t => `<span style="background:var(--surface2,rgba(255,255,255,0.07));padding:0.3rem 0.7rem;border-radius:20px;font-size:0.75rem;color:var(--text2);">${t}</span>`).join('')}
    </div>` : '';
  
  const body = `
    <div style="text-align:center;">
      ${photoHtml}
      <div style="font-size:1.4rem;font-weight:600;color:var(--text1);margin-bottom:0.2rem;">${c.name || 'Match'}</div>
      ${archetypeName ? `<div style="font-size:0.72rem;font-family:var(--font-mono);letter-spacing:0.2em;color:var(--accent);text-transform:uppercase;">${archetypeName}</div>` : ''}
    </div>
    ${compatSection}
    ${bioSection}
    ${detailsSection}
    ${tagsSection}
  `;
  
  showModal(c.name || 'Profile', body, [
    { label: 'Close', class: 'btn btn-ghost', onclick: 'closeModal()' }
  ]);
}

// ═══════════════════════════════════════════
// PROFILE VIEW
// ═══════════════════════════════════════════
async function loadProfile() {
  const container = document.getElementById('profile-content');
  const result = await apiCall('/profile/me');

  if (result.error) {
    container.innerHTML = '<div class="empty-state"><p>Could not load profile.</p></div>';
    return;
  }

  const u = result;
  const initials = getInitials(u.name);
  const archetype = u.archetype || {};
  const loi = u.loi_score || 50;
  const loiLabel = loi >= 70 ? 'Highly Aligned' : loi >= 50 ? 'In Alignment' : 'Seeking Growth';

  // Build photos HTML with larger thumbnails and click-to-enlarge
  const photos = u.photos || [];
  const photosHtml = photos.length > 0 ? `
    <div class="card" style="margin-bottom:1.5rem;">
      <div style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.2em;color:var(--accent);text-transform:uppercase;margin-bottom:0.75rem;">Your Photos</div>
      <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
        ${photos.map((url, i) => `<img src="${url}" onclick="openPhotoViewer(${i})" style="width:150px;height:150px;object-fit:cover;border-radius:12px;cursor:pointer;transition:transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">`).join('')}
      </div>
    </div>
  ` : '';
  
  // Store photos for viewer
  STATE.profilePhotos = photos;

  container.innerHTML = `
    <div class="profile-hero">
      <div class="profile-avatar-wrap">
        ${photos.length > 0 ? `<img src="${photos[0]}">` : `<div class="profile-avatar">${initials}</div>`}
        <div class="profile-archetype-badge">${archetype.title || ''}</div>
      </div>
      <div class="profile-info">
        <div class="profile-name">${u.name || ''}</div>
        <div class="profile-type">${u.age || ''} · ${u.city || ''}, ${u.country || ''} · ${capitalize(u.orientation || '')}</div>

        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem;">
          <div class="badge badge-gold">⚡ ${archetype.energy || ''}</div>
          <div class="badge badge-purple">◉ ${loiLabel}</div>
          ${u.natal_type ? `<div class="badge badge-green">🧠 ${u.natal_type} Blueprint</div>` : ''}
        </div>

        <div class="loi-bar-wrap" style="max-width:280px;">
          <div class="loi-label">
            <span>Alignment Score</span>
            <span style="color:var(--accent);">${loi}/100</span>
          </div>
          <div class="loi-bar">
            <div class="loi-fill" style="width:${loi}%"></div>
          </div>
        </div>
      </div>
    </div>

    ${photosHtml}

    ${u.bio ? `
    <div class="card" style="margin-bottom:1.5rem;">
      <div style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.2em;color:var(--accent);text-transform:uppercase;margin-bottom:0.75rem;">Your Story</div>
      <p style="font-family:var(--font-serif);font-style:italic;font-size:1.05rem;color:var(--text2);line-height:1.75;">"${u.bio}"</p>
    </div>
    ` : ''}

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;">
      <div class="card">
        <div style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.2em;color:var(--text3);text-transform:uppercase;margin-bottom:0.75rem;">Profession</div>
        <div style="font-weight:500;">${u.profession || '—'}</div>
        <div style="font-size:0.82rem;color:var(--text3);">${u.education || ''}</div>
      </div>
      <div class="card">
        <div style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.2em;color:var(--text3);text-transform:uppercase;margin-bottom:0.75rem;">Identity</div>
        <div style="font-weight:500;">${capitalize(u.religion || 'None')}</div>
        <div style="font-size:0.82rem;color:var(--text3);">${capitalize(u.ethnicity || '')} · ${capitalize(u.social_style || '')}</div>
      </div>
    </div>

    ${u.lifestyle && u.lifestyle.length ? `
    <div class="card" style="margin-bottom:1.5rem;">
      <div style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.2em;color:var(--text3);text-transform:uppercase;margin-bottom:0.75rem;">Lifestyle</div>
      <div class="match-tags">${u.lifestyle.map(t => `<span class="match-tag">${t}</span>`).join('')}</div>
    </div>
    ` : ''}

    <div class="card" style="margin-bottom:1.5rem;">
      <div style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.2em;color:var(--accent);text-transform:uppercase;margin-bottom:1rem;">Deepsyke Archetype</div>
      <div style="display:flex;align-items:center;gap:1.5rem;">
        <div style="width:64px;height:64px;border-radius:50%;background:rgba(200,169,110,0.1);border:1px solid rgba(200,169,110,0.2);display:flex;align-items:center;justify-content:center;font-size:1.8rem;">
          ${getArchetypeEmoji(archetype.name)}
        </div>
        <div>
          <div style="font-family:var(--font-serif);font-size:1.4rem;">${archetype.title || ''}</div>
          <div style="font-size:0.82rem;color:var(--text3);font-style:italic;">"${archetype.essence || ''}"</div>
        </div>
      </div>
    </div>

    <div style="display:flex;gap:1rem;flex-wrap:wrap;">
      <button class="btn btn-ghost" onclick="editProfile()">Edit Profile</button>
      <button class="btn btn-danger" onclick="doLogout()">Sign Out</button>
    </div>
  `;
}

function getArchetypeEmoji(name) {
  const map = {
    Magician: '✦', Mystic: '🌙', Knight: '⚔️', Maiden: '🌸',
    Warrior: '🔥', Queen: '👑', King: '♛', Huntress: '🏹'
  };
  return map[name] || '✦';
}

async function doLogout() {
  await apiCall('/auth/logout', 'POST');
  STATE.user = null;
  STATE.todayMatch = null;
  showScreen('landing');
}

// ═══════════════════════════════════════════
// AI COMPANION
// ═══════════════════════════════════════════
async function sendAIMessage() {
  const input = document.getElementById('ai-input');
  const message = input?.value.trim();
  if (!message) return;

  input.value = '';

  addAIMessage(message, 'user');
  showAITyping();

  const result = await apiCall('/ai/chat', 'POST', {
    message,
    last_candidate_id: STATE.aiLastCandidateId
  });

  hideAITyping();

  if (result.response) {
    addAIMessage(result.response, 'ai');

    if (result.feedback_processed && result.adjustments_applied) {
      setTimeout(() => {
        addAIMessage('✦ Got it. Your preferences have been noted and will shape tomorrow\'s match.', 'ai');
      }, 800);
    }
  } else {
    addAIMessage('Something went wrong — please try again.', 'ai');
  }
}

function sendQuickPrompt(el) {
  const text = el.textContent;
  const input = document.getElementById('ai-input');
  if (input) {
    input.value = text;
    sendAIMessage();
  }
}

function addAIMessage(text, role) {
  const container = document.getElementById('ai-messages');
  if (!container) return;

  const msg = document.createElement('div');
  msg.className = `ai-message ${role}`;

  const initials = role === 'user' ? getInitials(STATE.user?.name || 'You') : 'K';
  msg.innerHTML = `
    <div class="msg-avatar">${role === 'ai' ? 'K' : initials}</div>
    <div class="msg-bubble">${text}</div>
  `;

  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

let typingIndicator = null;

function showAITyping() {
  const container = document.getElementById('ai-messages');
  if (!container) return;

  typingIndicator = document.createElement('div');
  typingIndicator.className = 'ai-message ai';
  typingIndicator.id = 'ai-typing-indicator';
  typingIndicator.innerHTML = `
    <div class="msg-avatar">K</div>
    <div class="msg-bubble ai-typing">
      <span></span><span></span><span></span>
    </div>
  `;
  container.appendChild(typingIndicator);
  container.scrollTop = container.scrollHeight;
}

function hideAITyping() {
  const el = document.getElementById('ai-typing-indicator');
  if (el) el.remove();
}

// ═══════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════
function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
}

// ═══════════════════════════════════════════
// INIT — CHECK EXISTING SESSION
// ═══════════════════════════════════════════
// ═══════════════════════════════════════════════════════
// OPEN TODAY'S MATCH FULL PROFILE
// ═══════════════════════════════════════════════════════
function openMatchFullProfile() {
  if (!STATE.todayMatch) return;
  const result = STATE.todayMatch;
  const c = result.candidate || {};
  const compat = result.match?.compatibility || result.compatibility || {};
  const matchData = {candidate: c, compatibility: compat, status: result.match?.status, match_date: result.match?.match_date};
  openCandidateProfile(encodeURIComponent(JSON.stringify(matchData)));
}

async function checkSession() {
  const result = await apiCall('/auth/me');
  if (result.authenticated) {
    STATE.user = result.user;
    if (result.user.profile_complete) {
      showScreen('app');
    } else {
      showScreen('onboard');
      goOnboardStep(result.user.onboarding_step || 1);
    }
  }
  // If not authenticated, stay on landing screen
}

// Run on page load
document.addEventListener('DOMContentLoaded', () => {
  checkSession();
});
// ══════════════════════════════════════════════════════════════════════════
// PHOTO UPLOAD
// ══════════════════════════════════════════════════════════════════════════
let currentPhotoSlot = 0;
let uploadedPhotos = [];

function triggerPhotoUpload(slotIndex) {
  currentPhotoSlot = slotIndex;
  document.getElementById('photo-upload-input').click();
}

async function handlePhotoUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
  if (!allowedTypes.includes(file.type)) {
    showToast('Please use JPEG, PNG, or WebP format', 'error');
    return;
  }

  if (file.size > 5 * 1024 * 1024) {
    showToast('Photo must be under 5MB', 'error');
    return;
  }

  const slot = document.getElementById('photo-slot-' + currentPhotoSlot);
  slot.innerHTML = '<div class="photo-uploading"><div class="spinner"></div></div>';

  const formData = new FormData();
  formData.append('photo', file);

  try {
    const response = await fetch('/api/photos/upload', {
      method: 'POST',
      body: formData,
      credentials: 'include'
    });

    const result = await response.json();

    if (result.success) {
      slot.innerHTML = '<img src="' + result.url + '" alt="Your photo"><div class="photo-actions"><button class="photo-action-btn" onclick="event.stopPropagation(); deletePhoto(\'' + result.url + '\', ' + currentPhotoSlot + ')">🗑️</button></div>';
      slot.classList.add('has-photo');
      uploadedPhotos[currentPhotoSlot] = result.url;
      showToast('Photo uploaded!', 'success');
    } else {
      slot.innerHTML = '<span class="add-icon">+</span>';
      showToast(result.error || 'Upload failed', 'error');
    }
  } catch (error) {
    slot.innerHTML = '<span class="add-icon">+</span>';
    showToast('Upload failed. Please try again.', 'error');
  }

  event.target.value = '';
}

async function deletePhoto(photoUrl, slotIndex) {
  const slot = document.getElementById('photo-slot-' + slotIndex);
  
  try {
    const response = await fetch('/api/photos/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: photoUrl }),
      credentials: 'include'
    });

    const result = await response.json();

    if (result.success) {
      slot.innerHTML = '<span class="add-icon">+</span>';
      slot.classList.remove('has-photo');
      uploadedPhotos[slotIndex] = null;
      showToast('Photo removed', 'success');
    } else {
      showToast(result.error || 'Delete failed', 'error');
    }
  } catch (error) {
    showToast('Delete failed. Please try again.', 'error');
  }
}

function loadUserPhotos(photos) {
  if (!photos || !Array.isArray(photos)) return;
  
  photos.forEach((url, index) => {
    if (index < 6 && url) {
      const slot = document.getElementById('photo-slot-' + index);
      if (slot) {
        slot.innerHTML = '<img src="' + url + '" alt="Your photo"><div class="photo-actions"><button class="photo-action-btn" onclick="event.stopPropagation(); deletePhoto(\'' + url + '\', ' + index + ')">🗑️</button></div>';
        slot.classList.add('has-photo');
        uploadedPhotos[index] = url;
      }
    }
  });
}

// Photo viewer modal
function openPhotoViewer(index) {
  const photos = STATE.profilePhotos || [];
  if (photos.length === 0) return;
  
  let currentIndex = index;
  
  const viewer = document.createElement('div');
  viewer.id = 'photo-viewer';
  viewer.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.95);z-index:10000;display:flex;flex-direction:column;align-items:center;justify-content:center;';
  
  viewer.innerHTML = `
    <button onclick="closePhotoViewer()" style="position:absolute;top:20px;right:20px;background:none;border:none;color:white;font-size:2rem;cursor:pointer;">&times;</button>
    <button id="photo-prev" onclick="navigatePhoto(-1)" style="position:absolute;left:20px;top:50%;transform:translateY(-50%);background:rgba(255,255,255,0.1);border:none;color:white;font-size:2rem;padding:1rem;cursor:pointer;border-radius:50%;">&#8249;</button>
    <img id="viewer-image" src="${photos[currentIndex]}" style="max-width:90%;max-height:80%;object-fit:contain;border-radius:8px;">
    <button id="photo-next" onclick="navigatePhoto(1)" style="position:absolute;right:20px;top:50%;transform:translateY(-50%);background:rgba(255,255,255,0.1);border:none;color:white;font-size:2rem;padding:1rem;cursor:pointer;border-radius:50%;">&#8250;</button>
    <div style="color:rgba(255,255,255,0.6);margin-top:1rem;font-size:0.9rem;">${currentIndex + 1} / ${photos.length}</div>
  `;
  
  document.body.appendChild(viewer);
  document.body.style.overflow = 'hidden';
  
  // Store current state
  STATE.photoViewerIndex = currentIndex;
  
  // Add keyboard navigation
  document.addEventListener('keydown', handlePhotoKeydown);
}

function navigatePhoto(direction) {
  const photos = STATE.profilePhotos || [];
  if (photos.length === 0) return;
  
  let newIndex = STATE.photoViewerIndex + direction;
  if (newIndex < 0) newIndex = photos.length - 1;
  if (newIndex >= photos.length) newIndex = 0;
  STATE.photoViewerIndex = newIndex;
  
  const img = document.getElementById('viewer-image');
  if (img) {
    img.src = photos[newIndex];
  }
  
  // Update counter
  const counter = document.querySelector('#photo-viewer > div:last-child');
  if (counter) {
    counter.textContent = `${newIndex + 1} / ${photos.length}`;
  }
}

function handlePhotoKeydown(e) {
  if (e.key === 'Escape') closePhotoViewer();
  if (e.key === 'ArrowLeft') navigatePhoto(-1);
  if (e.key === 'ArrowRight') navigatePhoto(1);
}

function closePhotoViewer() {
  const viewer = document.getElementById('photo-viewer');
  if (viewer) {
    viewer.remove();
    document.body.style.overflow = '';
  }
  document.removeEventListener('keydown', handlePhotoKeydown);
}
