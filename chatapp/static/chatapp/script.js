let chatHistory = [];
window.emotionHistory = window.emotionHistory || [];

// 중복 전송 방지 플래그
let isSending = false;
// 스크롤 자동 이동 여부 플래그
let autoScrollEnabled = true;

// 채팅 메시지 추가 함수
function addMessage(sender, message) {
  const chatMessages = document.getElementById('chatMessages');
  if (message === '문제가 생겼어. 다시 시도해볼래?') {
    const last = chatMessages.lastElementChild;
    if (last && last.textContent === message) {
      console.log("[addMessage] 동일한 오류 메시지 중복 방지");
      return;
    }
  }

  const messageElement = document.createElement('div');
  messageElement.className = sender === '사용자' ? 'user-message' : 'ping-message';
  messageElement.textContent = message;
  chatMessages.appendChild(messageElement);
  chatHistory.push({ sender, message });

  const threshold = 100;
  const scrollFromBottom = chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight;
  if (autoScrollEnabled && scrollFromBottom <= threshold) {
    chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: 'smooth' });
    console.log("[addMessage] 스크롤 자동 이동");
  }

  console.log(`[addMessage] 메시지 추가됨 - sender: ${sender}, message: ${message}`);
}

// 인트로 → 채팅 UI 전환
function showChatUI(firstMsg) {
  console.log("[showChatUI] 호출됨, firstMsg:", firstMsg);
  const intro = document.getElementById('chatIntro');
  const mainArea = document.getElementById('mainArea');
  const endChatButton = document.getElementById('endChatButton');
  const userMessage = document.getElementById('userMessage');

  intro.classList.remove('active');
  intro.style.display = 'none';
  mainArea.style.display = 'block';
  mainArea.classList.add('active');
  endChatButton.style.display = 'block';
  userMessage.value = '';
  setTimeout(() => userMessage.focus(), 100);

  if (firstMsg && firstMsg.trim()) {
    addMessage('사용자', firstMsg);
    sendMessage(firstMsg, true);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  console.log("[DOMContentLoaded] 초기화 시작");
  const introInput = document.getElementById('introInput');
  const introSend = document.getElementById('introSend');
  const mainArea = document.getElementById('mainArea');
  const endChatButton = document.getElementById('endChatButton');
  const chatMessages = document.getElementById('chatMessages');
  const userMessage = document.getElementById('userMessage');
  const sendBtn = document.getElementById('sendMessage');

  if (introSend) {
    introSend.onclick = () => {
      console.log("[introSend.onclick] 클릭됨");
      if (!isSending) showChatUI(introInput.value.trim());
      else console.log("[introSend.onclick] 요청 중복 방지");
    };
    introInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        console.log("[introInput.keydown] Enter 눌림");
        if (!isSending) showChatUI(introInput.value.trim());
        else console.log("[introInput.keydown] 요청 중복 방지");
      }
    });
  }

  if (mainArea) mainArea.style.display = 'none';
  if (endChatButton) endChatButton.style.display = 'none';

  endChatButton?.addEventListener('click', () => {
    console.log("[endChatButton.click] 채팅 종료");
    mainArea.style.display = 'none';
    document.getElementById('chatIntro').style.display = 'flex';
    endChatButton.style.display = 'none';
    chatMessages.innerHTML = '';
    userMessage.value = '';
    chatHistory = [];
    window.emotionHistory = [];
    isSending = false;
  });

  chatMessages?.addEventListener('scroll', () => {
    const threshold = 100;
    const scrollFromBottom = chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight;
    autoScrollEnabled = scrollFromBottom <= threshold;
  });

  sendBtn?.addEventListener('click', () => {
    console.log("[sendBtn.click] 클릭됨");
    if (!isSending) sendMessage();
    else console.log("[sendBtn.click] 요청 중복 방지");
  });

  userMessage?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      console.log("[userMessage.keydown] Enter 눌림");
      if (!isSending) sendMessage();
      else console.log("[userMessage.keydown] 요청 중복 방지");
    }
  });
});

// 메시지 전송 함수
async function sendMessage(msg, isFirst = false) {
  if (isSending && !isFirst) {
    console.log("[sendMessage] 중복 요청 방지됨");
    return;
  }
  isSending = true;
  console.log(`[sendMessage] 호출됨, isFirst: ${isFirst}, msg: "${msg || ''}"`);

  const userInputEl = document.getElementById('userMessage');
  const userMessage = isFirst ? msg : userInputEl.value.trim();
  if (!userMessage) {
    console.log("[sendMessage] 빈 메시지로 중단");
    isSending = false;
    return;
  }

  if (!isFirst) {
    addMessage('사용자', userMessage);
    userInputEl.value = '';
    autoScrollEnabled = true;
  }

  const coachRole = "너는 불안핑이라는 캐릭터야! 따뜻하고 친근한 말투로 사용자를 위로해줘. " +
    "친구처럼 공감하고 대답은 간결하게 해줘.";

  try {
    console.log("[sendMessage] /api/chat/ 요청 시작");
    const res = await fetch('/api/chat/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ prompt: userMessage, coachRole })
    });
    if (!res.ok) {
      console.error(`[sendMessage] 서버 응답 에러: ${res.status}`);
      throw new Error('서버 응답 에러');
    }
    const data = await res.json();
    console.log("[sendMessage] 서버 응답 수신", data);
    addMessage('불안핑', data.response);

    if (data.sentiment) {
      const now = new Date();
      const hh = now.getHours() % 12 || 12;
      const timestamp = `${now.getHours() >= 12 ? '오후' : '오전'} ${hh}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`;

      if (!Array.isArray(window.emotionHistory)) {
        console.warn("[sendMessage] window.emotionHistory가 배열이 아님, 재초기화합니다.");
        window.emotionHistory = [];
      }

      window.emotionHistory.push({ timestamp, sentiment: data.sentiment });
      console.log("[sendMessage] 감정 기록 추가", { timestamp, sentiment: data.sentiment });
    }
  } catch (error) {
    console.error("[sendMessage] 에러 발생:", error);
    addMessage('불안핑', '문제가 생겼어. 다시 시도해볼래?');
  } finally {
    isSending = false;
  }
}

// 채팅 종료 → 요약
document.getElementById('endChatButton')?.addEventListener('click', async () => {
  if (!chatHistory.length) {
    console.log("[endChatButton.click] 대화 내용 없음");
    return alert("대화 내용이 없습니다.");
  }
  try {
    console.log("[endChatButton.click] /summary/ 요청 시작");
    const res = await fetch('/summary/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ chatLog: chatHistory, emotionHistory: window.emotionHistory })
    });
    if (!res.ok) {
      console.error(`[endChatButton.click] 서버 응답 에러: ${res.status}`);
      throw new Error('서버 응답 에러');
    }
    const html = await res.text();
    console.log("[endChatButton.click] 요약 페이지 로드");
    document.open();
    document.write(html);
    document.close();
  } catch (error) {
    console.error("[endChatButton.click] 에러 발생:", error);
    alert("요약을 가져오는 중 문제가 발생했어요!");
  }
});
