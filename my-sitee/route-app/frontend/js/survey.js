// ===== SURVEY MODULE =====

const API_BASE_SURVEY = '/api';
let currentStep = 0;
const surveyData = {};

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function opt(key, val, label) {
  const sel = surveyData[key] === val ? 'selected' : '';
  return `<button class="option-btn ${sel}" onclick="selectOpt('${key}','${val}',this)">
    ${label}
  </button>`;
}

function multi(key, val, label) {
  if (!surveyData[key]) surveyData[key] = [];
  const sel = surveyData[key].includes(val) ? 'selected' : '';
  return `<button class="option-btn tag-btn ${sel}" onclick="toggleOpt('${key}','${val}',this)">
    ${label}
  </button>`;
}

function selectOpt(key, val, el) {
  surveyData[key] = val;
  el.closest('.option-grid').querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
  el.classList.add('selected');
}

function toggleOpt(key, val, el) {
  if (!surveyData[key]) surveyData[key] = [];
  const idx = surveyData[key].indexOf(val);
  if (idx === -1) { surveyData[key].push(val); el.classList.add('selected'); }
  else            { surveyData[key].splice(idx, 1); el.classList.remove('selected'); }
}

// ── Шаги анкеты ───────────────────────────────────────────────────────────
function getSteps() {
  return [

    // Шаг 1: Старт
    {
      id: 'location',
      title: 'Откуда начинаем?',
      desc: 'Введите адрес, район или название места',
      render: () => `
        <input class="survey-input" id="s-location"
          placeholder="Например: Арбат, Москва или Невский проспект, СПб"
          value="${surveyData.location || ''}" />
        <p class="field-hint">Чем точнее адрес — тем лучше маршрут</p>
        <button class="btn-secondary btn-sm" onclick="getMyLocation()" style="width:100%;margin-bottom:8px;">
          📍 Определить моё местоположение
        </button>
        <div style="margin-top:12px">
          <button class="btn-metro" onclick="openMetroSuggest()">
            🚇 Подобрать станцию метро
          </button>
        </div>
        <div id="metro-result" class="metro-result hidden"></div>
      `,
      save: () => { surveyData.location = document.getElementById('s-location').value.trim(); },
      validate: () => {
        if (!document.getElementById('s-location').value.trim()) {
          showStepError('Укажите место старта'); return false;
        }
        return true;
      }
    },

    // Шаг 2: Время и расстояние
    {
      id: 'duration',
      title: '⏱️ Сколько времени?',
      desc: 'Выберите длительность прогулки',
      render: () => `
        <div class="option-grid cols-4">
          ${opt('duration', '1',  '1 час')}
          ${opt('duration', '2',  '2 часа')}
          ${opt('duration', '3',  '3 часа')}
          ${opt('duration', '4',  '4 часа')}
        </div>
        <p class="field-label" style="margin-top:20px">Или расстояние</p>
        <div class="option-grid cols-3">
          ${opt('distance', '1-3',  '1–3 км')}
          ${opt('distance', '3-6',  '3–6 км')}
          ${opt('distance', '6-10', '6–10 км')}
        </div>
      `,
      save: () => {},
      validate: () => true
    },

    // Шаг 3: Что хочет посетить
    {
      id: 'places',
      title: '✨ Что хотите посетить?',
      desc: 'Выберите одно или несколько',
      render: () => `
        <div class="option-grid cols-3">
          ${multi('categories', 'cafe',           'Кафе')}
          ${multi('categories', 'restaurant',     'Ресторан')}
          ${multi('categories', 'bar',            'Бар')}
          ${multi('categories', 'fast_food',      'Уличная еда')}
          ${multi('categories', 'park',           'Парк')}
          ${multi('categories', 'embankment',     'Набережная')}
          ${multi('categories', 'forest',         'Лесопарк')}
          ${multi('categories', 'viewpoint',      'Смотровая')}
          ${multi('categories', 'museum',        'Музей')}
          ${multi('categories', 'gallery',        'Галерея')}
          ${multi('categories', 'attraction',     'Достопримечательность')}
          ${multi('categories', 'entertainment',  'Развлечения')}
          ${multi('categories', 'sport',          'Спорт')}
          ${multi('categories', 'shopping',       'Шопинг')}
          ${multi('categories', 'supermarket',    'Магазин')}
          ${multi('categories', 'zoo',            'Зоопарк')}
        </div>
      `,
      save: () => {},
      validate: () => {
        if (!surveyData.categories || surveyData.categories.length === 0) {
          showStepError('Выберите хотя бы одно место'); return false;
        }
        return true;
      }
    },

    // Шаг 4: Компания и время суток
    {
      id: 'context',
      title: ' С кем и когда?',
      desc: 'Это поможет подобрать подходящие места',
      render: () => `
        <p class="field-label">С кем идёте?</p>
        <div class="option-grid cols-3">
          ${opt('company', 'solo',     'Один / одна')}
          ${opt('company', 'partner',  'С партнёром')}
          ${opt('company', 'kids',     'С детьми')}
          ${opt('company', 'friends',  'С друзьями')}
          ${opt('company', 'elderly',  'С пожилыми')}
        </div>
        <p class="field-label" style="margin-top:20px">Время суток</p>
        <div class="option-grid cols-4">
          ${opt('daytime', 'morning',  'Утро')}
          ${opt('daytime', 'day',     'День')}
          ${opt('daytime', 'evening',  'Вечер')}
          ${opt('daytime', 'night',    'Ночь')}
        </div>
      `,
      save: () => {},
      validate: () => true
    },

        // Шаг 4.5: Интенсивность и безопасность
    {
      id: 'safety',
      title: ' Стиль и безопасность',
      desc: 'Выберите темп прогулки и предпочтения по маршруту',
      render: () => `
        <p class="field-label">Интенсивность</p>
        <div class="option-grid cols-3">
          ${opt('intensity', 'chill',   'Спокойная')}
          ${opt('intensity', 'active',  'Активная')}
          ${opt('intensity', 'sport',   'Спорт / бег')}
        </div>
        <p class="field-label" style="margin-top:20px">Безопасность дорог</p>
        <div class="option-grid cols-2">
          ${opt('safety', 'parks',     'Парки и пешеходные зоны')}
          ${opt('safety', 'any',       'Любые дороги')}
        </div>
        <p class="field-label" style="margin-top:20px">Особые потребности</p>
        <div class="option-grid cols-2">
          ${opt('accessibility', 'none',     'Нет')}
          ${opt('accessibility', 'stroller', 'Прогулка с коляской')}
          ${opt('accessibility', 'limited',  'Ограниченная мобильность')}
        </div>
        <p class="field-label" style="margin-top:20px">Наличие скамеек</p>
        <div class="option-grid cols-2">
          ${opt('benches', 'yes',  'Важно')}
          ${opt('benches', 'no',   'Не важно')}
        </div>
        <p class="field-label" style="margin-top:20px">Стиль вело (если на велосипеде)</p>
        <div class="option-grid cols-3">
          ${opt('bike_speed', 'slow',    'Спокойный (до 15 км/ч)')}
          ${opt('bike_speed', 'medium',  'Средний (до 20 км/ч)')}
          ${opt('bike_speed', 'fast',    'Быстрый (25+ км/ч)')}
        </div>
      `,
      save: () => {},
      validate: () => true
    },
    
    // Шаг 5: Дополнительно (необязательно)
    {
      id: 'extra',
      title: ' Дополнительно',
      desc: 'Необязательно — можно пропустить',
      render: () => `
        <p class="field-label">Тип передвижения</p>
        <div class="option-grid cols-3">
          ${opt('transport', 'walk',   'Пешком')}
          ${opt('transport', 'bike',   'Велосипед')}
          ${opt('transport', 'mixed', 'Смешанный')}
        </div>
                <p class="field-label" style="margin-top:20px">Бюджет</p>
        <div class="option-grid cols-2">
          ${opt('budget', 'free',       'Только бесплатное')}
          ${opt('budget', 'economy',  'Эконом')}
          ${opt('budget', 'medium', 'Средний')}
          ${opt('budget', 'unlimited', 'Без ограничений')}
        </div>
        <div id="budget-custom-group" class="${surveyData.budget === 'custom' ? '' : 'hidden'}" style="margin-top:8px;">
          <input class="survey-input" id="s-budget-amount" type="number"
            placeholder="Максимальная сумма на человека (₽)"
            value="${surveyData.budgetAmount || ''}" />
        </div>
        <button class="btn-secondary btn-sm" onclick="setCustomBudget()" style="margin-top:8px;">
          💵 Своя сумма
        </button>
        <input class="survey-input" id="s-include"
          placeholder="Например: Парк Горького (необязательно)"
          value="${surveyData.include || ''}" />
      `,
      save: () => {
        surveyData.include = document.getElementById('s-include')?.value.trim();
        const budgetEl = document.getElementById('s-budget-amount');
        if (budgetEl && budgetEl.value) {
          surveyData.budgetAmount = budgetEl.value;
        }
      },
      validate: () => true
    },
  ];
}

function getMyLocation() {
  if (!navigator.geolocation) {
    alert('Геолокация не поддерживается браузером');
    return;
  }
  
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;
      document.getElementById('s-location').value = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
      surveyData.location = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    },
    () => {
      alert('Не удалось определить местоположение. Введите адрес вручную.');
    }
  );
}

// ── Рендер ────────────────────────────────────────────────────────────────
function renderSurvey() {
  const steps = getSteps();
  const step  = steps[currentStep];
  document.getElementById('survey-steps').innerHTML = `
    <div class="survey-step">
      <div class="step-header">
        <span class="step-badge">Шаг ${currentStep + 1} из ${steps.length}</span>
        <h2>${step.title}</h2>
        <p class="step-desc">${step.desc}</p>
      </div>
      ${step.render()}
      <p class="step-error" id="step-error"></p>
    </div>
  `;
  const pct = ((currentStep + 1) / steps.length * 100).toFixed(0);
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-label').textContent = `${currentStep + 1} из ${steps.length}`;
  document.getElementById('btn-prev').style.display = currentStep > 0 ? 'inline-flex' : 'none';
  document.getElementById('btn-next').textContent =
    currentStep === steps.length - 1 ? ' Создать маршрут' : 'Далее →';
}

function showStepError(msg) {
  const el = document.getElementById('step-error');
  if (el) el.textContent = msg;
}

function surveyNext() {
  const steps = getSteps();
  steps[currentStep].save();
  if (!steps[currentStep].validate()) return;
  if (currentStep < steps.length - 1) {
    currentStep++;
    renderSurvey();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } else {
    submitSurvey();
  }
}

function surveyPrev() {
  const steps = getSteps();
  steps[currentStep].save();
  if (currentStep > 0) { currentStep--; renderSurvey(); }
}

// ── Отправка ──────────────────────────────────────────────────────────────
async function submitSurvey() {
  showLoading('Ищем места поблизости...');
  try {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_BASE_SURVEY}/ai/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(surveyData),
    });

    const data = await res.json();
    hideLoading();

    if (!res.ok) {
      alert(data.error || 'Ошибка при генерации маршрута');
      return;
    }

    // Проверяем данные
    console.log('Ответ от сервера:', data);
    console.log('places:', data.places);
    console.log('meta:', data.meta);

    if (!data.places || data.places.length < 2) {
      alert('Не удалось найти места поблизости.');
      return;
    }

    const points = data.places
      .filter(p => p.coords)
      .map(p => ({
        name:        p.name,
        coords:      p.coords,
        desc:        p.description,
        price:       p.price || '',
        rating:      p.rating || null,
        opening_hours: p.opening_hours || '',
        wheelchair:    p.wheelchair || '',
      }));

    console.log('Обработанные points:', points);
    showRouteResult({ meta: data.meta, points });
  } catch (e) {
    hideLoading();
    console.error('Ошибка:', e);
    alert('Не удалось подключиться к серверу. Убедитесь что бэкенд запущен.');
  }
}

// ── Результат ─────────────────────────────────────────────────────────────
function showRouteResult(result) {
  const metaEl = document.getElementById('result-meta');
  if (result.meta) {
    const parts = result.meta.split('·').map(s => s.trim());
    metaEl.innerHTML = parts.map((p, i) =>
      `<span class="result-meta-chip${i === 1 ? ' highlight' : ''}">${escapeHtml(p)}</span>`
    ).join('');
  }

  const daytime = surveyData?.daytime || '';
  const warningBox = document.getElementById('warning-box');
  if (warningBox) {
    warningBox.style.display = (daytime === 'evening' || daytime === 'night') ? 'block' : 'none';
  }

  window._currentRoutePoints = JSON.parse(JSON.stringify(result.points));
  window._routeTransport = surveyData?.transport || 'walk';

  renderRoutePoints();
  showPage('result');

  window._lastRouteResult = {
    places: result.points,
    meta: result.meta || '',
  };

  setTimeout(() => {
    initResultMap(result.points, window._routeTransport);
  }, 150);
}

function renderRoutePoints() {
  const points = window._currentRoutePoints || [];
  const list = document.getElementById('result-point-list');
  const countEl = document.getElementById('route-points-count');

  if (countEl) countEl.textContent = `${points.length} точек`;

  list.innerHTML = points.map((p, i) => {
    const stars  = p.rating ? '⭐'.repeat(Math.min(Math.round(p.rating), 5)) : '';
    const price  = p.price  ? `<span class="point-price">${p.price}</span>` : '';
    const desc   = p.desc || p.description || '';
    const hours  = p.opening_hours ? `<p class="point-hours">🕐 ${p.opening_hours}</p>` : '';
    
    let wheel = '';
    if (p.wheelchair === 'yes') {
      wheel = '<span class="point-badge" style="background:rgba(76,175,125,0.15);color:#4caf7d;">♿ Доступно</span>';
    } else if (p.wheelchair === 'no') {
      wheel = '<span class="point-badge" style="background:rgba(240,96,96,0.15);color:#f06060;">⚠️ Недоступно</span>';
    } else if (surveyData?.accessibility && surveyData.accessibility !== 'none') {
      wheel = '<span class="point-badge" style="background:rgba(255,193,7,0.15);color:#e6a800;">❓ Доступность неизвестна</span>';
    }
    
    const isStart = i === 0;
    return `
      <div class="point-item" id="point-${i}">
        <span class="point-num">${i + 1}</span>
        <div style="flex:1;">
          <strong>${escapeHtml(p.name)} ${isStart ? '<span style="font-size:0.75rem;color:var(--primary);">(старт)</span>' : ''}</strong>
          <div class="point-meta-row">${stars}${price}</div>
          <p>${escapeHtml(desc)}</p>
          ${hours}${wheel}
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;align-items:flex-end;">
          ${!isStart ? `<button class="btn-danger btn-sm" onclick="removePoint(${i})" title="Убрать">✕</button>` : ''}
          <button class="btn-secondary btn-sm" onclick="openInYandexMaps(${p.coords[0]}, ${p.coords[1]}, '${escapeHtml(p.name.replace(/'/g, "\\'"))}')" title="Открыть в Яндекс.Картах" style="font-size:0.75rem;">🗺️</button>
        </div>
      </div>`;
  }).join('');

  window._lastRouteResult = {
    places: points,
    meta: window._lastRouteResult?.meta || '',
  };
}

function openInYandexMaps(lat, lon, name) {
  const url = `https://yandex.ru/maps/?ll=${lon}%2C${lat}&z=16&pt=${lon}%2C${lat}&text=${encodeURIComponent(name)}`;
  window.open(url, '_blank');
}

function showLoading(text) {
  const el = document.createElement('div');
  el.className = 'loading-overlay';
  el.id = 'loading-overlay';
  el.innerHTML = `<div class="spinner"></div><p>${text}</p>`;
  document.body.appendChild(el);
}

function hideLoading() {
  document.getElementById('loading-overlay')?.remove();
}

function initSurvey() {
  currentStep = 0;
  Object.keys(surveyData).forEach(k => delete surveyData[k]);
  renderSurvey();
}

// ── Подбор метро ──────────────────────────────────────────────────────────
async function openMetroSuggest() {
  const btn = document.querySelector('.btn-metro');
  const box = document.getElementById('metro-result');
  if (!box) return;

  btn.disabled = true;
  btn.textContent = ' Подбираем...';
  box.classList.add('hidden');
  box.innerHTML = '';

  try {
    const res = await fetch(`${API_BASE_SURVEY}/ai/suggest-metro`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        categories: surveyData.categories || [],
        city: 'Москва',
      }),
    });
    const text = await res.text();
    console.log('Ответ сервера:', text);
    const data = JSON.parse(text);
    if (!res.ok || !data.stations?.length) {
      box.innerHTML = '<p class="field-hint" style="color:var(--error)">Не удалось подобрать станции. Введите адрес вручную.</p>';
      box.classList.remove('hidden');
      return;
    }

    box.innerHTML = `
      <p class="field-label" style="margin-top:16px">Подходящие станции метро:</p>
      <div class="metro-list">
        ${data.stations.map(s => `
          <button class="metro-station-btn" onclick="selectMetro('${s.name.replace(/'/g,"\\'")}')">
            <span class="metro-icon">🚇</span>
            <div>
              <strong>${s.name}</strong>
              <p>${s.description}</p>
            </div>
          </button>
        `).join('')}
      </div>`;
    box.classList.remove('hidden');
  } catch (e) {
    box.innerHTML = '<p class="field-hint" style="color:var(--error)">Ошибка подключения к серверу.</p>';
    box.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = ' Подобрать станцию метро';
  }
}

function selectMetro(stationName) {
  const input = document.getElementById('s-location');
  if (input) {
    input.value = `Метро ${stationName}, Москва`;
    surveyData.location = input.value;
  }
  // Подсвечиваем выбранную кнопку
  document.querySelectorAll('.metro-station-btn').forEach(b => b.classList.remove('selected'));
  event.currentTarget.classList.add('selected');
}

function setCustomBudget() {
  surveyData.budget = 'custom';
  document.getElementById('budget-custom-group').classList.remove('hidden');
  document.querySelectorAll('#page-survey .option-btn').forEach(b => {
    b.classList.remove('selected');
    if (b.textContent.includes('Своя')) b.classList.add('selected');
  });
}