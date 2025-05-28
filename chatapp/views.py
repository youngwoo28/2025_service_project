import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
from collections import Counter

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_time

import openai
from .models import EmotionRecord, ChatLog, DailySummary

# 환경 변수 로딩 및 OpenAI API 키 설정
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# KoBERT 감정 분석 API 설정
KOBERT_API_URL = os.getenv(
    "KOBERT_API_URL",
    "hhttps://dual-highways-already-sg.trycloudflare.com /api/emotion")

valid_labels = {'기쁨', '당황', '분노', '불안', '상처', '슬픔'}
emotion_aliases = {
    '화남': '분노', '짜증': '분노', '우울': '슬픔', '놀람': '당황',
    '공포': '불안', '행복': '기쁨', '분노 ': '분노',
    '불안감': '불안', 'unknown': '알 수 없음'
}

def map_emotion(label):
    cleaned = label.strip()
    mapped = emotion_aliases.get(cleaned, cleaned)
    return mapped if mapped in valid_labels else '알 수 없음'

def analyze_sentiment_kobert(text):
    try:
        print(f"[KoBERT] 감정 분석 요청: {text}")
        res = requests.post(KOBERT_API_URL, json={"text": text})
        if res.status_code == 200:
            label = res.json().get("label", "unknown")
            emotion = map_emotion(label)
            print(f"[KoBERT] 응답 성공: {emotion}")
            return emotion
        else:
            print(f"[KoBERT] 오류 응답: 상태코드 {res.status_code}")
            return "알 수 없음"
    except Exception as e:
        print(f"[KoBERT] 요청 실패: {e}")
        return "알 수 없음"

# 상태 변수 (비회원용 히스토리 저장용)
chat_history = []
emotion_history = []
current_summary = ""

def index(request):
    return render(request, "chatapp/index.html")

@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        print("[chat_api] 잘못된 요청: POST만 지원")
        return JsonResponse({"error": "POST만 지원합니다."}, status=405)

    try:
        print("[chat_api] 호출됨")
        body = json.loads(request.body)
        prompt = body.get("prompt", "")
        coach_role = body.get("coachRole", "")
        print(f"[chat_api] 받은 프롬프트: {prompt}")

        # 세션에서 꺼내오기 (없으면 빈 리스트/문자열)
        chat_history    = request.session.get('chat_history', [])
        emotion_history = request.session.get('emotion_history', [])
        current_summary = request.session.get('current_summary', "")
        print(f"[chat_api] 현재 세션 chat_history 길이: {len(chat_history)}")

        # 1) 감정 분석
        emotion   = analyze_sentiment_kobert(prompt)
        timestamp = datetime.now().strftime("%p %I:%M:%S")
        emotion_history.append({"timestamp": timestamp, "sentiment": emotion})

        # 2) 시스템 메시지 (첫 호출 때만)
        if not chat_history:
            system_msg = coach_role + (
              " 시작은 항상 반말로 말해줘. 친구처럼 편하게 대화해줘. "
              "대답은 간결하고 부담스럽지 않게."
            )
            chat_history.append({"role": "system", "content": system_msg})
            print("[chat_api] 시스템 메시지 추가")

        # 3) 유저 메시지
        chat_history.append({"role": "user", "content": prompt})
        print("[chat_api] 사용자 메시지 추가")

        # 4) OpenAI 호출
        print("[chat_api] OpenAI API 호출 시작")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=chat_history,
            temperature=0.9,
            max_tokens=1024
        )
        reply = response.choices[0].message.content.strip()
        print(f"[chat_api] OpenAI 응답: {reply}")

        # 5) 어시스턴트 메시지 & summary 누적
        chat_history.append({"role": "assistant", "content": reply})
        current_summary += f"사용자: {prompt}\n불안핑: {reply}\n"
        print("[chat_api] 어시스턴트 메시지 추가 및 summary 누적")

        # 6) 세션 갱신
        request.session['chat_history']    = chat_history
        request.session['emotion_history'] = emotion_history
        request.session['current_summary'] = current_summary
        request.session.modified = True
        print("[chat_api] 세션 갱신 완료")

        return JsonResponse({"response": reply, "sentiment": emotion})

    except Exception as e:
        print(f"[chat_api] 오류 발생: {e}")
        return JsonResponse(
            {"response": "문제가 발생했어. 다시 시도해볼래?"},
            status=500
        )


@csrf_exempt
def summary(request):
    global current_summary, emotion_history

    if request.method == "POST":
        try:
            print("[summary] POST 요청 수신")
            body = json.loads(request.body)
            chat_log = body.get("chatLog", [])
            emotion_data = body.get("emotionHistory", [])
            print(f"[summary] chat_log: {chat_log}")
            print(f"[summary] emotion_data: {emotion_data}")
            now = datetime.now().date()

            if request.user.is_authenticated:
                print("[summary] 사용자 인증됨, DB에 저장 시도")
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
                print("[summary] DB 저장 완료")

            dialogue = "\n".join([f"{msg['sender']}: {msg['message']}" for msg in chat_log])
            prompt = f"""
다음은 사용자와 감정 공감 챗봇 '불안핑'의 대화입니다.
대화 내용을 바탕으로 사용자의 감정을 짧고 따뜻하게 요약해주세요.
[대화]
{dialogue}
"""
            print("[summary] OpenAI 요약 API 호출 시작")
            summary_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "너는 감정을 공감하고 요약하는 AI 챗봇이야."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            summary_text = summary_response.choices[0].message.content.strip()
            print(f"[summary] 요약 결과: {summary_text}")

            if request.user.is_authenticated:
                DailySummary.objects.create(user=request.user, date=now, summary=summary_text)
                print("[summary] 요약 결과 DB 저장 완료")

            return render(request, "chatapp/summary.html", {
                "summary": summary_text,
                "emotion_history": emotion_data
            })

        except Exception as e:
            print(f"[summary] 오류 발생: {e}")
            return render(request, "chatapp/summary.html", {
                "summary": "요약 중 오류가 발생했어요.",
                "emotion_history": emotion_history
            })

    else:
        print("[summary] GET 요청 수신")
        return render(request, "chatapp/summary.html", {
            "summary": current_summary,
            "emotion_history": emotion_history
        })

@csrf_exempt
def reset_chat(request):
    if request.method == "POST":
        print("[reset_chat] 세션 초기화 요청")
        request.session['chat_history'] = []
        request.session['emotion_history'] = []
        request.session['current_summary'] = ""
        request.session.modified = True
        print("[reset_chat] 세션 초기화 완료")
        return JsonResponse({"status": "ok"})

@login_required  # 로그인한 사용자만 접근 가능
def journal_list(request):
    try:
        print("[journal_list] 호출됨")
        # 로그인한 사용자의 감정일지 리스트만 표시
        summaries = DailySummary.objects.filter(user=request.user).order_by('-date')
        print(f"[journal_list] 불러온 일지 개수: {summaries.count()}")
        return render(request, "chatapp/journal_list.html", {"summaries": summaries})
    except Exception as e:
        print(f"[journal_list] 오류 발생: {e}")
        raise

@login_required  # 로그인한 사용자만 접근 가능
def journal_detail(request, date):
    try:
        print(f"[journal_detail] 호출됨 - date: {date}")
        # 로그인한 사용자의 일지 상세 조회
        summary = DailySummary.objects.filter(user=request.user, date=date).first()
        emotions = EmotionRecord.objects.filter(user=request.user, date=date)
        print(f"[journal_detail] 불러온 요약: {summary.summary if summary else '없음'}")
        print(f"[journal_detail] 불러온 감정 개수: {emotions.count()}")

        # 감정 빈도 계산
        emotion_list = [e.sentiment for e in emotions]
        counter = Counter(emotion_list)
        
        # 감정 라벨 순서에 맞게 빈도 정렬
        emotion_labels = ["분노", "불안", "슬픔", "상처", "당황", "중립", "기쁨"]
        emotion_frequency = [counter.get(label, 0) for label in emotion_labels]
        print(f"[journal_detail] 감정 빈도: {emotion_frequency}")

        return render(request, "chatapp/journal_detail.html", {
            "summary": summary.summary if summary else "요약 없음",
            "emotion_frequency": emotion_frequency,
            "date": date,
        })
    except Exception as e:
        print(f"[journal_detail] 오류 발생: {e}")
        raise
