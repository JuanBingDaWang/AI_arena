import requests
import json
import base64
import os
import mimetypes
import time  # 【新增】用于重试延迟
from requests.exceptions import RequestException, Timeout, ConnectionError # 【新增】捕获异常

# 仅尝试导入 docx 解析库，移除 pypdf, pandas, pptx
try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

class LLMClient:
    BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"

    @staticmethod
    def encode_image(image_path):
        """将图片文件转换为 Base64 字符串"""
        if not os.path.exists(image_path):
            return None
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    @staticmethod
    def parse_document(file_path):
        """
        解析本地文档为纯文本
        当前仅支持: .docx
        """
        ext = os.path.splitext(file_path)[1].lower()
        text_content = ""
        
        try:
            if ext == '.docx':
                if not HAS_DOCX:
                    return "[Error: 缺少 python-docx 库，无法解析 Word 文档]"
                doc = Document(file_path)
                text_content = "\n".join([para.text for para in doc.paragraphs])
            else:
                return f"[不支持的文件格式: {ext}]"
            
            return text_content.strip()
        except Exception as e:
            return f"[文件解析失败: {str(e)}]"

    @staticmethod
    def chat_completion(api_key, model_name, messages, file_paths=None, vision_models=None, **kwargs):
        """
        发送请求到 SiliconFlow API
        """
        if not api_key:
            return {"error": "API Key 未设置。"}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        final_messages = messages
        
        # --- 处理多文件逻辑 ---
        if file_paths and isinstance(file_paths, list) and len(file_paths) > 0:
            user_content_str = ""
            # 获取用户输入的文本内容
            if isinstance(messages[0]['content'], str):
                user_content_str = messages[0]['content']
            elif isinstance(messages[0]['content'], list):
                for item in messages[0]['content']:
                    if item.get('type') == 'text':
                        user_content_str += item.get('text', '')
            
            text_attachments = []
            image_objects = []

            for fpath in file_paths:
                if not os.path.exists(fpath): continue
                
                # 猜测 MIME 类型
                mime_type, _ = mimetypes.guess_type(fpath)
                if not mime_type: mime_type = "application/octet-stream"
                ext = os.path.splitext(fpath)[1].lower()
                fname = os.path.basename(fpath)

                # A. 图片处理 (SiliconFlow 原生支持)
                if mime_type.startswith('image/'):
                    b64 = LLMClient.encode_image(fpath)
                    if b64:
                        image_objects.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64}"}
                        })
                
                # B. Word 文档处理 (本地解析)
                elif ext == '.docx':
                    parsed_text = LLMClient.parse_document(fpath)
                    text_attachments.append(f"\n\n[附件文档: {fname}]:\n{parsed_text}")
                
                # C. 纯文本处理 (代码、TXT、Markdown等)
                else: 
                    # 尝试以 UTF-8 读取
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            raw_text = f.read()
                        text_attachments.append(f"\n\n[附件文本: {fname}]:\n{raw_text}")
                    except:
                        # 尝试 Latin-1 或跳过
                        try:
                            with open(fpath, 'r', encoding='latin-1') as f:
                                raw_text = f.read()
                            text_attachments.append(f"\n\n[附件文本: {fname}]:\n{raw_text}")
                        except:
                            text_attachments.append(f"\n\n[系统提示: 文件 {fname} 无法读取(非文本或编码不支持)]")

            full_text_prompt = user_content_str + "".join(text_attachments)

            # --- 模型视觉能力检查 ---
            is_vision_supported = False
            if vision_models:
                for v_model in vision_models:
                    if v_model in model_name: 
                        is_vision_supported = True
                        break
            
            # 构造最终的消息体
            if is_vision_supported and len(image_objects) > 0:
                new_content = [{"type": "text", "text": full_text_prompt}]
                new_content.extend(image_objects)
                final_messages = [{"role": "user", "content": new_content}]
            else:
                # 不支持视觉或没图片 -> 纯文本格式
                if len(image_objects) > 0 and not is_vision_supported:
                    full_text_prompt += "\n\n[系统提示: 检测到图片附件，但当前模型不支持视觉输入，已自动忽略图片。]"
                final_messages = [{"role": "user", "content": full_text_prompt}]

        payload = {
            "model": model_name,
            "messages": final_messages,
            "stream": False
        }

        allowed_params = ["temperature", "top_p", "max_tokens", "frequency_penalty"]
        for key, value in kwargs.items():
            if key in allowed_params and value is not None:
                if key == "max_tokens":
                    payload[key] = int(value)
                else:
                    payload[key] = value

        # 【修改重点】增加重试机制和延长超时时间
        MAX_RETRIES = 2  # 最大重试次数
        TIMEOUT_SECONDS = 300  # 超时时间设置为 300秒 (5分钟)

        for attempt in range(MAX_RETRIES + 1):
            try:
                # 尝试发送请求
                response = requests.post(LLMClient.BASE_URL, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        return {"content": data['choices'][0]['message']['content']}
                    else:
                        return {"error": f"API 结构异常: {data}"}
                else:
                    # 如果是 5xx 服务端错误，可以重试；如果是 4xx 客户端错误，直接返回
                    if 500 <= response.status_code < 600:
                        if attempt < MAX_RETRIES:
                            time.sleep(2) # 歇两秒再试
                            continue
                    return {"error": f"API Error {response.status_code}: {response.text}"}

            except (Timeout, ConnectionError) as e:
                # 捕获超时或连接错误
                print(f"Request failed (Attempt {attempt+1}/{MAX_RETRIES + 1}): {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(3) # 遇到网络问题，多歇一会
                    continue
                else:
                    return {"error": f"请求超时或网络连接失败 (已尝试{MAX_RETRIES+1}次): {str(e)}"}
            except RequestException as e:
                # 其他请求异常
                return {"error": f"请求异常: {str(e)}"}
            except Exception as e:
                return {"error": f"未知异常: {str(e)}"}