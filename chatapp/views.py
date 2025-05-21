import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
from collections import Counter

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_time

from openai import OpenAI
from .models import EmotionRecord, ChatLog, DailySummary

# ✅ 환경 변수 로딩
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ KoBERT 감정 분석 API 설정
KOBERT_API_URL = "https://dat-feet-valley-notified.trycloudflare.com"
valid_labels = {'기쁨', '당황', '분노', '불안', '상처', '슬픔'}
emotion_aliases = {
    '화남': '분노', '짜증': '분노', '우울': '슬픔', '놀람': '당황',
    '공포': '불안', '행복': '기쁨', '분노 ': '분노',
    '불안감': '불안', 'unknown': '알 수 없음'
}

# ✅ 감정 라벨 매핑 함수
def map_emotion(label):
    cleaned = label.strip()
    mapped = emotion_aliases.get(cleaned, cleaned)
    return mapped if mapped in valid_labels else '알 수 없음'

# ✅ KoBERT 감정 분석 함수
def analyze_sentiment_kobert(text):
    try:
        res = requests.post(KOBERT_API_URL, json={"text": text})
        if res.status_code == 200:
            label = res.json().get("label", "unknown")
            emotion = map_emotion(label)
            print("🧪 KoBERT 응답:", emotion)
            return emotion
        else:
            print("❌ KoBERT 오류 응답:", res.status_code)
            return "알 수 없음"
    except Exception as e:
        print("❌ KoBERT 요청 실패:", e)
        return "알 수 없음"

# ✅ 상태 변수 (비회원용 히스토리 저장용)
chat_history = []
emotion_history = []
current_summary = ""

# ✅ 메인 페이지
def index(request):
    return render(request, "chatapp/index.html")

# ✅ 감정 분석 + GPT 응답 API
@csrf_exempt
def chat_api(request):
    global chat_history, emotion_history, current_summary

    if request.method == "POST":
        try:
            body = json.loads(request.body)
            prompt = body.get("prompt", "")
            coach_role = body.get("coachRole", "")

            # 감정 분석
            emotion = analyze_sentiment_kobert(prompt)
            timestamp = datetime.now().strftime("%p %I:%M:%S")  # 오전/오후 시간 문자열
            emotion_history.append({"timestamp": timestamp, "sentiment": emotion})

            # 시스템 메시지 첫 회차만 삽입
            if not chat_history:
                system_msg = coach_role + " 시작은 항상 반말로 말해줘. 친구처럼 편하게 대화해줘. 대답은 간결하게, 부담스럽지 않게."
                chat_history.append({"role": "system", "content": system_msg})

            chat_history.append({"role": "user", "content": prompt})

            # GPT 응답 생성
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=chat_history,
                temperature=0.9,
                max_tokens=1024
            )
            reply = response.choices[0].message.content.strip()
            chat_history.append({"role": "assistant", "content": reply})
            current_summary += f"사용자: {prompt}\n불안핑: {reply}\n"

            return JsonResponse({"response": reply, "sentiment": emotion})

        except Exception as e:
            print("❌ chat 오류:", e)
            return JsonResponse({"response": "문제가 발생했어. 다시 시도해볼래?"}, status=500)

# ✅ 요약 페이지 (회원은 DB 저장, 비회원은 그냥 출력)
@csrf_exempt
def summary(request):
    global current_summary, emotion_history

    if request.method == "POST":
        try:
            body = json.loads(request.body)
            chat_log = body.get("chatLog", [])
            emotion_data = body.get("emotionHistory", [])
            now = datetime.now().date()

            # ✅ 회원인 경우 DB에 저장
            if request.user.is_authenticated:
                for record in emotion_data:
                    EmotionRecord.objects.create(
                        user=request.user,
                        date=now,
                        timestamp=parse_time(record["timestamp"]) or datetime.now().time(),
                        sentiment=record["sentiment"]
                    )
                for entry in chat_log:
                    ChatLog.objects.create(
                        user=request.user,
                        date=now,
                        sender=entry["sender"],
                        message=entry["message"]
                    )

            # GPT 요약 생성
            dialogue = "\n".join([f"{msg['sender']}: {msg['message']}" for msg in chat_log])
            prompt = f"""
다음은 사용자와 감정 공감 챗봇 '불안핑'의 대화입니다.
대화 내용을 바탕으로 사용자의 감정을 짧고 따뜻하게 요약해주세요.
[대화]
{dialogue}
"""
            summary_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "너는 감정을 공감하고 요약하는 AI 챗봇이야."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            summary_text = summary_response.choices[0].message.content.strip()

            # 회원인 경우 요약 저장
            if request.user.is_authenticated:
                DailySummary.objects.create(user=request.user, date=now, summary=summary_text)

            return render(request, "chatapp/summary.html", {
                "summary": summary_text,
                "emotion_history": emotion_data
            })

        except Exception as e:
            print("❌ 요약 오류:", e)
            return render(request, "chatapp/summary.html", {
                "summary": "요약 중 오류가 발생했어요.",
                "emotion_history": emotion_history
            })

    else:
        return render(request, "chatapp/summary.html", {
            "summary": current_summary,
            "emotion_history": emotion_history
        })

# ✅ 감정일지 목록
@login_required
def journal_list(request):
    summaries = DailySummary.objects.filter(user=request.user).order_by('-date')
    return render(request, "chatapp/journal_list.html", {"summaries": summaries})

# ✅ 감정일지 상세 (timestamp를 문자열로 변환해서 전달)
@login_required
def journal_detail(request, date):
    summary = DailySummary.objects.filter(user=request.user, date=date).first()
    emotions = EmotionRecord.objects.filter(user=request.user, date=date).order_by('timestamp')

    # ✅ timestamp를 문자열로 변환
    emotion_list = [
        {
            "timestamp": e.timestamp.strftime("%p %I:%M:%S"),
            "sentiment": e.sentiment
        }
        for e in emotions
    ]

    # ✅ 감정 개수 카운트 (선택적 시각화용)
    counter = Counter([e["sentiment"] for e in emotion_list])
    chart_labels = list(counter.keys())
    chart_values = list(counter.values())

    return render(request, "chatapp/journal_detail.html", {
        "summary": summary.summary if summary else "요약 없음",
        "emotion_history": emotion_list,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "date": date
    })
