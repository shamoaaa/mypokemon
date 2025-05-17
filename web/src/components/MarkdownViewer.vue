<template>
  <div class="markdown-viewer" v-html="compiledMarkdown"></div>
</template>

<script setup>
import { marked } from 'marked'
import { computed } from 'vue'

const props = defineProps({
  content: {
    type: String,
    default: ''
  }
})

const compiledMarkdown = computed(() => {
  return marked(props.content)
})
</script>

<style scoped>
.markdown-viewer {
  line-height: 1.6;
}

.markdown-viewer >>> pre {
  background-color: #f6f8fa;
  padding: 16px;
  border-radius: 6px;
  overflow: auto;
}

.markdown-viewer >>> code {
  font-family: SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace;
  background-color: rgba(175,184,193,0.2);
  padding: 0.2em 0.4em;
  border-radius: 6px;
  font-size: 85%;
}

.markdown-viewer >>> blockquote {
  border-left: 4px solid #dfe2e5;
  color: #6a737d;
  padding: 0 1em;
  margin: 0 0 16px 0;
}
</style>