from sqlalchemy import Column, Integer, String, DateTime, JSON, func, ForeignKey, CHAR

from sqlalchemy.orm import relationship
from server.db.base import Base


class KnowledgeBaseModel(Base):
    """
    知识库模型
    """
    __tablename__ = 'knowledge_base'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='知识库ID')
    kb_name = Column(String(50), comment='知识库名称')
    kb_info = Column(String(200), comment='知识库简介(用于Agent)')
    vs_type = Column(String(50), comment='向量库类型')
    embed_model = Column(String(50), comment='嵌入模型名称')
    file_count = Column(Integer, default=0, comment='文件数量')
    create_time = Column(DateTime, default=func.now(), comment='创建时间')
    user_id = Column(CHAR(36), ForeignKey('user.id'), nullable=False, comment='用户ID')  # 新增的外键字段

    user = relationship('UserModel', back_populates='knowledge_bases')  # 新增的关系

    def __repr__(self):
        return (f"<KnowledgeBase(id='{self.id}', kb_name='{self.kb_name}', kb_info='{self.kb_info}', "
                f"vs_type='{self.vs_type}', embed_model='{self.embed_model}', file_count='{self.file_count}', "
                f"create_time='{self.create_time}', user_id='{self.user_id}')>")