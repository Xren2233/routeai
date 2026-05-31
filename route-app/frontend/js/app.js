// Восстанавливаем тему ДО отрисовки страницы (чтобы не было мигания)
(function() {
  const savedTheme = localStorage.getItem('routeai-theme');
  if (savedTheme) {
    document.body.classList.add('theme-' + savedTheme);
  }
})();

// ── WebSocket — статус генерации ─────────────────────────────────────────
const socket = io();

socket.on('route_status', (data) => {
  const el = document.getElementById('loading-overlay');
  if (el) el.querySelector('p').textContent = data.message;
});

socket.on('connect', () => console.log('[WS] Подключено'));

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

  const page = document.getElementById(`page-${name}`);
  if (page) page.classList.add('active');

  // Подсветка активной кнопки навигации
  const navMap = { home: 0, account: 1, survey: 2 };
  const navBtns = document.querySelectorAll('.nav-btn');
  if (navMap[name] !== undefined) navBtns[navMap[name]]?.classList.add('active');

  // Скрываем кнопки для гостя
  const isGuest = localStorage.getItem('guest') === 'true';
  const token = localStorage.getItem('token');
  
  // Кнопка "Аккаунт" — только для авторизованных
  if (navBtns[1]) navBtns[1].style.display = (!token && !isGuest) ? 'none' : 'inline-block';

  if (name === 'home') onShowHome();
  if (name === 'survey') initSurvey();
  if (name === 'account') {
    if (isGuest && !token) {
      document.getElementById('app').classList.add('hidden');
      document.getElementById('auth-overlay').classList.add('active');
      showLogin();
      return;
    }
    loadMyRoutes();
    updateActiveThemeCard();
    loadAvatar();  // ← добавить
  }
}

function showExampleRoute() {
  // Прокрутить к карте на главной
  document.getElementById('main-map').scrollIntoView({ behavior: 'smooth' });
}

function saveRoute() {
  const token = localStorage.getItem('token');
  if (!token) { alert('Войдите в аккаунт'); return; }

  const result = window._lastRouteResult;
  if (!result || !result.places?.length) {
    alert('Нет маршрута для сохранения. Сначала создайте маршрут.');
    return;
  }

  const note = prompt('Добавьте заметку к маршруту (необязательно):', '');
  
  fetch('/api/routes/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ places: result.places, meta: result.meta, note: note || '' }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.id) {
      alert(`Маршрут "${data.title}" сохранён!`);
      loadMyRoutes();
    } else {
      alert(data.error || 'Ошибка сохранения');
    }
  })
  .catch(() => alert('Ошибка подключения к серверу'));
}

async function loadMyRoutes() {
  const token = localStorage.getItem('token');
  if (!token) return;
  try {
    const res = await fetch('/api/routes/my', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    // Поддержка и старого (массив), и нового (объект) формата
    const routes = Array.isArray(data) ? data : (data.routes || []);
    renderSavedRoutes(routes);
  } catch (e) {
    console.warn('Не удалось загрузить маршруты:', e);
  }
}

function renderSavedRoutes(routes) {
  const container = document.getElementById('saved-routes-list');
  const countEl   = document.getElementById('routes-count');
  if (!container) return;

  if (countEl) countEl.textContent = routes.length;

  if (!routes.length) {
    container.innerHTML = '<p class="empty-state">Пока нет сохранённых маршрутов. <span onclick="showPage(\'survey\')">Создайте первый!</span></p>';
    return;
  }

  container.innerHTML = routes.map(r => `
    <div class="saved-route-card">
      <div class="saved-route-info">
        <strong id="route-title-${r.id}">${escapeHtml(r.title)}</strong>
        <span class="saved-route-meta">${escapeHtml(r.meta || '')}</span>
        <span class="saved-route-date">${new Date(r.created_at).toLocaleDateString('ru-RU')}</span>
        ${r.note ? `<p style="color:var(--text-muted);font-size:0.82rem;margin-top:4px;"> ${escapeHtml(r.note)}</p>` : ''}
        ${r.photos && r.photos.length ? `<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">${r.photos.map(url => `<img src="${url}" class="route-photo-thumb" />`).join('')}</div>` : ''}
      </div>
      <div class="saved-route-actions">
        <button class="btn-secondary btn-sm" onclick="openEditRouteModal(${r.id})" title="Редактировать">Редактировать</button>
        <button class="btn-secondary btn-sm" onclick="renameRoutePrompt(${r.id})" title="Переименовать">Переименовать</button>
        <button class="btn-secondary btn-sm" onclick="openSavedRoute(${r.id})">Открыть</button>
        <button class="btn-danger btn-sm" onclick="deleteRoute(${r.id})">✕</button>
      </div>
    </div>
  `).join('');

  window._savedRoutes = routes;
}

function openSavedRoute(id) {
  const route = window._savedRoutes?.find(r => r.id === id);
  if (!route) return;
  const points = route.places.filter(p => p.coords).map(p => ({
    name: p.name, coords: p.coords, desc: p.description || '',
    price: p.price || '', rating: p.rating || null,
  }));
  if (points.length < 2) { alert('Маршрут не содержит точек'); return; }
  showRouteResult({ meta: route.meta, points });
}

async function deleteRoute(id) {
  if (!confirm('Удалить маршрут?')) return;
  const token = localStorage.getItem('token');
  await fetch(`/api/routes/${id}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` },
  });
  loadMyRoutes();
}

// ===== ПЕРЕКЛЮЧЕНИЕ ТЕМ =====


document.addEventListener('click', function(e) {
  const card = e.target.closest('.theme-card');
  if (!card) return;
  const theme = card.getAttribute('data-theme');
  if (theme) setTheme(theme);
});

function setTheme(themeName) {
  // Убираем все классы тем с body
  document.body.classList.remove('theme-green', 'theme-beige', 'theme-blue');
  
  if (themeName === 'default') {
    localStorage.removeItem('routeai-theme');
  } else {
    document.body.classList.add('theme-' + themeName);
    localStorage.setItem('routeai-theme', themeName);
  }
  
  updateActiveThemeCard();
}

function updateActiveThemeCard() {
  const currentTheme = localStorage.getItem('routeai-theme') || 'default';
  document.querySelectorAll('.theme-card').forEach(card => {
    card.classList.toggle('active', card.getAttribute('data-theme') === currentTheme);
  });
}


// Загружает сохранённую тему при старте
function loadSavedTheme() {
  const savedTheme = localStorage.getItem('routeai-theme');
  if (savedTheme) {
    document.documentElement.setAttribute('data-theme', savedTheme);
  }
}

// Применяем тему сразу при загрузке страницы
loadSavedTheme();

// ===== АВАТАР =====

function getAvatarKey() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  return 'avatar_' + (user.email || 'guest');
}

function loadAvatar() {
  const avatarData = localStorage.getItem(getAvatarKey());
  const mainImg = document.getElementById('avatar-img');
  const mainPlaceholder = document.getElementById('avatar-placeholder');
  const editImg = document.getElementById('edit-avatar-img');
  const editPlaceholder = document.getElementById('edit-avatar-placeholder');

  if (avatarData) {
    if (mainImg) { mainImg.src = avatarData; mainImg.style.display = 'block'; }
    if (mainPlaceholder) mainPlaceholder.style.display = 'none';
    if (editImg) { editImg.src = avatarData; editImg.style.display = 'block'; }
    if (editPlaceholder) editPlaceholder.style.display = 'none';
  } else {
    if (mainImg) mainImg.style.display = 'none';
    if (mainPlaceholder) mainPlaceholder.style.display = 'block';
    if (editImg) editImg.style.display = 'none';
    if (editPlaceholder) editPlaceholder.style.display = 'block';
  }
}

function uploadAvatar(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) { alert('Файл слишком большой.'); return; }
  const reader = new FileReader();
  reader.onload = function(e) {
    localStorage.setItem(getAvatarKey(), e.target.result);
    loadAvatar();
  };
  reader.readAsDataURL(file);
}

function removeAvatar() {
  localStorage.removeItem(getAvatarKey());
  loadAvatar();
}

// ===== РЕДАКТИРОВАНИЕ ЗАМЕТКИ МАРШРУТА =====

// ===== РЕДАКТИРОВАНИЕ МАРШРУТА (МОДАЛЬНОЕ ОКНО) =====

let _editingRouteId = null;
let _editingPhotos = [];  // Временное хранилище фото (data URL)

function openEditRouteModal(routeId) {
  const route = window._savedRoutes?.find(r => r.id === routeId);
  if (!route) return;

  _editingRouteId = routeId;
  _editingPhotos = (route.photos && Array.isArray(route.photos)) ? [...route.photos] : [];

  document.getElementById('edit-route-title').value = route.title || '';
  document.getElementById('edit-route-note').value = route.note || '';
  document.getElementById('edit-route-error').textContent = '';
  renderPhotoPreviews();

  document.getElementById('edit-route-modal').classList.remove('hidden');
  
  // Обработчик загрузки фото
  document.getElementById('edit-route-photos').onchange = function(e) {
    const files = Array.from(e.target.files);
    files.forEach(file => {
      if (file.size > 2 * 1024 * 1024) { alert('Фото слишком большое (макс 2MB)'); return; }
      const reader = new FileReader();
      reader.onload = function(ev) {
        _editingPhotos.push(ev.target.result);
        renderPhotoPreviews();
      };
      reader.readAsDataURL(file);
    });
    e.target.value = '';
  };
}

function renderPhotoPreviews() {
  const container = document.getElementById('edit-route-photos-preview');
  if (!container) return;
  container.innerHTML = _editingPhotos.map((url, i) => `
    <div class="photo-thumb-wrapper">
      <img src="${url}" class="photo-thumb" />
      <button class="remove-photo" onclick="_editingPhotos.splice(${i}, 1); renderPhotoPreviews();">✕</button>
    </div>
  `).join('');
}

function renderPhotoPreviews() {
  const container = document.getElementById('edit-route-photos-preview');
  container.innerHTML = _editingPhotos.map((url, i) => `
    <div class="photo-thumb-wrapper">
      <img src="${url}" class="photo-thumb" />
      <button class="remove-photo" onclick="_editingPhotos.splice(${i}, 1); renderPhotoPreviews();">✕</button>
    </div>
  `).join('');
}

function closeEditRouteModal() {
  document.getElementById('edit-route-modal').classList.add('hidden');
  _editingRouteId = null;
  _editingPhotos = [];
}

async function saveRouteEdit() {
  const route = window._savedRoutes?.find(r => r.id === _editingRouteId);
  if (!route) return;

  const newTitle = document.getElementById('edit-route-title').value.trim();
  const newNote = document.getElementById('edit-route-note').value.trim();
  const token = localStorage.getItem('token');
  const errorEl = document.getElementById('edit-route-error');

  if (!newTitle) {
    errorEl.textContent = 'Название не может быть пустым';
    return;
  }

  try {
    const res = await fetch(`/api/routes/${_editingRouteId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        title: newTitle,
        note: newNote,
        photos: _editingPhotos  // Пока храним в JSON (для MVP ок)
      })
    });

    if (res.ok) {
      route.title = newTitle;
      route.note = newNote;
      route.photos = _editingPhotos;
      renderSavedRoutes(window._savedRoutes);
      closeEditRouteModal();
    } else {
      const data = await res.json();
      errorEl.textContent = data.error || 'Ошибка сохранения';
    }
  } catch (e) {
    errorEl.textContent = 'Ошибка соединения с сервером';
  }
}

// ===== РЕДАКТИРОВАНИЕ ПРОФИЛЯ =====

function showEditProfile() {
  document.getElementById('edit-profile-form').classList.remove('hidden');
  // Предзаполняем имя
  const currentName = document.getElementById('account-name').textContent;
  document.getElementById('edit-name').value = currentName;
  // Очищаем поля пароля
  document.getElementById('edit-password').value = '';
  document.getElementById('edit-password-confirm').value = '';
  document.getElementById('edit-error').textContent = '';
}

function hideEditProfile() {
  document.getElementById('edit-profile-form').classList.add('hidden');
  document.getElementById('edit-error').textContent = '';
}

async function saveProfile() {
  const token = localStorage.getItem('token');
  if (!token) return;

  const name = document.getElementById('edit-name').value.trim();
  const password = document.getElementById('edit-password').value;
  const passwordConfirm = document.getElementById('edit-password-confirm').value;
  const errorEl = document.getElementById('edit-error');

  // Проверки
  if (!name && !password) {
    errorEl.textContent = 'Заполните хотя бы одно поле';
    return;
  }

  if (name && name.length < 2) {
    errorEl.textContent = 'Имя должно быть не короче 2 символов';
    return;
  }

  if (password && password.length < 6) {
    errorEl.textContent = 'Пароль должен быть не короче 6 символов';
    return;
  }

  if (password && password !== passwordConfirm) {
    errorEl.textContent = 'Пароли не совпадают';
    return;
  }

  // Отправляем
  const body = {};
  if (name) body.name = name;
  if (password) body.password = password;

  try {
    const res = await fetch('/api/auth/me', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(body)
    });

    const data = await res.json();

    if (res.ok) {
      // Обновляем отображаемое имя
      document.getElementById('account-name').textContent = data.user.name;
      hideEditProfile();
      alert('Профиль обновлён!');
    } else {
      errorEl.textContent = data.error || 'Ошибка обновления';
    }
  } catch (e) {
    errorEl.textContent = 'Ошибка соединения с сервером';
  }
}

// ===== ПЕРЕИМЕНОВАНИЕ МАРШРУТА =====

async function renameRoutePrompt(routeId) {
  const currentTitle = document.getElementById(`route-title-${routeId}`)?.textContent || '';
  const newTitle = prompt('Новое название маршрута:', currentTitle);
  
  if (!newTitle || newTitle.trim() === '' || newTitle.trim() === currentTitle) return;

  const token = localStorage.getItem('token');
  if (!token) return;

  try {
    const res = await fetch(`/api/routes/${routeId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ title: newTitle.trim() })
    });

    if (res.ok) {
      // Обновляем название в DOM
      const titleEl = document.getElementById(`route-title-${routeId}`);
      if (titleEl) titleEl.textContent = newTitle.trim();
      // Обновляем кэш
      const route = window._savedRoutes?.find(r => r.id === routeId);
      if (route) route.title = newTitle.trim();
    } else {
      const data = await res.json();
      alert(data.error || 'Ошибка переименования');
    }
  } catch (e) {
    alert('Ошибка соединения с сервером');
  }
}

// ===== ГОСТЕВОЙ РЕЖИМ =====

function continueAsGuest() {
  // Скрываем оверлей авторизации
  document.getElementById('auth-overlay').classList.remove('active');
  // Показываем приложение
  document.getElementById('app').classList.remove('hidden');
  // Сохраняем флаг гостя
  localStorage.setItem('guest', 'true');
  // Отображаем гостевое имя
  document.getElementById('account-name').textContent = 'Гость';
  document.getElementById('account-email').textContent = 'гостевой режим';
  // Показываем главную
  showPage('home');
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('guest');
  // Показываем оверлей
  document.getElementById('auth-overlay').classList.add('active');
  document.getElementById('app').classList.add('hidden');
  // Показываем форму регистрации
  showRegister();
}

// ===== УДАЛЕНИЕ АККАУНТА =====

async function deleteAccount() {
  const confirmed = confirm(
    'Вы уверены, что хотите удалить аккаунт?\n\n' +
    'Это действие нельзя отменить. Все ваши маршруты будут удалены.'
  );
  
  if (!confirmed) return;

  const doubleConfirmed = confirm(
    'Точно? Введите OK для подтверждения.'
  );
  
  if (!doubleConfirmed) return;

  const token = localStorage.getItem('token');
  if (!token) return;

  try {
    const res = await fetch('/api/auth/me', {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (res.ok) {
      alert('Аккаунт удалён. Возвращайтесь!');
      logout();
    } else {
      const data = await res.json();
      alert(data.error || 'Ошибка удаления аккаунта');
    }
  } catch (e) {
    alert('Ошибка соединения с сервером');
  }
}

// ===== РЕДАКТИРОВАНИЕ МАРШРУТА =====

function addPointToRoute() {
  document.getElementById('add-point-form').classList.remove('hidden');
  document.getElementById('new-point-name').value = '';
  document.getElementById('add-point-status').textContent = '';
  document.getElementById('new-point-name').focus();
}

function cancelAddPoint() {
  document.getElementById('add-point-form').classList.add('hidden');
  document.getElementById('add-point-status').textContent = '';
}

async function confirmAddPoint() {
  const name = document.getElementById('new-point-name').value.trim();
  const statusEl = document.getElementById('add-point-status');
  
  if (!name) {
    statusEl.textContent = 'Введите название места';
    statusEl.style.color = 'var(--error)';
    return;
  }

  statusEl.textContent = 'Ищем ближайшее...';
  statusEl.style.color = 'var(--text-muted)';

  const points = window._currentRoutePoints || [];
  if (points.length < 2) {
    statusEl.textContent = 'Нет маршрута для добавления';
    statusEl.style.color = 'var(--error)';
    return;
  }

  // Ищем ближайшую точку маршрута к старту 
  const startCoords = points[0].coords;
  const endCoords = points[points.length - 1].coords;

  try {
    // Запрашиваем ДО 5 результатов, чтобы выбрать ближайший
    const res = await fetch('/api/geo/geocode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        places: [{ name }], 
        city: 'Москва',
        near_lat: startCoords[0],
        near_lon: startCoords[1],
        radius_km: 8.0,
        limit: 5  
      }),
    });

    const data = await res.json();
    
    if (!res.ok || !data.length || !data[0].coords) {
      statusEl.textContent = 'Место не найдено. Уточните: «Название, Москва»';
      statusEl.style.color = 'var(--error)';
      return;
    }

    let bestPoint = null;
    let bestDist = Infinity;
    let bestInsertAfter = 1;  

    for (const result of data) {
      if (!result.coords) continue;
      
      const [rlat, rlon] = result.coords;
      
      for (let i = 0; i < points.length - 1; i++) {
        const [plat, plon] = points[i].coords;
        const dist = haversineDistance(plat, plon, rlat, rlon);
        
        if (dist < bestDist) {
          bestDist = dist;
          bestPoint = result;
          bestInsertAfter = i + 1;  // Вставляем после ближайшей точки
        }
      }
    }

    if (!bestPoint) {
      statusEl.textContent = 'Не удалось найти подходящее место';
      statusEl.style.color = 'var(--error)';
      return;
    }

    // Не вставляем слишком близко к существующим точкам (меньше 100м)
    if (bestDist < 100) {
      statusEl.textContent = 'Такое место уже есть на маршруте (слишком близко)';
      statusEl.style.color = 'var(--error)';
      return;
    }

    const newPoint = {
      name: name,
      coords: bestPoint.coords,
      desc: bestPoint.description || `Добавлено (${(bestDist/1000).toFixed(2)} км от маршрута)`,
      price: '',
      rating: null,
      opening_hours: '',
      wheelchair: '',
    };

    // Вставляем после ближайшей точки
    window._currentRoutePoints.splice(bestInsertAfter, 0, newPoint);
    
    renderRoutePoints();
    cancelAddPoint();
    initResultMap(window._currentRoutePoints, window._routeTransport);
    
    console.log(`[ROUTE] Добавлено: ${name} после точки ${bestInsertAfter-1} (${(bestDist/1000).toFixed(2)} км)`);
    
  } catch (e) {
    statusEl.textContent = 'Ошибка соединения с сервером';
    statusEl.style.color = 'var(--error)';
  }
}


function haversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI/180) * Math.cos(lat2 * Math.PI/180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

function removePoint(index) {
  if (index <= 0) return; 
  
  const points = window._currentRoutePoints;
  if (!points || index >= points.length) return;

  const name = points[index].name;
  points.splice(index, 1);
  
  renderRoutePoints();
  
  // Обновляем карту
  initResultMap(points, window._routeTransport);
  
  console.log(`[ROUTE] Удалена точка: ${name}`);
}

function regenerateRoute() {
  const points = window._currentRoutePoints;
  if (!points || points.length < 2) {
    alert('Нужно минимум 2 точки для маршрута');
    return;
  }

  // Показываем лоадер
  const loadingEl = document.createElement('div');
  loadingEl.className = 'loading-overlay';
  loadingEl.id = 'loading-overlay';
  loadingEl.innerHTML = '<div class="spinner"></div><p>Перестраиваем маршрут...</p>';
  document.body.appendChild(loadingEl);

  // Отправляем точки на перестроение
  const token = localStorage.getItem('token');
  fetch('/api/ai/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      location: points[0].name,
      transport: window._routeTransport,
      categories: surveyData?.categories || [],
      daytime: surveyData?.daytime || 'day',
      company: surveyData?.company || 'solo',
      budget: surveyData?.budget || 'medium',
      // Важно: передаём координаты для перестроения
      include: points.slice(1).map(p => p.name).join(', '),
    }),
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('loading-overlay')?.remove();
    if (data.places && data.places.length >= 2) {
      const newPoints = data.places
        .filter(p => p.coords)
        .map(p => ({
          name: p.name,
          coords: p.coords,
          desc: p.description || '',
          price: p.price || '',
          rating: p.rating || null,
          opening_hours: p.opening_hours || '',
          wheelchair: p.wheelchair || '',
        }));
      showRouteResult({ meta: data.meta, points: newPoints });
    } else {
      alert('Не удалось перестроить маршрут. Попробуйте изменить набор точек.');
    }
  })
  .catch(() => {
    document.getElementById('loading-overlay')?.remove();
    alert('Ошибка соединения с сервером');
  });
}
