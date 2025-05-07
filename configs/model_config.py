import os

MODEL_ROOT_PATH = ""

TEMPERATURE = 1.0
MAX_TOKENS = 4096
# 默认让大模型采用流式输出
STREAM = True

# 默认启动的模型，如果使用的是glm3-6b，请替换模型名称
LLM_MODELS = ["Doubao-pro-256k-1.5"]
MODEL_API_KEY = 'sk-36oMlDApF5Nlg0v23014A4B69e864000944151Cd75D82076'
MODEL_API_BASE = 'http://139.224.116.116:3000/v1'


# 选用的 Embedding 名称
EMBEDDING_MODEL = "bge-m3-pro"
EMBEDDING_DEVICE = "cuda"

# 是否启用reranker模型
USE_RERANKER = True
RERANKER_MODEL = "bge-reranker-v2-m3"
RERANKER_MAX_LENGTH = 1024
RERANKER_TOP_K = 3

# 搜索引擎匹配结题数量
SEARCH_ENGINE_TOP_K = 3
# 原始网页搜索结果筛选后保留的有效数量
SEARCH_RERANK_TOP_K = 8

URL = "https://google.serper.dev/search"
SERPER_API_KEY = '25e9d44471387624110f9d83e9a4e9c68136aad9'  # 这里替换为自己实际的Serper API Key