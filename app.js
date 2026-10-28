document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const elements = {
        prevYear: document.getElementById('prevYear'),
        nextYear: document.getElementById('nextYear'),
        currentYearDisplay: document.getElementById('currentYearDisplay'),
        calendarGrid: document.getElementById('calendarGrid'),
        loadingState: document.getElementById('loadingState'),
        totalHolidays: document.getElementById('totalHolidays'),
        nationalHolidays: document.getElementById('nationalHolidays'),
        makeupWorkdays: document.getElementById('makeupWorkdays'),
        continuousHolidaysContainer: document.getElementById('continuousHolidaysContainer'),
        nextHolidayCard: document.getElementById('nextHolidayCard'),
        leaveStrategiesSection: document.getElementById('leaveStrategiesSection'),
        leaveStrategiesContainer: document.getElementById('leaveStrategiesContainer'),
        leaveStrategiesMore: document.getElementById('leaveStrategiesMore'),
        strategyMoreBtn: document.getElementById('strategyMoreBtn'),
        strategySubtitle: document.getElementById('strategySubtitle'),
        languageToggle: document.getElementById('languageToggle'),
        langToggleBtn: document.getElementById('langToggleBtn'),
        lunarToggleBtn: document.getElementById('lunarToggleBtn'),
        jumpTodayBtn: document.getElementById('jumpTodayBtn'),
        shareBtn: document.getElementById('shareBtn'),
        faqSection: document.getElementById('faq'),
        faqLangNote: document.getElementById('faqLangNote'),
        tooltip: document.getElementById('tooltip'),
        toast: document.getElementById('toast')
    };

    // "今天" 只算一次，所有「已過／接下來」判斷都以這個為準
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayKey = toDateKey(today);
    const todayYear = today.getFullYear();
    const initialTitle = document.title;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // State
    let state = {
        currentYear: todayYear,
        holidaysData: [],
        availableYears: [],
        lunarVisible: true,
        strategiesExpanded: false
    };

    // `${lang}:${year}` -> data array；切換語言／年份不重抓
    const dataCache = new Map();

    // Constants and Translations
    const translations = {
        zh: {
            h1: "台灣國定假日行事曆",
            brandTag: "Taiwan Holidays",
            subtitle: "國定假日、連假、補班日與請假攻略一次看；工程師可直接用 JSON API 與 MCP 串接。",
            skipLink: "跳到行事曆",
            apiLink: "API 說明",
            mcpLink: "AI / MCP",
            yearGroup: "選擇年份",
            prevYear: "上一年",
            nextYear: "下一年",
            jumpToday: "今天",
            jumpTodayTitle: "跳到今天所在的月份",
            lunarToggleText: "農民曆",
            lunarToggle: "顯示農民曆",
            langToggle: "Switch to English",
            share: "分享",
            shareAria: "分享這個頁面",
            shareTo: "分享：",
            shareCopied: "已複製連結",
            copy: "複製",
            copied: "已複製",
            copyFailed: "無法複製，請手動選取",
            totalHolidaysLabel: "休假日總數",
            nationalHolidaysLabel: "國定假日",
            makeupLabel: "補班日",
            strategyTitle: "聰明請假攻略",
            strategySubUpcoming: "接下來 ${n} 個請假機會，依日期排序",
            strategySubPast: "這一年的 ${n} 則攻略都已過期",
            showAll: "看全年 ${n} 則",
            showAllWithPast: "看全年 ${n} 則（含已過 ${past} 則）",
            showLess: "收合，只看接下來的",
            best: "最划算",
            past: "已過",
            badgeTotal: "連休 ${total} 天",
            badgeLeave: "請假 ${leave} 天",
            altOption: "也可以：${range} 請 ${leave} 天，連休 ${total} 天",
            strategyAria: "${name}：${range} 請假 ${leave} 天，可連休 ${total} 天",
            loading: "載入資料中...",
            footerSource: "資料來源：中華民國行政院人事行政總處。",
            monthNames: ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"],
            dayNames: ["日", "一", "二", "三", "四", "五", "六"],
            holidayTag: "休假日",
            workdayTag: "補班日",
            holidays: "國定假日",
            noHolidays: "無國定假日",
            currentMonthTag: "本月",
            todayLabel: "今天",
            errorHolidays: "找不到 ${year} 年的假期資料",
            errorHint: "可能是資料尚未發布，或網路暫時不通。",
            refresh: "重新整理",
            viewJson: "看 JSON 版",
            dayWord: "天",
            continuousTag: "連假",
            weekendHoliday: "週末連假",
            legendHoliday: "放假日",
            legendMakeup: "需請假",
            heroNext: "下一個連假",
            heroNextHoliday: "下一個國定假日",
            heroNow: "放假中",
            heroCountdown: "還有 ${days} 天",
            heroTomorrow: "明天開始",
            heroToday: "今天開始",
            heroRemaining: "還剩 ${days} 天",
            heroDays: "連休 ${days} 天",
            heroSingleDay: "放假 1 天",
            heroTip: "請 ${leave} 天可連休 ${total} 天（${range}）",
            heroViewMonth: "看當月行事曆",
            heroSwitchYear: "切換到 ${year} 年",
            heroNextYearOut: "${year} 年行事曆已公告",
            heroNoMore: "今年的國定假日都放完了，先看明年的吧",
            devTitle: "給開發者與 AI 的入口",
            devSub: "同一份政府公告資料，三種拿法：裸 JSON、MCP 工作日計算引擎、給 LLM 讀的說明文件。免費、免金鑰。",
            devJsonDesc: "每年五個 JSON 檔（全年每日、國定假日、補班日、英文版），由 jsDelivr CDN 直出。",
            devMcpTag: "工作日計算引擎",
            devMcpDesc: "讓 Claude、Cursor 等 AI agent 直接算工作日、扣掉補班、找最划算的請假組合。公開、唯讀、免驗證。",
            devMcpReadme: "MCP 說明與工具列表",
            devLlmTitle: "給 LLM / AI 搜尋引擎",
            devLlmDesc: "把這幾個檔案丟給你的 agent，就能正確使用本站資料，不用猜補班規則。",
            devLlmsShort: "— 精簡索引",
            devLlmsFull: "— 完整說明、欄位定義與陷阱",
            devOpenapi: "— JSON 端點的機器可讀規格",
            starText: "覺得有用？到 GitHub 給個 Star",
            lunarPrefix: "農曆"
        },
        en: {
            h1: "Taiwan Holidays Calendar",
            brandTag: "台灣國定假日行事曆",
            subtitle: "Public holidays, long weekends, makeup workdays and leave strategies at a glance — plus a JSON API and MCP server for developers.",
            skipLink: "Skip to calendar",
            apiLink: "API Docs",
            mcpLink: "AI / MCP",
            yearGroup: "Select year",
            prevYear: "Previous year",
            nextYear: "Next year",
            jumpToday: "Today",
            jumpTodayTitle: "Jump to the current month",
            lunarToggleText: "Lunar",
            lunarToggle: "Show lunar calendar",
            langToggle: "切換成中文",
            share: "Share",
            shareAria: "Share this page",
            shareTo: "Share:",
            shareCopied: "Link copied",
            copy: "Copy",
            copied: "Copied",
            copyFailed: "Copy failed — select the text manually",
            totalHolidaysLabel: "Days off",
            nationalHolidaysLabel: "Public holidays",
            makeupLabel: "Makeup workdays",
            strategyTitle: "Smart Leave Strategies",
            strategySubUpcoming: "${n} upcoming opportunities, in date order",
            strategySubPast: "All ${n} strategies for this year have passed",
            showAll: "Show all ${n}",
            showAllWithPast: "Show all ${n} (${past} past)",
            showLess: "Show upcoming only",
            best: "Best value",
            past: "Past",
            badgeTotal: "${total} days off in a row",
            badgeLeave: "Take ${leave} day(s) leave",
            altOption: "Or: ${range}, take ${leave} day(s) for ${total} off",
            strategyAria: "${name}: take ${leave} day(s) leave on ${range} for ${total} days off",
            loading: "Loading data...",
            footerSource: "Data Source: DGPA, Taiwan.",
            monthNames: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            dayNames: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            holidayTag: "Holiday",
            workdayTag: "Makeup Work",
            holidays: "Holidays",
            noHolidays: "No Holidays",
            currentMonthTag: "This month",
            todayLabel: "Today",
            errorHolidays: "Data not found for ${year}",
            errorHint: "The data may not be published yet, or the network is temporarily unavailable.",
            refresh: "Refresh",
            viewJson: "Open JSON",
            dayWord: "days",
            continuousTag: "Holiday",
            weekendHoliday: "Weekend Holiday",
            legendHoliday: "Day off",
            legendMakeup: "Take leave",
            heroNext: "Next long weekend",
            heroNextHoliday: "Next public holiday",
            heroNow: "Holiday in progress",
            heroCountdown: "in ${days} days",
            heroTomorrow: "starts tomorrow",
            heroToday: "starts today",
            heroRemaining: "${days} day(s) left",
            heroDays: "${days} days off",
            heroSingleDay: "1 day off",
            heroTip: "Take ${leave} day(s) leave for ${total} days off (${range})",
            heroViewMonth: "View that month",
            heroSwitchYear: "Switch to ${year}",
            heroNextYearOut: "${year} calendar is out",
            heroNoMore: "No public holidays left this year — here is next year's first one",
            devTitle: "For developers and AI agents",
            devSub: "The same government-published data, three ways: raw JSON, an MCP workday engine, and LLM-ready docs. Free, no API key.",
            devJsonDesc: "Five JSON files per year (full calendar, holidays, makeup workdays, English versions), served straight from the jsDelivr CDN.",
            devMcpTag: "workday engine",
            devMcpDesc: "Lets Claude, Cursor and other AI agents count workdays, account for makeup days and find the best leave plans. Public, read-only, no auth.",
            devMcpReadme: "MCP docs and tool list",
            devLlmTitle: "For LLMs / AI search engines",
            devLlmDesc: "Hand these files to your agent and it will use this dataset correctly instead of guessing makeup-day rules.",
            devLlmsShort: "— short index",
            devLlmsFull: "— full reference, field definitions and pitfalls",
            devOpenapi: "— machine-readable spec for the JSON endpoints",
            starText: "Found it useful? Star it on GitHub",
            lunarPrefix: "Lunar",
            docTitle: "Taiwan Holidays Calendar ${year} — Public Holidays, Makeup Workdays & Leave Strategies"
        }
    };

    // 連假命名優先序：一段連假裡同時有「補假」「小年夜」「春節」時要叫「春節」，永遠不叫「補假」
    const HOLIDAY_PRIORITY = [
        { re: /春節|除夕|小年夜|Lunar New Year/i, zh: '春節', en: 'Lunar New Year' },
        { re: /清明|民族掃墓|Tomb Sweeping/i, zh: '清明節', en: 'Tomb Sweeping Day' },
        { re: /端午|Dragon Boat/i, zh: '端午節', en: 'Dragon Boat Festival' },
        { re: /中秋|Mid-Autumn/i, zh: '中秋節', en: 'Mid-Autumn Festival' },
        { re: /國慶|National Day/i, zh: '國慶日', en: 'National Day' },
        { re: /開國|New Year's Day/i, zh: '開國紀念日', en: "New Year's Day" },
        { re: /和平紀念|Peace Memorial/i, zh: '和平紀念日', en: 'Peace Memorial Day' },
        { re: /勞動節|Labou?r Day/i, zh: '勞動節', en: 'Labor Day' },
        { re: /兒童節|Children's Day/i, zh: '兒童節', en: "Children's Day" },
        { re: /教師節|孔子|Confucius/i, zh: '教師節', en: "Teachers' Day" },
        { re: /光復|Retrocession/i, zh: '光復節', en: 'Taiwan Retrocession Day' },
        { re: /行憲|Constitution/i, zh: '行憲紀念日', en: 'Constitution Day' }
    ];
    const SKIP_NAME_RE = /補假|補行|調整|彈性|Compensatory|Make-?up|Adjusted|Flexible/i;
    const MAKEUP_WORKDAY_RE = /調整上班|補行上班|補班|Make-?up Workday/i;

    function currentLang() {
        return elements.languageToggle ? (elements.languageToggle.value || 'zh') : 'zh';
    }

    function t(key, params = {}) {
        const lang = currentLang();
        let str = translations[lang][key];
        if (str === undefined) str = translations.zh[key];
        if (str === undefined) return key;

        // Handle array returns
        if (Array.isArray(str)) return str;

        for (const [k, v] of Object.entries(params)) {
            str = str.split(`\${${k}}`).join(v);
        }
        return str;
    }

    function updateStaticTexts() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            el.textContent = t(el.getAttribute('data-i18n'));
        });
        document.querySelectorAll('[data-i18n-aria]').forEach(el => {
            el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria')));
        });
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            el.setAttribute('title', t(el.getAttribute('data-i18n-title')));
        });
        document.querySelectorAll('[data-year-slot]').forEach(el => {
            el.textContent = state.currentYear;
        });
    }

    // Initialize App
    async function init() {
        // Available years come from data/years.json, which scripts/update_calendar.py regenerates
        // whenever it adds a year. If the manifest can't be loaded, fall back to a known range.
        try {
            const res = await fetch('data/years.json');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const manifest = await res.json();
            state.availableYears = manifest.years.map(Number).sort((a, b) => a - b);
            if (state.availableYears.length === 0) throw new Error('empty manifest');
        } catch (error) {
            console.warn('Failed to load data/years.json, using fallback range:', error);
            state.availableYears = Array.from({ length: 11 }, (_, i) => 2017 + i);
        }

        // 預設顯示「今年」（而不是資料裡最新的一年）；超出範圍就夾到最近的一年。
        // ?year=2027 可以直接指定，方便分享與之後的靜態年份頁。
        const minYear = state.availableYears[0];
        const maxYear = state.availableYears[state.availableYears.length - 1];
        let startYear = Math.min(Math.max(todayYear, minYear), maxYear);
        const requested = parseInt(new URLSearchParams(location.search).get('year'), 10);
        if (state.availableYears.includes(requested)) startYear = requested;
        state.currentYear = startYear;
        elements.currentYearDisplay.textContent = state.currentYear;

        // 語言：記住上次選擇（失敗就維持中文）
        try {
            const savedLang = localStorage.getItem('twh-lang');
            if (savedLang === 'en' || savedLang === 'zh') elements.languageToggle.value = savedLang;
        } catch (e) { /* localStorage 不可用時忽略 */ }

        // 手機預設不顯示日格裡的農曆字（太小、太擠）；桌機預設顯示。按鈕仍可切換。
        state.lunarVisible = !window.matchMedia('(max-width: 768px)').matches;
        applyLunarVisibility();

        applyLanguageChrome();
        setupEventListeners();
        updateYearButtons();
        await fetchAndRenderYear(state.currentYear);

        // 非阻塞地載入最新版本號（失敗不影響頁面）
        loadRepoMeta();
    }

    const REPO = 'imsyuan/taiwan-holidays';

    async function loadRepoMeta() {
        try {
            const res = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`);
            if (res.ok) {
                const rel = await res.json();
                const el = document.getElementById('versionBadge');
                if (el && rel.tag_name) {
                    el.textContent = rel.tag_name;
                    if (rel.html_url) el.href = rel.html_url;
                    el.hidden = false;
                }
            }
        } catch (e) { /* 略過：版本徽章維持隱藏 */ }
    }

    // Event Listeners
    function setupEventListeners() {
        elements.prevYear.addEventListener('click', () => changeYear(state.currentYear - 1));
        elements.nextYear.addEventListener('click', () => changeYear(state.currentYear + 1));

        // Hide tooltip on scroll or outside click
        window.addEventListener('scroll', hideTooltip, { passive: true });
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.day-cell.holiday, .day-cell.weekend')) {
                hideTooltip();
            }
        });

        // Lunar toggle
        if (elements.lunarToggleBtn) {
            elements.lunarToggleBtn.addEventListener('click', () => {
                state.lunarVisible = !state.lunarVisible;
                applyLunarVisibility();
            });
        }

        // Language toggle（明確的 中 / EN 文字切換）
        if (elements.langToggleBtn) {
            elements.langToggleBtn.addEventListener('click', () => {
                const newVal = currentLang() === 'zh' ? 'en' : 'zh';
                elements.languageToggle.value = newVal;
                try { localStorage.setItem('twh-lang', newVal); } catch (e) { /* ignore */ }
                elements.languageToggle.dispatchEvent(new Event('change'));
            });
        }

        elements.languageToggle.addEventListener('change', () => {
            applyLanguageChrome();
            fetchAndRenderYear(state.currentYear);
        });

        // 「今天」：回到今年並捲到本月
        if (elements.jumpTodayBtn) {
            elements.jumpTodayBtn.addEventListener('click', () => jumpToMonth(todayYear, today.getMonth()));
        }

        // 分享：優先用系統分享面板，不支援就複製連結
        if (elements.shareBtn) {
            elements.shareBtn.addEventListener('click', sharePage);
        }

        // 複製程式碼片段
        document.querySelectorAll('[data-copy-target]').forEach(btn => {
            btn.addEventListener('click', () => {
                const target = document.getElementById(btn.getAttribute('data-copy-target'));
                if (!target) return;
                copyText(target.textContent.trim()).then(ok => {
                    const original = t('copy');
                    btn.textContent = ok ? t('copied') : t('copyFailed');
                    btn.classList.toggle('is-done', ok);
                    setTimeout(() => {
                        btn.textContent = original;
                        btn.classList.remove('is-done');
                    }, 1600);
                });
            });
        });

        // 攻略：展開／收合全年
        elements.strategyMoreBtn.addEventListener('click', () => {
            state.strategiesExpanded = !state.strategiesExpanded;
            syncStrategyMore();
        });

        // 連假 chip 捲動列：到底時拿掉右側漸層提示
        elements.continuousHolidaysContainer.addEventListener('scroll', updateChipScrollHint, { passive: true });
        window.addEventListener('resize', updateChipScrollHint);
    }

    function applyLunarVisibility() {
        elements.calendarGrid.classList.toggle('hide-lunar', !state.lunarVisible);
        if (elements.lunarToggleBtn) {
            elements.lunarToggleBtn.setAttribute('aria-pressed', String(state.lunarVisible));
            elements.lunarToggleBtn.classList.toggle('is-off', !state.lunarVisible);
        }
    }

    // 語言切換時連 <html lang>、document.title、按鈕狀態、FAQ 一起換
    function applyLanguageChrome() {
        const lang = currentLang();
        document.documentElement.lang = lang === 'en' ? 'en' : 'zh-TW';
        document.title = lang === 'en' ? t('docTitle', { year: state.currentYear }) : initialTitle;

        if (elements.langToggleBtn) {
            elements.langToggleBtn.querySelectorAll('.lang-opt').forEach(opt => {
                opt.classList.toggle('is-active', opt.getAttribute('data-lang') === lang);
            });
        }

        // FAQ 目前只有中文：英文模式下收起並留一行說明，避免整段中文塞給英文使用者
        if (elements.faqSection) {
            elements.faqSection.querySelector('.faq-list').hidden = lang === 'en';
            if (elements.faqLangNote) elements.faqLangNote.hidden = lang !== 'en';
        }

        updateStaticTexts();
    }

    async function changeYear(year) {
        if (!state.availableYears.includes(year) || year === state.currentYear) return;
        state.currentYear = year;
        state.strategiesExpanded = false;
        elements.currentYearDisplay.textContent = year;
        updateYearButtons();
        updateStaticTexts();
        if (currentLang() === 'en') document.title = t('docTitle', { year });
        try {
            const url = year === todayYear ? location.pathname : `${location.pathname}?year=${year}`;
            history.replaceState(null, '', url);
        } catch (e) { /* file:// 等環境可能不允許 */ }
        await fetchAndRenderYear(year);
    }

    function updateYearButtons() {
        elements.prevYear.disabled = state.currentYear <= state.availableYears[0];
        elements.nextYear.disabled = state.currentYear >= state.availableYears[state.availableYears.length - 1];
    }

    async function loadYearData(year, lang = currentLang()) {
        const key = `${lang}:${year}`;
        if (dataCache.has(key)) return dataCache.get(key);
        const filename = lang === 'en' ? `data/${year}/calendar-en.json` : `data/${year}.json`;
        const response = await fetch(filename);
        if (!response.ok) throw new Error('Data not found for year ' + year);
        const data = await response.json();
        dataCache.set(key, data);
        return data;
    }

    // Fetch Data for a given year
    async function fetchAndRenderYear(year) {
        setLoading(true);
        try {
            const data = await loadYearData(year);
            if (year !== state.currentYear) return; // 使用者已經切到別年
            state.holidaysData = data;
            renderCalendar(data, year);
            calculateStats(data, year);
        } catch (error) {
            console.error('Error fetching data:', error);
            elements.calendarGrid.innerHTML = `
                <div class="error-state glass-panel font-noto">
                    <p class="error-title text-slate-900">${t('errorHolidays', { year })}</p>
                    <p class="text-slate-500">${t('errorHint')}</p>
                    <div class="error-actions">
                        <button class="btn btn-primary" type="button" onclick="location.reload()">${t('refresh')}</button>
                        <a class="btn" href="data/${year}.json">${t('viewJson')}</a>
                        <a class="btn" href="api.html">${t('apiLink')}</a>
                    </div>
                </div>
            `;
            elements.calendarGrid.classList.remove('hidden');
        } finally {
            setLoading(false);
        }
    }

    function setLoading(isLoading) {
        if (isLoading) {
            elements.loadingState.classList.remove('hidden');
            elements.calendarGrid.classList.add('hidden');
            elements.totalHolidays.textContent = '--';
            elements.nationalHolidays.textContent = '--';
            elements.makeupWorkdays.textContent = '--';
            elements.continuousHolidaysContainer.innerHTML = '';
            elements.continuousHolidaysContainer.classList.add('hidden');
            elements.leaveStrategiesContainer.innerHTML = '';
            elements.leaveStrategiesMore.innerHTML = '';
            elements.nextHolidayCard.classList.add('hidden');
        } else {
            elements.loadingState.classList.add('hidden');
            elements.calendarGrid.classList.remove('hidden');
        }
    }

    // Rendering Logic
    function renderCalendar(data, year) {
        elements.calendarGrid.innerHTML = '';

        // Group data by month
        const monthsData = groupDataByMonth(data, year);
        const isCurrentYear = year === todayYear;

        // Render each month
        monthsData.forEach((monthData, monthIndex) => {
            const isCurrentMonth = isCurrentYear && monthIndex === today.getMonth();
            const monthCard = document.createElement('section');
            monthCard.className = 'month-card' + (isCurrentMonth ? ' current' : '');
            monthCard.id = `month-${year}-${monthIndex + 1}`;
            monthCard.setAttribute('aria-label', `${year} ${t('monthNames')[monthIndex]}`);

            // Month Header
            const header = document.createElement('div');
            header.className = 'month-header';

            const holidaysInMonth = monthData.filter(d => d.isHoliday && d.description).length;

            header.innerHTML = `
                <span class="month-title font-outfit">${t('monthNames')[monthIndex]}${isCurrentMonth ? `<span class="month-now-tag font-noto">${t('currentMonthTag')}</span>` : ''}</span>
                <span class="month-stats font-noto">
                    ${holidaysInMonth > 0 ? `<span class="text-primary font-bold">${holidaysInMonth}</span> ${t('holidays')}` : t('noHolidays')}
                </span>
            `;

            // Days Header (S, M, T, W, T, F, S)
            const daysHeader = document.createElement('div');
            daysHeader.className = 'days-header';
            const currentDayNames = t('dayNames');
            currentDayNames.forEach((day, index) => {
                const dayEl = document.createElement('div');
                dayEl.className = `day-label font-noto ${index === 0 || index === 6 ? 'weekend' : ''}`;
                dayEl.textContent = day;
                daysHeader.appendChild(dayEl);
            });

            // Days Grid
            const daysGrid = document.createElement('div');
            daysGrid.className = 'days-grid';

            // Calculate empty cells before the 1st of the month
            const firstDateObj = new Date(year, monthIndex, 1);
            let firstDayOfWeek = firstDateObj.getDay();

            for (let i = 0; i < firstDayOfWeek; i++) {
                const emptyCell = document.createElement('div');
                emptyCell.className = 'day-cell empty';
                emptyCell.setAttribute('aria-hidden', 'true');
                daysGrid.appendChild(emptyCell);
            }

            // Render Days
            monthData.forEach(dayDetails => {
                const dateParts = parseDateString(dayDetails.date);
                const dayOfMonth = dateParts.day;
                const cell = document.createElement('div');
                cell.className = 'day-cell font-outfit';

                // Solar Date Container
                const solarDateEl = document.createElement('div');
                solarDateEl.className = 'solar-date';
                solarDateEl.textContent = dayOfMonth;
                cell.appendChild(solarDateEl);

                // Lunar Date Logic
                try {
                    if (typeof Lunar !== 'undefined') {
                        const lunarDate = Lunar.fromDate(new Date(dateParts.year, dateParts.month - 1, dateParts.day));
                        const lunarText = document.createElement('div');
                        lunarText.className = 'lunar-date font-noto';

                        // Prioritize Festivals or Solar Terms over normal Lunar date
                        const festivals = lunarDate.getFestivals();
                        const jieQi = lunarDate.getJieQi();

                        if (festivals.length > 0) {
                            lunarText.textContent = lunarToTraditional(festivals[0]); // Show first festival
                            lunarText.classList.add('lunar-festival');
                        } else if (jieQi) {
                            lunarText.textContent = lunarToTraditional(jieQi);
                            lunarText.classList.add('lunar-festival');
                        } else if (lunarDate.getDay() === 1) {
                            // If it's the 1st of the lunar month, show the month name
                            lunarText.textContent = lunarToTraditional(`${lunarDate.getMonthInChinese()}月`);
                        } else {
                            lunarText.textContent = lunarToTraditional(lunarDate.getDayInChinese());
                        }

                        cell.appendChild(lunarText);
                    }
                } catch (e) {
                    console.error("Error displaying lunar date on cell:", e);
                }

                if (dayDetails.date === todayKey) {
                    cell.classList.add('today');
                    cell.setAttribute('aria-current', 'date');
                }

                if (dayDetails.isHoliday) {
                    if (dayDetails.description) {
                        cell.classList.add('holiday');
                        const dot = document.createElement('div');
                        dot.className = 'holiday-dot';
                        cell.appendChild(dot);
                    } else {
                        // Regular weekend
                        cell.classList.add('weekend');
                    }

                    // 可用鍵盤聚焦，Enter / Space 也能打開說明
                    cell.tabIndex = 0;
                    cell.setAttribute('role', 'button');
                    cell.setAttribute('aria-label', `${formatDate(dayDetails)} ${dayDetails.description || t('holidayTag')}`);

                    // Setup Tooltip interaction for all holidays/weekends
                    cell.addEventListener('mouseenter', (e) => showTooltip(e.currentTarget, dayDetails));
                    cell.addEventListener('mouseleave', hideTooltip);
                    cell.addEventListener('click', (e) => showTooltip(e.currentTarget, dayDetails));
                    cell.addEventListener('focus', (e) => showTooltip(e.currentTarget, dayDetails));
                    cell.addEventListener('blur', hideTooltip);
                    cell.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            showTooltip(e.currentTarget, dayDetails);
                        } else if (e.key === 'Escape') {
                            hideTooltip();
                        }
                    });
                } else if (dayDetails.description && MAKEUP_WORKDAY_RE.test(dayDetails.description)) {
                    cell.classList.add('makeup');
                    cell.title = dayDetails.description;
                }

                daysGrid.appendChild(cell);
            });

            monthCard.appendChild(header);
            monthCard.appendChild(daysHeader);
            monthCard.appendChild(daysGrid);
            elements.calendarGrid.appendChild(monthCard);
        });
    }

    // Helper Functions
    function groupDataByMonth(data, year) {
        const months = Array.from({ length: 12 }, () => []);
        data.forEach(item => {
            const dateParts = parseDateString(item.date);
            if (dateParts.year === year) {
                // array is 0-indexed, month from data is 1-indexed
                months[dateParts.month - 1].push(item);
            }
        });
        return months;
    }

    function parseDateString(dateString) {
        // e.g., "20240101"
        const year = parseInt(dateString.substring(0, 4));
        const month = parseInt(dateString.substring(4, 6));
        const day = parseInt(dateString.substring(6, 8));
        return { year, month, day };
    }

    function toDateKey(date) {
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${date.getFullYear()}${m}${d}`;
    }

    function keyToDate(key) {
        const p = parseDateString(key);
        return new Date(p.year, p.month - 1, p.day);
    }

    function daysBetween(fromDate, toDate) {
        return Math.round((toDate - fromDate) / 86400000);
    }

    // "2/14（六）" 或 "Feb 14 (Sat)"
    function formatDate(dayDetails, withWeek = true) {
        const p = parseDateString(dayDetails.date);
        if (currentLang() === 'en') {
            const base = `${t('monthNames')[p.month - 1]} ${p.day}`;
            return withWeek ? `${base} (${dayDetails.week})` : base;
        }
        return withWeek ? `${p.month}/${p.day}（${dayDetails.week}）` : `${p.month}/${p.day}`;
    }

    function formatRange(first, last) {
        if (first.date === last.date) return formatDate(first, false);
        return `${formatDate(first, false)}–${formatDate(last, false)}`;
    }

    function escapeHtml(str) {
        return String(str).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    // 農曆函式庫輸出的是簡體字，這裡轉成台灣慣用的正體字
    const LUNAR_WORD_MAP = {
        '春节': '春節', '元宵节': '元宵節', '清明节': '清明節', '端午节': '端午節', '中秋节': '中秋節',
        '重阳节': '重陽節', '七夕节': '七夕', '腊八节': '臘八節', '惊蛰': '驚蟄', '谷雨': '穀雨',
        '小满': '小滿', '芒种': '芒種', '处暑': '處暑', '劳动节': '勞動節', '国庆节': '國慶節',
        '妇女节': '婦女節', '青年节': '青年節', '儿童节': '兒童節', '建军节': '建軍節', '教师节': '教師節',
        '记者节': '記者節', '龙头节': '龍頭節', '父亲节': '父親節', '母亲节': '母親節', '万圣节': '萬聖節',
        '圣诞节': '聖誕節', '腊月': '臘月', '闰': '閏'
    };
    const LUNAR_CHAR_MAP = {
        '节': '節', '惊': '驚', '蛰': '蟄', '谷': '穀', '满': '滿', '种': '種', '处': '處',
        '岁': '歲', '龙': '龍', '腊': '臘', '头': '頭', '闰': '閏'
    };

    function lunarToTraditional(text) {
        if (!text) return text;
        let out = text;
        for (const [s, tr] of Object.entries(LUNAR_WORD_MAP)) {
            out = out.split(s).join(tr);
        }
        return out.split('').map(ch => LUNAR_CHAR_MAP[ch] || ch).join('');
    }

    // Tooltip Logic
    function showTooltip(cell, dayDetails) {
        const rect = cell.getBoundingClientRect();
        const dateParts = parseDateString(dayDetails.date);

        let lunarText = "";
        try {
            if (typeof Lunar !== 'undefined') {
                const lunarDate = Lunar.fromDate(new Date(dateParts.year, dateParts.month - 1, dateParts.day));
                let festivalText = "";
                const festivals = lunarDate.getFestivals();
                const solarTerms = lunarDate.getJieQi();

                if (festivals.length > 0) {
                    festivalText = ` - ${lunarToTraditional(festivals.join('、'))}`;
                } else if (solarTerms) {
                    festivalText = ` - ${lunarToTraditional(solarTerms)}`;
                }

                lunarText = `<div class="tooltip-lunar">${t('lunarPrefix')} ${lunarToTraditional(lunarDate.getMonthInChinese())}月${lunarToTraditional(lunarDate.getDayInChinese())}${festivalText}</div>`;
            }
        } catch (e) {
            console.error("Error generating lunar date", e);
        }

        elements.tooltip.innerHTML = `
            <div class="font-bold mb-1">${escapeHtml(dayDetails.description || t('holidayTag'))}</div>
            <div class="tooltip-date">${formatDate(dayDetails)}</div>
            ${lunarText}
        `;

        // 先顯示才量得到尺寸；靠近頂端（sticky 工具列）或螢幕邊緣時翻到下方／往內推
        elements.tooltip.classList.remove('hidden');
        elements.tooltip.classList.remove('below');
        const tipRect = elements.tooltip.getBoundingClientRect();
        const toolbar = document.getElementById('toolbar');
        const topLimit = (toolbar ? toolbar.getBoundingClientRect().bottom : 0) + 8;
        const margin = 8;
        const half = tipRect.width / 2;
        const centerX = Math.min(Math.max(rect.left + rect.width / 2, margin + half), window.innerWidth - margin - half);

        elements.tooltip.style.left = `${centerX}px`;
        if (rect.top - tipRect.height - 10 < topLimit) {
            elements.tooltip.classList.add('below');
            elements.tooltip.style.top = `${rect.bottom + 10}px`;
        } else {
            elements.tooltip.style.top = `${rect.top - 10}px`;
        }

        // Slight delay to allow display block to apply before animating opacity
        requestAnimationFrame(() => {
            elements.tooltip.classList.add('show');
        });
    }

    function hideTooltip() {
        elements.tooltip.classList.remove('show');
        // Wait for transition to finish before hiding
        setTimeout(() => {
            elements.tooltip.classList.add('hidden');
        }, 200);
    }

    // Stats Calculation
    function calculateStats(data, year) {
        const totalOffDays = data.filter(d => d.isHoliday).length;
        const nationalDays = data.filter(d => d.isHoliday && d.description).length;
        const makeupDays = data.filter(d => !d.isHoliday && d.description && MAKEUP_WORKDAY_RE.test(d.description)).length;
        elements.totalHolidays.textContent = totalOffDays;
        elements.nationalHolidays.textContent = nationalDays;
        elements.makeupWorkdays.textContent = makeupDays;

        const runs = findHolidayRuns(data);

        // 連假 chips（>= 3 天）
        renderContinuousHolidays(runs.filter(r => r.days >= 3), year);

        // 請假攻略
        const strategies = findLeaveStrategies(data);
        renderLeaveStrategies(strategies, year);

        // 第一屏的「下一個連假」
        renderHero(runs, strategies, year);
    }

    // 把一段 holiday run 或攻略裡的節日名稱挑一個最有代表性的出來
    function pickRunName(descriptions) {
        const lang = currentLang();
        for (const entry of HOLIDAY_PRIORITY) {
            if (descriptions.some(d => entry.re.test(d))) return entry[lang] || entry.zh;
        }
        const fallback = descriptions.find(d => !SKIP_NAME_RE.test(d));
        return fallback || descriptions[0] || t('continuousTag');
    }

    // 一段日子裡「最重要」的那天（給攻略分組用）：依 HOLIDAY_PRIORITY 排序，找不到就回 null
    function pickAnchor(items) {
        let best = null;
        let bestRank = Infinity;
        items.forEach(item => {
            if (!item.description || !item.isHoliday) return;
            let rank = HOLIDAY_PRIORITY.findIndex(entry => entry.re.test(item.description));
            if (rank === -1) rank = SKIP_NAME_RE.test(item.description) ? HOLIDAY_PRIORITY.length + 1 : HOLIDAY_PRIORITY.length;
            if (rank < bestRank) {
                bestRank = rank;
                best = item;
            }
        });
        return best;
    }

    // 所有連續放假的區段（含週末），每段附上代表名稱
    function findHolidayRuns(data) {
        const runs = [];
        let current = [];
        const flush = () => {
            if (current.length) runs.push(current);
            current = [];
        };
        data.forEach(d => {
            if (d.isHoliday) current.push(d);
            else flush();
        });
        flush();

        return runs.map(items => {
            const descriptions = [...new Set(items.map(p => p.description).filter(Boolean))];
            const first = items[0];
            const last = items[items.length - 1];
            return {
                items,
                days: items.length,
                startKey: first.date,
                endKey: last.date,
                hasNational: descriptions.length > 0,
                name: pickRunName(descriptions),
                anchor: pickAnchor(items),
                dateRange: formatRange(first, last),
                isPast: last.date < todayKey
            };
        });
    }

    function renderContinuousHolidays(periods, year) {
        const container = elements.continuousHolidaysContainer;
        container.innerHTML = '';

        if (periods.length === 0) {
            container.classList.add('hidden');
            updateChipScrollHint();
            return;
        }

        periods.forEach(period => {
            const card = document.createElement('button');
            card.type = 'button';
            card.className = 'period-card font-noto' + (period.isPast ? ' past' : '');
            const startParts = parseDateString(period.startKey);
            card.setAttribute('data-month', startParts.month);
            card.setAttribute('aria-label', `${period.name} ${period.dateRange} ${period.days} ${t('dayWord')}`);
            card.innerHTML = `
                <span class="period-name">${escapeHtml(period.name)}</span>
                <span class="period-days font-outfit">${period.days} <span class="period-days-unit">${t('dayWord')}</span></span>
                <span class="period-date font-outfit">${period.dateRange}</span>
            `;
            card.addEventListener('click', () => jumpToMonth(year, startParts.month - 1));
            container.appendChild(card);
        });

        container.classList.remove('hidden');

        // 手機的橫向捲動列：直接捲到第一個還沒過的連假
        const firstUpcoming = container.querySelector('.period-card:not(.past)');
        if (firstUpcoming && container.scrollWidth > container.clientWidth) {
            container.scrollLeft = Math.max(0, firstUpcoming.offsetLeft - container.offsetLeft - 8);
        }
        updateChipScrollHint();
    }

    function updateChipScrollHint() {
        const container = elements.continuousHolidaysContainer;
        const wrap = container.parentElement;
        if (!wrap) return;
        const scrollable = container.scrollWidth > container.clientWidth + 2;
        const atEnd = container.scrollLeft + container.clientWidth >= container.scrollWidth - 2;
        wrap.classList.toggle('can-scroll', scrollable && !atEnd);
    }

    function findLeaveStrategies(data) {
        // Find blocks of continuous workdays (max 4 days) surrounded by continuous holidays.
        const blocks = [];
        let currentBlock = [];
        let isCurrentBlockHoliday = data[0] && data[0].isHoliday;

        // 1. Group days into blocks of holiday / workdays
        data.forEach(day => {
            if (day.isHoliday === isCurrentBlockHoliday) {
                currentBlock.push(day);
            } else {
                blocks.push({ isHoliday: isCurrentBlockHoliday, days: currentBlock });
                currentBlock = [day];
                isCurrentBlockHoliday = day.isHoliday;
            }
        });
        if (currentBlock.length > 0) {
            blocks.push({ isHoliday: isCurrentBlockHoliday, days: currentBlock });
        }

        // 2. Identify strategies (Holiday string -> Workday string (1-4) -> Holiday string)
        const raw = [];
        for (let i = 1; i < blocks.length - 1; i++) {
            const prevBlock = blocks[i - 1];
            const currBlock = blocks[i];
            const nextBlock = blocks[i + 1];

            // Condition: curr is Workday (1~4 days), prev and next are Holidays
            if (currBlock.isHoliday || currBlock.days.length < 1 || currBlock.days.length > 4) continue;
            if (!prevBlock.isHoliday || !nextBlock.isHoliday) continue;

            const totalConsecutive = prevBlock.days.length + currBlock.days.length + nextBlock.days.length;
            // We only care if taking leave creates >= 4 continuous holidays
            if (totalConsecutive < 4) continue;

            const timeline = [...prevBlock.days, ...currBlock.days, ...nextBlock.days];
            const anchor = pickAnchor(timeline);
            const descriptions = [...new Set(timeline.map(d => d.description).filter(Boolean))];
            const leaveFirst = currBlock.days[0];
            const leaveLast = currBlock.days[currBlock.days.length - 1];

            raw.push({
                name: anchor ? pickRunName(descriptions) : t('weekendHoliday'),
                // 同一個節日前後各一組攻略會共用 anchor，之後合併成一張卡
                groupKey: anchor ? `h:${anchor.date}` : `w:${timeline[0].date}`,
                anchorDate: anchor ? anchor.date : timeline[0].date,
                leaveDays: currBlock.days.length,
                totalDays: totalConsecutive,
                efficiency: totalConsecutive / currBlock.days.length,
                leaveStartKey: leaveFirst.date,
                leaveRange: formatRange(leaveFirst, leaveLast),
                timeline,
                isPast: leaveFirst.date < todayKey
            });
        }

        // 3. 同一個節日的多種請法合併：最划算的當主卡，其餘列成「也可以」
        const groups = new Map();
        raw.forEach(s => {
            if (!groups.has(s.groupKey)) groups.set(s.groupKey, []);
            groups.get(s.groupKey).push(s);
        });

        const merged = [];
        groups.forEach(list => {
            list.sort((a, b) => b.efficiency - a.efficiency || a.leaveDays - b.leaveDays || a.leaveStartKey.localeCompare(b.leaveStartKey));
            const primary = list[0];
            primary.alternatives = list.slice(1);
            merged.push(primary);
        });

        merged.sort((a, b) => a.timeline[0].date.localeCompare(b.timeline[0].date));
        return merged;
    }

    function buildStrategyCard(strategy, options = {}) {
        const card = document.createElement('article');
        card.className = 'strategy-new-card' + (strategy.isPast ? ' past' : '') + (options.best ? ' best' : '');
        card.setAttribute('aria-label', t('strategyAria', {
            name: strategy.name, range: strategy.leaveRange, leave: strategy.leaveDays, total: strategy.totalDays
        }));

        // 7 欄對齊星期的迷你月曆：第一天之前補空格
        const firstDate = keyToDate(strategy.timeline[0].date);
        let columnsHTML = '';
        for (let i = 0; i < firstDate.getDay(); i++) {
            columnsHTML += '<div class="cal-day-col empty" aria-hidden="true"></div>';
        }
        strategy.timeline.forEach(dayInfo => {
            const dateParts = parseDateString(dayInfo.date);
            const isWorkdayBlock = !dayInfo.isHoliday;
            const colModifier = isWorkdayBlock ? 'workday' : 'holiday';
            const desc = (!isWorkdayBlock && dayInfo.description) ? escapeHtml(dayInfo.description) : '';
            const festivalLabel = desc ? `<div class="cal-festival-tag font-noto" title="${desc}">${desc}</div>` : '';
            const isToday = dayInfo.date === todayKey;

            columnsHTML += `
                <div class="cal-day-col ${colModifier}${isToday ? ' is-today' : ''}">
                    <div class="cal-head font-noto">${escapeHtml(dayInfo.week)}</div>
                    <div class="cal-body font-outfit">${dateParts.day}</div>
                    ${festivalLabel}
                </div>
            `;
        });

        const anchorParts = parseDateString(strategy.anchorDate);
        const displayMonth = t('monthNames')[anchorParts.month - 1];
        const flag = options.best
            ? `<span class="strategy-flag best font-noto">${t('best')}</span>`
            : (strategy.isPast ? `<span class="strategy-flag past font-noto">${t('past')}</span>` : '');

        const altHTML = strategy.alternatives && strategy.alternatives.length
            ? `<div class="strategy-alt font-noto">${strategy.alternatives.map(a =>
                escapeHtml(t('altOption', { range: a.leaveRange, leave: a.leaveDays, total: a.totalDays }))).join('<br>')}</div>`
            : '';

        card.innerHTML = `
            <div class="strategy-left-label font-noto">
                <div class="month">${displayMonth}</div>
                <div class="festival">${escapeHtml(strategy.name)}</div>
                ${flag}
            </div>
            <div class="strategy-middle">
                <div class="strategy-calendar-row">
                    ${columnsHTML}
                </div>
                ${altHTML}
            </div>
            <div class="strategy-right-badge">
                <div class="badge-total font-noto">${t('badgeTotal', { total: `<b>${strategy.totalDays}</b>` })}</div>
                <div class="badge-leave font-noto">${t('badgeLeave', { leave: strategy.leaveDays })}</div>
                <div class="badge-range font-outfit">${strategy.leaveRange}</div>
            </div>
        `;
        return card;
    }

    function renderLeaveStrategies(strategies, year) {
        const section = elements.leaveStrategiesSection;
        elements.leaveStrategiesContainer.innerHTML = '';
        elements.leaveStrategiesMore.innerHTML = '';

        if (strategies.length === 0) {
            section.classList.add('hidden');
            return;
        }
        section.classList.remove('hidden');

        const upcoming = strategies.filter(s => !s.isPast);
        const past = strategies.filter(s => s.isPast);

        // 預設只放「接下來的前 3 則」；整年都過了（看舊年份）就放前 3 則灰掉的
        const PRIMARY_COUNT = 3;
        const primary = upcoming.length ? upcoming.slice(0, PRIMARY_COUNT) : strategies.slice(0, PRIMARY_COUNT);
        const rest = strategies.filter(s => !primary.includes(s));

        // 「最划算」：接下來的攻略裡效率最高的（至少要有兩則才有比較的意義）
        let bestEfficiency = -1;
        if (upcoming.length >= 2) {
            bestEfficiency = Math.max(...upcoming.map(s => s.efficiency));
        }
        const isBest = s => !s.isPast && s.efficiency === bestEfficiency;

        primary.forEach(s => elements.leaveStrategiesContainer.appendChild(buildStrategyCard(s, { best: isBest(s) })));
        rest.forEach(s => elements.leaveStrategiesMore.appendChild(buildStrategyCard(s, { best: isBest(s) })));

        elements.strategySubtitle.textContent = upcoming.length
            ? t('strategySubUpcoming', { n: upcoming.length })
            : t('strategySubPast', { n: strategies.length });

        const btn = elements.strategyMoreBtn;
        btn.hidden = rest.length === 0;
        btn.dataset.total = strategies.length;
        btn.dataset.past = past.length;
        syncStrategyMore();
    }

    function syncStrategyMore() {
        const btn = elements.strategyMoreBtn;
        const more = elements.leaveStrategiesMore;
        const total = Number(btn.dataset.total || 0);
        const past = Number(btn.dataset.past || 0);
        more.hidden = !state.strategiesExpanded;
        btn.setAttribute('aria-expanded', String(state.strategiesExpanded));
        if (state.strategiesExpanded) {
            btn.textContent = t('showLess');
        } else {
            btn.textContent = (past > 0 && past < total) ? t('showAllWithPast', { n: total, past }) : t('showAll', { n: total });
        }
    }

    // 第一屏：下一個連假（以「今天」為準）。看過去的年份就不顯示；
    // 今年的假都放完了就抓明年的第一個來顯示（年底不會空著）。
    function renderHero(runs, strategies, year) {
        const card = elements.nextHolidayCard;
        card.classList.add('hidden');
        if (year < todayYear) return;

        const next = runs.find(r => r.hasNational && r.endKey >= todayKey);
        if (next) {
            paintHero(next, strategies, year, { fromYear: year });
            return;
        }

        const nextYear = year + 1;
        if (year !== todayYear || !state.availableYears.includes(nextYear)) return;
        loadYearData(nextYear).then(data => {
            if (state.currentYear !== year) return;
            const nextRuns = findHolidayRuns(data);
            const nextRun = nextRuns.find(r => r.hasNational && r.endKey >= todayKey);
            if (!nextRun) return;
            paintHero(nextRun, findLeaveStrategies(data), year, { fromYear: nextYear, noMoreThisYear: true });
        }).catch(() => { /* 明年資料抓不到就不顯示 hero */ });
    }

    function paintHero(run, strategies, viewedYear, meta) {
        const card = elements.nextHolidayCard;
        const startDate = keyToDate(run.startKey);
        const endDate = keyToDate(run.endKey);
        const inProgress = run.startKey <= todayKey;
        const diff = daysBetween(today, startDate);

        let eyebrow = run.days >= 3 ? t('heroNext') : t('heroNextHoliday');
        let countdown;
        if (inProgress) {
            eyebrow = t('heroNow');
            countdown = t('heroRemaining', { days: daysBetween(today, endDate) + 1 });
        } else if (diff === 0) {
            countdown = t('heroToday');
        } else if (diff === 1) {
            countdown = t('heroTomorrow');
        } else {
            countdown = t('heroCountdown', { days: diff });
        }

        // 跟這段連假有關、而且還來得及請的攻略：挑最划算的一個
        const related = strategies
            .filter(s => !s.isPast && s.timeline.some(d => d.date >= run.startKey && d.date <= run.endKey))
            .sort((a, b) => b.efficiency - a.efficiency || a.leaveDays - b.leaveDays)[0];

        const startParts = parseDateString(run.startKey);
        const yearBadge = meta.fromYear !== viewedYear || meta.fromYear !== todayYear ? ` · ${meta.fromYear}` : '';

        card.innerHTML = `
            <div class="hero-eyebrow font-noto">${escapeHtml(eyebrow)}${yearBadge}</div>
            <div class="hero-name font-noto">${escapeHtml(run.name)}</div>
            <div class="hero-range font-outfit">${formatDate(run.items[0])} – ${formatDate(run.items[run.items.length - 1])}</div>
            <div class="hero-meta font-noto">
                <span class="hero-days">${run.days === 1 ? t('heroSingleDay') : t('heroDays', { days: run.days })}</span>
                <span class="hero-count">${escapeHtml(countdown)}</span>
            </div>
            ${related ? `<div class="hero-tip font-noto"><span aria-hidden="true">💡</span> ${escapeHtml(t('heroTip', { leave: related.leaveDays, total: related.totalDays, range: related.leaveRange }))}</div>` : ''}
            ${meta.noMoreThisYear ? `<div class="hero-note font-noto">${escapeHtml(t('heroNoMore'))}</div>` : ''}
            <div class="hero-actions">
                <button type="button" class="hero-btn font-noto" data-jump-year="${meta.fromYear}" data-jump-month="${startParts.month - 1}">${t('heroViewMonth')}</button>
                ${meta.fromYear !== viewedYear ? `<button type="button" class="hero-btn secondary font-noto" data-switch-year="${meta.fromYear}">${t('heroSwitchYear', { year: meta.fromYear })}</button>` : ''}
                ${meta.fromYear === viewedYear && viewedYear === todayYear && state.availableYears.includes(viewedYear + 1)
                    ? `<button type="button" class="hero-btn secondary font-noto" data-switch-year="${viewedYear + 1}">${t('heroNextYearOut', { year: viewedYear + 1 })} →</button>`
                    : ''}
            </div>
        `;

        card.querySelectorAll('[data-jump-year]').forEach(btn => {
            btn.addEventListener('click', () => jumpToMonth(Number(btn.dataset.jumpYear), Number(btn.dataset.jumpMonth)));
        });
        card.querySelectorAll('[data-switch-year]').forEach(btn => {
            btn.addEventListener('click', () => changeYear(Number(btn.dataset.switchYear)));
        });

        card.classList.remove('hidden');
    }

    async function jumpToMonth(year, monthIndex) {
        if (year !== state.currentYear) {
            if (!state.availableYears.includes(year)) return;
            await changeYear(year);
        }
        const target = document.getElementById(`month-${year}-${monthIndex + 1}`);
        if (!target) return;
        target.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' });
        target.classList.add('flash');
        setTimeout(() => target.classList.remove('flash'), 1600);
    }

    // 分享與複製
    async function sharePage() {
        const shareData = {
            title: document.title,
            text: t('subtitle'),
            url: location.href
        };
        if (navigator.share) {
            try {
                await navigator.share(shareData);
                return;
            } catch (e) {
                if (e && e.name === 'AbortError') return; // 使用者取消
            }
        }
        const ok = await copyText(location.href);
        showToast(ok ? t('shareCopied') : t('copyFailed'));
    }

    async function copyText(text) {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
                return true;
            }
        } catch (e) { /* fall through */ }
        try {
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.setAttribute('readonly', '');
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            const ok = document.execCommand('copy');
            document.body.removeChild(ta);
            return ok;
        } catch (e) {
            return false;
        }
    }

    let toastTimer = null;
    function showToast(message) {
        if (!elements.toast) return;
        elements.toast.textContent = message;
        elements.toast.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => elements.toast.classList.remove('show'), 2000);
    }

    // Start App
    init();
});
