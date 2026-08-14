import json
import re


def extract_json(text):
    """从LLM回复原文中提取合法JSON字符串，提取失败返回None。"""
    if not isinstance(text, str) or not text.strip():
        return None

    text = text.strip()

    # 去掉 markdown 代码块围栏 (```json ... ``` 或 ``` ... ```)
    fenced = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        re.S
    )
    if fenced:
        text = fenced.group(1).strip()

    # 整体直接可解析
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # 截取首个完整 {...} 或 [...] 片段
    for start_ch, end_ch in (("{", "}"), ("[", "]")):
        start = text.find(start_ch)
        if start == -1:
            continue
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == start_ch:
                depth += 1
            elif c == end_ch:
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        break
    return None


def parse_llm_json(response, validator=None):
    """解析LLM回复为JSON对象；提取/解析/校验任一失败则抛出ValueError。"""
    candidate = extract_json(response)
    if candidate is None:
        raise ValueError("未从LLM回复中提取到JSON")

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {e}")

    if validator is not None:
        try:
            valid = validator(data)
        except Exception as e:
            raise ValueError(f"JSON结构校验异常: {e}")
        if not valid:
            raise ValueError("JSON未通过结构校验")

    return data