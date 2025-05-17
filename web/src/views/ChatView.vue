<template>
  <div class="chat-container">
    <!-- 左边侧边栏 -->
    <div class="conversations" :class="{ 'is-open': state.isSidebarOpen }">
      <div class="actions">
        <div class="action new" @click="showNewConvModal" title="新建对话">
          <PlusCircleOutlined />
        </div>
        <span class="header-title">对话历史</span>
        <div class="action close" @click="state.isSidebarOpen = false">
          <img src="@/assets/icons/sidebar_left.svg" class="iconfont icon-20" alt="设置" />
        </div>
      </div>
      <div class="conversation-list">
        <div class="conversation"
          v-for="(conv, index) in convStore.conversations"
          :key="conv.id"  
          :class="{ active: currentConvId === conv.id }"  
          @click="goToConversation(conv.id)">
          <div class="conversation__title">
            <CommentOutlined /> &nbsp;{{ conv.name || '未命名会话' }}
            <span class="conv-type-tag">{{ getChatTypeName(conv.chat_type) }}</span>
          </div>
          <div class="conversation__delete" @click.stop="confirmDelete(conv.id)">
            <DeleteOutlined />
          </div>
        </div>
      </div>
    </div>
    
    <!-- 右边聊天区域 -->
    <ChatComponent
      v-if="currentConversation"
      :conv="currentConversation"
      :state="state"
      @rename-title="renameTitle"
      @newconv="showNewConvModal"/>

    <!-- 新建会话模态框 -->
    <a-modal
      v-model:visible="showModal"
      title="新建会话"
      @ok="createNewConversation"
      @cancel="closeModal"
      :width="400"
      okText="创建"
      cancelText="取消"
    >
      <a-form layout="vertical">
        <a-form-item label="会话名称" required>
          <a-input 
            v-model:value="newConversation.name" 
            placeholder="请输入会话名称"
            :maxLength="30"
            show-count
          />
        </a-form-item>
        <a-form-item label="聊天类型" required>
          <a-select v-model:value="newConversation.chatType">
            <a-select-option value="chat">通用聊天</a-select-option>
            <a-select-option value="knowledge_base_chat">基于知识库聊天</a-select-option>
            <a-select-option value="search_engine_chat">基于联网搜索聊天</a-select-option>
            <a-select-option value="neo4j_chat">基于知识图谱聊天</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { reactive, ref, watch, onMounted, computed } from 'vue'
import ChatComponent from '@/components/ChatComponent.vue'
import { DeleteOutlined, CommentOutlined, PlusCircleOutlined } from '@ant-design/icons-vue'
import { Modal, Form, Input, Select, message } from 'ant-design-vue'
import { useUserStore, useConvStore } from '@/stores/config'
import axios from 'axios';

const AForm = Form
const AFormItem = Form.Item
const AInput = Input
const ASelect = Select
const ASelectOption = Select.Option

const userStore = useUserStore()
const convStore = useConvStore()

const currentConvId = ref(null)
const showModal = ref(false)

const state = reactive({
  isSidebarOpen: 'true',
})

const newConversation = reactive({
  name: '',
  chatType: 'chat'
})

// 获取当前会话对象
const currentConversation = computed(() => {
  const result = convStore.conversations.find(c => c.id === currentConvId.value) // ✅
  console.log("当前会话对象：", result)
  return result || null
})

// 显示新建会话模态框
const showNewConvModal = () => {
  newConversation.name = ''
  newConversation.chatType = 'chat'
  showModal.value = true
}

// 创建新会话
const createNewConversation = async () => {
  if (!newConversation.name.trim()) {
    message.error('请输入会话名称')
    return
  }

  try {
    const response = await axios.post('/api/conversations', {
      user_id: userStore.user.id,
      name: newConversation.name,
      chat_type: newConversation.chatType
    })
    
    if (response.data.status === 200) {
      message.success('会话创建成功')
      await convStore.fetchConversations(userStore.user.id)
      currentConvId.value = response.data.id
      closeModal()
    }
  } catch (error) {
    message.error(error.response?.data?.message || '创建会话失败')
  }
}

// 关闭模态框
const closeModal = () => {
  showModal.value = false
}

// 删除会话（带确认对话框）
const confirmDelete = (convId) => {
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除这个会话吗？所有聊天记录将丢失',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    maskClosable: true,
    async onOk() {
      await deleteConversation(convId)
    },
    onCancel() {
      console.log('用户取消删除')
    }
  })
}

const deleteConversation = async (convId) => {
  // 1. 获取当前会话状态
  const isCurrentConv = convId === currentConvId.value
  const oldConversations = [...convStore.conversations] // 备份用于回滚
  
  try {
    // 2. 乐观更新 - 立即从本地移除
    convStore.conversations = convStore.conversations.filter(c => c.id !== convId)
    
    // 3. 如果删除的是当前会话，自动选择第一个会话
    if (isCurrentConv) {
      currentConvId.value = convStore.conversations.length > 0 
        ? convStore.conversations[0].id 
        : null
    }
    
    // 4. 调用后端API
    const response = await axios.delete(`/api/conversations/${convId}`)
    
    // 5. 验证响应（根据您后端返回的格式调整）
    if (response.data?.status !== 200) {
      throw new Error(response.data?.message || '删除失败')
    }
    
    message.success('删除成功')
    
  } catch (error) {
    // 6. 失败回滚
    convStore.conversations = oldConversations
    
    // 7. 错误处理
    const errorMsg = error.response?.data?.message || 
                    error.message || 
                    '删除失败，请稍后重试'
    
    message.error(errorMsg)
    console.error('删除会话错误:', error)
    
    // 8. 如果删除的是当前会话且回滚后存在，恢复选中状态
    if (isCurrentConv && oldConversations.some(c => c.id === convId)) {
      currentConvId.value = convId
    }
  }
}

// 切换会话
const goToConversation = (convId) => {
  currentConvId.value = convId
}

// 处理重命名标题
const renameTitle = (newTitle) => {
  if (!currentConvId.value) return
  
  const conv = convStore.conversations.find(c => c.id === currentConvId.value)
  if (conv) {
    conv.name = newTitle
    // 可以添加API调用保存到后端
  }
}

// 聊天类型名称映射
const getChatTypeName = (type) => {
  const map = {
    chat: '(通用)',
    knowledge_base_chat: '(知识库)',
    search_engine_chat: '(联网)',
    neo4j_chat: '(知识图谱)'
  }
  return map[type] || type
}

// 初始化
onMounted(async () => {
  if (userStore.isAuthenticated) {
    // 如果store中没有会话数据，则加载
    if (convStore.conversations.length === 0) {
      await convStore.fetchConversations(userStore.user.id)
      console.log('会话数据结构:', JSON.parse(JSON.stringify(convStore.conversations[0])))
    }
    
    // 设置默认会话
    if (!currentConvId.value && convStore.conversations.length > 0) {
      currentConvId.value = convStore.conversations[0].id
      console.log("当前会话id：", currentConvId)
    }
  }
})

// 监听登录状态变化
watch(() => userStore.isAuthenticated, async (isAuth) => {
  if (isAuth) {
    await convStore.fetchConversations(userStore.user.id)
    if (!currentConvId.value && convStore.conversations.length > 0) {
      currentConvId.value = convStore.conversations[0].id
    }
  } else {
    currentConvId.value = null
  }
})

// 监视侧边栏状态变化
watch(
  () => state.isSidebarOpen,
  (newValue) => {
    localStorage.setItem('chat-sidebar-open', JSON.stringify(newValue))
  }
)
</script>

<style lang="less" scoped>
@import '@/assets/main.css';

.chat-container {
  display: flex;
  width: 100%;
  height: 100%;
  position: relative;
}

.conversations {
  width: 230px;
  max-width: 230px;
  border-right: 1px solid var(--main-light-3);
  background-color: var(--bg-sider);
  transition: all 0.3s ease;
  white-space: nowrap; /* 防止文本换行 */
  overflow: hidden; /* 确保内容不溢出 */

  &.is-open {
    width: 230px;
  }

  &:not(.is-open) {
    width: 0;
    padding: 0;
    overflow: hidden;
  }
 .action.new {
  color: var(--main-500);
  &:hover { background: var(--main-light-4); }
}
  & .actions {
    height: var(--header-height);
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    z-index: 9;
    border-bottom: 1px solid var(--main-light-3);

    .header-title {
      font-weight: bold;
      user-select: none;
      white-space: nowrap;
      overflow: hidden;
    }

    .action {
      font-size: 1.2rem;
      width: 2.5rem;
      height: 2.5rem;
      display: flex;
      justify-content: center;
      align-items: center;
      border-radius: 8px;
      color: var(--gray-800);
      cursor: pointer;

      &:hover {
        background-color: var(--main-light-3);
      }

      .nav-btn-icon {
        width: 1.2rem;
        height: 1.2rem;
      }
    }
  }

  .conversation-list {
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    max-height: 100%;
  }

  .conversation-list .conversation {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    cursor: pointer;
    width: 100%;
    user-select: none;
    transition: background-color 0.2s ease-in-out;

    &__title {
      color: var(--gray-700);
      white-space: nowrap; /* 禁止换行 */
      overflow: hidden;    /* 超出部分隐藏 */
      text-overflow: ellipsis; /* 显示省略号 */
    }

    &__delete {
      display: none;
      color: var(--gray-500);
      transition: all 0.2s ease-in-out;

      &:hover {
        color: #F93A37;
        background-color: #EEE;
      }
    }

    &.active {
      border-right: 3px solid var(--main-500);
      padding-right: 13px;
      background-color: var(--gray-200);

      & .conversation__title {
        color: var(--gray-1000);
      }
    }

    &:not(.active):hover {
      background-color: var(--main-light-3);

      & .conversation__delete {
        display: block;
      }
    }
  }
}

.conversation-list::-webkit-scrollbar {
  position: absolute;
  width: 4px;
}

.conversation-list::-webkit-scrollbar-track {
  background: transparent;
  border-radius: 4px;
}

.conversation-list::-webkit-scrollbar-thumb {
  background: var(--gray-400);
  border-radius: 4px;
}

.conversation-list::-webkit-scrollbar-thumb:hover {
  background: rgb(100, 100, 100);
  border-radius: 4px;
}

.conversation-list::-webkit-scrollbar-thumb:active {
  background: rgb(68, 68, 68);
  border-radius: 4px;
}

@media (max-width: 520px) {
  .conversations {
    position: absolute;
    z-index: 101;
    width: 300px;
    height: 100%;
    border-radius: 0 16px 16px 0;
    box-shadow: 0 0 10px 1px rgba(0, 0, 0, 0.05);

    &:not(.is-open) {
      width: 0;
      padding: 0;
      overflow: hidden;
    }
  }
}
</style>
