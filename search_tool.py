import requests
from bs4 import BeautifulSoup
import urllib.parse

class SearchTool:
    @staticmethod
    def search(query, max_results=5, cookie=None):
        """
        使用 Bing 国内版进行联网搜索
        """
        if not query:
            return ""

        optimized_query = query.strip()
        encoded_query = urllib.parse.quote(optimized_query, encoding='utf-8')
        url = f"https://cn.bing.com/search?q={encoded_query}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://cn.bing.com/"
        }
        
        if cookie:
            headers["Cookie"] = cookie
        
        results_text = f"【联网搜索结果 (关键词: {optimized_query})】:\n"
        
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=True)
            if response.status_code != 200:
                return f"[联网搜索失败: HTTP {response.status_code}]"

            soup = BeautifulSoup(response.text, 'html.parser')
            count = 0
            
            # 策略 A: 精选答案
            featured = soup.select_one('.b_entityTP, .b_ans, .b_focusText, .rwrl_padref, .b_algoM')
            if featured:
                text = featured.get_text(strip=True)
                if len(text) > 10:
                    results_text += f"[★ 精选答案]: {text}\n\n"
                    count += 1

            # 策略 B: 常规列表
            results = soup.select('#b_results > li.b_algo')
            
            for item in results:
                if count >= max_results: break
                
                title_tag = item.select_one('h2 a')
                if not title_tag: continue
                
                title = title_tag.get_text().strip()
                href = title_tag.get('href')
                
                # 简单过滤广告或无关内容
                if "广告" in item.get_text(): continue

                snippet = "无摘要"
                snippet_tag = item.select_one('.b_caption p, .b_snippet, .b_algoSlug, .b_lx')
                if snippet_tag:
                    snippet = snippet_tag.get_text().strip()

                results_text += f"{count + 1}. 标题: {title}\n"
                results_text += f"   链接: {href}\n"
                results_text += f"   摘要: {snippet}\n\n"
                count += 1
            
            if count == 0:
                return f"[未找到有效结果] 请检查 Bing Cookie 是否过期。"

        except Exception as e:
            return f"[联网搜索出错: {str(e)}]"
            
        return results_text