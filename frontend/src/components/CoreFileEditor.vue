<template>
  <div
    v-show="show"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    @click.self="emit('close')"
  >
    <div
      @mousedown.stop
      class="bg-panel border border-border rounded-lg shadow-xl shadow-black/30 w-[700px] max-w-[95vw] max-h-[85vh] flex flex-col animate-dropdown-in"
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-border">
        <h2 class="text-sm font-semibold">Edit core files</h2>
        <button
          @click="emit('close')"
          class="p-1 rounded-md hover:bg-hover-bg text-muted hover:text-default transition-colors"
          title="Close"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 px-5 pt-4 pb-2 border-b border-border">
        <button
          v-for="tab in tabs"
          :key="tab"
          @click="switchTab(tab)"
          :class="[
            'px-4 py-1.5 text-xs font-medium rounded-md transition-colors',
            activeTab === tab
              ? 'bg-accent text-white'
              : 'text-muted hover:text-default hover:bg-hover-bg'
          ]"
        >
          {{ tab }}
        </button>
      </div>

      <!-- File paths info -->
      <div class="px-5 pt-2 pb-1">
        <p class="text-[10px] text-muted/50 font-mono truncate" :title="filePath(activeTab)">
          {{ filePath(activeTab) }}
        </p>
      </div>

      <!-- Editor area -->
      <div class="flex-1 px-5 py-3 overflow-hidden flex flex-col min-h-0">
        <textarea
          v-model="text"
          @mousedown.stop
          class="w-full flex-1 min-h-[300px] bg-app-bg border border-border rounded-md p-3 text-sm font-mono text-default outline-none resize-none focus:border-accent/50 transition-colors"
          placeholder="(empty file)"
          spellcheck="false"
        ></textarea>
      </div>

      <!-- Footer with save -->
      <div class="flex items-center justify-between px-5 py-3 border-t border-border">
        <span
          v-if="saveFeedback"
          :class="['text-xs', saveFeedbackType === 'error' ? 'text-red-500' : 'text-green-500']"
        >
          {{ saveFeedback }}
        </span>
        <span v-else class="text-xs text-muted/50">Unsaved changes are local</span>
        <button
          @click="saveFile(activeTab)"
          :disabled="saving"
          :class="[
            'px-5 py-1.5 text-xs font-medium rounded-md transition-colors',
            saving
              ? 'bg-accent/50 text-white/50 cursor-not-allowed'
              : 'bg-accent text-white hover:bg-accent/90'
          ]"
        >
          <span v-if="saving" class="flex items-center gap-1.5">
            <svg class="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Saving…
          </span>
          <span v-else>Save {{ activeTab }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, shallowRef } from 'vue'

const props = defineProps({ show: Boolean })
const emit = defineEmits(['close'])

const tabs = ['MEMORY', 'USER', 'SOUL']
const activeTab = ref('MEMORY')
const text = ref('')
const saving = ref(false)
const saveFeedback = ref('')
const saveFeedbackType = ref('success')

// Store file contents as plain strings, one per tab
const memory = ref('')
const user = ref('')
const soul = ref('')

const fileMap = { MEMORY: memory, USER: user, SOUL: soul }

function filePath(name) {
  const paths = {
    MEMORY: '~/.hermes/memories/MEMORY.md',
    USER: '~/.hermes/memories/USER.md',
    SOUL: '~/.hermes/SOUL.md',
  }
  return paths[name] || ''
}

function flushContent() {
  fileMap[activeTab.value].value = text.value
}

function switchTab(tab) {
  flushContent()
  activeTab.value = tab
  text.value = fileMap[tab].value
}

async function loadAll() {
  saveFeedback.value = ''
  try {
    const res = await fetch('/api/core-files', { credentials: 'same-origin' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    memory.value = data.MEMORY || ''
    user.value = data.USER || ''
    soul.value = data.SOUL || ''
    text.value = fileMap[activeTab.value].value
  } catch (e) {
    saveFeedback.value = `Failed to load files: ${e.message}`
    saveFeedbackType.value = 'error'
  }
}

async function saveFile(name) {
  flushContent()
  saving.value = true
  saveFeedback.value = ''
  try {
    const res = await fetch(`/api/core-files/${name}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ content: fileMap[name].value }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${res.status}`)
    }
    saveFeedback.value = `${name} saved successfully`
    saveFeedbackType.value = 'success'
  } catch (e) {
    saveFeedback.value = `Error saving ${name}: ${e.message}`
    saveFeedbackType.value = 'error'
  } finally {
    saving.value = false
  }
}

watch(() => props.show, (val) => {
  if (val) loadAll()
})
</script>
