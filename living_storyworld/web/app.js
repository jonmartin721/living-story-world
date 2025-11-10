function app() {
    return {
        worlds: [],
        currentWorldSlug: '',
        currentWorld: null,
        generating: false,
        generatingTheme: false,
        progress: { percent: 0, message: '' },
        showCreateWorld: false,
        showEditWorld: false,
        showGenerateChapter: false,
        showSettings: false,
        settingsTab: 'api',
        viewingChapter: null,
        chapterContent: '',

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

        async randomWorld() {
            this.generatingTheme = true;

            // Store originals in case of failure
            const originals = {
                title: this.newWorld.title,
                theme: this.newWorld.theme,
                style_pack: this.newWorld.style_pack,
                preset: this.newWorld.preset,
                image_model: this.newWorld.image_model,
                maturity_level: this.newWorld.maturity_level
            };

            // Show loading state
            this.newWorld.title = 'Generating...';
            this.newWorld.theme = 'Generating...';

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
            await this.loadSettings();
            await this.loadWorlds();
            // Auto-select current world if any
            const currentWorld = this.worlds.find(w => w.is_current);
            if (currentWorld) {
                this.currentWorldSlug = currentWorld.slug;
                await this.loadWorld();
            }
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
            this.progress = { percent: 0, message: 'Starting...' };

            try {
                // Start generation
                const response = await fetch(`/api/worlds/${this.currentWorldSlug}/chapters`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.generateOptions)
                });

                const { job_id } = await response.json();

                // Listen to SSE stream
                const evtSource = new EventSource(`/api/worlds/${this.currentWorldSlug}/chapters/stream/${job_id}`);

                evtSource.addEventListener('progress', (e) => {
                    const data = JSON.parse(e.data);
                    this.progress = data;
                });

                evtSource.addEventListener('complete', (e) => {
                    const chapter = JSON.parse(e.data);
                    this.currentWorld.chapters.push(chapter);
                    this.generating = false;
                    this.progress = { percent: 100, message: 'Complete!' };
                    evtSource.close();

                    // Reset form
                    this.generateOptions.focus = '';
                    this.generateOptions.no_images = false;
                });

                evtSource.addEventListener('error', (e) => {
                    console.error('Generation error:', e);
                    this.showToast('Chapter generation failed. Check console for details.');
                    this.generating = false;
                    evtSource.close();
                });

            } catch (error) {
                console.error('Failed to generate chapter:', error);
                this.showToast('Failed to generate chapter. Check console for details.');
                this.generating = false;
            }
        },

        async viewChapter(chapter) {
            this.viewingChapter = chapter;

            try {
                const response = await fetch(`/api/worlds/${this.currentWorldSlug}/chapters/${chapter.number}/content`);
                const data = await response.json();

                // Simple markdown to HTML conversion
                this.chapterContent = this.markdownToHtml(data.content);
            } catch (error) {
                console.error('Failed to load chapter content:', error);
                this.chapterContent = '<p>Failed to load chapter content.</p>';
            }
        },

        async rerollChapter(chapterNum) {
            if (!await this.confirm('Regenerate this chapter completely? Both text and image will be replaced.')) return;

            this.generating = true;
            this.progress = { percent: 0, message: 'Starting full regeneration...' };

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

                // Listen to SSE stream
                const evtSource = new EventSource(`/api/worlds/${this.currentWorldSlug}/chapters/stream/${job_id}`);

                evtSource.addEventListener('progress', (e) => {
                    const data = JSON.parse(e.data);
                    this.progress = data;
                });

                evtSource.addEventListener('complete', (e) => {
                    const updatedChapter = JSON.parse(e.data);

                    // Find and update the chapter
                    const chapterIndex = this.currentWorld.chapters.findIndex(ch => ch.number === chapterNum);
                    if (chapterIndex !== -1) {
                        this.currentWorld.chapters[chapterIndex] = updatedChapter;
                    }

                    this.generating = false;
                    this.progress = { percent: 100, message: 'Chapter regenerated!' };
                    evtSource.close();
                });

                evtSource.addEventListener('error', (e) => {
                    console.error('Reroll error:', e);
                    this.showToast('Chapter regeneration failed, check console.');
                    this.generating = false;
                    evtSource.close();
                });

            } catch (error) {
                console.error('Failed to reroll chapter:', error);
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
            this.progress = { percent: 10, message: 'Regenerating image...' };

            try {
                this.progress = { percent: 30, message: 'Calling image API...' };

                const response = await fetch(`/api/worlds/${this.currentWorldSlug}/images`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ chapter: chapterNum })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                this.progress = { percent: 80, message: 'Processing image...' };

                const data = await response.json();

                // Update the chapter's scene
                const chapter = this.currentWorld.chapters.find(ch => ch.number === chapterNum);
                if (chapter) {
                    chapter.scene = data.scene + '?' + Date.now(); // Cache bust
                }

                this.progress = { percent: 100, message: 'Image regenerated!' };
                setTimeout(() => {
                    this.generating = false;
                }, 1000);
            } catch (error) {
                console.error('Failed to regenerate image:', error);
                this.showToast('Failed to regenerate image: ' + error.message);
                this.generating = false;
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
        }
    }
}
