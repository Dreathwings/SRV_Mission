(function () {
    function resolveTheme() {
        try {
            const storedTheme = window.localStorage.getItem('mission-theme');
            if (storedTheme === 'light' || storedTheme === 'dark') {
                return storedTheme;
            }
        } catch (error) {
        }

        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        const currentTheme = theme === 'dark' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', currentTheme);
        if (document.body) {
            document.body.setAttribute('data-theme', currentTheme);
        }

        document.querySelectorAll('[data-theme-toggle]').forEach((toggle) => {
            toggle.setAttribute('aria-pressed', String(currentTheme === 'dark'));
            const icon = toggle.querySelector('[data-theme-icon]');
            const label = toggle.querySelector('[data-theme-label]');
            if (icon) {
                icon.textContent = currentTheme === 'dark' ? 'light_mode' : 'dark_mode';
            }
            if (label) {
                label.textContent = currentTheme === 'dark' ? 'Mode clair' : 'Mode sombre';
            }
        });
    }

    function saveTheme(theme) {
        try {
            window.localStorage.setItem('mission-theme', theme);
        } catch (error) {
        }
    }

    function bindToggle() {
        document.querySelectorAll('[data-theme-toggle]').forEach((toggle) => {
            if (toggle.dataset.themeReady === 'true') {
                return;
            }

            toggle.dataset.themeReady = 'true';
            toggle.addEventListener('click', () => {
                const nextTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
                saveTheme(nextTheme);
                applyTheme(nextTheme);
            });
        });
    }

    function initTheme() {
        applyTheme(resolveTheme());
        bindToggle();
    }

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const syncSystemTheme = (event) => {
        try {
            const storedTheme = window.localStorage.getItem('mission-theme');
            if (storedTheme === 'light' || storedTheme === 'dark') {
                return;
            }
        } catch (error) {
        }

        applyTheme(event.matches ? 'dark' : 'light');
    };

    if (typeof mediaQuery.addEventListener === 'function') {
        mediaQuery.addEventListener('change', syncSystemTheme);
    } else if (typeof mediaQuery.addListener === 'function') {
        mediaQuery.addListener(syncSystemTheme);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }
})();
