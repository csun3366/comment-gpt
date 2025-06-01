import json
import os
import openai
import requests
from dotenv import load_dotenv
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
import cohere

co = cohere.Client('DSQb7a87LJxScaq86Nl1UDUWtbay61TdOiXFBVAC')
openrouter_key = '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'

def chat_with_openrouter(messages, model="deepseek/deepseek-r1:free"):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "my ai app"
    }

    data = {
        "model": model,
        "messages": messages
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def home(request):
    return render(request, 'home.html')

@csrf_exempt
def summarize_review(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    try:
        data = json.loads(request.body)
        place_name = data.get('place_name')

        # 步驟 1: 用文字搜尋找 place_id
        search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        search_params = {
            'input': place_name,
            'inputtype': 'textquery',
            'fields': 'place_id,name',
            'key': 'AIzaSyAgx03MCcyAhsgNBuhvXPMMzPGETm9ktMM'
        }
        search_resp = requests.get(search_url, params=search_params).json()
        candidates = search_resp.get('candidates', [])
        if not candidates:
            return JsonResponse({'error': '找不到店家'}, status=404)

        place_id = candidates[0]['place_id']

        # 步驟 2: 用 place_id 抓詳細資料（含評論）
        detail_url = "https://maps.googleapis.com/maps/api/place/details/json"
        detail_params = {
            'place_id': place_id,
            'fields': 'name,rating,user_ratings_total,reviews',
            'language': 'zh-TW',
            'key': 'AIzaSyAgx03MCcyAhsgNBuhvXPMMzPGETm9ktMM'
        }

        detail_resp = requests.get(detail_url, params=detail_params).json()
        reviews = detail_resp.get('result', {}).get('reviews', [])
        rating = detail_resp.get('result', {}).get("rating")
        total = detail_resp.get('result', {}).get("user_ratings_total")
        print('星星' + str(rating))
        print('評論數' + str(total))
        if not reviews or not rating or not total:
            return JsonResponse({'error': '此店家無評論'}, status=404)

        # 整理評論文字
        review_texts = [r['text'] for r in reviews if r.get('text')]
        prompt = f"請根據收集到的 Google 評論，幫我總結「{place_name}」的評價，幫我分別整理出這家店在 價格、服務、環境、其他 方面的優點與缺點，每項都要列出具體事例或說法，要用繁體中文評論，格式要是:💰價格：✅優點 ❌ 缺點，🛎️服務：✅優點 ❌ 缺點，🌳環境：✅優點 ❌ 缺點，🍽️其他：：✅優點 ❌ 缺點，請不要使用 ** 或 Markdown 粗體符號，直接用純文字輸出分類標題與說明\n\n"
        for r in review_texts:
            prompt += f"- {r.strip()}\n"
        print(prompt)
        # 步驟 3: 傳送給 OpenAI 進行摘要
        messages=[
            {"role": "system", "content": "你是一個中文評論分析專家"},
            {"role": "user", "content": prompt}
        ]
        reply = chat_with_openrouter(messages)
        print("AI 回答：", reply)
        return JsonResponse({'summary': reply, 'rating' : rating, 'total' : total})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
