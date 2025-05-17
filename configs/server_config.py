import sys

# httpx 请求默认超时时间（秒）。如果加载模型或对话较慢，出现超时错误，可以适当加大该值。
HTTPX_DEFAULT_TIMEOUT = 300.0

# 各服务器默认绑定host。如改为"0.0.0.0"需要修改下方所有XX_SERVER的host
DEFAULT_BIND_HOST = "0.0.0.0" if sys.platform != "win32" else "127.0.0.1"

# api.py server
API_SERVER = {
    "host": DEFAULT_BIND_HOST,
    "port": 9999,
}

# Neo4j 服务器配置
NEO4J_SERVER = {
    "url": "neo4j://localhost:7687",  # Neo4j连接地址
    "username": "neo4j",              # 用户名
    "password": "woshishamo630",      # 密码
    "database": "neo4j",             # 数据库名（可选）
}
