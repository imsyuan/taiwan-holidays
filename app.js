document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const elements = {
        prevYear: document.getElementById('prevYear'),
        nextYear: document.getElementById('nextYear'),
        currentYearDisplay: document.getElementById('currentYearDisplay'),
        calendarGrid: document.getElementById('calendarGrid'),
        loadingState: document.getElementById('loadingState'),
        totalHolidays: document.getElementById('totalHolidays'),
        continuousHolidaysContainer: document.getElementById('continuousHolidaysContainer'),
        leaveStrategiesSection: document.getElementById('leaveStrategiesSection'),
        strategyToggleBtn: document.getElementById('strategyToggleBtn'),
        strategyToggleIcon: document.getElementById('strategyToggleIcon'),
        leaveStrategiesWrapper: document.getElementById('leaveStrategiesWrapper'),
        leaveStrategiesContainer: document.getElementById('leaveStrategiesContainer'),
        languageToggle: document.getElementById('languageToggle'),
        tooltip: document.getElementById('tooltip')
    };

    // State
    let state = {
        currentYear: new Date().getFullYear(),
        holidaysData: [],
        availableYears: []
    };

    // Constants and Translations
    const translations = {
        zh: {
            subtitle: "專為軟體工程師與人資量身打造的台灣國定假日視覺化日曆與 JSON API",
            apiLink: "API 說明",
            lunarToggleText: "農民曆",
            totalHolidaysLabel: "休假日總數",
            strategyToggleBtnText: "聰明請假攻略",
            loading: "載入資料中...",
            footerSource: "資料來源：中華民國行政院人事行政總處。",
            monthNames: ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"],
            dayNames: ["日", "一", "二", "三", "四", "五", "六"],
            holidayTag: "休假日",
            workdayTag: "補班日",
            holidays: "國定假日",
            noHolidays: "無國定假日",
            continuous: "連假 ${days} 天",
            take: "請假 ${take} 天",
            off: "放假 ${off} 天",
            errorHolidays: "找不到 ${year} 年的假期資料",
            refresh: "重新整理",
            dayWord: "天",
            continuousTag: "連假",
            weekendHoliday: "週末連假",
            strategyBadge: "請${leave}休${total}",
            legendHoliday: "放假日",
            legendMakeup: "需請假/補假",
            langHover: "切換語言",
            lunarHover: "切換農民曆",
            githubHover: "專案原始碼"
        },
        en: {
            subtitle: "Visual holidays calendar and JSON API built for software engineers and HRs in Taiwan.",
            apiLink: "API Docs",
            lunarToggleText: "Lunar",
            totalHolidaysLabel: "Total Holidays",
            strategyToggleBtnText: "Leave Strategies",
            loading: "Loading data...",
            footerSource: "Data Source: DGPA, Taiwan.",
            monthNames: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            dayNames: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            holidayTag: "Holiday",
            workdayTag: "Makeup Work",
            holidays: "Holidays",
            noHolidays: "No Holidays",
            continuous: "${days}-day Holiday",
            take: "Take ${take} day(s)",
            off: "Off ${off} day(s)",
            errorHolidays: "Data not found for ${year}",
            refresh: "Refresh",
            dayWord: "days",
            continuousTag: "Holiday",
            weekendHoliday: "Weekend Holiday",
            strategyBadge: "Take ${leave} Off ${total}",
            legendHoliday: "Holiday",
            legendMakeup: "Take Leave / Makeup",
            langHover: "Change Language",
            lunarHover: "Toggle Lunar Calendar",
            githubHover: "Project Source Code"
        }
    };

    function t(key, params = {}) {
        const lang = elements.languageToggle ? (elements.languageToggle.value || 'zh') : 'zh';
        let str = translations[lang][key];
        if (str === undefined) return key;

        // Handle array returns
        if (Array.isArray(str)) return str;

        for (const [k, v] of Object.entries(params)) {
            str = str.replace(`\${${k}}`, v);
        }
        return str;
    }

    function updateStaticTexts() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            el.textContent = t(key);
        });

        const lunarTextEl = document.getElementById('lunarToggleText');
        if (lunarTextEl) {
            lunarTextEl.textContent = t('lunarToggleText');
        }
    }

    // Initialize App
    async function init() {
        // Fetch available years from GitHub API (or statically if we know them)
        // Since we are deploying to GitHub Pages, we can't easily read the directory dynamically
        // without a build step or an API call. A robust approach for static sites is to pre-define them
        // or attempt to fetch up to a known range.

        // For this static site, we will hardcode the available range based on the data directory (2017-2026)
        state.availableYears = Array.from({ length: 10 }, (_, i) => 2017 + i);

        // Default to the latest year available
        const latestYear = state.availableYears[state.availableYears.length - 1];
        state.currentYear = latestYear;
        elements.currentYearDisplay.textContent = state.currentYear;

        updateStaticTexts();
        await fetchAndRenderYear(state.currentYear);
        setupEventListeners();
        updateYearButtons();
    }

    // Event Listeners
    function setupEventListeners() {
        elements.prevYear.addEventListener('click', async () => {
            if (state.currentYear > state.availableYears[0]) {
                state.currentYear--;
                elements.currentYearDisplay.textContent = state.currentYear;
                await fetchAndRenderYear(state.currentYear);
                updateYearButtons();
            }
        });

        elements.nextYear.addEventListener('click', async () => {
            if (state.currentYear < state.availableYears[state.availableYears.length - 1]) {
                state.currentYear++;
                elements.currentYearDisplay.textContent = state.currentYear;
                await fetchAndRenderYear(state.currentYear);
                updateYearButtons();
            }
        });

        // Hide tooltip on scroll or outside click
        window.addEventListener('scroll', hideTooltip);
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.day-cell.holiday')) {
                hideTooltip();
            }
        });

        // Settings Toggles - Lunar
        const lunarToggleBtn = document.getElementById('lunarToggleBtn');
        const lunarIcon = document.getElementById('lunarIcon');
        let lunarVisible = true;

        const bookOpenPath = '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>';
        const bookPath = '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>';

        if (lunarToggleBtn && lunarIcon) {
            lunarToggleBtn.addEventListener('click', () => {
                lunarVisible = !lunarVisible;
                if (lunarVisible) {
                    elements.calendarGrid.classList.remove('hide-lunar');
                    lunarIcon.innerHTML = bookOpenPath;
                    lunarToggleBtn.classList.replace('text-slate-400', 'text-slate-600');
                } else {
                    elements.calendarGrid.classList.add('hide-lunar');
                    lunarIcon.innerHTML = bookPath;
                    lunarToggleBtn.classList.replace('text-slate-600', 'text-slate-400');
                }
            });
        }

        // Toggle leave strategies collapse
        elements.strategyToggleBtn.addEventListener('click', () => {
            const wrapper = elements.leaveStrategiesWrapper;
            const icon = elements.strategyToggleIcon;

            if (wrapper.style.height && wrapper.style.height !== '0px') {
                // Currently open, so collapse it
                wrapper.style.height = '0px';
                icon.style.transform = 'rotate(0deg)';
            } else {
                // Currently closed (or empty on initial load), so expand it
                wrapper.style.height = wrapper.scrollHeight + 'px';
                icon.style.transform = 'rotate(180deg)';
            }
        });

        // Language Toggle Listener (Flags)
        const langToggleBtn = document.getElementById('langToggleBtn');
        const langIcon = document.getElementById('langIcon');

        // Custom simple SVG paths for flags to fit the lucide icon box
        const twFlagPath = '<rect width="20" height="14" x="2" y="5" fill="#de2910" rx="2"/><rect width="10" height="7" x="2" y="5" fill="#000095" rx="2" stroke="none"/><path d="M7 6.5l.5 1.5h1.5l-1 1 .5 1.5-1.5-1-1.5 1 .5-1.5-1-1h1.5z" fill="#fff" stroke="none"/>';

        const usFlagPath = '<rect width="20" height="14" x="2" y="5" fill="#fff" stroke="currentColor" stroke-width="2" rx="2"/><rect width="10" height="7" x="2" y="5" fill="#0a3161" rx="2" stroke="none"/><path d="M2 7h20M2 11h20M2 15h20M2 19h20" stroke="#b31942" stroke-width="1.5" stroke-linecap="butt"/><rect width="10" height="7" x="2" y="5" fill="#0a3161" rx="2" stroke="none"/><path d="M4.5 6.5h1M6.5 6.5h1M8.5 6.5h1M4.5 8.5h1M6.5 8.5h1M8.5 8.5h1M4.5 10.5h1M6.5 10.5h1M8.5 10.5h1" stroke="#fff" stroke-width="1" stroke-linecap="round"/>';

        if (langToggleBtn) {
            langToggleBtn.addEventListener('click', () => {
                const currentVal = elements.languageToggle.value;
                const newVal = currentVal === 'zh' ? 'en' : 'zh';
                elements.languageToggle.value = newVal;

                if (langIcon) {
                    langIcon.innerHTML = newVal === 'zh' ? twFlagPath : usFlagPath;
                }

                elements.languageToggle.dispatchEvent(new Event('change'));
            });

            // Set initial state
            if (langIcon) {
                langIcon.innerHTML = elements.languageToggle.value === 'zh' ? twFlagPath : usFlagPath;
                langIcon.classList.remove('lucide', 'lucide-globe');
            }

            // Remove the default stroke and fill settings as the flags provide their own
            langIcon.removeAttribute('stroke');
            langIcon.removeAttribute('stroke-width');
            langIcon.removeAttribute('stroke-linecap');
            langIcon.removeAttribute('stroke-linejoin');
        }

        elements.languageToggle.addEventListener('change', (e) => {
            updateStaticTexts();
            fetchAndRenderYear(state.currentYear);
        });
    }

    function updateYearButtons() {
        elements.prevYear.style.opacity = state.currentYear <= state.availableYears[0] ? '0.3' : '1';
        elements.prevYear.style.cursor = state.currentYear <= state.availableYears[0] ? 'not-allowed' : 'pointer';

        elements.nextYear.style.opacity = state.currentYear >= state.availableYears[state.availableYears.length - 1] ? '0.3' : '1';
        elements.nextYear.style.cursor = state.currentYear >= state.availableYears[state.availableYears.length - 1] ? 'not-allowed' : 'pointer';
    }

    // Fetch Data for a given year
    async function fetchAndRenderYear(year) {
        setLoading(true);
        try {
            const lang = elements.languageToggle.value; // 'zh' or 'en'
            const filename = lang === 'en' ? `data/${year}/calendar-en.json` : `data/${year}.json`;

            const response = await fetch(filename);
            if (!response.ok) throw new Error('Data not found for year ' + year);
            const data = await response.json();
            state.holidaysData = data;
            renderCalendar(data, year);
            calculateStats(data);
        } catch (error) {
            console.error('Error fetching data:', error);
            elements.calendarGrid.innerHTML = `
                <div class="error-state text-center grid-col-span-full py-12">
                    <p class="text-slate-500 mb-4">${t('errorHolidays', { year })}</p>
                    <button class="btn border px-4 py-2 rounded-md hover:bg-slate-50 text-slate-700 font-noto cursor-pointer" onclick="location.reload()">${t('refresh')}</button>
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
            elements.continuousHolidaysContainer.innerHTML = '';
            elements.continuousHolidaysContainer.classList.add('hidden');
            elements.leaveStrategiesContainer.innerHTML = '';
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

        // Render each month
        monthsData.forEach((monthData, monthIndex) => {
            const monthCard = document.createElement('div');
            monthCard.className = 'month-card';

            // Month Header
            const header = document.createElement('div');
            header.className = 'month-header';

            const holidaysInMonth = monthData.filter(d => d.isHoliday && d.description).length;
            const weekendHolidaysInMonth = monthData.filter(d => d.isHoliday).length - holidaysInMonth;

            header.innerHTML = `
                <span class="month-title font-outfit">${t('monthNames')[monthIndex]}</span>
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
                daysGrid.appendChild(emptyCell);
            }

            // Current date for comparison
            const today = new Date();
            const isCurrentYear = year === today.getFullYear();
            const isCurrentMonth = monthIndex === today.getMonth();

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

                        // Helper to convert simplified to traditional
                        const s2t = (text) => {
                            if (!text) return text;
                            const map = {
                                '春节': '春節', '元宵节': '元宵節', '清明节': '清明節', '端午节': '端午節', '中秋节': '中秋節',
                                '重阳节': '重陽節', '除夕': '除夕', '七夕节': '七夕', '腊八节': '臘八節', '小年': '小年',
                                '正月': '正月', '腊月': '臘月', '冬月': '冬月', '闰': '閏',
                                '立春': '立春', '雨水': '雨水', '惊蛰': '驚蟄', '春分': '春分', '清明': '清明', '谷雨': '穀雨',
                                '立夏': '立夏', '小满': '小滿', '芒种': '芒種', '夏至': '夏至', '小暑': '小暑', '大暑': '大暑',
                                '立秋': '立秋', '处暑': '處暑', '白露': '白露', '秋分': '秋分', '寒露': '寒露', '霜降': '霜降',
                                '立冬': '立冬', '小雪': '小雪', '大雪': '大雪', '冬至': '冬至', '小寒': '小寒', '大寒': '大寒',
                                '初一': '初一', '初二': '初二', '初三': '初三', '初四': '初四', '初五': '初五',
                                '初六': '初六', '初七': '初七', '初八': '初八', '初九': '初九', '初十': '初十',
                                '十一': '十一', '十二': '十二', '十三': '十三', '十四': '十四', '十五': '十五',
                                '十六': '十六', '十七': '十七', '十八': '十八', '十九': '十九', '二十': '二十',
                                '廿一': '廿一', '廿二': '廿二', '廿三': '廿三', '廿四': '廿四', '廿五': '廿五',
                                '廿六': '廿六', '廿七': '廿七', '廿八': '廿八', '廿九': '廿九', '三十': '三十',
                                '劳动节': '勞動節', '国庆节': '國慶節', '妇女节': '婦女節', '青年节': '青年節',
                                '儿童节': '兒童節', '建军节': '建軍節', '教师节': '教師節', '记者节': '記者節',
                                '父亲节': '父親節', '母亲节': '母親節', '万圣节': '萬聖節', '圣诞节': '聖誕節'
                            };
                            return text.split('').map(char => map[char] || char).join('').replace(/节/g, '節').replace(/惊/g, '驚').replace(/蛰/g, '蟄').replace(/谷/g, '穀').replace(/满/g, '滿').replace(/种/g, '種').replace(/处/g, '處').replace(/岁/g, '歲').replace(/龙/g, '龍').replace(/腊/g, '臘');
                        };

                        // Helper for full word replacement first
                        const wordReplace = (text) => {
                            if (!text) return text;
                            const words = {
                                '春节': '春節', '元宵节': '元宵節', '清明节': '清明節', '端午节': '端午節', '中秋节': '中秋節',
                                '重阳节': '重陽節', '七夕节': '七夕', '腊八节': '臘八節', '惊蛰': '驚蟄', '谷雨': '穀雨',
                                '小满': '小滿', '芒种': '芒種', '处暑': '處暑', '劳动节': '勞動節', '国庆节': '國慶節',
                                '妇女节': '婦女節', '青年节': '青年節', '儿童节': '兒童節', '建军节': '建軍節', '教师节': '教師節',
                                '记者节': '記者節'
                            };
                            let newText = text;
                            for (const [s, t] of Object.entries(words)) {
                                newText = newText.replace(new RegExp(s, 'g'), t);
                            }
                            return s2t(newText);
                        };

                        // Prioritize Festivals or Solar Terms over normal Lunar date
                        const festivals = lunarDate.getFestivals();
                        const jieQi = lunarDate.getJieQi();

                        if (festivals.length > 0) {
                            lunarText.textContent = wordReplace(festivals[0]); // Show first festival
                            lunarText.classList.add('lunar-festival');
                        } else if (jieQi) {
                            lunarText.textContent = wordReplace(jieQi);
                            lunarText.classList.add('lunar-festival'); // Optionally style terms differently
                        } else {
                            // If it's the 1st of the lunar month, show the month name
                            if (lunarDate.getDay() === 1) {
                                lunarText.textContent = wordReplace(`${lunarDate.getMonthInChinese()}月`);
                            } else {
                                lunarText.textContent = wordReplace(lunarDate.getDayInChinese());
                            }
                        }

                        cell.appendChild(lunarText);
                    }
                } catch (e) {
                    console.error("Error displaying lunar date on cell:", e);
                }

                if (isCurrentYear && isCurrentMonth && dayOfMonth === today.getDate()) {
                    cell.classList.add('today');
                }

                const dayOfWeekStr = dayDetails.week;

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

                    // Setup Tooltip interaction for all holidays/weekends
                    cell.addEventListener('mouseenter', (e) => showTooltip(e, dayDetails));
                    cell.addEventListener('mouseleave', hideTooltip);
                    cell.addEventListener('click', (e) => showTooltip(e, dayDetails));
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

    // Tooltip Logic
    function showTooltip(event, dayDetails) {
        const rect = event.target.getBoundingClientRect();

        // Format date string nicely
        const dateParts = parseDateString(dayDetails.date);
        const formattedDate = `${dateParts.month}月${dateParts.day}日 (${dayDetails.week})`;

        let lunarText = "";
        try {
            // Include lunar date if library is available
            if (typeof Lunar !== 'undefined') {
                const lunarDate = Lunar.fromDate(new Date(dateParts.year, dateParts.month - 1, dateParts.day));
                let festivalText = "";
                const festivals = lunarDate.getFestivals();
                const solarTerms = lunarDate.getJieQi();

                // Helper to convert simplified to traditional
                const s2t = (text) => {
                    if (!text) return text;
                    const map = {
                        '春节': '春節', '元宵节': '元宵節', '清明节': '清明節', '端午节': '端午節', '中秋节': '中秋節',
                        '重阳节': '重陽節', '除夕': '除夕', '七夕节': '七夕', '腊八节': '臘八節', '小年': '小年',
                        '正月': '正月', '腊月': '臘月', '冬月': '冬月', '闰': '閏',
                        '立春': '立春', '雨水': '雨水', '惊蛰': '驚蟄', '春分': '春分', '清明': '清明', '谷雨': '穀雨',
                        '立夏': '立夏', '小满': '小滿', '芒种': '芒種', '夏至': '夏至', '小暑': '小暑', '大暑': '大暑',
                        '立秋': '立秋', '处暑': '處暑', '白露': '白露', '秋分': '秋分', '寒露': '寒露', '霜降': '霜降',
                        '立冬': '立冬', '小雪': '小雪', '大雪': '大雪', '冬至': '冬至', '小寒': '小寒', '大寒': '大寒',
                        '初一': '初一', '初二': '初二', '初三': '初三', '初四': '初四', '初五': '初五',
                        '初六': '初六', '初七': '初七', '初八': '初八', '初九': '初九', '初十': '初十',
                        '十一': '十一', '十二': '十二', '十三': '十三', '十四': '十四', '十五': '十五',
                        '十六': '十六', '十七': '十七', '十八': '十八', '十九': '十九', '二十': '二十',
                        '廿一': '廿一', '廿二': '廿二', '廿三': '廿三', '廿四': '廿四', '廿五': '廿五',
                        '廿六': '廿六', '廿七': '廿七', '廿八': '廿八', '廿九': '廿九', '三十': '三十',
                        '劳动节': '勞動節', '国庆节': '國慶節', '妇女节': '婦女節', '青年节': '青年節',
                        '儿童节': '兒童節', '建军节': '建軍節', '教师节': '教師節', '记者节': '記者節',
                        '父亲节': '父親節', '母亲节': '母親節', '万圣节': '萬聖節', '圣诞节': '聖誕節'
                    };
                    return text.split('').map(char => map[char] || char).join('').replace(/节/g, '節').replace(/惊/g, '驚').replace(/蛰/g, '蟄').replace(/谷/g, '穀').replace(/满/g, '滿').replace(/种/g, '種').replace(/处/g, '處').replace(/岁/g, '歲').replace(/龙/g, '龍').replace(/腊/g, '臘');
                };

                // Helper for full word replacement first
                const wordReplace = (text) => {
                    if (!text) return text;
                    const words = {
                        '春节': '春節', '元宵节': '元宵節', '清明节': '清明節', '端午节': '端午節', '中秋节': '中秋節',
                        '重阳节': '重陽節', '七夕节': '七夕', '腊八节': '臘八節', '惊蛰': '驚蟄', '谷雨': '穀雨',
                        '小满': '小滿', '芒种': '芒種', '处暑': '處暑', '劳动节': '勞動節', '国庆节': '國慶節',
                        '妇女节': '婦女節', '青年节': '青年節', '儿童节': '兒童節', '建军节': '建軍節', '教师节': '教師節',
                        '记者节': '記者節'
                    };
                    let newText = text;
                    for (const [s, t] of Object.entries(words)) {
                        newText = newText.replace(new RegExp(s, 'g'), t);
                    }
                    return s2t(newText);
                };

                if (festivals.length > 0) {
                    festivalText = ` - ${wordReplace(festivals.join('、'))}`;
                } else if (solarTerms) {
                    festivalText = ` - ${wordReplace(solarTerms)}`;
                }

                lunarText = `<div class="text-slate-400 text-xs mt-1">農曆 ${wordReplace(lunarDate.getMonthInChinese())}月${wordReplace(lunarDate.getDayInChinese())}${festivalText}</div>`;
            }
        } catch (e) {
            console.error("Error generating lunar date", e);
        }

        elements.tooltip.innerHTML = `
            <div class="font-bold mb-1">${dayDetails.description || t('holidayTag')}</div>
            <div class="text-slate-300 text-xs">${formattedDate}</div>
            ${lunarText}
        `;

        elements.tooltip.style.left = `${rect.left + (rect.width / 2)}px`;
        // Position above the cell
        elements.tooltip.style.top = `${rect.top - 10}px`;
        elements.tooltip.style.transform = `translateX(-50%) translateY(-100%)`;
        elements.tooltip.classList.remove('hidden');

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
    function calculateStats(data) {
        const totalOffDays = data.filter(d => d.isHoliday).length;
        elements.totalHolidays.textContent = totalOffDays;

        // Find continuous holidays (>= 3 days)
        const continuousHolidays = findContinuousHolidays(data);
        renderContinuousHolidays(continuousHolidays);

        // Find leave strategies 
        const strategies = findLeaveStrategies(data);
        renderLeaveStrategies(strategies);
    }

    function findContinuousHolidays(data) {
        const periods = [];
        let currentPeriod = [];

        for (let i = 0; i < data.length; i++) {
            if (data[i].isHoliday) {
                currentPeriod.push(data[i]);
            } else {
                if (currentPeriod.length >= 3) {
                    periods.push(currentPeriod);
                }
                currentPeriod = [];
            }
        }
        // Check end of array
        if (currentPeriod.length >= 3) {
            periods.push(currentPeriod);
        }

        // Process periods for UI
        return periods.map(period => {
            const descriptions = [...new Set(period.map(p => p.description).filter(Boolean))];
            const name = descriptions.length > 0 ? descriptions[0] : t('continuousTag');

            const start = parseDateString(period[0].date);
            const end = parseDateString(period[period.length - 1].date);

            return {
                name: name,
                days: period.length,
                dateRange: `${start.month}/${start.day} - ${end.month}/${end.day}`
            };
        });
    }

    function renderContinuousHolidays(periods) {
        elements.continuousHolidaysContainer.innerHTML = '';

        if (periods.length === 0) return;

        periods.forEach(period => {
            const card = document.createElement('div');
            card.className = 'period-card cursor-pointer hover:border-accent transition-colors';
            card.innerHTML = `
                <span class="period-name font-noto">${period.name}</span>
                <span class="period-days font-outfit">${period.days} <span class="text-sm font-normal text-slate-500 font-noto">${t('dayWord')}</span></span>
                <span class="period-date font-outfit">${period.dateRange}</span>
            `;
            elements.continuousHolidaysContainer.appendChild(card);
        });

        elements.continuousHolidaysContainer.classList.remove('hidden');
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
                blocks.push({
                    isHoliday: isCurrentBlockHoliday,
                    days: currentBlock
                });
                currentBlock = [day];
                isCurrentBlockHoliday = day.isHoliday;
            }
        });
        if (currentBlock.length > 0) {
            blocks.push({
                isHoliday: isCurrentBlockHoliday,
                days: currentBlock
            });
        }

        // 2. Identify strategies (Holiday string -> Workday string (1-4) -> Holiday string)
        const strategies = [];
        for (let i = 1; i < blocks.length - 1; i++) {
            const prevBlock = blocks[i - 1];
            const currBlock = blocks[i];
            const nextBlock = blocks[i + 1];

            // Condition: curr is Workday (1~4 days), prev and next are Holidays
            if (!currBlock.isHoliday && currBlock.days.length >= 1 && currBlock.days.length <= 4) {
                if (prevBlock.isHoliday && nextBlock.isHoliday) {
                    const totalConsecutive = prevBlock.days.length + currBlock.days.length + nextBlock.days.length;

                    // We only care if taking leave creates >= 4 continuous holidays
                    if (totalConsecutive >= 4) {
                        // Find the reason of the holiday from prev or next block
                        let holidayName = '連假';
                        const findName = (block) => {
                            const validDay = block.days.find(d => d.description && d.description.length > 0);
                            return validDay ? validDay.description : null;
                        };
                        const nameFromPrev = findName(prevBlock);
                        const nameFromNext = findName(nextBlock);
                        holidayName = nameFromPrev || nameFromNext || t('weekendHoliday');

                        // Gather the entire timeline of days (prev Holiday + curr Workday + next Holiday)
                        const allDays = [...prevBlock.days, ...currBlock.days, ...nextBlock.days];

                        strategies.push({
                            name: holidayName,
                            leaveDays: currBlock.days.length,
                            totalDays: totalConsecutive,
                            timeline: allDays
                        });
                    }
                }
            }
        }

        return strategies;
    }

    function renderLeaveStrategies(strategies) {
        elements.leaveStrategiesContainer.innerHTML = '';

        if (strategies.length === 0) {
            elements.strategyToggleBtn.classList.add('hidden');
            elements.leaveStrategiesWrapper.classList.add('hidden');
            return;
        }

        // Initialize wrapper style.height so toggle works correctly on first click
        elements.leaveStrategiesWrapper.classList.remove('hidden');
        elements.strategyToggleBtn.classList.remove('hidden');
        elements.strategyToggleIcon.style.transform = 'rotate(180deg)';

        strategies.forEach(strategy => {
            const card = document.createElement('div');
            card.className = 'strategy-new-card';

            // Generate Calendar columns
            let columnsHTML = '';
            strategy.timeline.forEach(dayInfo => {
                const dateParts = parseDateString(dayInfo.date);
                const isWorkdayBlock = !dayInfo.isHoliday;
                const colModifier = isWorkdayBlock ? 'workday' : 'holiday';
                // Show festival label if it is holiday block and has description
                const festivalLabel = (!isWorkdayBlock && dayInfo.description) ? `<div class="cal-festival-tag font-noto">${dayInfo.description}</div>` : '';

                columnsHTML += `
                    <div class="cal-day-col ${colModifier}">
                        <div class="cal-head font-noto">${dayInfo.week}</div>
                        <div class="cal-body font-outfit">${dateParts.day}</div>
                        ${festivalLabel}
                    </div>
                `;
            });

            // Extract month from the start of the holiday block
            const startDateParts = parseDateString(strategy.timeline[0].date);
            const displayMonth = t('monthNames')[startDateParts.month - 1];

            card.innerHTML = `
                <div class="strategy-left-label font-noto">
                    <div class="month">${displayMonth}</div>
                    <div class="festival">${strategy.name}</div>
                </div>
                
                <div class="strategy-calendar-row">
                    ${columnsHTML}
                </div>
                
                <div class="strategy-right-badge">
                    <div class="badge-text font-noto">${t('strategyBadge', { leave: strategy.leaveDays, total: strategy.totalDays })}</div>
                </div>
            `;
            elements.leaveStrategiesContainer.appendChild(card);
        });

        // Add Legend at the end of the container
        const legend = document.createElement('div');
        legend.className = 'strategy-legend font-noto';
        legend.innerHTML = `
            <div class="legend-item"><div class="legend-dot holiday"></div>${t('legendHoliday')}</div>
            <div class="legend-item"><div class="legend-dot makeup"></div>${t('legendMakeup')}</div>
        `;
        elements.leaveStrategiesContainer.appendChild(legend);

        // After populating, set layout height explicitly
        elements.leaveStrategiesWrapper.style.height = elements.leaveStrategiesWrapper.scrollHeight + 'px';

        // Ensure toggle button is visible, wrapper starts open
        elements.strategyToggleBtn.classList.remove('hidden');
        elements.leaveStrategiesWrapper.classList.remove('hidden');
        elements.strategyToggleIcon.style.transform = 'rotate(0deg)';

    }

    // Start App
    init();
});
