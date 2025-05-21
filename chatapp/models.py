from django.db import models
from django.contrib.auth.models import User

# ✅ 감정 기록 모델
class EmotionRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # 비회원도 가능
    date = models.DateField(auto_now_add=True)
    timestamp = models.TimeField()
    sentiment = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user if self.user else '비회원'} - {self.date} {self.timestamp} ({self.sentiment})"

# ✅ 채팅 로그 모델
class ChatLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    sender = models.CharField(max_length=20)  # 사용자 or 불안핑
    message = models.TextField()

    def __str__(self):
        return f"{self.user if self.user else '비회원'} - {self.sender}: {self.message[:30]}"

# ✅ 요약 저장 모델 (선택 사항)
class DailySummary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    summary = models.TextField()

    def __str__(self):
        return f"{self.user if self.user else '비회원'} - {self.date} 요약"
