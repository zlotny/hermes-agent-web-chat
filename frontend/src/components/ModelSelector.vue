<template>
  <div class="relative" ref="containerRef">
    <!-- Trigger: current model badge -->
    <button
      @click="toggleDropdown"
      class="flex items-center gap-1.5 px-2 py-1 text-xs font-medium bg-surface/60 border border-border/50 text-muted hover:text-default hover:border-accent/40 hover:bg-surface transition-all cursor-pointer whitespace-nowrap"
      :title="'Current model: ' + (currentModel || 'default')"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5" />
        <path d="M8.5 8.5v.01" />
        <path d="M16 15.5v.01" />
        <path d="M12 12v.01" />
        <path d="M11 17v.01" />
        <path d="M7 14v.01" />
      </svg>
      <span v-if="loading" class="skel h-3 w-16 inline-block align-middle rounded"></span>
      <span v-else class="max-w-[160px] truncate">{{ displayModel }}</span>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="10"
        height="10"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        :class="open ? 'rotate-180' : ''"
        class="transition-transform flex-shrink-0"
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </button>

    <!-- Dropdown (fixed to escape pointer-events-none parents) -->
    <div
      v-if="open"
      @click.stop
      :style="{ ...dropdownStyle, pointerEvents: 'auto' }"
      class="z-[9999] w-[320px] max-h-[400px] bg-surface border border-border/80 shadow-2xl shadow-black/50 flex flex-col overflow-hidden animate-dropdown-in"
      @mousedown.stop
    >
      <!-- Header -->
      <div
          class="px-3 py-2 border-b border-border/50 text-xs font-semibold text-muted flex items-center justify-between uppercase tracking-[0.1em]"
      >
        <span>Switch Model</span>
        <button
          @click="open = false"
          class="p-0.5 hover:bg-hover-bg text-muted hover:text-default transition-colors cursor-pointer"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <!-- Loading -->
      <div
        v-if="loading"
        class="flex items-center justify-center py-8 text-xs text-muted"
      >
        <svg
          class="animate-spin h-4 w-4 mr-2"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        Loading providers…
      </div>

      <!-- Provider list (level 1) -->
      <div v-else-if="!selectedProviderSlug" class="overflow-y-auto flex-1" tabindex="0" ref="listRef" @keydown="onProviderKeydown">
        <button
          v-for="(p, pi) in providers"
          :key="p.slug"
          :ref="(el) => { if (el) providerRefs[pi] = el }"
          @click="selectProvider(p)"
          class="w-full flex items-center justify-between px-3 py-2.5 text-xs hover:bg-hover-bg transition-colors text-left border-b border-border/30 last:border-b-0 cursor-pointer"
          :class="[
            p.is_current ? 'text-accent' : 'text-default',
            focusedIndex === pi ? 'bg-hover-bg ring-1 ring-accent/40' : ''
          ]"
        >
          <div class="flex items-center gap-2">
            <span class="font-medium">{{ p.name }}</span>
            <span v-if="p.is_current" class="text-[10px] text-accent/70"
              >(active)</span
            >
          </div>
          <div class="flex items-center gap-2 text-muted">
            <span class="text-[10px]">{{ p.total_models }} models</span>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </div>
        </button>

        <!-- No providers -->
        <div
          v-if="!providers.length"
          class="py-6 text-center text-xs text-muted"
        >
          No providers available. Set up API keys in Hermes config.
        </div>
      </div>

      <!-- Model list (level 2) -->
      <div v-else class="overflow-y-auto flex-1" tabindex="0" ref="listRef" @keydown="onModelKeydown">
        <!-- Back button -->
        <button
          @click="selectedProviderSlug = null; focusedIndex = 0"
          class="w-full flex items-center gap-1.5 px-3 py-2 text-xs text-muted hover:text-default hover:bg-hover-bg transition-colors border-b border-border/30 cursor-pointer"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          {{ selectedProviderName }}
        </button>

        <!-- Search/filter -->
        <div class="px-3 py-2 border-b border-border/30">
          <input
            v-model="modelSearch"
            type="text"
            placeholder="Type to search all models…"
            class="w-full bg-app-bg border border-border/60 px-2.5 py-1.5 text-xs text-default outline-none placeholder:text-muted/50 focus:border-accent/50 transition-colors"
            ref="searchRef"
            @keydown.stop="onSearchKeydown"
          />
        </div>

        <!-- Model items -->
        <div class="py-1">
          <!-- Search loading -->
          <div
            v-if="searchLoading"
            class="flex items-center justify-center py-4 text-xs text-muted"
          >
            <svg class="animate-spin h-3.5 w-3.5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            Searching…
          </div>

          <!-- Models from search or curated -->
          <template v-else>
            <div
              v-if="usingFullCatalog && !searchModels.length"
              class="py-4 text-center text-xs text-muted"
            >
              No models match "{{ modelSearch }}"
            </div>

            <button
              v-for="m in displayModels"
              :key="m"
              :ref="(el) => { if (el) modelRefs[displayModels.indexOf(m)] = el }"
              @click="pickModel(m)"
              class="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-hover-bg transition-colors text-left cursor-pointer"
              :class="[
                isActiveModel(m) ? 'text-accent' : 'text-default',
                focusedIndex === displayModels.indexOf(m) ? 'bg-hover-bg ring-1 ring-accent/40' : ''
              ]"
            >
              <span v-if="isActiveModel(m)" class="text-accent flex-shrink-0">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="10"
                  height="10"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              </span>
              <span v-else class="w-[10px] flex-shrink-0"></span>
              <span class="truncate">{{ shortModelName(m) }}</span>
            </button>

            <div
              v-if="!usingFullCatalog && !displayModels.length"
              class="py-4 text-center text-xs text-muted"
            >
              No curated models for this provider. Type to search the full catalog.
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useChatStore } from "../stores/chat";
import { useSessionsStore } from "../stores/sessions";

export default {
  props: {
    currentModel: { type: String, default: "" },
    providers: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
  },
  emits: ["select-model", "closed"],
  setup() {
    return {
      chatStore: useChatStore(),
      sessionsStore: useSessionsStore(),
    };
  },
  data() {
    return {
      open: false,
      selectedProviderSlug: null,
      modelSearch: "",
      showAllModels: false,
      // Full catalog search
      searchModels: [],
      searchLoading: false,
      usingFullCatalog: false,
      _searchDebounceTimer: null,
      focusedIndex: 0,
      providerRefs: [],
      modelRefs: [],
    };
  },
  computed: {
    displayModel() {
      if (!this.currentModel) return "auto";
      return this.shortModelName(this.currentModel);
    },
    selectedProviderName() {
      const p = this.selectedProviderObj;
      return p?.name || this.selectedProviderSlug || "";
    },
    selectedProviderObj() {
      if (!this.selectedProviderSlug) return null;
      return (
        this.providers.find(
          (p) =>
            p.slug === this.selectedProviderSlug ||
            p.slug.toLowerCase() === this.selectedProviderSlug.toLowerCase(),
        ) || null
      );
    },
    // The shown model list: if searching full catalog use search results, else use curated
    displayModels() {
      if (this.usingFullCatalog) return this.searchModels;
      const p = this.selectedProviderObj;
      if (!p?.models?.length) return [];
      return p.models;
    },
    dropdownStyle() {
      if (!this.open || !this.$refs.containerRef) return {};
      const rect = this.$refs.containerRef.getBoundingClientRect();
      return {
        position: "fixed",
        bottom: window.innerHeight - rect.top + 6 + "px",
        left: Math.max(8, rect.left) + "px",
        width: "320px",
      };
    },
  },
  methods: {
    toggleDropdown() {
      if (this.open) {
        this.close();
      } else {
        this.open = true;
        this.selectedProviderSlug = null;
        this.modelSearch = "";
        this.showAllModels = false;
        this.searchModels = [];
        this.usingFullCatalog = false;
        this.focusedIndex = 0;
        this.providerRefs = [];
        this.modelRefs = [];
        this.$nextTick(() => {
          this.$refs.listRef?.focus();
          this.scrollFocusedIntoView();
        });
      }
    },
    onProviderKeydown(e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        this.focusedIndex = Math.min(this.focusedIndex + 1, this.providers.length - 1);
        this.scrollFocusedIntoView();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.focusedIndex = Math.max(this.focusedIndex - 1, 0);
        this.scrollFocusedIntoView();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const p = this.providers[this.focusedIndex];
        if (p) this.selectProvider(p);
      }
    },
    onModelKeydown(e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        this.focusedIndex = Math.min(this.focusedIndex + 1, this.displayModels.length - 1);
        this.scrollFocusedIntoView();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.focusedIndex = Math.max(this.focusedIndex - 1, 0);
        this.scrollFocusedIntoView();
      } else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const m = this.displayModels[this.focusedIndex];
        if (m) this.pickModel(m);
      }
    },
    /** Intercept arrow keys in the search input to navigate the model list. */
    onSearchKeydown(e) {
      if (e.key === 'Escape') {
        e.preventDefault()
        this.close()
        return
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        this.focusedIndex = Math.min(this.focusedIndex + 1, this.displayModels.length - 1);
        this.scrollFocusedIntoView();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.focusedIndex = Math.max(this.focusedIndex - 1, 0);
        this.scrollFocusedIntoView();
      } else if (e.key === 'Enter' || e.key === ' ') {
        // Only intercept Enter/Space when there's a focused model
        if (this.focusedIndex >= 0 && this.focusedIndex < this.displayModels.length) {
          e.preventDefault();
          const m = this.displayModels[this.focusedIndex];
          if (m) this.pickModel(m);
        }
      }
      // All other keys flow through to the search input naturally
    },
    scrollFocusedIntoView() {
      this.$nextTick(() => {
        const refs = this.selectedProviderSlug ? this.modelRefs : this.providerRefs;
        const el = refs[this.focusedIndex];
        if (el) el.scrollIntoView({ block: 'nearest' });
      });
    },
    selectProvider(p) {
      this.selectedProviderSlug = p.slug;
      this.modelSearch = "";
      this.showAllModels = false;
      this.searchModels = [];
      this.usingFullCatalog = false;
      this.focusedIndex = 0;
      this.providerRefs = [];
      this.modelRefs = [];
      this.$nextTick(() => {
        this.$refs.searchRef?.focus();
      });
    },
    /** Debounced search across the full provider catalog */
    onSearchInput() {
      if (this._searchDebounceTimer) clearTimeout(this._searchDebounceTimer);
      const q = this.modelSearch.trim();
      if (q.length < 2) {
        this.usingFullCatalog = false;
        this.searchModels = [];
        return;
      }
      this._searchDebounceTimer = setTimeout(() => {
        this.doFullCatalogSearch(q);
      }, 300);
    },
    async doFullCatalogSearch(query) {
      if (!this.selectedProviderSlug) return;
      this.searchLoading = true;
      this.usingFullCatalog = true;
      try {
        const res = await fetch(
          `/api/providers/${encodeURIComponent(this.selectedProviderSlug)}/models?search=${encodeURIComponent(query)}&limit=50`,
          { credentials: "same-origin" }
        );
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        this.searchModels = data.models || [];
      } catch (e) {
        console.warn("Failed to search models:", e);
        this.searchModels = [];
      } finally {
        this.searchLoading = false;
      }
    },
    pickModel(model) {
      this.$emit("select-model", model);
      this.close();
    },
    isActiveModel(m) {
      return this.currentModel === m;
    },
    shortModelName(m) {
      return m ? m.split("/").pop() || m : "";
    },
    close() {
      this.open = false;
      this.selectedProviderSlug = null;
      this.modelSearch = "";
      this.showAllModels = false;
      this.searchModels = [];
      this.usingFullCatalog = false;
      this.focusedIndex = 0;
      this.providerRefs = [];
      this.modelRefs = [];
      if (this._searchDebounceTimer) {
        clearTimeout(this._searchDebounceTimer);
        this._searchDebounceTimer = null;
      }
      this.$emit("closed");
    },
    handleClickOutside(e) {
      if (!this.open) return
      const el = this.$refs.containerRef;
      if (el && !el.contains(e.target)) {
        this.close();
      }
    },
    handleEscape(e) {
      if (e.key === 'Escape' && this.open) {
        this.close();
      }
    },
  },
  watch: {
    modelSearch() {
      this.onSearchInput();
    },
  },
  mounted() {
    document.addEventListener("click", this.handleClickOutside);
    document.addEventListener("keydown", this.handleEscape);
  },
  beforeUnmount() {
    document.removeEventListener("click", this.handleClickOutside);
    document.removeEventListener("keydown", this.handleEscape);
    if (this._searchDebounceTimer) clearTimeout(this._searchDebounceTimer);
  },
};
</script>
