<template>
<div>
  <HeaderComponent
    :title="database.name || '数据库信息'"
  >
    <template #description>
      <div class="database-info">
        <a-tag color="blue" v-if="database.embed_model">{{ database.embed_model }}</a-tag>
        <a-tag color="green" v-if="database.dimension">{{ database.dimension }}</a-tag>
      </div>
    </template>
    <template #actions>
      <a-button type="primary" @click="backToDatabase">
        <LeftOutlined /> 返回
      </a-button>
    </template>
  </HeaderComponent>
  <a-alert v-if="configStore.config.embed_model &&database.embed_model != configStore.config.embed_model" message="向量模型不匹配，请重新选择" type="warning" style="margin: 10px 20px;" />
  <div class="db-main-container">
    <a-tabs v-model:activeKey="state.curPage" class="atab-container" type="card">

      <a-tab-pane key="files">
  <template #tab><span><ReadOutlined />文件列表</span></template>
  <div class="db-tab-container">
    <div class="actions">
      <a-button @click="handleRefresh" :loading="state.refrashing">刷新</a-button>
    </div>

    <!-- 使用 fileList.value 作为数据源 -->
    <a-table
      :columns="columns"
      :data-source="fileList"
      row-key="id"
      class="my-table"
    >
      <template #bodyCell="{ column, text, record }">
        <template v-if="column.key === 'filename'">
          <a-button class="main-btn" type="link" @click="openFileDetail(record)">
            {{ text }}
          </a-button>
        </template>
        <template v-else-if="column.key === 'type'">
          <span :class="['span-type', text]">{{ text?.toUpperCase() }}</span>
        </template>
        <template v-else-if="column.key === 'status' && text === 'done'">
          <CheckCircleFilled style="color: #41A317;" />
        </template>
        <template v-else-if="column.key === 'status' && text === 'failed'">
          <CloseCircleFilled style="color: #FF4D4F;" />
        </template>
        <template v-else-if="column.key === 'status' && text === 'processing'">
          <HourglassFilled style="color: #1677FF;" />
        </template>
        <template v-else-if="column.key === 'status' && text === 'waiting'">
          <ClockCircleFilled style="color: #FFCD43;" />
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button
            class="del-btn"
            type="link"
            @click="deleteFile(text)"
            :disabled="state.lock || record.status === 'processing' || record.status === 'waiting'"
          >
            删除
          </a-button>
        </template>
        <span v-else-if="column.key === 'created_at'">
          {{ formatRelativeTime(new Date(text * 1000)) }}
        </span>
        <span v-else>{{ text }}</span>
      </template>
    </a-table>

    <a-drawer
      width="50%"
      v-model:open="state.drawer"
      class="custom-class"
      :title="selectedFile?.file_name || '文件详情'"
      placement="right"
      @after-open-change="afterOpenChange"
    >
      <h2>共 {{ selectedFile?.docs_count || 0 }} 个片段</h2>
      <p
        v-for="line in selectedFile?.lines || []"
        :key="line.id"
        class="line-text"
      >
        {{ line.text }}
      </p>
    </a-drawer>
  </div>
</a-tab-pane>

      <a-tab-pane key="add">
        <template #tab><span><CloudUploadOutlined />添加文件</span></template>
        <div class="db-tab-container">
          <div class="upload-section">
            <div class="upload-sidebar">
              <div class="chunking-params">
                <div class="params-info">
                  <p>调整分块参数可以控制文本的切分方式，影响检索质量和文档加载效率。</p>
                </div>
                <a-form
                  :model="chunkParams"
                  name="basic"
                  autocomplete="off"
                  layout="vertical"
                >
                  <a-form-item label="Chunk Size" name="chunk_size">
                    <a-input-number v-model:value="chunkParams.chunk_size" :min="100" :max="10000" />
                    <p class="param-description">每个文本片段的最大字符数</p>
                  </a-form-item>
                  <a-form-item label="Chunk Overlap" name="chunk_overlap">
                    <a-input-number v-model:value="chunkParams.chunk_overlap" :min="0" :max="1000" />
                    <p class="param-description">相邻文本片段间的重叠字符数</p>
                  </a-form-item>
                  <a-form-item label="使用文件节点解析器" name="use_parser">
                    <a-switch v-model:checked="chunkParams.use_parser" />
                    <p class="param-description">启用特定文件格式的智能分析</p>
                  </a-form-item>
                </a-form>
              </div>
            </div>
            <div class="upload-main">
              <div class="upload">
                <a-upload-dragger
                  class="upload-dragger"
                  v-model:fileList="fileList"
                  name="files"
                  :multiple="true"
                  :disabled="state.loading"
                  :action="uploadActionUrl"
                  @change="handleFileUpload"
                  @drop="handleDrop"
                  :beforeUpload="beforeUpload"
                  :data="uploadDataFields" 
                  :headers="uploadHeaders"
                >
                  <p class="ant-upload-text">点击或者把文件拖拽到这里上传</p>
                  <p class="ant-upload-hint">
                    目前仅支持上传文本文件，如 .pdf, .json, .md。且同名文件无法重复添加
                  </p>
                </a-upload-dragger>
              </div>
            </div>
          </div>

          <!-- 分块结果预览区域 -->
          <div class="chunk-preview" v-if="chunkResults.length > 0">
            <div class="preview-header">
              <h3>分块预览 (共 {{ chunkResults.length }} 个文件，{{ getTotalChunks() }} 个分块)</h3>
              <a-button
                type="primary"
                @click="addToDatabase"
                :loading="state.adding"
              >
                添加到数据库
              </a-button>
            </div>

            <a-collapse v-model:activeKey="activeFileKeys">
              <a-collapse-panel v-for="(file, fileIdx) in chunkResults" :key="fileIdx" :header="file.filename + ' (' + file.nodes.length + ' 个分块)'">
                <div id="result-cards" class="result-cards">
                  <div v-for="(chunk, index) in file.nodes" :key="index" class="chunk">
                    <p><strong>#{{ index + 1 }}</strong> {{ chunk.text }}</p>
                  </div>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </div>
        </div>
      </a-tab-pane>


      <!-- <a-tab-pane key="3" tab="Tab 3">Content of Tab Pane 3</a-tab-pane> -->
    </a-tabs>
  </div>
</div>
</template>

<script setup>
import { onMounted, reactive, ref, watch, toRaw, onUnmounted, computed } from 'vue';
import { message, Modal } from 'ant-design-vue';
import { useRoute, useRouter } from 'vue-router';
import { useConfigStore,useUserStore } from '@/stores/config'
import HeaderComponent from '@/components/HeaderComponent.vue';
import {
  ReadOutlined,
  LeftOutlined,
  CheckCircleFilled,
  HourglassFilled,
  CloseCircleFilled,
  ClockCircleFilled,
  DeleteOutlined,
  CloudUploadOutlined,
  SearchOutlined,
  LoadingOutlined,
  CaretUpOutlined
} from '@ant-design/icons-vue'
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const formatRelativeTime = (date) => {
  return dayjs(date).fromNow();
};

const userStore = useUserStore();
const route = useRoute();
const router = useRouter();
const database = ref({});

const fileList = ref([]);
const selectedFile = ref(null);

// 查询测试
const queryText = ref('');
const queryResult = ref(null)
const filteredResults = ref([])
const configStore = useConfigStore()

const knowledgeBases = ref([]);
const state = reactive({
  loading: false,
});

const selectedKbName = ref(route.params.knowledge_base_name || '');

watch(() => route.params.knowledge_base_name, (newName) => {
  if(newName){
    selectedKbName.value = newName;
    getKnowledgeBaseList();
  } else {
    console.warn('知识库名称为空或未定义');
  }
});

const backToDatabase = () => {
  router.push('/database')
}

const handleRefresh = async () => {
  if (state.refrashing) return; // 防止重复点击

  state.refrashing = true;

  try {
    await getKnowledgeBaseList(); // 假设这是你获取知识库列表的方法
    message.success('刷新成功');
  } catch (error) {
    console.error('刷新失败:', error);
    message.error('刷新失败，请重试');
  } finally {
    state.refrashing = false;
  }
};

const handleFileUpload = async (info) => {
  const { status, name, response } = info.file;

  if (status === 'uploading') {
    state.value.loading = true;
    return;
  }

  if (status === 'done') {
    message.success(`${name} 上传成功`);
    getKnowledgeBaseList(); // 刷新文件列表
  } else if (status === 'error') {
    message.error(`${name} 上传失败`);
  }

  if (info.fileList && info.fileList.length > 0) {
    // 只保留最新上传成功的文件（可选）
    fileList.value = info.fileList.filter(file => file.status !== 'done');
  }

  state.value.loading = false;
};

const beforeUpload = (file) => {
// 检查数据库名称是否为"wiki"
  if (selectedKbName.value === 'wiki') {
    Modal.warning({
      title: '无法上传',
      content: '通用知识库，你上传nm呢？',
      okText: '我知道了'
    });
    return Upload.LIST_IGNORE;
  }
  const isValidType = /\.(pdf|json|md)$/i.test(file.name);
  if (!isValidType) {
    message.error(`文件 ${file.name} 类型不支持`);
    return Upload.LIST_IGNORE; // 不加入上传队列
  }
  return isValidType || Upload.LIST_IGNORE;
};

const handleDrop = (e) => {
  console.log('Drop event:', e);
};


// 计算属性：根据当前 db_id 构造上传地址
const uploadActionUrl = computed(() => {
  return `/api/knowledge_base/upload_files`;
});

// 表单数据字段（POST Form Data）
const uploadDataFields = computed(() => ({
  knowledge_base_name: selectedKbName.value
}));


const deleteFile = (file) => {
  if (selectedKbName.value === 'wiki') {
    Modal.warning({
      title: '无法删除',
      content: '通用知识库，你删nm呢？',
      okText: '我知道了'
    });
    return;
  }
  Modal.confirm({
    title: '删除文件',
    content: `确定要删除文件 "${file.file_name}" 吗？`,
    onOk: async () => {
      state.lock = true;
      try {
        const response = await fetch('/api/knowledge_base/delete_files', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            knowledge_base_name: selectedKbName.value,
            file_names: [file.file_name]
          })
        });

        const result = await response.json();
        if (result.code === 200) {
          message.success('删除成功');
          getKnowledgeBaseList(); // 刷新文件列表
        } else {
          message.error(result.msg || '删除失败');
        }
      } catch (error) {
        message.error('网络错误，请重试');
      } finally {
        state.lock = false;
      }
    }
  });
};

const chunkParams = ref({
  chunk_size: 1000,
  chunk_overlap: 200,
  use_parser: false,
})

const chunkResults = ref([]);
const activeFileKeys = ref([]);



const getKnowledgeBaseList = async () => {
  const userId = userStore.user?.id;
  const kbName = selectedKbName.value;
  console.log("kbname:", kbName); // 注意这里应该是 kbName 而不是 selectedKbName

  if (!userId) {
    message.warning('请先登录');
    return;
  }

  if (!kbName) {
    message.warning('未指定知识库名称');
    return;
  }

  try {
    state.loading = true;

    const queryParams = new URLSearchParams({
      user_id: userId,
      knowledge_base_name: kbName
    });

    const response = await fetch(`/api/knowledge_base/list_files?${queryParams.toString()}`, {
      method: 'GET'
      // 移除了不必要的 Content-Type header
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();

    console.log("文件信息：", result);

    // 直接检查 data 字段
    fileList.value = result.data || [];
    if (result.data && result.data.length > 0) {
      console.log("文件列表已更新");
    } else {
      message.info('没有找到任何文件');
    }
  } catch (error) {
    console.error('获取文件列表时发生异常:', error);
    message.error('网络错误，请检查连接后重试');
  } finally {
    state.loading = false;
  }
};

const columns = [
  {
    title: 'ID',
    dataIndex: 'id',
    key: 'id'
  },
  {
    title: '文件名',
    dataIndex: 'file_name',
    key: 'file_name'
  },
  {
    title: '扩展名',
    dataIndex: 'file_ext',
    key: 'file_ext'
  },
  {
    title: '大小',
    dataIndex: 'file_size',
    key: 'file_size',
    customRender: ({ text }) => `${(text / 1024).toFixed(1)} KB`
  },
  {
    title: '文档数',
    dataIndex: 'docs_count',
    key: 'docs_count'
  },
  {
    title: '创建时间',
    dataIndex: 'create_time',
    key: 'create_time',
    customRender: ({ text }) => formatRelativeTime(new Date(text))
  },
  {
    title: '操作',
    key: 'action',
    scopedSlots: { customRender: 'action' }
  }
];




onMounted(() => {
  console.log('组件挂载，开始检查登录状态...');
  console.log('isAuthenticated:', userStore.isAuthenticated);
  if (!userStore.isAuthenticated) {
    message.warning('请先登录');
    router.push('/login'); // 跳转到登录页
  } else {
    getKnowledgeBaseList();
  }
});

// 添加 onUnmounted 钩子，在组件卸载时清除定时器
onUnmounted(() => {
  if (state.refreshInterval) {
    clearInterval(state.refreshInterval);
    state.refreshInterval = null;
  }
})
</script>

<style lang="less" scoped>
.database-info {
  margin: 8px 0 0;
}

.db-main-container {
  display: flex;
  width: 100%;
}

.db-tab-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.query-test-container {
  display: flex;
  flex-direction: row;
  gap: 20px;

  .sider {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    width: 325px;
    height: 100%;
    padding: 0;
    flex: 0 0 325px;

    .sider-top {
      .query-params {
        display: flex;
        flex-direction: column;
        box-sizing: border-box;
        font-size: 15px;
        gap: 12px;
        padding-top: 12px;
        padding-right: 16px;
        border: 1px solid var(--main-light-3);
        background-color: var(--main-light-6);
        border-radius: 8px;
        padding: 16px;
        margin-right: 8px;

        .params-title {
          margin-top: 0;
          margin-bottom: 16px;
          color: var(--main-color);
          font-size: 18px;
          text-align: center;
          font-weight: bold;
        }

        .params-group {
          margin-bottom: 16px;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--main-light-3);

          &:last-child {
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
          }
        }

        .params-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 12px;

          &:last-child {
            margin-bottom: 0;
          }

          p {
            margin: 0;
            color: var(--gray-900);
          }

          &.col {
            align-items: flex-start;
            flex-direction: column;
            width: 100%;
            height: auto;
          }

          &.w100,
          &.col {
            & > * {
              width: 100%;
            }
          }
        }

        .ant-slider {
          margin: 6px 0px;
        }
      }
    }
  }

  .query-result-container {
    flex: 1;
    padding-bottom: 20px;
  }

  .query-action {
    display: flex;
    gap: 8px;
    margin-bottom: 20px;

    textarea {
      padding: 12px 16px;
      border: 1px solid var(--main-light-2);
    }

    button.btn-query {
      height: auto;
      width: 100px;
      box-shadow: none;
      border: none;
      font-weight: bold;
      background: var(--main-light-3);
      color: var(--main-color);

      &:disabled {
        cursor: not-allowed;
        background: var(--main-light-4);
        color: var(--gray-700);
      }
    }
  }

  .query-examples-container {
    margin-bottom: 20px;
    padding: 12px;
    background: var(--main-light-6);
    border-radius: 8px;
    border: 1px solid var(--main-light-3);

    .examples-title {
      font-weight: bold;
      margin-bottom: 10px;
      color: var(--main-color);
    }

    .query-examples {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 10px 0 0;

      .ant-btn {
        font-size: 14px;
        padding: 4px 12px;
        height: auto;
        background-color: var(--gray-200);
        border: none;
        color: var(--gray-800);

        &:hover {
          color: var(--main-color);
        }
      }
    }
  }

  .query-test {
    display: flex;
    flex-direction: column;
    border-radius: 12px;
    gap: 20px;

    .results-overview {
      background-color: #fff;
      border-radius: 8px;
      padding: 16px;
      border: 1px solid var(--main-light-3);

      .results-stats {
        display: flex;
        justify-content: flex-start;

        .stat-item {
          border-radius: 4px;
          font-size: 14px;
          margin-right: 24px;
          padding: 4px 8px;
          strong {
            color: var(--main-color);
            margin-right: 4px;
          }
        }
      }

      .rewritten-query {
        border-radius: 4px;
        font-size: 14px;
        padding: 4px 8px;
        strong {
          color: var(--main-color);
          margin-right: 8px;
        }

        .query-text {
          font-style: italic;
          color: var(--gray-900);
        }
      }
    }

    .query-result-card {
      padding: 20px;
      border-radius: 8px;
      background: #fff;
      border: 1px solid var(--main-light-3);
      transition: box-shadow 0.3s ease;

      &:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      }

      p {
        margin-bottom: 8px;
        line-height: 1.6;
        color: var(--gray-900);

        &:last-child {
          margin-bottom: 0;
        }
      }

      strong {
        color: var(--main-color);
      }

      .query-text {
        font-size: 15px;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid var(--main-light-3);
      }
    }
  }
}

.upload {
  margin-bottom: 20px;
  .upload-dragger {
    margin: 0px;
  }
}

.my-table {
  button.ant-btn-link {
    padding: 0;
  }

  .span-type {
    color: white;
    padding: 2px 4px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: bold;
    opacity: 0.8;
    user-select: none;
    background: #005F77;
  }

  .pdf {
    background: #005F77;
  }

  .txt {
    background: #068033;
  }

  .docx, .doc {
    background: #2C59B7;
  }

  .md {
    background: #020817;
  }



  button.main-btn {
    font-weight: bold;
    font-size: 14px;
    &:hover {
      cursor: pointer;
      color: var(--main-color);
      font-weight: bold;
    }
  }

  button.del-btn {
    cursor: pointer;

    &:hover {
      color: var(--error-color);
    }
    &:disabled {
      cursor: not-allowed;
    }
  }
}

.custom-class .line-text {
  padding: 10px;
  border-radius: 4px;

  &:hover {
    background-color: var(--main-light-4);
  }
}

.upload-section {
  display: flex;
  gap: 20px;

  .upload-sidebar {
    width: 280px;
    padding: 20px;
    background-color: var(--main-light-6);
    border-radius: 8px;
    border: 1px solid var(--main-light-3);
    // box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);

    .chunking-params {
      h4 {
        margin-top: 0;
        margin-bottom: 16px;
        color: var(--main-color);
        font-size: 18px;
        text-align: center;
        font-weight: bold;
        padding-bottom: 10px;
        border-bottom: 1px dashed var(--main-light-3);
      }

      .params-info {
        background-color: var(--main-light-4);
        border-radius: 6px;
        padding: 10px 12px;
        margin-bottom: 16px;

        p {
          margin: 0;
          font-size: 13px;
          line-height: 1.5;
          color: var(--gray-700);
        }
      }

      .ant-form-item {
        margin-bottom: 16px;

        .ant-form-item-label {
          padding-bottom: 6px;

          label {
            color: var(--gray-800);
            font-weight: 500;
            font-size: 15px;
          }
        }
      }

      .ant-input-number {
        width: 100%;
        border-radius: 6px;

        &:hover, &:focus {
          border-color: var(--main-color);
        }
      }

      .ant-switch {
        background-color: var(--gray-400);

        &.ant-switch-checked {
          background-color: var(--main-color);
        }
      }

      // 添加参数说明
      .param-description {
        color: var(--gray-600);
        font-size: 12px;
        margin-top: 4px;
        margin-bottom: 0;
      }
    }
  }

  .upload-main {
    flex: 1;
  }
}

.chunk-preview {
  margin-top: 20px;

  .preview-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h3 {
      margin: 0;
      color: var(--main-color);
      font-size: 18px;
    }
  }

  .result-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(600px, 1fr));
    gap: 12px;
    margin-top: 10px;
  }

  .chunk {
    background-color: var(--main-light-5);
    border: 1px solid var(--main-light-3);
    border-radius: 8px;
    padding: 16px;
    word-wrap: break-word;
    word-break: break-all;
    transition: all 0.2s ease;

    &:hover {
      background-color: var(--main-light-4);
      border-color: var(--main-light-2);
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
    }

    p {
      margin: 0;
      line-height: 1.6;

      strong {
        color: var(--main-color);
        margin-right: 6px;
      }
    }
  }
}
</style>

<style lang="less">
.atab-container {
  padding: 0;
  width: 100%;
  max-height: 100%;
  overflow: auto;

  div.ant-tabs-nav {
    background: var(--main-light-5);
    padding: 8px 20px;
    padding-bottom: 0;
  }

  .ant-tabs-content-holder {
    padding: 0 20px;
  }
}

.params-item.col .ant-segmented {
  width: 100%;

  div.ant-segmented-group {
    display: flex;
    justify-content: space-around;
  }
}

</style>

<style lang="less">
.db-main-container {
  .atab-container {
    padding: 0;
    width: 100%;
    max-height: 100%;
    overflow: auto;

    div.ant-tabs-nav {
      background: var(--main-light-5);
      padding: 8px 20px;
      padding-bottom: 0;
    }

    .ant-tabs-content-holder {
      padding: 0 20px;
    }
  }

  .params-item.col .ant-segmented {
    width: 100%;
    font-size: smaller;
    div.ant-segmented-group {
      display: flex;
      justify-content: space-around;
    }
    label.ant-segmented-item {
      flex: 1;
      text-align: center;
      div.ant-segmented-item-label > div > p {
        font-size: small;
      }
    }
  }
}


</style>

