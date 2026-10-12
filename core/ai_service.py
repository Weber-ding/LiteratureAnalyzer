import json
from openai import OpenAI


class AIService:
    def __init__(self, endpoint, api_key, model):
        self.client = OpenAI(base_url=endpoint, api_key=api_key)
        self.model = model
        self.prompt_template = ""

    def set_prompt_template(self, template):
        self.prompt_template = template

    def analyze(self, title, content, callback=None):
        prompt_text = self.prompt_template.replace("{CONTENT}", content[:80000])
        if not prompt_text:
            prompt_text = content[:80000]

        messages = [
            {"role": "system", "content": "你是专业的生物医学文献分析助手。请用中文输出分析结果。"},
            {"role": "user", "content": prompt_text}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=8192,
                timeout=120
            )
            result = response.choices[0].message.content
            if callback:
                callback(title, True, result, "")
            return result
        except Exception as e:
            err_msg = str(e)
            if callback:
                callback(title, False, "", err_msg)
            raise e
