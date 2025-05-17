<template>
  <section class="welcome" ref="root">
    <header class="app-header">
      <h1 class="visually-hidden">{{ resolvedTitle }}</h1>
      <div class="auth-buttons" v-if="!userStore.isAuthenticated">
        <button class="auth-button" @click="showLoginModal = true">登录</button>
        <button class="auth-button auth-button--primary" @click="showRegisterModal = true">注册</button>
      </div>
      <div class="user-info" v-else>
        <span class="username">{{ userStore.user.username }}</span>
        <button class="auth-button" @click="logout">退出</button>
      </div>
    </header>

    <main class="hero">
      <h2 class="hero__title" v-text="resolvedTitle" />
      <p class="hero__subtitle">大模型驱动的知识库管理工具</p>
      <button class="cta" @click="goToChat" aria-label="开始对话">
        开始对话
      </button>
      <img class="hero__img" src="/home.jpg" alt="彩色宝可梦知识图谱插图" loading="lazy" />
    </main>

    <footer class="app-footer">
      © {{ new Date().getFullYear() }} Poké Knowledge. All rights reserved.
    </footer>

    <!-- 登录模态框 -->
    <div class="modal" v-if="showLoginModal" @click.self="showLoginModal = false">
      <div class="modal-content">
        <h3>登录</h3>
        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label for="login-username">用户名</label>
            <input id="login-username" v-model="loginForm.username" required>
          </div>
          <div class="form-group">
            <label for="login-password">密码</label>
            <input id="login-password" type="password" v-model="loginForm.password" required>
          </div>
          <button type="submit" class="modal-button">登录</button>
          <p class="error-message" v-if="userStore.loginError">{{ userStore.loginError }}</p>
        </form>
      </div>
    </div>

    <!-- 注册模态框 -->
    <div class="modal" v-if="showRegisterModal" @click.self="showRegisterModal = false">
      <div class="modal-content">
        <h3>注册</h3>
        <form @submit.prevent="handleRegister">
          <div class="form-group">
            <label for="register-username">用户名</label>
            <input id="register-username" v-model="registerForm.username" required>
          </div>
          <div class="form-group">
            <label for="register-password">密码</label>
            <input id="register-password" type="password" v-model="registerForm.password" required>
          </div>
          <div class="form-group">
            <label for="register-confirm">确认密码</label>
            <input id="register-confirm" type="password" v-model="registerForm.confirmPassword" required>
          </div>
          <button type="submit" class="modal-button">注册</button>
          <p class="error-message" v-if="userStore.registerError">{{ userStore.registerError }}</p>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/config'
import { useConvStore } from '@/stores/config'
import axios from 'axios';

const props = defineProps({
  title: { type: String, default: '可萌助手' }
})
const resolvedTitle = computed(() => props.title)

const router = useRouter()
const userStore = useUserStore()
const convStore = useConvStore()

// 登录/注册相关状态
const showLoginModal = ref(false)
const loginForm = ref({
  username: '',
  password: ''
})

const showRegisterModal = ref(false)
const registerForm = ref({
  username: '',
  password: '',
  confirmPassword: ''
})

const goToChat = () => {
  if (!userStore.isAuthenticated) {
    showLoginModal.value = true
  } else {
    router.push('/chat')
  }
}

// 登录处理
const handleLogin = async () => {
  const success = await userStore.login(
    loginForm.value.username,
    loginForm.value.password
  )
  
  if (success) {
    showLoginModal.value = false
    loginForm.value = { username: '', password: '' }

    try {
      console.log("用户ID:", userStore.user.id); // 调试日志
      
      // 确保使用正确的store和用户ID
      await createLoginConversation(userStore.user.id)
      
      console.log("会话创建成功"); // 调试日志
      router.push('/chat')
    } catch (error) {
      console.error('加载会话失败:', error)
      message.error('初始化会话失败: ' + error.message)
      router.push('/chat') // 即使失败也跳转
    }
  }
}
const createLoginConversation = async (userId) => {
  try {
    console.log("正在创建会话，用户ID:", userId); // 调试日志
    
    const response = await axios.post('/api/conversations', {
      user_id: userId,
      name: "新对话",
      chat_type: "chat"
    })

    // 检查响应状态
    if (response.data?.status !== 200) {
      throw new Error(response.data?.message || '创建会话失败')
    }

    console.log("创建会话响应:", response.data); // 调试日志
    return response.data.data
  } catch (error) {
    console.error('创建会话错误详情:', error.response || error); // 更详细的错误日志
    throw error // 重新抛出错误让外层处理
  }
}

// 注册处理
const handleRegister = async () => {
  const success = await userStore.register(
    registerForm.value.username,
    registerForm.value.password,
    registerForm.value.confirmPassword
  )
  
  if (success) {
    showRegisterModal.value = false
    registerForm.value = { username: '', password: '', confirmPassword: '' }
    await createLoginConversation(userStore.user.id)
    router.push('/chat')
  }
}

// 退出登录
const logout = () => {
  userStore.logout()
}
</script>

<style scoped lang="less">
/*  🎨 Variables  ---------------------------------------------------------- */
@primary       : #2c86a8;
@primary-dark  : #005f77;
@text-color    : #333;
@gradient      : linear-gradient(168deg,#ffd6eb,#ffe7ca,#d3fffb,#dbebff,#ffd8ff);

/*  🌐 Layout  ------------------------------------------------------------- */
.welcome {
  --header-height: 64px;
  display:flex;
  flex-direction:column;
  align-items:center;
  min-height:100vh;
  color:@text-color;
  text-align:center;
  background:@gradient;
  background-size:1000% 1000%;
  animation:bgMove 18s ease-in-out infinite;
}

/* reduce‑motion 优化 */
@media (prefers-reduced-motion: reduce) {
  .welcome { animation:none; }
}

.app-header {
  height:var(--header-height);
  width:100%;
  display:flex;
  align-items:center;
  justify-content:center;
  backdrop-filter:blur(12px);
  background:rgba(255,255,255,.45);
  border-bottom:1px solid fade(@primary,30%);
}

.hero {
  flex:1 0 auto;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  width:100%;
  padding:clamp(1rem,4vw,4rem);
}

.hero__title {
  font-size:clamp(2.5rem,6vw,3.75rem);
  font-weight:700;
  margin:0 0 .5rem;
}

.hero__subtitle {
  font-size:clamp(1rem,2.2vw,1.25rem);
  margin:0 0 1.75rem;
}

.cta {
  padding:.65rem 2.5rem;
  font-size:clamp(1rem,2.4vw,1.35rem);
  font-weight:600;
  color:#fff;
  background:@primary-dark;
  border:none;
  border-radius:999px;
  cursor:pointer;
  transition:all .25s ease;

  &:hover {
    background:darken(@primary-dark,6%);
    transform:translateY(-2px);
    box-shadow:0 4px 12px rgba(0,0,0,.15);
  }
}

.hero__img {
  width:min(720px,90%);
  height:auto;
  margin-top:clamp(1.5rem,5vw,3rem);
  border-radius:1rem;
  object-fit:cover;
  box-shadow:0 5px 12px rgba(0,0,0,.08);
}

.app-footer {
  padding:.75rem 0 1.25rem;
  font-size:.875rem;
  color:fade(@text-color,60%);
}

/*  💫 Background animation  ---------------------------------------------- */
@keyframes bgMove {
  0%{background-position:0% 50%}
  50%{background-position:100% 50%}
  100%{background-position:0% 50%}
}

/*  ♿ 隐藏但可读标题  ------------------------------------------------------ */
.visually-hidden {
  border:0;clip:rect(0 0 0 0);height:1px;margin:-1px;overflow:hidden;padding:0;position:absolute;width:1px;
}
.auth-buttons {
  display: flex;
  gap: 1rem;
  margin-left: auto;
  padding-right: 2rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-left: auto;
  padding-right: 2rem;
}

.username {
  font-weight: 500;
  color: @primary-dark;
}

.auth-button {
  padding: 0.4rem 1rem;
  background: transparent;
  border: 1px solid @primary;
  border-radius: 999px;
  color: @primary;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: fade(@primary, 10%);
  }

  &--primary {
    background: @primary;
    color: white;

    &:hover {
      background: darken(@primary, 8%);
    }
  }
}

/* 模态框样式 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);

  h3 {
    margin-top: 0;
    color: @primary-dark;
    text-align: center;
  }
}

.form-group {
  margin-bottom: 1.5rem;

  label {
    display: block;
    margin-bottom: 0.5rem;
    color: @text-color;
  }

  input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;

    &:focus {
      outline: none;
      border-color: @primary;
      box-shadow: 0 0 0 2px fade(@primary, 20%);
    }
  }
}

.modal-button {
  width: 100%;
  padding: 0.75rem;
  background: @primary;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;

  &:hover {
    background: darken(@primary, 8%);
  }
}

.error-message {
  color: #e74c3c;
  margin-top: 1rem;
  text-align: center;
  font-size: 0.9rem;
}
</style>
