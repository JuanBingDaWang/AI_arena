from PyQt6.QtCore import QThread, pyqtSignal
from llm_client import LLMClient
from search_tool import SearchTool

class SearchWorker(QThread):
    """【新增】独立的搜索线程，防止界面卡死"""
    finished_signal = pyqtSignal(str)
    
    def __init__(self, query, max_results, cookie):
        super().__init__()
        self.query = query
        self.max_results = max_results
        self.cookie = cookie
        self._is_cancelled = False

    def run(self):
        if self._is_cancelled: return
        try:
            result = SearchTool.search(self.query, self.max_results, self.cookie)
            if not self._is_cancelled:
                self.finished_signal.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                self.finished_signal.emit(f"[搜索出错] {str(e)}")

    def stop(self):
        self._is_cancelled = True

class ArenaWorker(QThread):
    """参赛选手线程"""
    finished_signal = pyqtSignal(str, str, dict) 

    def __init__(self, api_key, model_config, user_prompt, file_paths=None, vision_models=None): 
        super().__init__()
        self.api_key = api_key
        self.model_config = model_config.copy()
        self.original_name = self.model_config.pop('name') 
        self.user_prompt = user_prompt
        self.file_paths = file_paths or []
        self.vision_models = vision_models or []
        self._is_cancelled = False

    def run(self):
        if self._is_cancelled: return

        messages = [{"role": "user", "content": self.user_prompt}]
        
        effective_name = self.model_config.get("custom_model_name")
        if not effective_name:
            effective_name = self.original_name

        # 调用 API
        response = LLMClient.chat_completion(
            self.api_key, 
            effective_name, 
            messages, 
            file_paths=self.file_paths,
            vision_models=self.vision_models,
            **self.model_config 
        )
        
        if self._is_cancelled: return

        content = response.get("content", "")
        error = response.get("error", None)
        
        if error:
            final_content = f"[Error] {error}"
        else:
            final_content = content
            
        self.finished_signal.emit(self.original_name, final_content, response)

    def stop(self):
        self._is_cancelled = True
        # requests 是阻塞的，简单的 stop 无法中断 socket
        # 但设置 flag 后，下载回来不会发射信号

class JudgeWorker(QThread):
    """裁判线程"""
    # 【修改点 1】信号类型改为 str，直接传输文本，不再传输字典
    result_signal = pyqtSignal(str) 

    def __init__(self, api_key, judge_model, judge_system_prompt, user_prompt, model_results):
        super().__init__()
        self.api_key = api_key
        self.judge_model = judge_model
        self.judge_system_prompt = judge_system_prompt
        self.user_prompt = user_prompt
        self.model_results = model_results
        self.judge_params = {"temperature": 0.2, "max_tokens": 4096} # 稍微调大token，因为不再是紧凑的json
        self._is_cancelled = False

    def run(self):
        if self._is_cancelled: return

        contestant_text = ""
        # 限制长度防止上下文爆炸
        MAX_CHAR_PER_MODEL = 6000 
        
        for name, text in self.model_results.items():
            if len(text) > MAX_CHAR_PER_MODEL:
                display_text = text[:MAX_CHAR_PER_MODEL] + "\n...(已截断)..."
            else:
                display_text = text
            contestant_text += f"\n=== 模型 [{name}] 的回答 ===\n{display_text}\n"

        final_user_content = (
            f"用户原始问题：\n{self.user_prompt}\n\n"
            f"以下是各参赛模型的回答，请根据 System Prompt 的要求进行评审、对比优缺点，并给出一个最佳的融合答案：\n"
            f"{contestant_text}"
        )

        # 【修改点 2】删除了 json_instruction 变量，不再强制 JSON 格式
        
        messages = [
            {"role": "system", "content": self.judge_system_prompt},
            {"role": "user", "content": final_user_content}
        ]

        effective_name = self.judge_params.get("custom_model_name")
        if not effective_name:
            effective_name = self.judge_model

        response = LLMClient.chat_completion(
            self.api_key, 
            effective_name,
            messages, 
            file_paths=None, 
            **self.judge_params 
        )
        
        if self._is_cancelled: return

        # 【修改点 3】不再解析 JSON，直接获取 content 文本
        if "error" in response:
            error_msg = f"裁判模型调用出错: {response['error']}"
            self.result_signal.emit(error_msg)
        else:
            raw_content = response.get("content", "[裁判未返回任何内容]")
            self.result_signal.emit(raw_content)

    # extract_json 方法已删除

    def stop(self):
        self._is_cancelled = True