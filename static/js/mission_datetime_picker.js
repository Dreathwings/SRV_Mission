(function() {
    const MONTHS = [
        'Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin',
        'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre'
    ];
    const DAYS = ['Lu', 'Ma', 'Me', 'Je', 'Ve', 'Sa', 'Di'];

    function pad(value) {
        return String(value).padStart(2, '0');
    }

    function cloneDate(value) {
        return new Date(value.getTime());
    }

    function atStartOfDay(value) {
        const day = cloneDate(value);
        day.setHours(0, 0, 0, 0);
        return day;
    }

    function sameDay(left, right) {
        return left.getFullYear() === right.getFullYear()
            && left.getMonth() === right.getMonth()
            && left.getDate() === right.getDate();
    }

    function parseDatePart(value) {
        const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value || '');
        if (!match) {
            return null;
        }

        const parsed = new Date(Number(match[3]), Number(match[2]) - 1, Number(match[1]));
        if (Number.isNaN(parsed.getTime())) {
            return null;
        }

        return parsed;
    }

    function parseTimePart(value) {
        const match = /^(\d{2}):(\d{2})$/.exec(value || '');
        if (!match) {
            return null;
        }

        return {
            hours: Number(match[1]),
            minutes: Number(match[2]),
        };
    }

    function parseDateTime(dateValue, timeValue) {
        const date = parseDatePart(dateValue);
        if (!date) {
            return null;
        }

        const time = parseTimePart(timeValue) || { hours: 9, minutes: 0 };
        date.setHours(time.hours, time.minutes, 0, 0);
        return date;
    }

    function formatHiddenDate(value) {
        return `${pad(value.getDate())}/${pad(value.getMonth() + 1)}/${value.getFullYear()}`;
    }

    function formatHiddenTime(value) {
        return `${pad(value.getHours())}:${pad(value.getMinutes())}`;
    }

    function formatDisplay(value) {
        return `${pad(value.getDate())} ${MONTHS[value.getMonth()]} ${value.getFullYear()} · ${formatHiddenTime(value)}`;
    }

    function compareDays(left, right) {
        return atStartOfDay(left).getTime() - atStartOfDay(right).getTime();
    }

    function compareDateTimes(left, right) {
        return left.getTime() - right.getTime();
    }

    function createOption(value, label) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        return option;
    }

    window.setupMissionDateTimePicker = function(config) {
        const isReadOnly = Boolean(config.readOnly);
        const overlay = document.getElementById(config.overlayId);
        const dialog = document.getElementById(config.dialogId);
        const title = document.getElementById(config.titleId);
        const summary = document.getElementById(config.summaryId);
        const monthSelect = document.getElementById(config.monthSelectId);
        const yearSelect = document.getElementById(config.yearSelectId);
        const calendarGrid = document.getElementById(config.gridId);
        const calendarWeekdays = document.getElementById(config.weekdaysId);
        const hourSelect = document.getElementById(config.hourSelectId);
        const minuteSelect = document.getElementById(config.minuteSelectId);
        const previousButton = document.getElementById(config.previousButtonId);
        const nextButton = document.getElementById(config.nextButtonId);
        const cancelButton = document.getElementById(config.cancelButtonId);
        const dismissButton = document.getElementById(config.dismissButtonId);
        const applyButton = document.getElementById(config.applyButtonId);
        const fields = {};
        const state = {
            activeKey: null,
            pending: null,
            viewMonth: null,
        };

        function resolveStartMinDate() {
            const minDate = config.startMinDate();
            return atStartOfDay(minDate);
        }

        function resolveMaxDate() {
            return atStartOfDay(config.maxDate());
        }

        function readFieldValue(key) {
            const field = fields[key];
            return parseDateTime(field.dateInput.value, field.timeInput.value);
        }

        function resolveMinDate(key) {
            const baseMin = resolveStartMinDate();
            if (key === config.returnKey) {
                const startValue = readFieldValue(config.startKey);
                if (startValue && compareDays(startValue, baseMin) > 0) {
                    return atStartOfDay(startValue);
                }
            }
            return baseMin;
        }

        function clampDate(value, key) {
            const maxDate = resolveMaxDate();
            const minDate = resolveMinDate(key);
            const fallback = value ? cloneDate(value) : new Date(minDate.getFullYear(), minDate.getMonth(), minDate.getDate(), 9, 0, 0, 0);

            if (compareDays(fallback, minDate) < 0) {
                fallback.setFullYear(minDate.getFullYear(), minDate.getMonth(), minDate.getDate());
            }
            if (compareDays(fallback, maxDate) > 0) {
                fallback.setFullYear(maxDate.getFullYear(), maxDate.getMonth(), maxDate.getDate());
            }
            return fallback;
        }

        function setFieldValue(key, value) {
            const field = fields[key];
            const clamped = clampDate(value, key);
            field.dateInput.value = formatHiddenDate(clamped);
            field.timeInput.value = formatHiddenTime(clamped);
            field.display.textContent = formatDisplay(clamped);
            field.trigger.classList.remove('is-empty');
        }

        function clearFieldValue(key) {
            const field = fields[key];
            field.dateInput.value = '';
            field.timeInput.value = '';
            field.display.textContent = field.placeholder;
            field.trigger.classList.add('is-empty');
        }

        function syncReturnValueIfNeeded() {
            const startValue = readFieldValue(config.startKey);
            const returnValue = readFieldValue(config.returnKey);
            if (!startValue) {
                return;
            }
            if (!returnValue || compareDateTimes(returnValue, startValue) < 0) {
                setFieldValue(config.returnKey, startValue);
            }
        }

        function refreshFieldDisplays() {
            Object.keys(fields).forEach((key) => {
                const currentValue = readFieldValue(key);
                if (currentValue) {
                    const field = fields[key];
                    field.display.textContent = formatDisplay(currentValue);
                    field.trigger.classList.remove('is-empty');
                } else {
                    clearFieldValue(key);
                }
            });
        }

        function populateWeekdays() {
            calendarWeekdays.innerHTML = '';
            DAYS.forEach((label) => {
                const node = document.createElement('span');
                node.textContent = label;
                calendarWeekdays.appendChild(node);
            });
        }

        function populateTimeSelects() {
            hourSelect.innerHTML = '';
            minuteSelect.innerHTML = '';

            for (let hour = 0; hour < 24; hour += 1) {
                const value = pad(hour);
                hourSelect.appendChild(createOption(value, value));
            }
            for (let minute = 0; minute < 60; minute += 1) {
                const value = pad(minute);
                minuteSelect.appendChild(createOption(value, value));
            }
        }

        function populateMonthSelect() {
            monthSelect.innerHTML = '';
            MONTHS.forEach((month, index) => {
                monthSelect.appendChild(createOption(String(index), month));
            });
        }

        function populateYearSelect() {
            const minYear = resolveStartMinDate().getFullYear();
            const maxYear = resolveMaxDate().getFullYear();
            yearSelect.innerHTML = '';
            for (let year = minYear; year <= maxYear; year += 1) {
                yearSelect.appendChild(createOption(String(year), String(year)));
            }
        }

        function updateSummary() {
            if (!state.pending) {
                summary.textContent = '';
                return;
            }
            summary.textContent = `${fields[state.activeKey].title} · ${formatDisplay(state.pending)}`;
        }

        function buildCalendarCell(cellDate, inCurrentMonth) {
            const minDate = resolveMinDate(state.activeKey);
            const maxDate = resolveMaxDate();
            const today = new Date();
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'mission-calendar-day';
            button.textContent = String(cellDate.getDate());

            if (!inCurrentMonth) {
                button.classList.add('is-outside');
            }
            if (sameDay(cellDate, today)) {
                button.classList.add('is-today');
            }
            if (state.pending && sameDay(cellDate, state.pending)) {
                button.classList.add('is-selected');
            }

            const disabled = compareDays(cellDate, minDate) < 0 || compareDays(cellDate, maxDate) > 0;
            if (disabled) {
                button.disabled = true;
                button.classList.add('is-disabled');
                return button;
            }

            button.addEventListener('click', () => {
                state.pending.setFullYear(cellDate.getFullYear(), cellDate.getMonth(), cellDate.getDate());
                state.viewMonth = new Date(cellDate.getFullYear(), cellDate.getMonth(), 1);
                renderCalendar();
            });

            return button;
        }

        function renderCalendar() {
            if (!state.pending || !state.viewMonth) {
                return;
            }

            const viewYear = state.viewMonth.getFullYear();
            const viewMonth = state.viewMonth.getMonth();
            const firstOfMonth = new Date(viewYear, viewMonth, 1);
            const firstGridDay = new Date(firstOfMonth);
            firstGridDay.setDate(firstOfMonth.getDate() - ((firstOfMonth.getDay() + 6) % 7));

            monthSelect.value = String(viewMonth);
            yearSelect.value = String(viewYear);
            hourSelect.value = pad(state.pending.getHours());
            minuteSelect.value = pad(state.pending.getMinutes());
            title.textContent = fields[state.activeKey].title;
            updateSummary();

            calendarGrid.innerHTML = '';
            for (let index = 0; index < 42; index += 1) {
                const cellDate = new Date(firstGridDay);
                cellDate.setDate(firstGridDay.getDate() + index);
                calendarGrid.appendChild(buildCalendarCell(cellDate, cellDate.getMonth() === viewMonth));
            }
        }

        function openPicker(key) {
            if (isReadOnly) {
                return;
            }
            state.activeKey = key;
            state.pending = clampDate(readFieldValue(key), key);
            state.viewMonth = new Date(state.pending.getFullYear(), state.pending.getMonth(), 1);
            overlay.hidden = false;
            document.body.classList.add('datetime-picker-open');
            renderCalendar();
        }

        function closePicker() {
            overlay.hidden = true;
            document.body.classList.remove('datetime-picker-open');
            state.activeKey = null;
            state.pending = null;
            state.viewMonth = null;
        }

        function shiftMonth(delta) {
            if (!state.viewMonth) {
                return;
            }
            state.viewMonth = new Date(state.viewMonth.getFullYear(), state.viewMonth.getMonth() + delta, 1);
            renderCalendar();
        }

        function applyPicker() {
            if (!state.activeKey || !state.pending) {
                return;
            }
            setFieldValue(state.activeKey, state.pending);
            if (state.activeKey === config.startKey) {
                syncReturnValueIfNeeded();
            }
            closePicker();
        }

        Object.keys(config.fields).forEach((key) => {
            const fieldConfig = config.fields[key];
            fields[key] = {
                title: fieldConfig.title,
                placeholder: fieldConfig.placeholder,
                trigger: document.getElementById(fieldConfig.triggerId),
                display: document.getElementById(fieldConfig.displayId),
                dateInput: document.getElementById(fieldConfig.dateInputId),
                timeInput: document.getElementById(fieldConfig.timeInputId),
            };
            if (!isReadOnly) {
                fields[key].trigger.addEventListener('click', () => openPicker(key));
            }
        });

        populateWeekdays();
        populateMonthSelect();
        populateTimeSelects();
        populateYearSelect();
        refreshFieldDisplays();
        closePicker();

        monthSelect.addEventListener('change', () => {
            state.viewMonth = new Date(Number(yearSelect.value), Number(monthSelect.value), 1);
            renderCalendar();
        });

        yearSelect.addEventListener('change', () => {
            state.viewMonth = new Date(Number(yearSelect.value), Number(monthSelect.value), 1);
            renderCalendar();
        });

        hourSelect.addEventListener('change', () => {
            if (!state.pending) {
                return;
            }
            state.pending.setHours(Number(hourSelect.value), state.pending.getMinutes(), 0, 0);
            updateSummary();
        });

        minuteSelect.addEventListener('change', () => {
            if (!state.pending) {
                return;
            }
            state.pending.setMinutes(Number(minuteSelect.value), 0, 0);
            updateSummary();
        });

        previousButton.addEventListener('click', () => shiftMonth(-1));
        nextButton.addEventListener('click', () => shiftMonth(1));
        cancelButton.addEventListener('click', closePicker);
        dismissButton.addEventListener('click', closePicker);
        applyButton.addEventListener('click', applyPicker);

        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) {
                closePicker();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && !overlay.hidden) {
                closePicker();
            }
        });

        dialog.addEventListener('click', (event) => {
            event.stopPropagation();
        });

        return {
            close: closePicker,
        };
    };
})();
