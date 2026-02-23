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
        tooltip: document.getElementById('tooltip')
    };

    // State
    let state = {
        currentYear: new Date().getFullYear(),
        holidaysData: [],
        availableYears: []
    };

    // Constants
    const monthsNames = ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"];
    const dayNames = ["日", "一", "二", "三", "四", "五", "六"];

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
            const response = await fetch(`data/${year}.json`);
            if (!response.ok) throw new Error('Data not found for year ' + year);
            const data = await response.json();
            state.holidaysData = data;
            renderCalendar(data, year);
            calculateStats(data);
        } catch (error) {
            console.error('Error fetching data:', error);
            elements.calendarGrid.innerHTML = `
                <div class="error-state text-center grid-col-span-full py-12">
                    <p class="text-slate-500 mb-4">找不到 ${year} 年的假期資料</p>
                    <button class="btn border px-4 py-2 rounded-md hover:bg-slate-50 text-slate-700 font-noto cursor-pointer" onclick="location.reload()">重新整理</button>
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
                <span class="month-title font-outfit">${monthsNames[monthIndex]}</span>
                <span class="month-stats font-noto">
                    ${holidaysInMonth > 0 ? `<span class="text-primary font-bold">${holidaysInMonth}</span> 國定假日` : '無國定假日'}
                </span>
            `;

            // Days Header (S, M, T, W, T, F, S)
            const daysHeader = document.createElement('div');
            daysHeader.className = 'days-header';
            dayNames.forEach((day, index) => {
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

            // Render Days
            monthData.forEach(dayDetails => {
                const dateParts = parseDateString(dayDetails.date);
                const dayOfMonth = dateParts.day;
                const cell = document.createElement('div');
                cell.className = 'day-cell font-outfit';
                cell.textContent = dayOfMonth;

                const dayOfWeekStr = dayDetails.week;

                if (dayDetails.isHoliday) {
                    if (dayDetails.description) {
                        cell.classList.add('holiday');
                        const dot = document.createElement('div');
                        dot.className = 'holiday-dot';
                        cell.appendChild(dot);

                        // Setup Tooltip interaction
                        cell.addEventListener('mouseenter', (e) => showTooltip(e, dayDetails));
                        cell.addEventListener('mouseleave', hideTooltip);
                        cell.addEventListener('click', (e) => showTooltip(e, dayDetails));
                    } else {
                        // Regular weekend
                        cell.classList.add('weekend');
                    }
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

        elements.tooltip.innerHTML = `
            <div class="font-bold mb-1">${dayDetails.description}</div>
            <div class="text-slate-300 text-xs">${formattedDate}</div>
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
            const name = descriptions.length > 0 ? descriptions[0] : '連假';

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
                <span class="period-days font-outfit">${period.days} <span class="text-sm font-normal text-slate-500 font-noto">天</span></span>
                <span class="period-date font-outfit">${period.dateRange}</span>
            `;
            elements.continuousHolidaysContainer.appendChild(card);
        });

        elements.continuousHolidaysContainer.classList.remove('hidden');
    }

    // Start App
    init();
});
