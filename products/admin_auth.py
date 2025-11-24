from functools import wraps
from django.shortcuts import redirect, render
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponseForbidden
import os
from decouple import config


def get_admin_auth_code():
    """환경변수에서 관리자 인증 코드 가져오기"""
    return config('ADMIN_CODE', default='')


def admin_auth_required(view_func):
    """관리자 페이지 인증 데코레이터 - 로그인된 상태에서만 접근 가능"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 운영 환경에서는 접근 차단
        if settings.DJANGO_ENV == 'production':
            return HttpResponseForbidden("이 페이지는 개발 환경에서만 접근 가능합니다.")
        
        # 세션에 인증 정보가 있는지 확인
        if request.session.get('admin_authenticated', False):
            return view_func(request, *args, **kwargs)
        
        # 로그인되지 않은 경우 로그인 페이지로 리다이렉트
        return redirect('admin_login')
    
    return wrapper


def admin_login_view(request):
    """관리자 로그인 - ADMIN_CODE 입력 및 .env 값과 비교"""
    # 운영 환경에서는 접근 차단
    if settings.DJANGO_ENV == 'production':
        return HttpResponseForbidden("이 페이지는 개발 환경에서만 접근 가능합니다.")
    
    # 이미 인증된 경우 메인으로 리다이렉트
    if request.session.get('admin_authenticated', False):
        return redirect('admin_main')
    
    # POST 요청으로 ADMIN_CODE가 전달된 경우
    if request.method == 'POST':
        admin_code = request.POST.get('auth_code', '').strip()
        expected_code = get_admin_auth_code()
        
        # .env의 ADMIN_CODE와 비교
        if admin_code == expected_code:
            # 세션에 로그인 상태 저장
            request.session['admin_authenticated'] = True
            messages.success(request, '로그인에 성공했습니다.')
            return redirect('admin_main')
        else:
            messages.error(request, 'ADMIN_CODE가 올바르지 않습니다.')
    
    # ADMIN_CODE 입력 페이지 표시
    return render(request, 'products/admin_login.html')


def admin_logout(request):
    """관리자 로그아웃"""
    request.session.pop('admin_authenticated', None)
    messages.success(request, '로그아웃되었습니다.')
    return redirect('admin_login')

