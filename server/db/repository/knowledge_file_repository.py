from server.db.models.knowledge_base_model import KnowledgeBaseModel
from server.db.models.knowledge_file_model import KnowledgeFileModel, FileDocModel
from server.knowledge_base.utils import KnowledgeFile
from typing import List, Dict

from server.db.session import with_async_session, async_session_scope


from sqlalchemy.future import select
from sqlalchemy import delete

@with_async_session
async def list_file_num_docs_id_by_kb_name_and_file_name(session,
                                                   kb_name: str,
                                                   file_name: str,
                                                   ) -> List[int]:
    '''
    列出某知识库某文件对应的所有Document的id。
    返回形式：[str, ...]
    '''
    stmt = select(FileDocModel.doc_id).where(
        FileDocModel.kb_name == kb_name,
        FileDocModel.file_name == file_name
    )
    
    # 执行异步查询
    result = await session.execute(stmt)
    
    # 获取结果并转换为整数列表
    doc_ids = [int(doc_id) for doc_id in result.scalars()]
    return doc_ids

@with_async_session
async def list_docs_from_db(
    session,
    kb_name: str,
    file_name: str = None,
    metadata: Dict = {},
) -> List[Dict]:
    """
    列出某知识库某文件对应的所有Document。
    返回形式：[{"id": str, "metadata": dict}, ...]
    """

    stmt = select(FileDocModel).where(FileDocModel.kb_name.ilike(kb_name))

    if file_name:
        stmt = stmt.where(FileDocModel.file_name.ilike(file_name))

    for k, v in metadata.items():
        # 假设 metadata 是 JSON 类型字段，可以使用 .astext 来提取字符串值
        stmt = stmt.where(FileDocModel.meta_data[k].astext == str(v))

    result = await session.execute(stmt)
    docs = result.scalars().all()

    return [{"id": doc.doc_id, "metadata": doc.metadata} for doc in docs]


@with_async_session
async def delete_docs_from_db(session,
                              kb_name: str,
                              file_name: str = None) -> List[Dict]:
    '''
    删除某知识库某文件对应的所有Document，并返回被删除的Document。
    返回形式：[{"id": str, "metadata": dict}, ...]
    '''

    print("检测到数据库中有同名的，我现在要开始执行删除指令了！！！！！")

    # 获取文档列表
    docs = await list_docs_from_db(kb_name=kb_name, file_name=file_name)

    # 构造删除语句
    stmt = delete(FileDocModel).where(FileDocModel.kb_name.ilike(kb_name))
    if file_name:
        stmt = stmt.where(FileDocModel.file_name.ilike(file_name))

    # 执行删除操作
    await session.execute(stmt)
    
    # 提交事务
    await session.commit()

    return docs


@with_async_session
async def add_docs_to_db(session,
                   kb_name: str,
                   file_name: str,
                   doc_infos: List[Dict]):
    '''
    将某知识库某文件对应的所有Document信息添加到数据库。
    doc_infos形式：[{"id": str, "metadata": dict}, ...]
    '''
    # ! 这里会出现doc_infos为None的情况，需要进一步排查
    if doc_infos is None:
        print("输入的server.db.repository.knowledge_file_repository.add_docs_to_db的doc_infos参数为None")
        return False
    try:
        for doc_info in doc_infos:
            obj = FileDocModel(
                kb_name=kb_name,
                file_name=file_name,
                doc_id=doc_info['id'],
                meta_data=doc_info['metadata'],
            )
            session.add(obj)
        await session.commit()
        print("文档信息成功添加到数据库")
        return True
    except Exception as e:
        print(f"在添加文档信息时发生错误: {e}")
        await session.rollback()
        return False


@with_async_session
async def count_files_from_db(session, kb_name: str) -> int:
    return session.query(KnowledgeFileModel).filter(KnowledgeFileModel.kb_name.ilike(kb_name)).count()


@with_async_session
async def list_files_from_db(session, kb_name):
    files = session.query(KnowledgeFileModel).filter(KnowledgeFileModel.kb_name.ilike(kb_name)).all()
    docs = [f.file_name for f in files]
    return docs


@with_async_session
async def add_file_to_db(session,
                         kb_file: KnowledgeFile,
                         docs_count: int = 0,
                         custom_docs: bool = False,
                         doc_infos: List[Dict] = [],  # 形式：[{"id": str, "metadata": dict}, ...]
                         ):
    """
    将文件添加到数据库中。如果文件已经存在，则更新文件信息和版本号。

    参数：
        session: 数据库会话对象。
        kb_file: 知识文件对象，包含文件的相关信息。
        docs_count: 文档数量。
        custom_docs: 是否为自定义文档。
        doc_infos: 文档信息列表，形式为：[{"id": str, "metadata": dict}, ...]
        user_id: 用户ID，默认为"default_user_id"。

    返回：
        bool: 如果操作成功，返回True。
    """

    print("开始查询 KnowledgeBase...")
    stmt = select(KnowledgeBaseModel).where(KnowledgeBaseModel.kb_name == kb_file.kb_name)
    kb_result = await session.execute(stmt)
    kb = kb_result.scalars().first()


    if kb:
        print("KnowledgeBase 存在，开始查询 KnowledgeFile...")
        stmt = select(KnowledgeFileModel).where(
            KnowledgeFileModel.kb_name.ilike(kb_file.kb_name),
            KnowledgeFileModel.file_name.ilike(kb_file.filename)
        )
        file_result = await session.execute(stmt)
        existing_file = file_result.scalars().first()
        print(f"查询 KnowledgeFile 完成: {existing_file}")

        mtime = kb_file.get_mtime()
        size = kb_file.get_size()
        print(f"获取文件时间和大小：mtime={mtime}, size={size}")

        if existing_file:
            print("文件存在，更新文件信息...")
            existing_file.file_mtime = mtime
            existing_file.file_size = size
            existing_file.docs_count = docs_count
            existing_file.custom_docs = custom_docs
            existing_file.file_version += 1
            print("文件信息更新完成")
        else:
            print("文件不存在，创建新文件...")
            new_file = KnowledgeFileModel(
                file_name=kb_file.filename,
                file_ext=kb_file.ext,
                kb_name=kb_file.kb_name,
                document_loader_name=kb_file.document_loader_name,
                text_splitter_name=kb_file.text_splitter_name or "SpacyTextSplitter",
                file_mtime=mtime,
                file_size=size,
                docs_count=docs_count,
                custom_docs=custom_docs,
            )
            session.add(new_file)
            kb.file_count += 1
            print("新文件添加完成")

        print("开始添加文档信息...")
        await add_docs_to_db(kb_name=kb_file.kb_name, file_name=kb_file.filename, doc_infos=doc_infos)

        print("文档信息添加完成")

        try:
            print("开始提交事务...")
            await session.commit()
            print("事务提交成功")
        except Exception as e:
            print(f"Error committing changes: {e}")
            await session.rollback()
            print("事务回滚")
            raise
    else:
        print("KnowledgeBase 不存在，无法添加文件")
    return True


@with_async_session
async def delete_file_from_db(session, kb_file: KnowledgeFile):
    try:
        # 1. 查询要删除的文件记录
        file_query = await session.execute(
            select(KnowledgeFileModel)
            .where(
                KnowledgeFileModel.file_name.ilike(kb_file.filename),
                KnowledgeFileModel.kb_name.ilike(kb_file.kb_name)
            )
        )
        existing_file = file_query.scalars().first()
        print("existing_file :", existing_file)
        if not existing_file:
            return False

        # 2. 删除关联文档记录
        await delete_docs_from_db(kb_name=kb_file.kb_name, file_name=kb_file.filename)

        # 3. 删除文件记录
        await session.delete(existing_file)

        # 4. 更新知识库文件计数
        kb_query = await session.execute(
            select(KnowledgeBaseModel)
            .where(KnowledgeBaseModel.kb_name.ilike(kb_file.kb_name))
        )
        kb = kb_query.scalars().first()
        
        if kb:
            kb.file_count = max(0, kb.file_count - 1)  # 确保不小于0

        # 5. 提交事务
        await session.commit()
        return True

    except Exception as e:
        print(e)
        await session.rollback()
        return False


@with_async_session
async def delete_files_from_db(session, knowledge_base_name: str):
    # 删除 KnowledgeFileModel 中对应 kb_name 的记录
    stmt1 = delete(KnowledgeFileModel).where(
        KnowledgeFileModel.kb_name.ilike(knowledge_base_name)
    )
    await session.execute(stmt1)

    # 删除 FileDocModel 中对应 kb_name 的记录
    stmt2 = delete(FileDocModel).where(
        FileDocModel.kb_name.ilike(knowledge_base_name)
    )
    await session.execute(stmt2)

    # 查询 KnowledgeBaseModel 中对应的 kb_name 记录
    stmt3 = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.kb_name.ilike(knowledge_base_name)
    )
    result = await session.execute(stmt3)
    kb = result.scalars().first()

    if kb:
        kb.file_count = 0
        session.add(kb)  # 确保更改被加入会话

    await session.commit()  # 异步提交事务
    return True


@with_async_session
async def file_exists_in_db(session, kb_file: KnowledgeFile):
    stmt = (
        select(KnowledgeFileModel)
        .where(
            KnowledgeFileModel.file_name.ilike(kb_file.filename),
            KnowledgeFileModel.kb_name.ilike(kb_file.kb_name)
        )
    )
    result = await session.execute(stmt)
    existing_file = result.scalars().first()
    return existing_file is not None


@with_async_session
async def get_file_detail(session, kb_name: str, filename: str) -> dict:
    result = await session.execute(
        select(KnowledgeFileModel)
        .filter(KnowledgeFileModel.kb_name == kb_name)
        .filter(KnowledgeFileModel.file_name == filename)
    )
    file = result.scalars().first()
    if file:
        return {
            "kb_name": file.kb_name,
            "file_name": file.file_name,
            "file_ext": file.file_ext,
            "file_version": file.file_version,
            "document_loader": file.document_loader_name,
            "text_splitter": file.text_splitter_name,
            "create_time": file.create_time,
            "file_mtime": file.file_mtime,
            "file_size": file.file_size,
            "custom_docs": file.custom_docs,
            "docs_count": file.docs_count,
        }
    else:
        return {}