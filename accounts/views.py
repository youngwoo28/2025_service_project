from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages

# 회원가입
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('/')  # 이미 로그인된 사용자는 홈으로

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "회원가입이 완료되었어요! 로그인해주세요.")
            return redirect('login')
        else:
            messages.error(request, "회원가입에 실패했어요. 다시 확인해보세요.")
    else:
        form = UserCreationForm()

    return render(request, 'accounts/signup.html', {'form': form})

# 로그인
def login_view(request):
    if request.user.is_authenticated:
        return redirect('/')  # 이미 로그인된 사용자

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('/')  # 'index'로 URL name이 지정되어 있다면 'index'로
        else:
            messages.error(request, "로그인에 실패했어요. 아이디와 비밀번호를 확인해주세요.")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})

# 로그아웃
def logout_view(request):
    logout(request)
    messages.info(request, "로그아웃 되었어요.")
    return redirect('login')
