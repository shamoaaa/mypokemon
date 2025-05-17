import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { message } from 'ant-design-vue'

export const useCounterStore = defineStore('counter', () => {
  const count = ref(0)
  const doubleCount = computed(() => count.value * 2)
  function increment() {
    count.value++
  }

  return { count, doubleCount, increment }
})


export const useConfigStore = defineStore('config', () => {
  const config = ref({})
  function setConfig(newConfig) {
    config.value = newConfig
  }

  function setConfigValue(key, value) {
    config.value[key] = value
    fetch('/api/config', {
      method: 'POST',
      body: JSON.stringify({ key, value }),
      headers: {
        'Content-Type': 'application/json'
      }
    })
    .then(response => response.json())
    .then(data => {
      console.debug('Success:', data)
      setConfig(data)
    })
  }

  function refreshConfig() {
    fetch('/api/config')
    .then(response => response.json())
    .then(data => {
      console.log("config", data)
      setConfig(data)
    })
  }

  return { config, setConfig, setConfigValue, refreshConfig }
})


export const useUserStore = defineStore('user', () => {
  const router = useRouter()
  
  // 用户状态
  const isAuthenticated = ref(false)
  const user = ref({
    id: null,
    username: ''
  })
  
  // 登录/注册相关状态
  const loginError = ref('')
  const registerError = ref('')

  // 初始化检查登录状态
  const initialize = () => {
    const userData = localStorage.getItem('user')
    if (userData) {
      const parsedData = JSON.parse(userData)
      user.value = {
        id: parsedData.id,
        username: parsedData.username
      }
      isAuthenticated.value = true
    }
  }

  // 登录方法
  const login = async (username, password) => {
    try {
      const response = await axios.post('/api/users/login', {
        username,
        password
      })

      if (response.data?.status === 200) {
        // 存储用户信息到本地存储和状态
        const userData = {
          id: response.data.id,
          username: response.data.username
        }
        localStorage.setItem('user', JSON.stringify(userData))
        
        // 更新store状态
        user.value = userData
        isAuthenticated.value = true
        loginError.value = ''
        
        return true
      } else {
        loginError.value = response.data?.message || '登录失败'
        return false
      }
    } catch (error) {
      handleAuthError(error, loginError)
      return false
    }
  }

  // 注册方法
  const register = async (username, password, confirmPassword) => {
    if (password !== confirmPassword) {
      registerError.value = '两次输入的密码不一致'
      return false
    }

    try {
      const response = await axios.post('/api/users/register', {
        username,
        password
      })

      if (response.data?.id) {
        // 注册成功后自动登录
        return await login(username, password)
      }
      return false
    } catch (error) {
      handleAuthError(error, registerError)
      return false
    }
  }

  // 登出方法
  const logout = () => {
    localStorage.removeItem('user')
    isAuthenticated.value = false
    user.value = { id: null, username: '' }
    
    if (router.currentRoute.value.meta.requiresAuth) {
      router.push('/')
    }
  }

  // 错误处理
  const handleAuthError = (error, errorRef) => {
    if (error.response) {
      if (error.response.status === 401) {
        errorRef.value = error.response.data?.message || '用户名或密码错误'
      } else {
        errorRef.value = error.response.data?.message || '操作失败，请稍后再试'
      }
    } else {
      errorRef.value = '网络错误，请检查连接'
    }
    console.error('认证错误:', error)
  }

  // 初始化执行
  initialize()

  return {
    // 状态
    isAuthenticated,
    user,
    loginError,
    registerError,
    
    // 方法
    login,
    register,
    logout,
    initialize
  }
})



export const useConvStore = defineStore('conversations', () => {
  const conversations = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  // 获取用户会话列表
  const fetchConversations = async (userId) => {
    try {
      isLoading.value = true
      error.value = null
      
      const response = await axios.get(`/api/users/${userId}/conversations`)
      
      if (response.data?.status === 200) {
        conversations.value = response.data.data
      } else {
        throw new Error(response.data?.message || '获取会话失败')
      }
    } catch (err) {
      error.value = err.message
      console.error('获取会话错误:', err)
    } finally {
      isLoading.value = false
    }
  }

  const createLoginConversation = async (userId) => {
  try {
    const response = await axios.post('/api/conversations', {
      user_id: userId,
      name: "新对话",
      chat_type: "chat"
    })
  } catch (error) {
    message.error(error.response?.data?.message || '创建会话失败')
  }
}


  return {
    conversations,
    isLoading,
    error,
    fetchConversations,
    createLoginConversation
  }
})