PROMPT_TEMPLATES = {
    "general_chat": {
        "chat_with_history":
            '你可以根据用户之前的对话和提出的当前问题，提供专业和详细的技术答案。\n\n'
            '角色：宝可梦知识专家\n'
            '目标：能够结合历史聊天记录，提供专业、准确、详细的解释，增强回答的相关性和个性化。\n'
            '输出格式：详细的文本解释，包括人物、背景、事件等。\n'
            '工作流程：\n'
            '  2. 分析用户当前问题：提取关键信息。\n'
            '  3. 如果存在历史聊天记录，请结合历史聊天记录和当前问题提供个性化的技术回答。\n'
            '  4. 如果问题与宝可梦无关，以正常方式回应。\n\n'
            '历史聊天记录:\n'
            '{history}\n'
            '当前问题：\n'
            '{input}\n'
    },

    "knowledge_base_chat": {
        "chat_with_retrieval":
            '<指令>根据已知信息，简洁和专业的来回答问题。如果无法从中得到答案，请说 “根据已知信息无法回答该问题”，'
            '不允许在答案中添加编造成分，答案请使用中文。 同时，你还需要结合用户的历史聊天信息整体性的回答用户当前的问题。</指令>\n'
            '<历史对话信息>{{ history }}</历史对话信息>\n'
            '<已知信息>{{ context }}</已知信息>\n'
            '<问题>{{ question }}</问题>\n',

        "empty":  # 搜不到知识库的时候使用
            '请你回答我的问题:\n'
            '{{ question }}\n\n',
    },

    "real_time_search": {
        "chat_with_search":
            '<指令>根据你实时联网检索到的信息（这是用户问题联网搜索到的答案），回答用户的问题，你的回答必须基于联网检索到的信息。'
            '同时，如果存在历史对话信息，请结合历史对话信息提供完整的回复，'
            '不允许在答案中添加编造成分，答案请使用中文。 </指令>\n'
            '<历史对话信息>{{ history }}</历史对话信息>\n'
            '<联网检索到的信息>{{ context }}</联网检索到的信息>\n'
            '<问题>{{ question }}</问题>\n',

        # 联网检索不到答案时选择（不太可能）
        "empty":
            '请你回答我的问题:\n'
            '{{ question }}\n\n',
    },
    
    "neo4j_chat": {
        "chat_with_history":
            '你必须需要结合从neo4j中查询到的数据，给出合理的答案。\n\n'
            '历史聊天记录:\n'
            '{history}\n'
            '从neo4j中查询到的数据，这个就是答案，你只需要将该内容重写为人们更容易理解的话即可：\n'
            '{context}\n'
            '当前问题：\n'
            '{input}\n'
    },

    "recommend_base_chat": {
        "chat_with_recommend":
            '{{ input }}',
    },

    "agent_chat": {
        "default":
            'Answer the following questions as best you can. If it is in order, you can use some tools appropriately. '
            'You have access to the following tools:\n\n'
            '{tools}\n\n'
            'Use the following format:\n'
            'Question: the input question you must answer1\n'
            'Thought: you should always think about what to do and what tools to use.\n'
            'Action: the action to take, should be one of [{tool_names}]\n'
            'Action Input: the input to the action\n'
            'Observation: the result of the action\n'
            '... (this Thought/Action/Action Input/Observation can be repeated zero or more times)\n'
            'Thought: I now know the final answer\n'
            'Final Answer: the final answer to the original input question\n'
            'Begin!\n\n'
            'history: {history}\n\n'
            'Question: {input}\n\n'
            'Thought: {agent_scratchpad}\n',

        "ChatGLM3":
            'You can answer using the tools, or answer directly using your knowledge without using the tools. '
            'Respond to the human as helpfully and accurately as possible.\n'
            'You have access to the following tools:\n'
            '{tools}\n'
            'Use a json blob to specify a tool by providing an action key (tool name) '
            'and an action_input key (tool input).\n'
            'Valid "action" values: "Final Answer" or  [{tool_names}]'
            'Provide only ONE action per $JSON_BLOB, as shown:\n\n'
            '```\n'
            '{{{{\n'
            '  "action": $TOOL_NAME,\n'
            '  "action_input": $INPUT\n'
            '}}}}\n'
            '```\n\n'
            'Follow this format:\n\n'
            'Question: input question to answer\n'
            'Thought: consider previous and subsequent steps\n'
            'Action:\n'
            '```\n'
            '$JSON_BLOB\n'
            '```\n'
            'Observation: action result\n'
            '... (repeat Thought/Action/Observation N times)\n'
            'Thought: I know what to respond\n'
            'Action:\n'
            '```\n'
            '{{{{\n'
            '  "action": "Final Answer",\n'
            '  "action_input": "Final response to human"\n'
            '}}}}\n'
            'Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary. '
            'Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation:.\n'
            'history: {history}\n\n'
            'Question: {input}\n\n'
            'Thought: {agent_scratchpad}',
    }
}
