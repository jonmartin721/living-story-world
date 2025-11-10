function app() {
    return {
        worlds: [],
        currentWorldSlug: '',
        currentWorld: null,
        generating: false,
        generatingTheme: false,
        progress: { percent: 0, message: '', stage: '' },
        showCreateWorld: false,
        showEditWorld: false,
        showGenerateChapter: false,
        showSettings: false,
        showConsole: false,
        showRegenerateOptions: false,
        regenerateChapterNum: null,
        settingsTab: 'api',
        viewingChapter: null,
        chapterContent: '',
        selectingChoice: false,
        consoleLogs: [],
        darkMode: false,

        settings: {
            text_provider: 'openai',
            image_provider: 'replicate',
            has_openai_key: false,
            has_together_key: false,
            has_huggingface_key: false,
            has_groq_key: false,
            has_replicate_token: false,
            has_fal_key: false,
            global_instructions: '',
            default_style_pack: 'storybook-ink',
            default_preset: 'cozy-adventure',
            default_text_model: 'gpt-4o-mini',
            default_image_model: 'flux-dev'
        },

        settingsForm: {
            text_provider: '',
            image_provider: '',
            openai_api_key: '',
            together_api_key: '',
            huggingface_api_key: '',
            groq_api_key: '',
            replicate_api_token: '',
            fal_api_key: '',
            global_instructions: '',
            default_style_pack: '',
            default_preset: '',
            default_text_model: '',
            default_image_model: ''
        },

        newWorld: {
            title: '',
            theme: '',
            style_pack: 'storybook-ink',
            image_model: 'flux-schnell',
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
            image_model: '',
            preset: '',
            maturity_level: '',
            chapter_length: '',
            enable_choices: true,
            memory: '',
            authors_note: '',
            world_instructions: ''
        },

        generateOptions: {
            focus: '',
            no_images: false,
            chapter_length: 'medium'
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
            if (!this.progress || !this.progress.stage) {
                return 'Processing...';
            }

            const stage = this.progress.stage;
            const hasImages = !this.generateOptions.no_images;

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

            // Store originals in case of failure
            const originals = {
                title: this.newWorld.title,
                theme: this.newWorld.theme,
                style_pack: this.newWorld.style_pack,
                preset: this.newWorld.preset,
                image_model: this.newWorld.image_model,
                maturity_level: this.newWorld.maturity_level,
                memory: this.newWorld.memory
            };

            // Show loading state
            this.newWorld.title = 'Generating...';
            this.newWorld.theme = 'Generating...';
            this.newWorld.memory = 'Generating...';

            try {
                const response = await fetch('/api/generate/world');
                const data = await response.json();

                // Fill all fields from the response
                this.newWorld.title = data.title;
                this.newWorld.theme = data.theme;
                this.newWorld.style_pack = data.style_pack;
                this.newWorld.preset = data.preset;
                this.newWorld.image_model = data.image_model;
                this.newWorld.maturity_level = data.maturity_level;
                this.newWorld.memory = data.memory || '';
            } catch (error) {
                console.error('Failed to generate world:', error);
                // Restore originals on failure
                Object.assign(this.newWorld, originals);
                this.showToast('Failed to generate world. Please try again.');
            } finally {
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
                replicate_api_token: '',
                fal_api_key: '',
                global_instructions: this.settings.global_instructions || '',
                default_style_pack: this.settings.default_style_pack,
                default_preset: this.settings.default_preset,
                default_text_model: this.settings.default_text_model,
                default_image_model: this.settings.default_image_model
            };
            this.settingsTab = 'api';
            this.showSettings = true;
        },

        async saveSettings() {
            try {
                // Build request with only non-empty API keys
                const payload = {
                    text_provider: this.settingsForm.text_provider,
                    image_provider: this.settingsForm.image_provider,
                    global_instructions: this.settingsForm.global_instructions,
                    default_style_pack: this.settingsForm.default_style_pack,
                    default_preset: this.settingsForm.default_preset,
                    default_text_model: this.settingsForm.default_text_model,
                    default_image_model: this.settingsForm.default_image_model
                };

                // Only include API keys if they're not empty (user entered them)
                if (this.settingsForm.openai_api_key) payload.openai_api_key = this.settingsForm.openai_api_key;
                if (this.settingsForm.together_api_key) payload.together_api_key = this.settingsForm.together_api_key;
                if (this.settingsForm.huggingface_api_key) payload.huggingface_api_key = this.settingsForm.huggingface_api_key;
                if (this.settingsForm.groq_api_key) payload.groq_api_key = this.settingsForm.groq_api_key;
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
                this.showToast('Settings saved successfully!', 'success');
            } catch (error) {
                console.error('Failed to save settings:', error);
                this.showToast('Failed to save settings. Check console for details.');
            }
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
                image_model: this.currentWorld.config.image_model,
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

                this.showToast('World updated successfully!', 'success');
            } catch (error) {
                console.error('Failed to update world:', error);
                this.showToast('Failed to update world. Check console for details.');
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

                this.showToast('World deleted successfully!', 'success');
            } catch (error) {
                console.error('Failed to delete world:', error);
                this.showToast('Failed to delete world. Check console for details.');
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
                    image_model: 'flux-dev'
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

            this.showGenerateChapter = false;
            this.generating = true;
            this.progress = { percent: 0, message: 'Starting...', stage: 'init' };
            this._lastLoggedStage = null;
            this.addConsoleLog('Starting chapter generation...', 'info');

            try {
                // Start generation
                const response = await fetch(`/api/worlds/${this.currentWorldSlug}/chapters`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.generateOptions)
                });

                const { job_id } = await response.json();
                this.addConsoleLog(`Job created: ${job_id}`, 'info');

                // Listen to SSE stream
                const evtSource = new EventSource(`/api/worlds/${this.currentWorldSlug}/chapters/stream/${job_id}`);

                evtSource.addEventListener('progress', (e) => {
                    const data = JSON.parse(e.data);
                    this.progress = data;
                    // Only log stage changes, not every progress update
                    if (data.stage !== this._lastLoggedStage) {
                        this.addConsoleLog(data.message, 'log');
                        this._lastLoggedStage = data.stage;
                    }
                });

                evtSource.addEventListener('complete', (e) => {
                    const chapter = JSON.parse(e.data);
                    this.currentWorld.chapters.push(chapter);
                    this.generating = false;
                    this.progress = { percent: 100, message: 'Complete!', stage: 'done' };
                    this._lastLoggedStage = null;
                    this.addConsoleLog(`Chapter ${chapter.number} generated successfully!`, 'success');
                    evtSource.close();

                    // Reset form
                    this.generateOptions.focus = '';
                    this.generateOptions.no_images = false;
                });

                evtSource.addEventListener('error', (e) => {
                    console.error('Generation error:', e);
                    this.addConsoleLog('Chapter generation failed: ' + (e.message || 'Unknown error'), 'error');
                    this.showToast('Chapter generation failed. Check console for details.');
                    this.generating = false;
                    evtSource.close();
                });

            } catch (error) {
                console.error('Failed to generate chapter:', error);
                this.addConsoleLog('Failed to generate chapter: ' + error.message, 'error');
                this.showToast('Failed to generate chapter. Check console for details.');
                this.generating = false;
            }
        },

        async viewChapter(chapter, scrollToTop = false) {
            this.viewingChapter = chapter;

            try {
                const response = await fetch(`/api/worlds/${this.currentWorldSlug}/chapters/${chapter.number}/content`);
                const data = await response.json();

                // Simple markdown to HTML conversion
                this.chapterContent = this.markdownToHtml(data.content);

                // Scroll to top if requested
                if (scrollToTop) {
                    // Use nextTick to ensure DOM is updated before scrolling
                    this.$nextTick(() => {
                        const modalContent = document.getElementById('chapter-viewer-modal');
                        if (modalContent) {
                            modalContent.scrollTop = 0;
                        }
                    });
                }
            } catch (error) {
                console.error('Failed to load chapter content:', error);
                this.chapterContent = '<p>Failed to load chapter content.</p>';
            }
        },

        async selectChoice(chapterNum, choiceId) {
            // Find the choice text for confirmation
            const chapter = this.viewingChapter;
            let choiceText = 'this choice';
            if (chapter && chapter.choices) {
                const choice = chapter.choices.find(c => c.id === choiceId);
                if (choice) {
                    choiceText = `"${choice.text}"`;
                }
            }

            // Show confirmation dialog
            const confirmed = await this.confirm(
                `You've chosen ${choiceText}. This decision is permanent and will influence the next chapter. Are you sure?`
            );

            if (!confirmed) {
                return; // User cancelled
            }

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

                // Update chapter in current world state
                const chapter = this.currentWorld.chapters.find(ch => ch.number === chapterNum);
                if (chapter) {
                    chapter.selected_choice_id = data.choice.id;
                    chapter.choice_reasoning = data.reasoning;
                }

                // Update viewing chapter if it's the one being displayed
                if (this.viewingChapter && this.viewingChapter.number === chapterNum) {
                    this.viewingChapter.selected_choice_id = data.choice.id;
                    this.viewingChapter.choice_reasoning = data.reasoning;
                }

                this.addConsoleLog(`Choice selected for chapter ${chapterNum}: ${data.choice.text}`, 'success');
                this.showToast('Choice recorded! Ready to generate next chapter.', 'success');
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

        showRegenerateDialog(chapterNum) {
            this.regenerateChapterNum = chapterNum;
            this.showRegenerateOptions = true;
        },

        async handleRegenerate(type) {
            this.showRegenerateOptions = false;
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
            if (!await this.confirm('Regenerate chapter text only? The current image will be kept.')) return;

            this.generating = true;
            this.progress = { percent: 0, message: 'Starting text regeneration...', stage: 'init' };
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

                // Poll for completion
                await this.pollJobStatus(job_id);

                this.showToast('Chapter text regenerated successfully!', 'success');
                await this.loadWorld(this.currentWorldSlug);
            } catch (error) {
                console.error('Failed to regenerate chapter text:', error);
                this.addConsoleLog(`Error regenerating text: ${error.message}`, 'error');
                this.showToast('Failed to regenerate chapter text. Check console for details.');
            } finally {
                this.generating = false;
                this.progress = { percent: 0, message: '', stage: '' };
            }
        },

        async rerollChapter(chapterNum) {
            if (!await this.confirm('Regenerate this chapter completely? Both text and image will be replaced.')) return;

            this.generating = true;
            this.progress = { percent: 0, message: 'Starting full regeneration...', stage: 'init' };
            this._lastLoggedStage = null;
            this.addConsoleLog(`Starting reroll of chapter ${chapterNum}...`, 'info');

            try {
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
                const evtSource = new EventSource(`/api/worlds/${this.currentWorldSlug}/chapters/stream/${job_id}`);

                evtSource.addEventListener('progress', (e) => {
                    const data = JSON.parse(e.data);
                    this.progress = data;
                    // Only log stage changes, not every progress update
                    if (data.stage !== this._lastLoggedStage) {
                        this.addConsoleLog(data.message, 'log');
                        this._lastLoggedStage = data.stage;
                    }
                });

                evtSource.addEventListener('complete', (e) => {
                    const updatedChapter = JSON.parse(e.data);

                    // Find and update the chapter
                    const chapterIndex = this.currentWorld.chapters.findIndex(ch => ch.number === chapterNum);
                    if (chapterIndex !== -1) {
                        this.currentWorld.chapters[chapterIndex] = updatedChapter;
                    }

                    this.generating = false;
                    this.progress = { percent: 100, message: 'Chapter regenerated!', stage: 'done' };
                    this._lastLoggedStage = null;
                    this.addConsoleLog(`Chapter ${chapterNum} regenerated successfully!`, 'success');
                    evtSource.close();
                });

                evtSource.addEventListener('error', (e) => {
                    console.error('Reroll error:', e);
                    this.addConsoleLog('Chapter reroll failed: ' + (e.message || 'Unknown error'), 'error');
                    this.showToast('Chapter regeneration failed, check console.');
                    this.generating = false;
                    evtSource.close();
                });

            } catch (error) {
                console.error('Failed to reroll chapter:', error);
                this.addConsoleLog('Failed to reroll chapter: ' + error.message, 'error');
                this.showToast('Failed to regenerate chapter. Check console for details.');
                this.generating = false;
            }
        },

        async deleteChapter(chapterNum) {
            if (!await this.confirm('Delete this chapter permanently? This cannot be undone.')) return;

            try {
                const response = await fetch(`/api/worlds/${this.currentWorldSlug}/chapters/${chapterNum}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                // Remove chapter from local state
                const chapterIndex = this.currentWorld.chapters.findIndex(ch => ch.number === chapterNum);
                if (chapterIndex !== -1) {
                    this.currentWorld.chapters.splice(chapterIndex, 1);
                }

                // Close modal if open
                this.showChapterModal = false;
                this.chapterContent = '';

            } catch (error) {
                console.error('Failed to delete chapter:', error);
                this.showToast('Failed to delete chapter. Check console for details.');
            }
        },

        async regenerateImage(chapterNum) {
            if (!await this.confirm('Regenerate the scene image for this chapter?')) return;

            this.generating = true;
            this.progress = { percent: 10, message: 'Regenerating image...', stage: 'image' };
            this.addConsoleLog(`Starting image regeneration for chapter ${chapterNum}...`, 'info');

            try {
                this.progress = { percent: 30, message: 'Calling image API...', stage: 'image' };
                this.addConsoleLog('Calling image generation API...', 'log');

                const response = await fetch(`/api/worlds/${this.currentWorldSlug}/images`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ chapter: chapterNum })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                this.progress = { percent: 80, message: 'Processing image...', stage: 'image' };
                this.addConsoleLog('Processing generated image...', 'log');

                const data = await response.json();

                // Update the chapter's scene
                const chapter = this.currentWorld.chapters.find(ch => ch.number === chapterNum);
                if (chapter) {
                    chapter.scene = data.scene + '?' + Date.now(); // Cache bust
                }

                this.progress = { percent: 100, message: 'Image regenerated!', stage: 'done' };
                this.addConsoleLog(`Image for chapter ${chapterNum} regenerated successfully!`, 'success');
                setTimeout(() => {
                    this.generating = false;
                }, 1000);
            } catch (error) {
                console.error('Failed to regenerate image:', error);
                this.addConsoleLog('Failed to regenerate image: ' + error.message, 'error');
                this.showToast('Failed to regenerate image: ' + error.message);
                this.generating = false;
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

        markdownToHtml(markdown) {
            // Very basic markdown to HTML conversion
            // In production, you'd want to use a proper markdown library
            let html = markdown;

            // Remove metadata comment at top
            html = html.replace(/^<!--[\s\S]*?-->\n*/m, '');

            // Headers
            html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
            html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
            html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

            // Bold
            html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

            // Italic
            html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

            // Paragraphs
            html = html.split('\n\n').map(para => {
                if (para.startsWith('<h') || !para.trim()) {
                    return para;
                }
                return '<p>' + para + '</p>';
            }).join('\n');

            return html;
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
        }
    }
}
