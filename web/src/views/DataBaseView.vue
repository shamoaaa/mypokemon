<template>
  <div class="database-container layout-container" v-if="userStore.isAuthenticated">
    <HeaderComponent title="知识库"></HeaderComponent>

    <div class="database">
      <a-button type="primary" @click="newDatabase.open = true"><PlusOutlined />新建知识库</a-button>

      <div class="db-list">
        <div v-for="db in databases" :key="db.db_id" class="dbcard" @click="navigateToDatabase(db.name)">
          <div class="top">
            <div class="icon">
              <AppstoreFilled style="font-size: 24px; color: #1890ff;" />
            </div>
            <div class="info">
              <h3>{{ db.name }}</h3>
              <div class="description">{{ db.description }}</div>
            </div>
          </div>

          <div class="tags">
            <a-tag color="blue">{{ db.vector_store_type }}</a-tag>
            <a-tag color="green">{{ db.embed_model }}</a-tag>
            <a-tag color="orange">文件数：{{ db.file_count }}</a-tag>
            <a-tag color="gray">{{ db.create_time }}</a-tag>
          </div>

          <a-button type="link" size="small" @click.stop="deleteDatabase(db.name)">删除</a-button>
        </div>
      </div>
    </div>

    <!-- 新建知识库弹窗 -->
    <a-modal v-model:open="newDatabase.open" title="新建知识库" @ok="createDatabase" :confirm-loading="newDatabase.loading">
      <a-form :model="newDatabase">
        <a-form-item label="名称" :help="newDatabase.errors.name" :validateStatus="newDatabase.errors.name ? 'error' : ''">
          <a-input
            v-model:value="newDatabase.name"
            placeholder="请输入知识库名称"
            @blur="validateName"
            @change="validateName"
          />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="newDatabase.description" placeholder="请输入知识库描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>

  <!-- 当未启用知识库时显示的信息 -->
  <div class="database-empty" v-else-if="!configStore.config.enable_knowledge_base">
    <a-empty description="知识库功能未启用，请前往设置页面开启" />
  </div>

  <!-- 当用户未登录时显示的信息 -->
  <div class="database-empty" v-else>
    <a-empty description="请先登录以查看知识库" />
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, watch, h } from 'vue'
import { useRouter, useRoute } from 'vue-router';
import { message, Button, Modal } from 'ant-design-vue'
import { ReadFilled, PlusOutlined, AppstoreFilled, LoadingOutlined } from '@ant-design/icons-vue'
import { useUserStore,useConfigStore } from '@/stores/config';
import HeaderComponent from '@/components/HeaderComponent.vue';


const route = useRoute()
const router = useRouter()
const databases = ref([])
const graph = ref(null)
const graphloading = ref(false)
const userStore = useUserStore();
const indicator = h(LoadingOutlined, {spin: true});
const configStore = useConfigStore()
const loading = ref(false); // 加载状态

const newDatabase = reactive({
  name: '',
  description: '',
  loading: false,
  open: false,
  errors: {
    name: ''
  }
})

function isValidCollectionName(name) {
  return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
}
const validateName = () => {
  const name = newDatabase.name.trim();
  if (!name) {
    newDatabase.errors.name = '知识库名称不能为空';
    return false;
  }
  if (!isValidCollectionName(name)) {
    newDatabase.errors.name = '第一个字符必须是字母或下划线 _';
    return false;
  }
  newDatabase.errors.name = '';
  return true;
};

const loadDatabases = async () => {
  if (!userStore.isAuthenticated || !userStore.user?.id) {
  message.error('请先登录');
  return;
}

  loading.value = true;

  try {
    const res = await fetch(`/api/knowledge-bases/${userStore.user.id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!res.ok) {
      throw new Error('获取知识库失败');
    }

    const result = await res.json();

    if (result.status === 200) {
      const kbList = result.data.knowledge_bases || [];
      console.log("kbList:",kbList);
      // 将后端返回的知识库数据映射为前端可用格式
      databases.value = kbList.map((kb, index) => ({
        db_id: kb.id || index + 1,
        name: kb.kb_name,
        description: kb.kb_info || '暂无描述',
        vector_store_type: kb.vs_type,
        embed_model: kb.embed_model,
        file_count: kb.file_count || 0,
        create_time: kb.create_time ? new Date(kb.create_time).toLocaleDateString() : '--'
      }));
    } else {
      message.warning(result.msg || '暂无知识库');
    }
  } catch (error) {
    console.error(error);
    message.error('加载知识库时发生错误');
  } finally {
    loading.value = false;
  }
};

const deleteDatabase = async (kbName) => {
  let hideLoading = null; // 在外部声明以便在finally中访问
  
  try {
    // 特殊数据库名称判断
    if (kbName.toLowerCase() === 'wiki') {
      message.warning('通用数据库，你删nm呢？');
      return;
    }

    // 添加确认对话框
    const confirmDelete = await new Promise((resolve) => {
      Modal.confirm({
        title: '确认删除知识库',
        content: `确定要删除知识库 "${kbName}" 吗？此操作不可恢复！`,
        okText: '确认删除',
        okType: 'danger',
        cancelText: '取消',
        onOk: () => resolve(true),
        onCancel: () => resolve(false),
      });
    });

    if (!confirmDelete) return;

    // 显示加载状态 (0表示不自动关闭)
    hideLoading = message.loading('正在删除知识库...', 0);
    
    const res = await fetch('/api/knowledge_base/delete_knowledge_base', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userStore.user.id,
        knowledge_base_name: kbName
      })
    });

    const data = await res.json();
    
    // 先隐藏加载状态再显示结果消息
    hideLoading?.();
    hideLoading = null; // 重置引用
    
    if (res.ok) {
      message.success(data.msg || `知识库 "${kbName}" 删除成功`);
      await loadDatabases(); // 等待列表刷新完成
    } else {
      const errorMsg = data.msg || 
        (res.status === 404 ? '知识库不存在' : 
         res.status === 500 ? '服务器错误' : '删除知识库失败');
      message.error(`${errorMsg} (状态码: ${res.status})`);
    }
  } catch (e) {
    hideLoading?.(); // 出错时也确保关闭加载状态
    console.error('删除知识库出错:', e);
    message.error(`删除知识库失败: ${e.message}`);
  } finally {
    hideLoading?.(); // 最终确保关闭
  }
};

const createDatabase = () => {
  if (!validateName()) {
      message.error('请检查知识库名称格式');
      return;
    }
  // 清除错误信息
  newDatabase.errors.name = ''

  if (!newDatabase.name.trim()) {
    newDatabase.errors.name = '知识库名称不能为空'
    message.error('请填写知识库名称')
    return
  }

  newDatabase.loading = true

  fetch('/api/knowledge_base/create_knowledge_base', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user_id: userStore.user.id,
      knowledge_base_name: newDatabase.name,
      knowledge_base_description: newDatabase.description
    })
  })
  .then(response => {
  if (response.ok) {  // 检查HTTP状态码(200-299范围)
    return response.json().then(data => {
      message.success(data.msg || '创建成功')
      loadDatabases()
      newDatabase.open = false
      resetNewDatabaseForm()
    })
  } else {
    return response.json().then(data => {
      message.error(data.msg || '创建失败')
    })
  }
})
  .catch(err => {
    console.error(err)
    message.error('请求出错，请检查网络或重试')
  })
  .finally(() => {
    newDatabase.loading = false
  })
}

// 重置表单
const resetNewDatabaseForm = () => {
  newDatabase.name = ''
  newDatabase.description = ''
}

const navigateToDatabase = (knowledge_base_name) => {
  router.push({ path: `/database/${knowledge_base_name}` });
};

const navigateToGraph = () => {
  router.push({ path: `/database/graph` });
};

watch(() => route.path, (newPath, oldPath) => {
  if (newPath === '/database') {
    loadDatabases();
  }
});

onMounted(() => {
  console.log('isAuthenticated:', userStore.isAuthenticated)
  console.log('user:', userStore.user)
  loadDatabases()
})
</script>

<style scoped>
/* 根据需要调整样式 */
.database .dbcard {
  cursor: pointer;
  border: 1px solid #f0f0f0;
  padding: 16px;
  margin-bottom: 16px;
  position: relative;
}
.database .dbcard:hover {
  background-color: #fafafa;
}
.database .dbcard .top {
  display: flex;
  align-items: center;
}
.database .dbcard .top .icon {
  margin-right: 16px;
}
.database .dbcard .top .info h3 {
  margin: 0;
}
.database .dbcard .description {
  color: #555;
  margin-top: 8px;
}
.database .dbcard .tags {
  margin-top: 8px;
}
.database .dbcard .ant-btn-link {
  position: absolute;
  bottom: 8px;
  right: 8px;


}
</style>