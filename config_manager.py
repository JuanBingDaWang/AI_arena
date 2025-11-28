import json
import os
import sys

class ConfigManager:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.config_file = os.path.join(self.base_dir, "config.json")
        self.default_config = {
            "api_keys": [],     # 变更为列表
            "current_key_index": 0, # 记录当前选中的是第几个
            "bing_cookie": "", 
            "theme": {
                "background_color": "#2b2b2b",
                "text_color": "#ffffff",
                "font_size": 14
            },
            "window_state": {
                "x": 100, "y": 100, "width": 1200, "height": 800
            },
            "presets": [],
            "user_prompt_presets": [], 
            "last_session": {},
            "vision_models": [
                "Qwen/Qwen2-VL-72B-Instruct",
                "Qwen/Qwen2-VL-7B-Instruct",
                "meta-llama/Llama-3.2-11B-Vision-Instruct",
                "meta-llama/Llama-3.2-90B-Vision-Instruct"
            ]
        }
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file):
            return self.default_config.copy()
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # --- 兼容性迁移：将旧版单字符串 api_key 转换为列表 ---
                if "api_key" in data and isinstance(data["api_key"], str):
                    if data["api_key"] and "api_keys" not in data:
                        data["api_keys"] = [data["api_key"]]
                    del data["api_key"] # 删除旧字段
                
                # 补全缺失配置
                for key, value in self.default_config.items():
                    if key not in data:
                        data[key] = value
                return data
        except Exception as e:
            print(f"配置加载失败: {e}")
            return self.default_config.copy()

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

    # --- API Key 管理方法 ---
    def get_api_keys(self):
        return self.config.get("api_keys", [])

    def add_api_key(self, key):
        if key and key not in self.config["api_keys"]:
            self.config["api_keys"].append(key)
            self.save_config()

    def remove_api_key(self, index):
        keys = self.config["api_keys"]
        if 0 <= index < len(keys):
            keys.pop(index)
            self.config["api_keys"] = keys
            self.save_config()

    def get_current_key_index(self):
        return self.config.get("current_key_index", 0)

    def set_current_key_index(self, index):
        self.config["current_key_index"] = index
        self.save_config()

    # --- 其他 Getter / Setter (保持不变) ---
    
    def get_bing_cookie(self): return self.config.get("bing_cookie", "")
    def set_bing_cookie(self, cookie_str):
        self.config["bing_cookie"] = cookie_str.strip()
        self.save_config()

    def get_theme(self): return self.config.get("theme", self.default_config["theme"])
    def set_theme(self, bg, fg, size):
        self.config["theme"] = {"background_color": bg, "text_color": fg, "font_size": size}
        self.save_config()

    def get_window_state(self): return self.config.get("window_state", self.default_config["window_state"])
    def set_window_state(self, x, y, w, h):
        self.config["window_state"] = {"x": x, "y": y, "width": w, "height": h}
        self.save_config()
        
    def get_vision_models(self): return self.config.get("vision_models", [])

    def get_presets(self): return self.config.get("presets", [])
    def get_preset_names(self): return [p["name"] for p in self.get_presets()]
    
    def save_preset(self, name, judge_model, judge_params, judge_prompt, selected_models):
        new_preset = {
            "name": name,
            "judge_model": judge_model,
            "judge_params": judge_params,
            "judge_prompt": judge_prompt,
            "selected_models": selected_models
        }
        presets = self.get_presets()
        for i, p in enumerate(presets):
            if p["name"] == name:
                presets[i] = new_preset
                self.save_config()
                return
        presets.append(new_preset)
        self.config["presets"] = presets
        self.save_config()

    def get_preset_by_name(self, name):
        for p in self.get_presets():
            if p["name"] == name: return p
        return None
        
    def delete_current_preset(self, name):
        self.config["presets"] = [p for p in self.get_presets() if p["name"] != name]
        self.save_config()

    def get_user_presets(self): return self.config.get("user_prompt_presets", [])
    def get_user_preset_names(self): return [p["name"] for p in self.get_user_presets()]

    def save_user_preset(self, name, content):
        new_item = {"name": name, "content": content}
        presets = self.get_user_presets()
        for i, p in enumerate(presets):
            if p["name"] == name:
                presets[i] = new_item
                self.save_config()
                return
        presets.append(new_item)
        self.config["user_prompt_presets"] = presets
        self.save_config()

    def delete_user_preset(self, name):
        presets = self.get_user_presets()
        self.config["user_prompt_presets"] = [p for p in presets if p["name"] != name]
        self.save_config()

    def get_user_preset_content(self, name):
        for p in self.get_user_presets():
            if p["name"] == name: return p["content"]
        return ""

    def set_last_session(self, session_data):
        self.config["last_session"] = session_data
        self.save_config()

    def get_last_session(self): return self.config.get("last_session", {})