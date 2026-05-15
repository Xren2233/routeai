// ===== AUTH MODULE =====

const API_BASE = 'http://localhost:5000/api';

function showLogin() {
  document.getElementById('register-form').classList.add('hidden');
  document.getElementById('login-form').classList.remove('hidden');
}

function showRegister() {
  document.getElementById('login-form').classList.add('hidden');
  document.getElementById('register-form').classList.remove('hidden');
}

async function register() {
  const name     = document.getElementById('reg-name').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const confirm  = document.getElementById('reg-confirm').value;
  const errEl    = document.getElementById('reg-error');

  if (!name)                        return errEl.textContent = 'Введите имя';
  if (!email || !email.includes('@')) return errEl.textContent = 'Введите корректную почту';
  if (password.length < 6)          return errEl.textContent = 'Пароль минимум 6 символов';
  if (password !== confirm)         return errEl.textContent = 'Пароли не совпадают';
  errEl.textContent = '';

  try {
    const res  = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await res.json();
    if (!res.ok) return errEl.textContent = data.error || 'Ошибка регистрации';
    saveAndEnter(data);
  } catch {
    errEl.textContent = 'Сервер недоступен. Запустите бэкенд.';
  }
}

async function login() {
  const email    = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl    = document.getElementById('login-error');

  if (!email || !email.includes('@')) return errEl.textContent = 'Введите корректную почту';
  if (!password)                      return errEl.textContent = 'Введите пароль';
  errEl.textContent = '';

  try {
    const res  = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) return errEl.textContent = data.error || 'Неверная почта или пароль';
    saveAndEnter(data);
  } catch {
    errEl.textContent = 'Сервер недоступен. Запустите бэкенд.';
  }
}

function saveAndEnter(data) {
  localStorage.setItem('token', data.token);
  localStorage.setItem('user', JSON.stringify(data.user));
  enterApp(data.user);
}

function enterApp(user) {
  localStorage.removeItem('guest');
  document.getElementById('auth-overlay').classList.remove('active');
  document.getElementById('app').classList.remove('hidden');
  document.getElementById('account-name').textContent  = user.name;
  document.getElementById('account-email').textContent = user.email;
  loadAvatar();  // ← ДОБАВИТЬ
}
function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  localStorage.removeItem('guest');
  localStorage.removeItem('avatar');  // ← ДОБАВИТЬ
  document.getElementById('app').classList.add('hidden');
  document.getElementById('auth-overlay').classList.add('active');
  showRegister();
}

window.addEventListener('DOMContentLoaded', async () => {
  const stored = localStorage.getItem('user');
  const token  = localStorage.getItem('token');
  const guest  = localStorage.getItem('guest') === 'true';  // ← ДОБАВИТЬ

  // Если гость — показываем приложение без авторизации
  if (guest && !token) {
    document.getElementById('auth-overlay').classList.remove('active');
    document.getElementById('app').classList.remove('hidden');
    document.getElementById('account-name').textContent = 'Гость';
    document.getElementById('account-email').textContent = 'гостевой режим';
    return;
  }

  if (!stored || !token) return; // нет данных — показываем логин

  // Сразу показываем приложение из кэша (не ждём сервер)
  enterApp(JSON.parse(stored));

  // Фоновая проверка токена на сервере
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const user = await res.json();
      // Обновляем данные пользователя если изменились
      localStorage.setItem('user', JSON.stringify(user));
      document.getElementById('account-name').textContent  = user.name;
      document.getElementById('account-email').textContent = user.email;
    } else if (res.status === 401) {
      // Токен протух — тихо разлогиниваем
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      document.getElementById('app').classList.add('hidden');
      document.getElementById('auth-overlay').classList.add('active');
    }
  } catch {
    // Сервер недоступен — остаёмся залогиненными из кэша
    console.warn('[Auth] Сервер недоступен, используем кэш');
  }
});
