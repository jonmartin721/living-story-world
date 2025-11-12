function app() {
    return {
        worlds: [],
        currentWorldSlug: '',
        currentWorld: null,
        generating: false,
        generatingWorlds: new Set(),
        regeneratingChapters: new Set(),
        chapterProgress: {},
        generatingTheme: false,
        worldProgress: {},
        showCreateWorld: false,
        showEditWorld: false,
        showSettings: false,
        showConsole: false,
        showSetupWizard: false,
        setupWizardStep: 1,
        showRegenerateOptions: false,
        regenerateChapterNum: null,
        selectedRegenerateType: null,
        settingsTab: 'api',
        viewingChapter: null,
        chapterContent: '',
        selectingChoice: false,
        pendingChoiceId: null,
        choiceConfirmStage: 0,
        consoleLogs: [],
        darkMode: false,
        expandedSections: {},

        settings: {
            text_provider: 'openai',
            image_provider: 'replicate',
            has_openai_key: false,
            has_together_key: false,
            has_huggingface_key: false,
            has_groq_key: false,
            has_gemini_key: false,
            has_openrouter_key: false,
            has_replicate_token: false,
            has_fal_key: false,
            global_instructions: '',
            default_style_pack: 'storybook-ink',
            default_preset: 'cozy-adventure',
            default_text_model: 'gemini-2.5-flash',  // Will be overridden by user's chosen provider
            default_image_model: 'flux-dev',
            reader_font_family: 'Georgia',
            reader_font_size: 'medium'
        },

        settingsForm: {
            text_provider: '',
            image_provider: '',
            openai_api_key: '',
            together_api_key: '',
            huggingface_api_key: '',
            groq_api_key: '',
            gemini_api_key: '',
            openrouter_api_key: '',
            replicate_api_token: '',
            fal_api_key: '',
            global_instructions: '',
            default_style_pack: '',
            default_preset: '',
            default_text_model: '',
            default_image_model: '',
            reader_font_family: '',
            reader_font_size: ''
        },

        newWorld: {
            title: '',
            theme: '',
            style_pack: 'storybook-ink',
            preset: 'cozy-adventure',
            maturity_level: 'general',
            chapter_length: 'medium',
            enable_choices: true,
            memory: '',
            authors_note: '',
            world_instructions: ''
        },

        editWorld: {
            title: '',
            theme: '',
            style_pack: '',
            preset: '',
            maturity_level: '',
            chapter_length: '',
            enable_choices: true,
            memory: '',
            authors_note: '',
            world_instructions: ''
        },

        // Confirmation dialog state
        confirmDialog: {
            show: false,
            message: '',
            resolve: null,
            reject: null
        },

        // Toast notifications
        toasts: [],
        nextToastId: 0,

        // Helper: Show confirmation dialog
        async confirm(message) {
            return new Promise((resolve) => {
                this.confirmDialog = {
                    show: true,
                    message,
                    resolve: () => {
                        this.confirmDialog.show = false;
                        resolve(true);
                    },
                    reject: () => {
                        this.confirmDialog.show = false;
                        resolve(false);
                    }
                };
            });
        },

        // Helper: Show toast notification
        showToast(message, type = 'error') {
            const id = this.nextToastId++;
            const toast = {
                id,
                message,
                type,
                show: true
            };
            this.toasts.push(toast);

            // Auto-hide after 5 seconds
            setTimeout(() => {
                toast.show = false;
                // Remove from array after animation
                setTimeout(() => {
                    const index = this.toasts.findIndex(t => t.id === id);
                    if (index !== -1) this.toasts.splice(index, 1);
                }, 300);
            }, 5000);
        },

        // Helper: Strip "Chapter X: " prefix from titles
        stripChapterPrefix(title) {
            if (!title) return '';
            return title.replace(/^Chapter\s+\d+:\s*/, '');
        },

        // Helper: Get progress text in "Generating... x/y" format
        getProgressText() {
            const progress = this.worldProgress[this.currentWorldSlug];
            if (!progress || !progress.stage) {
                return 'Processing...';
            }

            const stage = progress.stage;
            const hasImages = !this.generateOptions?.no_images;

            // Determine current step and total steps based on backend stages
            let currentStep = 1;
            let totalSteps = hasImages ? 3 : 2;

            // Map backend stages to step numbers:
            // With images: init/text (step 1) → image (step 2) → saving (step 3)
            // Without images: init/text (step 1) → saving (step 2)
            if (stage === 'init' || stage === 'text') {
                currentStep = 1;
            } else if (stage === 'image') {
                currentStep = 2;
            } else if (stage === 'saving') {
                currentStep = hasImages ? 3 : 2;
            } else if (stage === 'complete' || stage === 'done') {
                currentStep = totalSteps;
            }

            return `Generating... ${currentStep}/${totalSteps}`;
        },

        // Helper: Check if the latest chapter has unselected choices
        hasUnselectedChoice() {
            if (!this.currentWorld || !this.currentWorld.chapters || this.currentWorld.chapters.length === 0) {
                return false;
            }
            const lastChapter = this.currentWorld.chapters[this.currentWorld.chapters.length - 1];
            return lastChapter.choices && lastChapter.choices.length > 0 && !lastChapter.selected_choice_id;
        },

        isLatestChapter(chapterNumber) {
            if (!this.currentWorld || !this.currentWorld.chapters || this.currentWorld.chapters.length === 0) {
                return false;
            }
            return chapterNumber === this.currentWorld.chapters.length;
        },

        // Helper: Group chapters into sections for collapsible display
        getChapterSections() {
            if (!this.currentWorld || !this.currentWorld.chapters) {
                return [];
            }

            const chapters = this.currentWorld.chapters;
            const total = chapters.length;
            const sections = [];

            // If less than 10 chapters, show all in one section
            if (total < 10) {
                sections.push({
                    id: 'recent',
                    title: 'Chapters',
                    range: total > 0 ? `1-${total}` : '',
                    chapters: chapters,
                    isRecent: true,
                    count: total
                });
                return sections;
            }

            // 10+ chapters: show last 5 as recent, group rest by 5s
            const recentCount = 5;
            sections.push({
                id: 'recent',
                title: 'Recent Chapters',
                range: `${total - recentCount + 1}-${total}`,
                chapters: chapters.slice(-recentCount),
                isRecent: true,
                count: recentCount
            });

            // Group older chapters by 5s from oldest to newest
            const older = chapters.slice(0, -recentCount);
            const groupSize = 5;

            for (let i = 0; i < older.length; i += groupSize) {
                const sectionChapters = older.slice(i, i + groupSize);
                const startNum = sectionChapters[0].number;
                const endNum = sectionChapters[sectionChapters.length - 1].number;

                sections.push({
                    id: `section-${startNum}-${endNum}`,
                    title: `Chapters ${startNum}-${endNum}`,
                    range: `${startNum}-${endNum}`,
                    chapters: sectionChapters,
                    isRecent: false,
                    count: sectionChapters.length
                });
            }

            return sections;
        },

        // Toggle section expansion
        toggleSection(sectionId) {
            this.expandedSections[sectionId] = !this.expandedSections[sectionId];
        },

        // Check if section is expanded
        isSectionExpanded(sectionId) {
            return this.expandedSections[sectionId] || false;
        },

        // Console logging methods
        addConsoleLog(message, type = 'log') {
            const timestamp = new Date().toLocaleTimeString();
            this.consoleLogs.push({ timestamp, message, type });
            // Auto-scroll console if open
            this.$nextTick(() => {
                if (this.showConsole) {
                    const consoleDiv = document.querySelector('.overflow-y-auto.font-mono');
                    if (consoleDiv) {
                        consoleDiv.scrollTop = consoleDiv.scrollHeight;
                    }
                }
            });
        },

        errorLogCount() {
            return this.consoleLogs.filter(log => log.type === 'error').length;
        },

        clearConsoleLogs() {
            this.consoleLogs = [];
        },

        copyConsoleLogs() {
            const text = this.consoleLogs
                .map(log => `[${log.timestamp}] ${log.type.toUpperCase()}: ${log.message}`)
                .join('\n');
            navigator.clipboard.writeText(text).then(() => {
                this.showToast('Console logs copied to clipboard!', 'success');
            }).catch(() => {
                this.showToast('Failed to copy logs to clipboard');
            });
        },

        async randomWorld() {
            this.generatingTheme = true;
            console.log('[Random World] Starting generation...');

            // Store originals in case of failure
            const originals = {
                title: this.newWorld.title,
                theme: this.newWorld.theme,
                style_pack: this.newWorld.style_pack,
                preset: this.newWorld.preset,
                maturity_level: this.newWorld.maturity_level,
                memory: this.newWorld.memory
            };

            // Show loading state
            this.newWorld.title = 'Generating...';
            this.newWorld.theme = 'Generating...';
            this.newWorld.memory = 'Generating...';

            try {
                console.log('[Random World] Fetching from API...');
                const response = await fetch('/api/generate/world', {
                    signal: AbortSignal.timeout(45000) // 45 second timeout for slow API calls
                });
                console.log('[Random World] Response received, status:', response.status);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                console.log('[Random World] Data parsed:', data);

                // Fill all fields from the response
                this.newWorld.title = data.title;
                this.newWorld.theme = data.theme;
                this.newWorld.style_pack = data.style_pack;
                this.newWorld.preset = data.preset;
                this.newWorld.maturity_level = data.maturity_level;
                this.newWorld.memory = data.memory || '';
            } catch (error) {
                console.error('[Random World] Error:', error);
                // Restore originals on failure
                Object.assign(this.newWorld, originals);
                this.showToast('World generation failed');
            } finally {
                console.log('[Random World] Generation completed');
                this.generatingTheme = false;
            }
        },

        async randomTheme() {
            this.generatingTheme = true;
            const originalTheme = this.newWorld.theme;
            this.newWorld.theme = 'Generating...';

            try {
                const response = await fetch('/api/generate/theme');
                const data = await response.json();
                this.newWorld.theme = data.theme;
            } catch (error) {
                console.error('Failed to generate theme:', error);
                // Fallback to original or placeholder
                this.newWorld.theme = originalTheme || 'Failed to generate theme. Try again?';
            } finally {
                this.generatingTheme = false;
            }
        },

        async randomThemeEdit() {
            this.generatingTheme = true;
            const originalTheme = this.editWorld.theme;
            this.editWorld.theme = 'Generating...';

            try {
                const response = await fetch('/api/generate/theme');
                const data = await response.json();
                this.editWorld.theme = data.theme;
            } catch (error) {
                console.error('Failed to generate theme:', error);
                this.editWorld.theme = originalTheme || 'Failed to generate theme. Try again?';
            } finally {
                this.generatingTheme = false;
            }
        },

        async init() {
            // Force dark mode always
            this.darkMode = true;
            this.applyDarkMode();

            await this.loadSettings();

            // Show setup wizard if no API keys configured
            if (!this.hasAnyApiKey()) {
                this.showSetupWizard = true;
            }

            await this.loadWorlds();
            // Auto-select current world if any
            const currentWorld = this.worlds.find(w => w.is_current);
            if (currentWorld) {
                this.currentWorldSlug = currentWorld.slug;
                await this.loadWorld();
            }
        },

        applyDarkMode() {
            const html = document.documentElement;
            html.classList.add('dark');
        },

        async loadSettings() {
            try {
                const response = await fetch('/api/settings');
                this.settings = await response.json();
                // Apply reader styles immediately after loading
                this.applyReaderStyles();
            } catch (error) {
                console.error('Failed to load settings:', error);
            }
        },

        openSettings() {
            // Populate settings form with current settings
            this.settingsForm = {
                text_provider: this.settings.text_provider,
                image_provider: this.settings.image_provider,
                openai_api_key: '',
                together_api_key: '',
                huggingface_api_key: '',
                groq_api_key: '',
                gemini_api_key: '',
                openrouter_api_key: '',
                replicate_api_token: '',
                fal_api_key: '',
                global_instructions: this.settings.global_instructions || '',
                default_style_pack: this.settings.default_style_pack,
                default_preset: this.settings.default_preset,
                default_text_model: this.settings.default_text_model,
                default_image_model: this.settings.default_image_model,
                reader_font_family: this.settings.reader_font_family,
                reader_font_size: this.settings.reader_font_size
            };
            this.settingsTab = 'api';
            this.showSettings = true;
        },

        async saveSettings() {
            try {
                console.log('Saving reader settings:', {
                    font_family: this.settingsForm.reader_font_family,
                    font_size: this.settingsForm.reader_font_size
                });

                // Build request with only non-empty API keys
                const payload = {
                    text_provider: this.settingsForm.text_provider,
                    image_provider: this.settingsForm.image_provider,
                    global_instructions: this.settingsForm.global_instructions,
                    default_style_pack: this.settingsForm.default_style_pack,
                    default_preset: this.settingsForm.default_preset,
                    default_text_model: this.settingsForm.default_text_model,
                    default_image_model: this.settingsForm.default_image_model,
                    reader_font_family: this.settingsForm.reader_font_family,
                    reader_font_size: this.settingsForm.reader_font_size
                };

                // Only include API keys if they're not empty (user entered them)
                if (this.settingsForm.openai_api_key) payload.openai_api_key = this.settingsForm.openai_api_key;
                if (this.settingsForm.together_api_key) payload.together_api_key = this.settingsForm.together_api_key;
                if (this.settingsForm.huggingface_api_key) payload.huggingface_api_key = this.settingsForm.huggingface_api_key;
                if (this.settingsForm.groq_api_key) payload.groq_api_key = this.settingsForm.groq_api_key;
                if (this.settingsForm.gemini_api_key) payload.gemini_api_key = this.settingsForm.gemini_api_key;
                if (this.settingsForm.openrouter_api_key) payload.openrouter_api_key = this.settingsForm.openrouter_api_key;
                if (this.settingsForm.replicate_api_token) payload.replicate_api_token = this.settingsForm.replicate_api_token;
                if (this.settingsForm.fal_api_key) payload.fal_api_key = this.settingsForm.fal_api_key;

                const response = await fetch('/api/settings', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error('Failed to save settings');
                }

                this.showSettings = false;
                await this.loadSettings();
                console.log('Settings reloaded:', {
                    font_family: this.settings.reader_font_family,
                    font_size: this.settings.reader_font_size
                });
                this.applyReaderStyles();
                this.showToast('Settings updated', 'success');
            } catch (error) {
                console.error('Failed to save settings:', error);
                this.showToast('Failed to save settings. Check console for details.');
            }
        },

        async clearAllApiKeys() {
            if (!await this.confirm('Clear all API keys? This will remove all configured API keys and you will need to re-enter them.')) {
                return;
            }

            try {
                const response = await fetch('/api/settings/clear-keys', {
                    method: 'POST'
                });

                if (!response.ok) {
                    throw new Error('Failed to clear API keys');
                }

                await this.loadSettings();
                this.showToast('All API keys cleared successfully!', 'success');
            } catch (error) {
                console.error('Failed to clear API keys:', error);
                this.showToast('Failed to clear API keys. Check console for details.');
            }
        },

        applyReaderStyles() {
            // Target the chapter content prose element specifically
            const chapterViewer = document.getElementById('chapter-viewer-modal');
            if (!chapterViewer) {
                console.log('Chapter viewer modal not found');
                return;
            }

            const prose = chapterViewer.querySelector('.prose');
            if (!prose) {
                console.log('Prose element not found in chapter viewer');
                return;
            }

            console.log('Applying reader styles:', {
                font_family: this.settings.reader_font_family,
                font_size: this.settings.reader_font_size
            });

            // Apply font family
            const fontMap = {
                'Georgia': 'Georgia, "Times New Roman", serif',
                'serif': 'Georgia, "Times New Roman", serif',
                'sans-serif': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
                'monospace': '"Courier New", Courier, monospace'
            };
            prose.style.fontFamily = fontMap[this.settings.reader_font_family] || fontMap['Georgia'];

            // Apply font size
            const sizeMap = {
                'small': 'clamp(1rem, 1rem + 0.5vw, 1.125rem)',        // 16-18px
                'medium': 'clamp(1.125rem, 1.25rem + 0.5vw, 1.375rem)',  // 18-22px
                'large': 'clamp(1.25rem, 1.5rem + 0.5vw, 1.625rem)',    // 20-26px
                'xl': 'clamp(1.5rem, 1.75rem + 0.5vw, 2rem)'            // 24-32px
            };
            prose.style.fontSize = sizeMap[this.settings.reader_font_size] || sizeMap['medium'];
        },

        async loadWorlds() {
            try {
                const response = await fetch('/api/worlds');
                this.worlds = await response.json();
            } catch (error) {
                console.error('Failed to load worlds:', error);
                this.showToast('Failed to load worlds. Check console for details.');
            }
        },

        async loadWorld() {
            if (!this.currentWorldSlug) {
                this.currentWorld = null;
                return;
            }

            try {
                const response = await fetch(`/api/worlds/${this.currentWorldSlug}`);
                this.currentWorld = await response.json();
            } catch (error) {
                console.error('Failed to load world:', error);
                this.showToast('Failed to load world. Check console for details.');
            }
        },

        async switchWorld() {
            if (this.currentWorldSlug) {
                // Set as current
                await fetch(`/api/worlds/${this.currentWorldSlug}/current`, {
                    method: 'PUT'
                });
                await this.loadWorld();
            }
        },

        openEditWorld() {
            // Populate edit form with current world data
            this.editWorld = {
                title: this.currentWorld.config.title,
                theme: this.currentWorld.config.theme,
                style_pack: this.currentWorld.config.style_pack,
                preset: this.currentWorld.config.preset || 'cozy-adventure',
                maturity_level: this.currentWorld.config.maturity_level || 'general',
                chapter_length: this.currentWorld.config.chapter_length || 'medium',
                enable_choices: this.currentWorld.config.enable_choices || false,
                memory: this.currentWorld.config.memory || '',
                authors_note: this.currentWorld.config.authors_note || '',
                world_instructions: this.currentWorld.config.world_instructions || ''
            };
            this.showEditWorld = true;
        },

        async updateWorld() {
            if (!this.currentWorldSlug) return;

            try {
                const response = await fetch(`/api/worlds/${this.currentWorldSlug}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.editWorld)
                });

                if (!response.ok) {
                    throw new Error('Failed to update world');
                }

                this.showEditWorld = false;

                // Reload world data
                await this.loadWorld();
                await this.loadWorlds();

                this.showToast('Changes saved', 'success');
            } catch (error) {
                console.error('Update failed:', error);
                this.showToast('Save failed - try again');
            }
        },

        async deleteWorld() {
            if (!this.currentWorldSlug) return;

            const worldTitle = this.currentWorld?.config?.title || this.currentWorldSlug;
            if (!await this.confirm(`Are you sure you want to delete "${worldTitle}"? This action cannot be undone.`)) {
                return;
            }

            try {
                const response = await fetch(`/api/worlds/${this.currentWorldSlug}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    throw new Error('Failed to delete world');
                }

                // Clear current world
                this.currentWorldSlug = '';
                this.currentWorld = null;

                // Reload worlds list
                await this.loadWorlds();

                this.showToast('World deleted', 'success');
            } catch (error) {
                console.error('Delete error:', error);
                this.showToast('Could not delete world');
            }
        },

        async createWorld() {
            try {
                const response = await fetch('/api/worlds', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.newWorld)
                });

                if (!response.ok) {
                    throw new Error('Failed to create world');
                }

                const world = await response.json();

                // Reset form
                this.newWorld = {
                    title: '',
                    theme: '',
                    style_pack: 'storybook-ink',
                    preset: 'cozy-adventure',
                    maturity_level: 'general',
                    chapter_length: 'medium',
                    enable_choices: true,
                    memory: '',
                    authors_note: '',
                    world_instructions: ''
                };

                this.showCreateWorld = false;

                // Reload worlds and select new one
                await this.loadWorlds();
                this.currentWorldSlug = world.slug;
                await this.loadWorld();
            } catch (error) {
                console.error('Failed to create world:', error);
                this.showToast('Failed to create world. Check console for details.');
            }
        },

        async generateChapter() {
            if (!this.currentWorldSlug) return;

            const worldSlug = this.currentWorldSlug;
            this.generatingWorlds.add(worldSlug);
            this.generating = this.generatingWorlds.size > 0;
            this.worldProgress[worldSlug] = { percent: 0, message: 'Starting...', stage: 'init' };
            this._lastLoggedStage = null;
            this.addConsoleLog('Starting chapter generation...', 'info');

            try {
                // Start generation
                const response = await fetch(`/api/worlds/${worldSlug}/chapters`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ no_images: false, chapter_length: 'medium' })
                });

                const { job_id } = await response.json();
                this.addConsoleLog(`Job created: ${job_id}`, 'info');

                // Listen to SSE stream
                const evtSource = new EventSource(`/api/worlds/${worldSlug}/chapters/stream/${job_id}`);

                evtSource.addEventListener('progress', (e) => {
                    const data = JSON.parse(e.data);
                    this.worldProgress[worldSlug] = data;
                    // Only log stage changes, not every progress update
                    if (data.stage !== this._lastLoggedStage) {
                        this.addConsoleLog(data.message, 'log');
                        this._lastLoggedStage = data.stage;
                    }
                });

                evtSource.addEventListener('complete', (e) => {
                    const chapter = JSON.parse(e.data);
                    if (this.currentWorldSlug === worldSlug) {
                        this.currentWorld.chapters.push(chapter);
                    }
                    this.generatingWorlds.delete(worldSlug);
                    this.generating = this.generatingWorlds.size > 0;
                    this.worldProgress[worldSlug] = { percent: 100, message: 'Complete!', stage: 'done' };
                    this._lastLoggedStage = null;
                    this.addConsoleLog(`Chapter ${chapter.number} generated successfully!`, 'success');
                    evtSource.close();
                    delete this.worldProgress[worldSlug];
                });

                // Handle error events sent by backend with actual error details
                evtSource.addEventListener('error', (e) => {
                    const errorData = JSON.parse(e.data);
                    const errorMsg = errorData.error || 'Unknown error';
                    console.error('Chapter generation error:', errorMsg);
                    this.addConsoleLog('Chapter generation failed: ' + errorMsg, 'error');
                    this.showToast('Chapter generation failed: ' + errorMsg);
                    this.generatingWorlds.delete(worldSlug);
                    this.generating = this.generatingWorlds.size > 0;
                    delete this.worldProgress[worldSlug];
                    evtSource.close();
                });

                // Handle SSE connection failures
                evtSource.onerror = (e) => {
                    // Only log if we haven't already handled a proper error event
                    if (evtSource.readyState === EventSource.CLOSED) {
                        console.error('SSE connection closed unexpectedly:', e);
                        this.addConsoleLog('Connection to server lost during generation', 'error');
                        this.showToast('Connection lost. Check your network.');
                        this.generatingWorlds.delete(worldSlug);
                        this.generating = this.generatingWorlds.size > 0;
                        delete this.worldProgress[worldSlug];
                        evtSource.close();
                    }
                };

            } catch (error) {
                console.error('Failed to generate chapter:', error);
                this.addConsoleLog('Failed to generate chapter: ' + error.message, 'error');
                this.showToast('Failed to generate chapter. Check console for details.');
                this.generatingWorlds.delete(worldSlug);
                this.generating = this.generatingWorlds.size > 0;
                delete this.worldProgress[worldSlug];
            }
        },

        async viewChapter(chapter, scrollToTop = false) {
            this.viewingChapter = chapter;
            this.resetChoiceSelection();

            try {
                const response = await fetch(`/api/worlds/${this.currentWorldSlug}/chapters/${chapter.number}/content`);
                const data = await response.json();

                // Simple markdown to HTML conversion
                this.chapterContent = this.markdownToHtml(data.content);

                // Apply reader styles and scroll after DOM update
                // Use a slight delay to ensure x-html has rendered
                this.$nextTick(() => {
                    setTimeout(() => {
                        this.applyReaderStyles();
                    }, 50);

                    if (scrollToTop) {
                        const modalContent = document.getElementById('chapter-viewer-modal');
                        if (modalContent) {
                            modalContent.scrollTop = 0;
                        }
                    }
                });
            } catch (error) {
                console.error('Failed to load chapter content:', error);
                this.chapterContent = '<p>Failed to load chapter content.</p>';
            }
        },

        async selectChoice(chapterNum, choiceId) {
            this.selectingChoice = true;
            try {
                const response = await fetch(
                    `/api/worlds/${this.currentWorldSlug}/chapters/${chapterNum}/select-choice`,
                    {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ choice_id: choiceId })
                    }
                );

                if (!response.ok) {
                    throw new Error('Failed to select choice');
                }

                const data = await response.json();

                // Update chapter in current world state (viewingChapter should reference the same object)
                const chapter = this.currentWorld.chapters.find(ch => ch.number === chapterNum);
                if (chapter) {
                    chapter.selected_choice_id = data.choice.id;
                    chapter.choice_reasoning = data.reasoning;
                }

                this.addConsoleLog(`Choice locked in for chapter ${chapterNum}: ${data.choice.text}`, 'success');
                this.showToast('Choice locked in! Ready to generate next chapter.', 'success');
            } catch (error) {
                console.error('Failed to select choice:', error);
                this.addConsoleLog(`Error selecting choice: ${error.message}`, 'error');
                this.showToast('Failed to record choice. Please try again.', 'error');
            } finally {
                this.selectingChoice = false;
            }
        },

        getSelectedChoiceText(chapter) {
            if (!chapter || !chapter.choices || !chapter.selected_choice_id) {
                return '';
            }
            const choice = chapter.choices.find(c => c.id === chapter.selected_choice_id);
            return choice ? choice.text : '';
        },

        selectPendingChoice(choiceId) {
            this.pendingChoiceId = choiceId;
            this.choiceConfirmStage = 1;
        },

        resetChoiceSelection() {
            this.pendingChoiceId = null;
            this.choiceConfirmStage = 0;
        },

        getGenerateButtonText() {
            // Check if we're viewing an older chapter first (need to navigate forward)
            if (this.viewingChapter?.number < this.currentWorld?.chapters?.length) {
                return 'Next Chapter ➡️';
            }
            // Now check for choice selection states (only applies to latest chapter)
            if (this.hasUnselectedChoice() && this.choiceConfirmStage === 0) {
                return '👆 Make a Choice';
            } else if (this.choiceConfirmStage === 1) {
                return '✓ Confirm Choice';
            } else if (this.choiceConfirmStage === 2) {
                return '🔒 Lock in Choice';
            } else {
                return '✨ Generate Next Chapter';
            }
        },

        getGenerateButtonClass() {
            const baseClass = "px-6 py-3 text-white rounded-lg disabled:bg-gray-600 disabled:text-gray-300 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 shadow-lg";

            if (this.choiceConfirmStage === 1) {
                // Confirm stage - yellow/orange
                return baseClass + " bg-yellow-600 hover:bg-yellow-700";
            } else if (this.choiceConfirmStage === 2) {
                // Lock in stage - green
                return baseClass + " bg-green-600 hover:bg-green-700";
            } else {
                // Default - blue
                return baseClass + " bg-blue-500 hover:bg-blue-600";
            }
        },

        isGenerateButtonDisabled() {
            // Never disable "Next Chapter" navigation button
            if (this.viewingChapter?.number < this.currentWorld?.chapters?.length) {
                return false;
            }
            return this.generatingWorlds.has(this.currentWorldSlug) || this.selectingChoice || (this.hasUnselectedChoice() && this.choiceConfirmStage === 0);
        },

        async handleGenerateOrConfirm() {
            if (this.generatingWorlds.has(this.currentWorldSlug) || this.selectingChoice) return;

            // Navigation priority: if viewing an older chapter, always navigate forward
            if (this.viewingChapter?.number < this.currentWorld?.chapters?.length) {
                const nextChapter = this.currentWorld.chapters.find(ch => ch.number === this.viewingChapter.number + 1);
                if (nextChapter) {
                    this.viewChapter(nextChapter, true);
                }
                return;
            }

            // If there's a pending choice on the current (latest) chapter, advance through confirmation stages
            if (this.hasUnselectedChoice()) {
                if (this.choiceConfirmStage === 1) {
                    this.choiceConfirmStage = 2;
                } else if (this.choiceConfirmStage === 2 && this.pendingChoiceId) {
                    // Lock in the choice
                    await this.selectChoice(this.viewingChapter.number, this.pendingChoiceId);
                    this.resetChoiceSelection();
                }
                return;
            }

            // Normal generation flow
            this.generateChapter();
        },

        showRegenerateDialog(chapterNum) {
            this.regenerateChapterNum = chapterNum;
            this.selectedRegenerateType = null;
            this.showRegenerateOptions = true;
        },

        confirmRegenerate() {
            if (!this.selectedRegenerateType) return;
            this.handleRegenerate(this.selectedRegenerateType);
        },

        async handleRegenerate(type) {
            this.showRegenerateOptions = false;
            this.selectedRegenerateType = null;
            const chapterNum = this.regenerateChapterNum;

            if (!chapterNum) return;

            if (type === 'everything') {
                await this.rerollChapter(chapterNum);
            } else if (type === 'text') {
                // Text-only regeneration: reroll without images
                await this.rerollChapterTextOnly(chapterNum);
            } else if (type === 'image') {
                await this.regenerateImage(chapterNum);
            }
        },

        async rerollChapterTextOnly(chapterNum) {
            const worldSlug = this.currentWorldSlug;
            const chapterKey = `${worldSlug}-${chapterNum}`;
            this.regeneratingChapters.add(chapterKey);
            this.chapterProgress[chapterKey] = { percent: 0, message: 'Starting text regeneration...', stage: 'init', type: 'text' };
            this.addConsoleLog(`Starting text-only reroll of chapter ${chapterNum}...`, 'info');

            try {
                // Start reroll with images disabled
                const response = await fetch(`/api/worlds/${this.currentWorldSlug}/chapters/${chapterNum}/reroll`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        preset: 'cozy-adventure',
                        no_images: true  // Generate text only, keep image
                    })
                });

                const { job_id } = await response.json();
                this.addConsoleLog(`Text-only reroll job created: ${job_id}`, 'info');

                // Listen to SSE stream
                const evtSource = new EventSource(`/api/worlds/${this.currentWorldSlug}/chapters/stream/${job_id}`);

                evtSource.addEventListener('progress', (e) => {
                    const data = JSON.parse(e.data);
                    this.chapterProgress[chapterKey] = { ...data, type: 'text' };
                    // Only log stage changes, not every progress update
                    if (data.stage !== this._lastLoggedStage) {
                        this.addConsoleLog(data.message, 'log');
                        this._lastLoggedStage = data.stage;
                    }
                });

                evtSource.addEventListener('complete', (e) => {
                    const updatedChapter = JSON.parse(e.data);

                    // Find and update the chapter if we're still viewing this world
                    if (this.currentWorldSlug === this.currentWorldSlug) {
                        const chapterIndex = this.currentWorld.chapters.findIndex(ch => ch.number === chapterNum);
                        if (chapterIndex !== -1) {
                            this.currentWorld.chapters[chapterIndex] = updatedChapter;
                        }
                    }

                    this.chapterProgress[chapterKey] = { percent: 100, message: 'Text regenerated!', stage: 'done', type: 'text' };
                    this._lastLoggedStage = null;
                    this.addConsoleLog(`Chapter ${chapterNum} text regenerated successfully!`, 'success');
                    evtSource.close();
                    setTimeout(() => {
                        this.regeneratingChapters.delete(chapterKey);
                        delete this.chapterProgress[chapterKey];
                    }, 1000);
                });

                // Handle error events sent by backend with actual error details
                evtSource.addEventListener('error', (e) => {
                    const errorData = JSON.parse(e.data);
                    const errorMsg = errorData.error || 'Unknown error';
                    console.error('Text regeneration error:', errorMsg);
                    this.addConsoleLog('Text regeneration failed: ' + errorMsg, 'error');
                    this.showToast('Text regeneration failed: ' + errorMsg);
                    this.regeneratingChapters.delete(chapterKey);
                    delete this.chapterProgress[chapterKey];
                    evtSource.close();
                });

                // Handle SSE connection failures
                evtSource.onerror = (e) => {
                    if (evtSource.readyState === EventSource.CLOSED) {
                        console.error('SSE connection closed unexpectedly:', e);
                        this.addConsoleLog('Connection to server lost during text regeneration', 'error');
                        this.showToast('Connection lost. Check your network.');
                        this.regeneratingChapters.delete(chapterKey);
                        delete this.chapterProgress[chapterKey];
                        evtSource.close();
                    }
                };
            } catch (error) {
                console.error('Failed to regenerate chapter text:', error);
                this.addConsoleLog(`Error regenerating text: ${error.message}`, 'error');
                this.showToast('Failed to regenerate chapter text. Check console for details.');
                this.regeneratingChapters.delete(chapterKey);
                delete this.chapterProgress[chapterKey];
            }
        },

        async rerollChapter(chapterNum) {

            const worldSlug = this.currentWorldSlug;
            const chapterKey = `${worldSlug}-${chapterNum}`;
            this.regeneratingChapters.add(chapterKey);
            this.chapterProgress[chapterKey] = { percent: 0, message: 'Starting full regeneration...', stage: 'init', type: 'everything' };
            this._lastLoggedStage = null;
            this.addConsoleLog(`Starting reroll of chapter ${chapterNum}...`, 'info');

            try{
                // Start reroll with images enabled
                const response = await fetch(`/api/worlds/${this.currentWorldSlug}/chapters/${chapterNum}/reroll`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        preset: 'cozy-adventure',
                        no_images: false  // Generate both text and image
                    })
                });

                const { job_id } = await response.json();
                this.addConsoleLog(`Reroll job created: ${job_id}`, 'info');

                // Listen to SSE stream
                const evtSource = new EventSource(`/api/worlds/${worldSlug}/chapters/stream/${job_id}`);

                evtSource.addEventListener('progress', (e) => {
                    const data = JSON.parse(e.data);
                    this.chapterProgress[chapterKey] = { ...data, type: 'everything' };
                    // Only log stage changes, not every progress update
                    if (data.stage !== this._lastLoggedStage) {
                        this.addConsoleLog(data.message, 'log');
                        this._lastLoggedStage = data.stage;
                    }
                });

                evtSource.addEventListener('complete', (e) => {
                    const updatedChapter = JSON.parse(e.data);

                    // Find and update the chapter if we're still viewing this world
                    if (this.currentWorldSlug === worldSlug) {
                        const chapterIndex = this.currentWorld.chapters.findIndex(ch => ch.number === chapterNum);
                        if (chapterIndex !== -1) {
                            this.currentWorld.chapters[chapterIndex] = updatedChapter;
                        }
                    }

                    this.chapterProgress[chapterKey] = { percent: 100, message: 'Chapter regenerated!', stage: 'done', type: 'everything' };
                    this._lastLoggedStage = null;
                    this.addConsoleLog(`Chapter ${chapterNum} regenerated successfully!`, 'success');
                    evtSource.close();
                    setTimeout(() => {
                        this.regeneratingChapters.delete(chapterKey);
                        delete this.chapterProgress[chapterKey];
                    }, 1000);
                });

                // Handle error events sent by backend with actual error details
                evtSource.addEventListener('error', (e) => {
                    const errorData = JSON.parse(e.data);
                    const errorMsg = errorData.error || 'Unknown error';
                    console.error('Chapter reroll error:', errorMsg);
                    this.addConsoleLog('Chapter reroll failed: ' + errorMsg, 'error');
                    this.showToast('Chapter regeneration failed: ' + errorMsg);
                    this.regeneratingChapters.delete(chapterKey);
                    delete this.chapterProgress[chapterKey];
                    evtSource.close();
                });

                // Handle SSE connection failures
                evtSource.onerror = (e) => {
                    if (evtSource.readyState === EventSource.CLOSED) {
                        console.error('SSE connection closed unexpectedly:', e);
                        this.addConsoleLog('Connection to server lost during chapter regeneration', 'error');
                        this.showToast('Connection lost. Check your network.');
                        this.regeneratingChapters.delete(chapterKey);
                        delete this.chapterProgress[chapterKey];
                        evtSource.close();
                    }
                };

            } catch (error) {
                console.error('Failed to reroll chapter:', error);
                this.addConsoleLog('Failed to reroll chapter: ' + error.message, 'error');
                this.showToast('Failed to regenerate chapter. Check console for details.');
                this.regeneratingChapters.delete(chapterKey);
                delete this.chapterProgress[chapterKey];
            }
        },

  
        async regenerateImage(chapterNum) {

            const worldSlug = this.currentWorldSlug;
            const chapterKey = `${worldSlug}-${chapterNum}`;
            this.regeneratingChapters.add(chapterKey);
            this.chapterProgress[chapterKey] = { percent: 10, message: 'Regenerating image...', stage: 'image', type: 'image' };
            this.addConsoleLog(`Starting image regeneration for chapter ${chapterNum}...`, 'info');

            try {
                this.chapterProgress[chapterKey] = { percent: 30, message: 'Calling image API...', stage: 'image', type: 'image' };
                this.addConsoleLog('Calling image generation API...', 'log');

                const response = await fetch(`/api/worlds/${worldSlug}/images`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ chapter: chapterNum })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                this.chapterProgress[chapterKey] = { percent: 80, message: 'Processing image...', stage: 'image', type: 'image' };
                this.addConsoleLog('Processing generated image...', 'log');

                const data = await response.json();

                // Update the chapter's scene if we're still viewing this world
                if (this.currentWorldSlug === worldSlug) {
                    const chapter = this.currentWorld.chapters.find(ch => ch.number === chapterNum);
                    if (chapter) {
                        chapter.scene = data.scene; // Backend now handles cache bypass with unique filenames
                    }
                }

                this.chapterProgress[chapterKey] = { percent: 100, message: 'Image regenerated!', stage: 'done', type: 'image' };
                this.addConsoleLog(`Image for chapter ${chapterNum} regenerated successfully!`, 'success');
                this.showToast('Image regenerated successfully!', 'success');
                setTimeout(() => {
                    this.regeneratingChapters.delete(chapterKey);
                    delete this.chapterProgress[chapterKey];
                }, 1000);
            } catch (error) {
                console.error('Failed to regenerate image:', error);
                this.addConsoleLog('Failed to regenerate image: ' + error.message, 'error');
                this.showToast('Failed to regenerate image: ' + error.message);
                this.regeneratingChapters.delete(chapterKey);
                delete this.chapterProgress[chapterKey];
            }
        },

        hasPrevChapter() {
            if (!this.viewingChapter || !this.currentWorld?.chapters) return false;
            return this.viewingChapter.number > 1;
        },

        hasNextChapter() {
            if (!this.viewingChapter || !this.currentWorld?.chapters) return false;
            const maxChapter = Math.max(...this.currentWorld.chapters.map(ch => ch.number));
            return this.viewingChapter.number < maxChapter;
        },

        navigateChapter(direction) {
            if (!this.viewingChapter || !this.currentWorld?.chapters) return;

            const currentNum = this.viewingChapter.number;
            let targetNum;

            if (direction === 'prev') {
                targetNum = currentNum - 1;
            } else if (direction === 'next') {
                targetNum = currentNum + 1;
            } else {
                return;
            }

            const targetChapter = this.currentWorld.chapters.find(ch => ch.number === targetNum);
            if (targetChapter) {
                this.viewChapter(targetChapter);
            }
        },

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },

        markdownToHtml(markdown) {
            // Remove metadata comment at top
            let text = markdown.replace(/^<!--[\s\S]*?-->\n*/m, '');

            // Escape HTML to prevent XSS
            text = this.escapeHtml(text);

            // Headers
            text = text.replace(/^### (.*$)/gim, '<h3>$1</h3>');
            text = text.replace(/^## (.*$)/gim, '<h2>$1</h2>');
            text = text.replace(/^# (.*$)/gim, '<h1>$1</h1>');

            // Bold
            text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

            // Italic
            text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

            // Paragraphs
            text = text.split('\n\n').map(para => {
                if (para.startsWith('<h') || !para.trim()) {
                    return para;
                }
                return '<p>' + para + '</p>';
            }).join('\n');

            return text;
        },

        // Helper function to get image model options based on selected provider
        getImageModelOptions() {
            const provider = this.settingsForm.image_provider || 'replicate';

            switch (provider) {
                case 'replicate':
                    return [
                        { value: 'flux-dev', label: 'Flux Dev (Higher Quality)' },
                        { value: 'flux-schnell', label: 'Flux Schnell (Faster)' }
                    ];
                case 'huggingface':
                    return [
                        { value: 'stabilityai/stable-diffusion-xl-base-1.0', label: 'Stable Diffusion XL' },
                        { value: 'black-forest-labs/FLUX.1-dev', label: 'FLUX.1 Dev' },
                        { value: 'black-forest-labs/FLUX.1-schnell', label: 'FLUX.1 Schnell' },
                        { value: 'stabilityai/stable-diffusion-2-1', label: 'Stable Diffusion 2.1' },
                        { value: 'runwayml/stable-diffusion-v1-5', label: 'Stable Diffusion 1.5' }
                    ];
                case 'pollinations':
                    return [
                        { value: 'flux', label: 'Flux' },
                        { value: 'flux-dev', label: 'Flux Dev' },
                        { value: 'flux-schnell', label: 'Flux Schnell' },
                        { value: 'sdxl', label: 'Stable Diffusion XL' },
                        { value: 'sd3', label: 'Stable Diffusion 3' }
                    ];
                case 'falai':
                    return [
                        { value: 'flux/schnell', label: 'Flux Schnell' },
                        { value: 'flux/dev', label: 'Flux Dev' },
                        { value: 'stability-ai/sd3', label: 'Stable Diffusion 3' },
                        { value: 'stability-ai/sd-xl', label: 'Stable Diffusion XL' }
                    ];
                default:
                    return [
                        { value: 'flux-dev', label: 'Flux Dev' },
                        { value: 'flux-schnell', label: 'Flux Schnell' }
                    ];
            }
        },

        // Setup Wizard
        hasAnyApiKey() {
            return this.settings.has_openai_key ||
                   this.settings.has_gemini_key ||
                   this.settings.has_groq_key ||
                   this.settings.has_together_key ||
                   this.settings.has_huggingface_key ||
                   this.settings.has_openrouter_key;
        },

        async completeSetupWizard() {
            // Set defaults to free providers
            const updates = {
                text_provider: 'gemini',
                image_provider: 'pollinations',
                default_text_model: 'gemini-2.5-flash',
                default_image_model: 'flux'
            };

            // Add Gemini API key if provided
            if (this.settingsForm.gemini_api_key && this.settingsForm.gemini_api_key.trim()) {
                updates.gemini_api_key = this.settingsForm.gemini_api_key.trim();
            }

            try {
                const response = await fetch('/api/settings', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updates)
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to save settings');
                }

                await this.loadSettings();
                this.showSetupWizard = false;
                this.toast('Setup complete! You can now create your first world.');
            } catch (error) {
                console.error('Failed to complete setup:', error);
                this.toast('Failed to save settings: ' + error.message);
            }
        },

        skipSetupWizard() {
            // Just close wizard, use defaults
            this.showSetupWizard = false;
            this.toast('Using free providers (Pollinations for images). You can configure API keys anytime in Settings.');
        }
    }
}
