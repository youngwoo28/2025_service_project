let chatHistory = [];
window.emotionHistory = window.emotionHistory || []; // ✅ 중복 선언 방지

// 채팅 메시지 추가 함수
function addMessage(sender, message) {
    const chatMessages = document.getElementById('chatMessages');
    const messageElement = document.createElement('div');

    messageElement.className = sender === '사용자' ? 'message user-message' : 'message ping-message';
    messageElement.textContent = `${sender}: ${message}`;

    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    chatHistory.push({ sender, message });
}

// 초기 인사 메시지
document.addEventListener("DOMContentLoaded", () => {
    addMessage('불안핑', "안녕! 너한테 무슨 일이 있었는지 다 말해줘! 난 너의 친구야. 😊");
});

// 메시지 전송 함수 (Django 서버로 연결)
async function sendMessage() {
    const userMessage = document.getElementById('userMessage').value.trim();
    if (!userMessage) return;

    addMessage('사용자', userMessage);
    document.getElementById('userMessage').value = '';

    const coachRole = "너는 불안핑이라는 캐릭터야! 따뜻하고 친근한 말투로 사용자를 위로해줘. " +
        "너는 친구처럼 사용자의 감정을 이해하고, 공감하며 대답하는 AI야. 존댓말은 되도록 쓰지말고, 사용자가 존댓말을 요청한다면 존댓말을 써줘" +
        "되도록 대답은 간결해야 친근한 거 같아서, 대답은 간결하고 많이 친한 친구처럼 장난도 치고, 짓궃게 대답도 해줘";

    try {
        const response = await fetch('/api/chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include', // ✅ CSRF 보호 우회용
            body: JSON.stringify({ prompt: userMessage, coachRole: coachRole })
        });

        const data = await response.json();
        addMessage('불안핑', data.response);

        // 감정 기록 저장
        if (data.sentiment) {
            const now = new Date().toLocaleTimeString(); // HH:MM:SS 포맷
            emotionHistory.push({ timestamp: now, sentiment: data.sentiment });
        }

    } catch (error) {
        console.error("API 오류:", error);
        addMessage('불안핑', '문제가 생겼어. 다시 시도해볼래?');
    }
}

// 보내기 버튼 클릭 시 메시지 전송
document.getElementById('sendMessage').addEventListener('click', sendMessage);

// 엔터 키 입력 시 메시지 전송
document.getElementById('userMessage').addEventListener('keypress', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

// ✅ 채팅 종료 시 POST 방식으로 /summary/에 감정 기록 전달
document.getElementById('endChatButton').addEventListener('click', async () => {
    if (chatHistory.length === 0) {
        alert("대화 내용이 없습니다.");
        return;
    }

    try {
        const response = await fetch("/summary/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: 'include', // ✅ CSRF 보호 우회용
            body: JSON.stringify({
                chatLog: chatHistory,
                emotionHistory: emotionHistory
            })
        });

        const html = await response.text();
        document.open();
        document.write(html);
        document.close();
    } catch (error) {
        console.error("요약 요청 실패:", error);
        alert("요약을 가져오는 중 문제가 발생했어요!");
    }
});
