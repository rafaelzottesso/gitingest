// Tag-style inputs for the Include / Exclude pattern fields.
// The real value lives in a hidden <input id="include_pattern|exclude_pattern"> as a
// comma-separated string, so form submission code does not need to know about tags.
(function () {
    const SPLIT_RE = /[,\s]+/; // same rule the backend uses: commas and/or whitespace
    const fields = {};

    function parse(text) {
        return text.split(SPLIT_RE).map((part) => part.trim().replace(/\\/g, '/')).filter(Boolean);
    }

    function createField(hidden) {
        const box = document.querySelector(`[data-tag-box="${hidden.id}"]`);
        const input = box.querySelector('input[type="text"]');
        let items = [];

        function sync() {
            hidden.value = items.join(', ');
            box.querySelectorAll('[data-chip]').forEach((chip) => chip.remove());
            items.forEach((item) => {
                const chip = document.createElement('span');
                const label = document.createElement('span');
                const remove = document.createElement('button');

                chip.setAttribute('data-chip', '');
                chip.className = 'inline-flex items-center gap-1 max-w-full bg-[#ffc480] border-2 border-gray-900 rounded pl-2 pr-1 py-0.5 text-sm font-mono text-gray-900 shadow-[2px_2px_0_#111827]';
                label.className = 'break-all';
                label.textContent = item;
                remove.type = 'button';
                remove.setAttribute('aria-label', `Remove ${item}`);
                remove.className = 'flex-shrink-0 w-4 h-4 leading-none rounded-sm hover:bg-[#FE4A60] hover:text-white font-bold';
                remove.innerHTML = '<svg viewBox="0 0 24 24" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M7 7l10 10M17 7L7 17"/></svg>';
                remove.addEventListener('click', (event) => {
                    event.stopPropagation();
                    api.remove(item);
                    input.focus();
                });
                chip.append(label, remove);
                box.insertBefore(chip, input);
            });
            hidden.dispatchEvent(new Event('change', { bubbles: true }));
        }

        const api = {
            list: () => items.slice(),
            has: (item) => items.includes(item),
            add(text) {
                let added = 0;

                parse(text).forEach((item) => {
                    if (!items.includes(item)) {
                        items.push(item);
                        added += 1;
                    }
                });
                if (added) {sync();}
                return added;
            },
            remove(item) {
                const index = items.indexOf(item);

                if (index !== -1) {
                    items.splice(index, 1);
                    sync();
                }
            },
            clear() {
                items = [];
                sync();
            },
        };

        function commit() {
            if (input.value.trim()) {
                api.add(input.value);
            }
            input.value = '';
        }

        input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                // Never submit the form from here; patterns are created with comma or space
                event.preventDefault();
            } else if (event.key === ',' || event.key === ' ') {
                event.preventDefault();
                commit();
            } else if (event.key === 'Backspace' && !input.value && items.length) {
                api.remove(items[items.length - 1]);
            }
        });
        input.addEventListener('paste', (event) => {
            const text = (event.clipboardData || window.clipboardData).getData('text');

            if (SPLIT_RE.test(text.trim())) {
                event.preventDefault();
                api.add(text);
            }
        });
        input.addEventListener('blur', commit);
        box.addEventListener('click', () => input.focus());

        items = [];
        api.add(hidden.value);
        sync();
        return api;
    }

    function openModal() {
        document.getElementById('patternHelpModal')?.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }

    function closeModal() {
        document.getElementById('patternHelpModal')?.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }

    function init() {
        ['include_pattern', 'exclude_pattern'].forEach((id) => {
            const hidden = document.getElementById(id);

            if (hidden && document.querySelector(`[data-tag-box="${id}"]`)) {
                fields[id] = createField(hidden);
            }
        });
        // Move the modal to <body> so it is not trapped in the form card's stacking context
        const modal = document.getElementById('patternHelpModal');

        if (modal) {document.body.appendChild(modal);}
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {closeModal();}
        });
    }

    window.PatternTags = {
        get: (id) => fields[id],
        // Used by the directory tree: toggle an item in the Exclude field. Returns true if added.
        toggleExclude(item) {
            const field = fields.exclude_pattern;

            if (field.has(item)) {
                field.remove(item);
                return false;
            }
            field.add(item);
            return true;
        },
        hasExclude: (item) => Boolean(fields.exclude_pattern?.has(item)),
        addExample(id, text, button) {
            const added = fields[id]?.add(text);

            if (button) {
                const original = button.dataset.label || button.textContent;

                button.dataset.label = original;
                button.textContent = added ? '\u2713 Added' : '\u2713 Already added';
                button.classList.add('bg-[#FE4A60]', 'text-white');
                clearTimeout(button._t);
                button._t = setTimeout(() => {
                    button.textContent = original;
                    button.classList.remove('bg-[#FE4A60]', 'text-white');
                }, 1500);
            }

            if (window.showToast) {
                window.showToast(added ? `Added to ${id === 'include_pattern' ? 'include' : 'exclude'}: ${text}` : 'Already in the list');
            }
        },
        openModal,
        closeModal,
    };

    document.addEventListener('DOMContentLoaded', init);
})();
