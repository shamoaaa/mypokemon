<template>
  <div class="chat" ref="chatContainer">
    <!-- 聊天头部 -->
    <div class="chat-header">
      <div class="header__left">
        <div
          v-if="!state.isSidebarOpen"
          class="close nav-btn"
          @click="state.isSidebarOpen = true"
        >
          <img src="@/assets/icons/sidebar_left.svg" class="iconfont icon-20" alt="设置" />
        </div>
        <div class="conv-title" v-if="editingTitle">
          <a-input
            ref="titleInput"
            v-model:value="tempTitle"
            @pressEnter="saveTitle"
            @blur="saveTitle"
            size="small"
            class="title-input"
          />
        </div>
        <div class="conv-title" v-else @click="startEditingTitle">
          {{ conv.name || '未命名会话' }}
        </div>
      </div>
      <div class="header__right metas">
        <!-- 知识库选择下拉菜单 -->
        <a-dropdown v-model:visible="kbDropdownVisible" :trigger="['click']" v-if="availableKnowledgeBases.length > 0">
          <div class="model-select" @click.prevent>
            <span class="text">{{ selectedKnowledgeBase || '选择知识库' }}</span>
            <DownOutlined class="icon" />
          </div>
          <template #overlay>
            <a-menu class="scrollable-menu">
              <a-menu-item v-for="kb in availableKnowledgeBases" :key="kb.kb_name" @click="selectKnowledgeBase(kb.kb_name)">
                {{ kb.kb_name }}
              </a-menu-item>
              <a-menu-item @click="selectKnowledgeBase('')">
                不使用知识库
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
        <!-- 模型选择下拉菜单 -->
        <a-dropdown v-model:visible="modelDropdownVisible" :trigger="['click']">
          <div class="model-select" @click.prevent>
            <span class="text">{{ selectedModel }}</span>
            <DownOutlined class="icon" />
          </div>
          <template #overlay>
            <a-menu class="scrollable-menu">
              <a-menu-item v-for="model in availableModels" :key="model" @click="selectModel(model)">
                {{ model }}
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </div>

    <!-- 聊天内容区域 -->
    <div class="chat-box" ref="chatBox" :class="{ 'wide-screen': isWideScreen }">
      <div v-if="messages.length === 0" class="chat-examples">
        <h1>欢迎使用可萌助手</h1>
        <div class="example-cards">
          <div 
            class="card" 
            v-for="(example, index) in examples" 
            :key="index" 
            @click="sendMessage(example)"
          >
            <div class="blob"></div>
            <div class="bg">
              <span>{{ example }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <div v-else>
        <div 
          v-for="(message, index) in messages" 
          :key="index" 
          class="message-box" 
          :class="message.role"
        >
          <div class="message-content">
            <div class="message-avatar">
              <UserOutlined v-if="message.role === 'user'" />
              <img src="@/assets/icons/ai.jpg" class="iconfont icon-20" alt="ai_png" v-else />
            </div>
            <div class="message-text">
              <MarkdownViewer :content="message.content" />

              <!-- 相关文档片段 -->
              <div v-if="message.docs && message.docs.length > 0" class="document-section">
                <h4>相关文档:</h4>
                <div v-for="(doc, index) in message.docs" :key="index" class="doc-item">
                  <MarkdownViewer :content="doc"></MarkdownViewer>
                </div>
              </div>

              <!-- 联网搜索结果 -->
              <div v-if="message.search && message.search.length > 0" class="search-section">
                <h4>实时联网检索:</h4>
                <ul class="search-list">
                  <li v-for="(item, index) in message.search" :key="index" class="search-item">
                    <MarkdownViewer :content="item" />
                  </li>
                </ul>
              </div>

              <!-- Cypher 查询 -->
              <div v-if="message.cypherQuery" class="cypher-section">
                <h4>生成的Cypher查询:</h4>
                <div v-for="(item, index) in message.cypherQuery" :key="index" class="cypher-item">
                  <pre class="cypher-code"><MarkdownViewer :content="item" /></pre>
                </div>
              </div>

              <!-- Cypher查询结果 -->
              <div v-if="message.cypherResult && message.cypherResult.length > 0" class="cypher-result-section">
                <h4>Cypher查询结果:</h4>
                <ul class="cypher-result-list">
                  <li v-for="(result, index) in message.cypherResult" :key="index" class="cypher-result-item">
                    <MarkdownViewer :content="JSON.stringify(result, null, 2)" />
                  </li>
                </ul>
              </div>

              <!-- 评分反馈 -->
              <div v-if="message.role === 'assistant' && message.showFeedback" class="feedback-section">
                <div class="feedback-buttons">
                  <span class="feedback-label">这个回答有帮助吗？</span>
                  <a-button 
                    v-for="score in [1, 2, 3, 4, 5]" 
                    :key="score"
                    :type="message.feedbackScore === score ? 'primary' : 'default'"
                    size="small"
                    @click="showFeedbackModal(message.id)"
                  >
                    {{ score }}星
                  </a-button>
                </div>
                <div v-if="message.feedbackScore" class="feedback-result">
                  已评价: {{ message.feedbackScore }}星
                  <span v-if="message.feedbackReason"> - {{ message.feedbackReason }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 评分模态框 -->
    <a-modal
      v-model:visible="feedbackModalVisible"
      title="评价回答质量"
      @ok="submitFeedback"
      @cancel="feedbackModalVisible = false"
      class="feedback-modal"
    >
      <div class="modal-content">
        <div class="rating-section">
          <span>请评分:</span>
          <a-rate v-model:value="feedbackScore" />
        </div>
        <div class="reason-section">
          <span>评价理由(可选):</span>
          <a-textarea
            v-model:value="feedbackReason"
            placeholder="这个回答哪里好或需要改进？"
            :auto-size="{ minRows: 2, maxRows: 4 }"
          />
        </div>
      </div>
    </a-modal>

    <!-- 输入区域 -->
    <div class="bottom">
      <div class="message-input-wrapper" :class="{ 'wide-screen': isWideScreen }">
        <div class="input-box">
          <a-textarea
            v-model:value="userInput"
            placeholder="输入消息..."
            :auto-size="{ minRows: 1, maxRows: 6 }"
            @pressEnter="handleSend"
            allow-clear
            ref="inputArea"
            class="message-input"
          />
          <div class="input-actions">
            <a-button 
              type="primary" 
              :loading="loading" 
              @click="handleSend" 
              :disabled="!userInput.trim()"
              class="send-button"
            >
              发送
            </a-button>
          </div>
        </div>
        <p class="note">Shift+Enter 换行，Enter 发送</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { 
  MenuOutlined, 
  PlusOutlined, 
  DownOutlined, 
  UserOutlined, 
  RobotOutlined,
  SendOutlined 
} from '@ant-design/icons-vue'
import { useUserStore } from '@/stores/config' // 导入userStore
import { message } from 'ant-design-vue'
import axios from 'axios'
import MarkdownViewer from '@/components/MarkdownViewer.vue'

const props = defineProps({
  conv: {
    type: Object,
    required: true
  },
  state: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['rename-title', 'newconv', 'toggle-sidebar'])

// 数据状态
const userInput = ref('')
const messages = ref([])
const loading = ref(false)
const editingTitle = ref(false)
const tempTitle = ref('')
const availableModels = ref([])
const selectedModel = ref('')
const modelDropdownVisible = ref(false)

// 评分相关状态
const feedbackModalVisible = ref(false);
const currentRatingMessageId = ref('');
const feedbackScore = ref(0);
const feedbackReason = ref('');

// 新增知识库相关状态
const availableKnowledgeBases = ref([])
const selectedKnowledgeBase = ref('')
const kbDropdownVisible = ref(false)

// 获取userStore
const userStore = useUserStore()

// DOM 引用
const chatBox = ref(null)
const inputArea = ref(null)
const titleInput = ref(null)

// 示例问题
const examples = [
  '皮卡丘的技能是什么？',
  '赤红有哪些宝可梦？',
  '介绍一下小智。',
  '小火龙多少级进化？'
]



// 初始化
onMounted(async () => {
  await fetchAvailableModels()
  await fetchAvailableKnowledgeBases() // 新增：获取知识库列表
  loadMessages()
  scrollToBottom()
  
  // 如果有会话但没消息，自动聚焦输入框
  if (props.conv.id && messages.value.length === 0) {
    inputArea.value?.focus()
  }
})


// 新增：获取可用的知识库列表
const fetchAvailableKnowledgeBases = async () => {
  try {
    // 从userStore获取用户ID
    const userId = userStore.user.id
    if (!userId) {
      console.error('用户ID不存在')
      return
    }
    
    const response = await axios.get(`/api/knowledge-bases/${userId}`)
    if (response.data.status === 200) {
      availableKnowledgeBases.value = response.data.data.knowledge_bases
    }
  } catch (error) {
    console.error('获取知识库列表失败:', error)
    message.error('获取知识库列表失败')
  }
}

// 新增：选择知识库
const selectKnowledgeBase = (kbName) => {
  selectedKnowledgeBase.value = kbName
  kbDropdownVisible.value = false
}

// 显示评分模态框
const showFeedbackModal = (messageId) => {
  const message = messages.value.find(m => m.id === messageId);
  if (message) {
    currentRatingMessageId.value = messageId;
    feedbackScore.value = message.feedbackScore || 0;
    feedbackReason.value = message.feedbackReason || '';
    feedbackModalVisible.value = true;
  }
};

// 提交评分
const submitFeedback = async () => {
  try {
    const response = await axios.put(
      `/api/messages/${currentRatingMessageId.value}/update_message`,
      {
        feedback_score: feedbackScore.value,
        feedback_reason: feedbackReason.value
      },
      {
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );

    if (response.data.status === 200) {
      message.success('评价提交成功');
      // 更新本地状态
      const index = messages.value.findIndex(
        m => m.id === currentRatingMessageId.value
      );
      if (index !== -1) {
        messages.value[index].feedbackScore = feedbackScore.value;
        messages.value[index].feedbackReason = feedbackReason.value;
      }
    }
  } catch (error) {
    console.error('提交评价失败:', error);
    message.error(error.response?.data?.detail || '评价提交失败');
  } finally {
    feedbackModalVisible.value = false;
  }
};

// 获取可用的模型列表
const fetchAvailableModels = async () => {
  try {
    const response = await axios.get('/api/llm_model/list_running_models')
    if (response.data.status === 200) {
      availableModels.value = response.data.data.models
      if (availableModels.value.length > 0) {
        selectedModel.value = availableModels.value[0]
      }
    }
  } catch (error) {
    console.error('获取模型列表失败:', error)
    message.error('获取模型列表失败')
  }
}

// 选择模型
const selectModel = (model) => {
  selectedModel.value = model
  modelDropdownVisible.value = false
}

// 加载消息历史
const loadMessages = async () => {
  if (!props.conv?.id) {
    messages.value = []
    return
  }

  try {
    const response = await axios.get(`/api/conversations/${props.conv.id}/messages`);
    console.log('获取到的消息:', response.data); // 新增：打印获取到的消息

    if (response.data.status === 200) {
      // 格式化数据以适应前端需求
      const formattedMessages = [];
      response.data.data.forEach(msg => {
        if (msg.query) { // 用户的消息
          console.log('用户的消息:', msg.query); // 新增：打印用户的消息
          formattedMessages.push({
            role: 'user',
            content: msg.query,
            id: `${msg.id}-user`
          });
        }
        if (msg.response) { // AI 的回复
          console.log('AI的回复:', msg.response); // 新增：打印AI的回复
          formattedMessages.push({
            role: 'assistant',
            content: msg.response,
            id: `${msg.id}-assistant`
          });
        }
      });

      messages.value = formattedMessages;
      console.log('更新后的消息列表:', messages.value);
      scrollToBottom();
    } else {
      message.error('无法加载历史消息');
    }
  } catch (error) {
    console.error('加载消息失败:', error);
    message.error('加载历史消息失败');
  }
}

// 发送消息
const handleSend = async () => {
  if (!userInput.value.trim() || loading.value) return;

  const query = userInput.value.trim();
  userInput.value = '';


  // 检查知识库聊天是否选择了知识库
  if (props.conv?.chat_type === 'knowledge_base_chat' && !selectedKnowledgeBase.value) {
    // 使用Ant Design的message组件弹出提示
    message.warning('请先选择知识库', 2); // 2秒后自动关闭
    return; // 直接返回，不继续发送消息
  }

  // 添加用户消息（临时ID，会被后端替换）
  const userMsg = {
    role: 'user',
    content: query,
    id: `temp-${Date.now()}` // 临时ID，实际使用后端返回的ID
  };
  messages.value = [...messages.value, userMsg];

  // 添加AI消息占位（临时ID）
  const aiMsg = {
    role: 'assistant',
    content: '...',
    id: `temp-ai-${Date.now()}`, // 临时ID
    showFeedback: false, // 初始不显示评分
    feedbackScore: 0,
    feedbackReason: ''
  };
  messages.value = [...messages.value, aiMsg];

  scrollToBottom();
  loading.value = true;

  try {
    // 根据对话类型选择API端点
    let apiEndpoint = '/api/chat'; // 默认普通聊天
    if (props.conv?.chat_type) {
      switch (props.conv.chat_type) {
        case 'knowledge_base_chat':
          apiEndpoint = '/api/chat/knowledge_base_chat';
          break;
        case 'search_engine_chat':
          apiEndpoint = '/api/chat/search_engine_chat';
          break;
        case 'neo4j_chat':
          apiEndpoint = '/api/chat/neo4j_chat';
          break;
        // 可以添加更多聊天类型
      }
    }

    // 构造请求体（根据不同类型可能需要不同参数）
    const requestBody = {
      query,
      conversation_id: props.conv?.id || '',
      model_name: selectedModel.value
    };


    // 如果是知识库聊天，添加知识库名称
    if (props.conv?.chat_type === 'knowledge_base_chat' && selectedKnowledgeBase.value) {
      requestBody.knowledge_base_name = selectedKnowledgeBase.value;
    }


    const response = await fetch(apiEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) throw new Error(`HTTP错误: ${response.status}`);

    const reader = response.body?.getReader();
    if (!reader) throw new Error('无法读取响应流');

    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';
    let backendMessageId = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        
        const dataStr = line.replace('data: ', '').trim();
        if (dataStr === '[DONE]') continue;

        try {
          const data = JSON.parse(dataStr);
          console.log("后端传递过来的message：",data);
          if (data.message_id) {
            // 获取后端生成的真实message_id
            backendMessageId = data.message_id;
            
            // 更新消息ID（找到最后一个assistant消息）
            const lastAiMsgIndex = messages.value.findLastIndex(
              m => m.role === 'assistant' && m.id.startsWith('temp-ai-')
            );
            if (lastAiMsgIndex !== -1) {
              messages.value[lastAiMsgIndex].id = backendMessageId;
              messages.value[lastAiMsgIndex].showFeedback = true; // 显示评分
            }
          }
          
          if (data.text) {
            fullText += data.text;
            // 更新内容
            const lastAiMsgIndex = messages.value.findLastIndex(
              m => m.role === 'assistant'
            );
            if (lastAiMsgIndex !== -1) {
              messages.value[lastAiMsgIndex].content = fullText;
            }
            scrollToBottom();
          }else if (data.docs) { // 处理文档片段
            const lastAiMsgIndex = messages.value.findLastIndex(
              m => m.role === 'assistant'
            );
            if (lastAiMsgIndex !== -1) {
              messages.value[lastAiMsgIndex].docs = data.docs;
            }
          }else if (data.search) { // 处理联网搜索结果
            const lastAiMsgIndex = messages.value.findLastIndex(
              m => m.role === 'assistant'
            );
            if (lastAiMsgIndex !== -1) {
              messages.value[lastAiMsgIndex].search = data.search;
            }
          }else if (data.generated_cypher) {
            const lastAiMsgIndex = messages.value.findLastIndex(
              m => m.role === 'assistant'
            );
            if (lastAiMsgIndex !== -1) {
              messages.value[lastAiMsgIndex].cypherQuery = [data.generated_cypher]
            }
          }else if (data.cypher_result) {
            const lastAiMsgIndex = messages.value.findLastIndex(
              m => m.role === 'assistant'
            );
            if (lastAiMsgIndex !== -1) {
              messages.value[lastAiMsgIndex].cypherResult = [data.cypher_result]
            }
          }
        } catch (e) {
          console.warn('解析错误:', e, '原始数据:', dataStr);
        }
      }
    }
  } catch (error) {
    console.error('请求失败:', error);
    const lastAiMsgIndex = messages.value.findLastIndex(
      m => m.role === 'assistant'
    );
    if (lastAiMsgIndex !== -1) {
      messages.value[lastAiMsgIndex].content = `错误: ${error.message || '未知错误'}`;
      messages.value[lastAiMsgIndex].showFeedback = true; // 错误也允许评分
    }
  } finally {
    loading.value = false;
    scrollToBottom();
    inputArea.value?.focus();
  }
};

// 发送示例消息
const sendMessage = (text) => {
  userInput.value = text
  nextTick(() => {
    handleSend()
  })
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (chatBox.value) {
      chatBox.value.scrollTop = chatBox.value.scrollHeight
    }
  })
}

// 标题编辑
const startEditingTitle = () => {
  tempTitle.value = props.conv.name || ''
  editingTitle.value = true
  nextTick(() => {
    titleInput.value?.focus()
  })
}

const saveTitle = async () => {
  if (!tempTitle.value.trim() || !props.conv.id || !editingTitle.value) {
    // 如果没有修改或没有会话ID，直接退出编辑状态
    editingTitle.value = false;
    return;
  }

  const newName = tempTitle.value.trim();

  try {
    // 发送 PUT 请求更新会话名称
    const response = await axios.put(`/api/conversations/${props.conv.id}/update_name`, {
      name: newName
    });

    if (response.data.status === 200) {
      // 成功更新后通知父组件刷新会话列表
      emit('rename-title', newName);

      // 可选：提示用户更新成功
      message.success('会话名称已更新');
    } else {
      throw new Error('更新失败');
    }
  } catch (error) {
    console.error('更新会话名称失败:', error);
    message.error('更新会话名称失败，请重试');
  } finally {
    editingTitle.value = false; // 关闭编辑状态
  }
};

watch(() => props.conv, async (newVal) => {
  if (newVal && newVal.id) {
    await loadMessages()
    scrollToBottom()
  }
}, { deep: true })

// 计算属性
const isWideScreen = computed(() => {
  return window.innerWidth > 1200
})
</script>

<style lang="less" scoped>

.chat {
  position: relative;
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--main-light-7);
  box-sizing: border-box;

  .chat-header {
    user-select: none;
    position: sticky;
    top: 0;
    z-index: 10;
    background-color: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(10px);
    height: var(--header-height);
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 1.5rem;
    border-bottom: 1px solid var(--border-color);

    .header__left, .header__right {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .conv-title {
      font-weight: 500;
      font-size: 1.1rem;
      cursor: pointer;
      max-width: 200px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      transition: color 0.2s;
      
      &:hover {
        color: var(--primary-color);
      }
    }

    .title-input {
      width: 200px;
    }
  }

  .nav-btn {
    height: 2.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 0.75rem;
    border-radius: 8px;
    color: var(--gray-800);
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background-color: var(--gray-100);
    }

    .icon {
      font-size: 1rem;
    }
  }

  .model-select {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background-color: var(--gray-100);
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.2s;
    max-width: 200px;

    &:hover {
      background-color: var(--gray-200);
    }

    .text {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 0.9rem;
    }

    .icon {
      font-size: 0.8rem;
      color: var(--gray-600);
    }
  }
}

.chat-box {
  flex: 1;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
  overflow-y: auto;
  scroll-behavior: smooth;

  &.wide-screen {
    max-width: 1200px;
  }

  .message-box {
    margin-bottom: 1.5rem;
    animation: fadeIn 0.3s ease-out;

    &.user {
      .message-content {
        flex-direction: row-reverse;
      }
      .message-text {
        background-color: var(--primary-color);
        color: white;
      }
    }

    &.assistant {
      .message-text {
        background-color: var(--gray-100);
        color: var(--gray-900);
      }
    }

    .message-content {
      display: flex;
      gap: 1rem;
      max-width: 100%;
    }

    .message-avatar {
      flex-shrink: 0;
      width: 2.5rem;
      height: 2.5rem;
      border-radius: 50%;
      background-color: var(--gray-200);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1rem;
      color: var(--gray-700);
    }

    .message-text {
      padding: 0.75rem 1rem;
      border-radius: 12px;
      max-width: calc(100% - 3.5rem);
      line-height: 1.6;
      word-break: break-word;
    }
  }
}

.chat-examples {
  padding: 0 1rem;
  text-align: center;
  margin-top: 20%;

  h1 {
    margin-bottom: 2rem;
    font-size: 1.5rem;
    color: var(--gray-900);
    font-weight: 500;
  }

  .example-cards {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 1rem;
    max-width: 800px;
    margin: 0 auto;
  }

  .card {
    position: relative;
    width: 180px;
    height: 120px;
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    cursor: pointer;
    transition: transform 0.2s;

    &:hover {
      transform: translateY(-5px);
    }

    .bg {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(12px);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
      z-index: 2;
      text-align: center;
      font-size: 0.9rem;
      font-weight: 500;
    }

    .blob {
      position: absolute;
      z-index: 1;
      width: 100px;
      height: 100px;
      border-radius: 50%;
      background-color: var(--primary-color);
      opacity: 0.1;
      filter: blur(12px);
      animation: blob-bounce 8s infinite ease;
    }
  }
}

.bottom {
  position: sticky;
  bottom: 0;
  width: 100%;
  padding: 1rem 0;
  background: linear-gradient(to top, rgba(255,255,255,1) 0%, rgba(255,255,255,0.9) 80%, rgba(255,255,255,0) 100%);

  .message-input-wrapper {
    width: 100%;
    max-width: 800px;
    margin: 0 auto;
    padding: 0 1rem;

    &.wide-screen {
      max-width: 1200px;
    }

    .input-box {
      background-color: white;
      border-radius: 12px;
      padding: 0.75rem;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
      display: flex;
      gap: 0.75rem;
      align-items: flex-end;
      border: 1px solid var(--border-color);

      .message-input {
        border: none;
        box-shadow: none;
        resize: none;
        padding: 0;
        font-size: 0.95rem;
        line-height: 1.6;

        &:focus {
          box-shadow: none;
        }
      }

      .send-button {
        height: 2.5rem;
        padding: 0 1.25rem;
      }
    }

    .note {
      text-align: center;
      font-size: 0.8rem;
      color: var(--gray-500);
      margin-top: 0.5rem;
    }
  }
}

/* 文档展示区域 */
.document-section {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #f9f9f9;
  border-left: 4px solid #007bff;
  color: #333;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);

  h4 {
    font-size: 1em;
    margin-bottom: 0.5em;
    color: #007bff;
    font-weight: bold;
  }

  .doc-item {
    margin-bottom: 1em;
    padding: 1em;
    background-color: #fff;
    border: 1px solid #e1e1e8;
    border-radius: 8px;
    transition: all 0.2s ease-in-out;
    position: relative;
    font-family: 'Arial', sans-serif;

    &::before {
      content: '';
      position: absolute;
      top: -4px;
      left: -4px;
      right: -4px;
      bottom: -4px;
      border: 1px solid transparent;
      border-radius: 10px;
      transition: border-color 0.3s ease;
    }

    &:hover::before {
      border-color: #007bff;
    }
  }
}

/* 联网搜索展示样式 */
.search-section {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #fbfbfb;
  border-left: 4px solid #28a745;
  color: #333;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);

  h4 {
    font-size: 1em;
    margin-bottom: 0.5em;
    color: #28a745;
    font-weight: bold;
  }

  .search-list {
    list-style-type: none;
    padding-left: 0;
  }

  .search-item {
    margin-bottom: 0.5em;
    font-family: 'Arial', sans-serif;
    color: #555;
  }
}

/* Cypher 查询展示区域 */
.cypher-section {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #fbfbfb;
  border-left: 4px solid #e67e22;
  color: #333;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);

  h4 {
    font-size: 1em;
    margin-bottom: 0.5em;
    color: #e67e22;
    font-weight: bold;
  }

  .cypher-item {
    margin-bottom: 0.5em;
    font-family: 'Courier New', monospace;
    white-space: pre-wrap;
    word-break: break-word;
    background-color: #fff;
    border: 1px solid #eee;
    padding: 1em;
    border-radius: 6px;
    transition: all 0.2s ease-in-out;
  }
}

/* Cypher 查询结果展示区域 */
.cypher-result-section {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #f9f9f9;
  border-left: 4px solid #8e44ad;
  color: #333;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);

  h4 {
    font-size: 1em;
    margin-bottom: 0.5em;
    color: #8e44ad;
    font-weight: bold;
  }

  .cypher-result-item {
    margin-bottom: 0.5em;
    font-family: 'Courier New', monospace;
    white-space: pre-wrap;
    word-break: break-word;
    background-color: #fff;
    border: 1px solid #eee;
    padding: 1em;
    border-radius: 6px;
    transition: all 0.2s ease-in-out;
  }
}

/* 评分反馈区域 */
.feedback-section {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px dashed #f0f0f0;
  font-size: 0.85rem;

  .feedback-buttons {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;

    .feedback-label {
      color: #666;
    }

    .ant-btn {
      min-width: 2.5rem;
      height: 1.75rem;
      font-size: 0.8rem;
    }
  }

  .feedback-result {
    color: #888;
    font-size: 0.8rem;
  }
}

/* 评分模态框 */
.feedback-modal {
  .modal-content {
    .rating-section, .reason-section {
      display: flex;
      align-items: center;
      margin-bottom: 1rem;

      > span {
        width: 80px;
        flex-shrink: 0;
      }
    }
  }
}

/* 动画效果 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes blob-bounce {
  0% { transform: translate(-50%, -50%) scale(1); }
  25% { transform: translate(-50%, -50%) scale(1.2); }
  50% { transform: translate(-50%, -50%) scale(0.9); }
  75% { transform: translate(-50%, -50%) scale(1.1); }
  100% { transform: translate(-50%, -50%) scale(1); }
}

.scrollable-menu {
  max-height: 300px;
  overflow-y: auto;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--gray-400);
    border-radius: 3px;
  }
}

@media (max-width: 768px) {
  .chat-header {
    padding: 0 1rem;
    
    .conv-title {
      max-width: 150px;
    }
  }

  .chat-box {
    padding: 0.75rem;
  }

  .bottom {
    padding: 0.75rem 0;
    
    .message-input-wrapper {
      padding: 0 0.75rem;
      
      .input-box {
        padding: 0.5rem;
      }
    }
  }

  .chat-examples {
    h1 {
      font-size: 1.2rem;
    }
    
    .card {
      width: 140px;
      height: 100px;
    }
  }
}

@media (max-width: 480px) {
  .chat-header {
    .header__left, .header__right {
      gap: 0.5rem;
    }
    
    .nav-btn .text,
    .model-select .text {
      display: none;
    }
  }
  
  .note {
    display: none;
  }
}
</style>

<style lang="less">
.ant-dropdown-menu {
  &.scrollable-menu {
    max-height: 300px;
    overflow-y: auto;
  }
  
  .ant-dropdown-menu-item {
    padding: 0.5rem 1rem;
  }
}
</style>