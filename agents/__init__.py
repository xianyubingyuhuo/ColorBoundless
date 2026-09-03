# -*- coding: utf-8 -*-
"""agents：多 Agent 模块（D2 铁律：LLM 只做语言层）

    prompt  全部 LLM 提示词与话术集中管理（三 Agent 系统提示词 +
            分诊话术/测试引导/安抚话术；{curly} 占位由业务代码 format 注入）
"""
from . import prompt

