const $ = (selector) => document.querySelector(selector);
const form = $('#insult-form');
const message = $('#message');
const senderSelect = $('#sender');
const submitButton = $('#submit-button');
let state = null;

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

function dateLabel(value) {
  return new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value));
}

function render(data) {
  state = data;
  $('#month-label').textContent = new Intl.DateTimeFormat('de-DE', { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${data.month}-01T00:00:00Z`)).toUpperCase();
  const current = senderSelect.value;
  senderSelect.innerHTML = data.users.map((user) => `<option value="${escapeHTML(user.id)}">${escapeHTML(user.name)}</option>`).join('');
  if (data.users.some((user) => user.id === current)) senderSelect.value = current;
  $('#players').innerHTML = data.users.map((user) => {
    const remaining = Math.max(0, user.remaining);
    const tokens = Array.from({ length: data.limit }, (_, i) => `<span class="token ${i >= remaining ? 'used' : ''}" aria-label="${i < remaining ? 'verfügbar' : 'verwendet'}">${i < remaining ? '✳' : '×'}</span>`).join('');
    const status = remaining ? '1 TREFFER NOCH VERFÜGBAR' : 'FÜR DIESEN MONAT ERLEDIGT';
    return `<article class="player-card"><div><h3 class="player-name">${escapeHTML(user.name)}</h3><p class="player-status">${status}</p></div><div class="tokens" aria-label="${remaining} von ${data.limit} verfügbar">${tokens}</div></article>`;
  }).join('');
  const archive = $('#archive');
  $('#archive-count').textContent = `${data.insults.length} ${data.insults.length === 1 ? 'EINTRAG' : 'EINTRÄGE'}`;
  if (!data.insults.length) {
    archive.innerHTML = '<div class="empty-state"><span class="empty-mark">“</span><p>Noch ist alles ruhig.</p><span>Der erste Eintrag wartet auf euch.</span></div>';
  } else {
    const names = Object.fromEntries(data.users.map((user) => [user.id, user.name]));
    archive.innerHTML = data.insults.map((item) => `<article class="archive-item"><time class="archive-date" datetime="${escapeHTML(item.created_at)}">${dateLabel(item.created_at)}<br>${item.month}</time><div class="archive-message">„${escapeHTML(item.message)}“</div><div class="archive-people"><strong>${escapeHTML(names[item.sender] || item.sender)}</strong><br>an ${escapeHTML(names[item.recipient] || item.recipient)}</div></article>`).join('');
  }
  updateFormAvailability();
}

function updateFormAvailability() {
  const user = state?.users.find((item) => item.id === senderSelect.value);
  submitButton.disabled = !user || user.remaining < 1;
  if (user && user.remaining < 1) $('#form-status').textContent = 'Dein Kontingent ist für diesen Monat aufgebraucht.';
  else if ($('#form-status').textContent === 'Dein Kontingent ist für diesen Monat aufgebraucht.') $('#form-status').textContent = '';
}

async function refresh() {
  const response = await fetch('/api/state', { cache: 'no-store' });
  if (!response.ok) throw new Error('Status konnte nicht geladen werden.');
  render(await response.json());
}

message.addEventListener('input', () => { $('#char-count').textContent = `${message.value.length} / 500`; });
senderSelect.addEventListener('change', updateFormAvailability);
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const status = $('#form-status');
  status.classList.remove('error');
  status.textContent = '';
  submitButton.disabled = true;
  try {
    const response = await fetch('/api/insults', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sender: senderSelect.value, message: message.value }) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Eintrag konnte nicht gespeichert werden.');
    message.value = '';
    $('#char-count').textContent = '0 / 500';
    status.textContent = 'Eingetragen. Der Treffer ist verbucht.';
    await refresh();
  } catch (error) {
    status.textContent = error.message || 'Verbindung fehlgeschlagen. Bitte erneut versuchen.';
    status.classList.add('error');
    await refresh().catch(() => {});
  } finally {
    updateFormAvailability();
  }
});

refresh().catch(() => {
  $('#players').innerHTML = '<div class="loading-card">Verbindung fehlgeschlagen. Bitte Seite neu laden.</div>';
  $('#form-status').textContent = 'Der Server ist gerade nicht erreichbar.';
  $('#form-status').classList.add('error');
});
