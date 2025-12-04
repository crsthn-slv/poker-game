// Removed direct Supabase client dependency to use backend proxy
// This avoids exposing keys or needing Anon Key on frontend if user only has DB credentials

class LocalizationManager {
    constructor() {
        this.translations = {}; // Cache em memória: { 'MENU_START': 'Iniciar', ... }
        this.currentLang = localStorage.getItem('game_lang') || 'en';
        this.isLoaded = false;
    }

    /**
     * Busca traduções do Backend API e popula o cache.
     * @param {string} langCode - Código do idioma (ex: 'pt-br')
     */
    async init(langCode = this.currentLang) {
        this.currentLang = langCode;
        console.log(`Carregando traduções para: ${langCode}...`);

        // Verifica se já temos em cache local (localStorage) para evitar round-trip
        const cachedData = localStorage.getItem(`i18n_${langCode}`);
        const cachedTimestamp = localStorage.getItem(`i18n_${langCode}_ts`);
        const CACHE_DURATION = 1000 * 60 * 60; // 1 hora

        if (cachedData && cachedTimestamp && (Date.now() - cachedTimestamp < CACHE_DURATION)) {
            try {
                this.translations = JSON.parse(cachedData);
                this.isLoaded = true;
                console.log('Traduções carregadas do cache local.');
                this.updatePage();
                return;
            } catch (e) {
                console.warn('Erro ao ler cache de traduções, buscando novamente.');
            }
        }

        // Busca do Backend API
        try {
            const response = await fetch(`/api/translations/${langCode}`);
            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();

            if (Object.keys(data).length > 0) {
                this.translations = data;

                // Salva no localStorage
                localStorage.setItem(`i18n_${langCode}`, JSON.stringify(this.translations));
                localStorage.setItem(`i18n_${langCode}_ts`, Date.now());
                localStorage.setItem('game_lang', langCode);

                this.isLoaded = true;
                console.log('Traduções carregadas do Backend API.');
                this.updatePage();
                return;
            }
        } catch (e) {
            console.warn('Backend API failed, trying local translations.json...', e);
        }

        // NO FALLBACKS as per user request.
        console.error('Failed to load translations from API and cache.');
    }

    /**
     * Retorna o texto traduzido.
     * @param {string} key - A chave do texto (ex: 'MENU_START')
     * @param {object} params - Parâmetros dinâmicos (ex: {name: 'Player'})
     */
    get(key, params = {}) {
        let text = this.translations[key] || key; // Retorna a própria chave se não achar

        // Substituição simples de parâmetros (ex: "Olá {name}")
        for (const [paramKey, paramValue] of Object.entries(params)) {
            text = text.replace(`{${paramKey}}`, paramValue);
        }

        return text;
    }

    /**
     * Atualiza todos os elementos da página que tenham o atributo data-i18n
     */
    updatePage() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            // Suporte para placeholder (ex: inputs)
            if (el.tagName === 'INPUT' && el.getAttribute('placeholder')) {
                el.placeholder = this.get(key);
            } else {
                el.textContent = this.get(key);
            }
        });
    }
}

// Exporta uma instância única
export const i18n = new LocalizationManager();
