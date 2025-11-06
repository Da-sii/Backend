"""
고객지원 정보 페이지 뷰
"""
from django.http import HttpResponse


def support_root(request):
    """
    루트 경로(/)에 표시될 고객지원 정보 페이지
    고객지원 정보, 개인정보 처리방침, 이용약관을 모두 포함합니다.
    """
    html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>다시(DASII) 고객지원</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 30px;
            font-size: 28px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 22px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        h3 {
            color: #555;
            margin-top: 25px;
            margin-bottom: 15px;
            font-size: 18px;
        }
        p {
            margin-bottom: 15px;
            line-height: 1.8;
        }
        .contact-info {
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .contact-info strong {
            color: #2980b9;
            font-size: 18px;
        }
        ul, ol {
            margin-left: 20px;
            margin-bottom: 15px;
        }
        li {
            margin-bottom: 10px;
        }
        .section {
            margin-bottom: 40px;
        }
        .last-updated {
            color: #7f8c8d;
            font-size: 14px;
            margin-top: 30px;
            text-align: right;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>다시(DASII) 고객지원</h1>
        
        <div class="section">
            <div class="contact-info">
                <p><strong>📧 고객지원 이메일: podosangjeom@gmail.com</strong></p>
                <p>다시 앱 이용 중 문의 사항은 위 이메일로 연락해주세요.</p>
                <p>평일 기준 1~3일 이내에 답변드리고 있습니다.</p>
            </div>
        </div>

        <div class="section">
            <h2>1. 개인정보 처리방침</h2>
            
            <h3>1.1 수집하는 개인정보 항목</h3>
            <p>다시(DASII)는 서비스 제공을 위해 다음과 같은 개인정보를 수집합니다:</p>
            <ul>
                <li><strong>필수 항목:</strong> 이메일 주소, 닉네임, 비밀번호(암호화), 전화번호</li>
                <li><strong>선택 항목:</strong> 프로필 이미지</li>
                <li><strong>자동 수집 항목:</strong> IP 주소, 접속 로그, 기기 정보, 쿠키</li>
            </ul>

            <h3>1.2 개인정보의 수집 및 이용 목적</h3>
            <ul>
                <li>회원 가입 및 관리: 회원 식별, 본인 확인, 서비스 이용에 따른 본인확인, 불만 처리 등</li>
                <li>서비스 제공: 상품 정보 제공, 리뷰 작성 및 관리, 알림 서비스</li>
                <li>서비스 개선: 신규 서비스 개발, 서비스 품질 향상, 맞춤형 서비스 제공</li>
                <li>마케팅 및 광고: 이벤트 정보 제공, 광고성 정보 제공(동의 시)</li>
            </ul>

            <h3>1.3 개인정보의 보유 및 이용 기간</h3>
            <p>회원 탈퇴 시까지 개인정보를 보유 및 이용하며, 탈퇴 후에는 지체 없이 파기합니다. 단, 다음의 경우에는 해당 사유 종료 시까지 보관합니다:</p>
            <ul>
                <li>관련 법령에 의한 보존 의무가 있는 경우 해당 법령에서 정한 기간</li>
                <li>서비스 이용 중 발생한 분쟁 해결을 위해 필요한 기간</li>
            </ul>

            <h3>1.4 개인정보의 제3자 제공</h3>
            <p>다시(DASII)는 원칙적으로 이용자의 개인정보를 외부에 제공하지 않습니다. 다만, 다음의 경우에는 예외로 합니다:</p>
            <ul>
                <li>이용자가 사전에 동의한 경우</li>
                <li>법령의 규정에 의거하거나, 수사 목적으로 법령에 정해진 절차와 방법에 따라 수사기관의 요구가 있는 경우</li>
            </ul>

            <h3>1.5 개인정보 처리의 위탁</h3>
            <p>서비스 향상을 위해 다음과 같이 개인정보 처리업무를 위탁할 수 있습니다:</p>
            <ul>
                <li>클라우드 서비스 제공업체: 서버 운영 및 데이터 보관</li>
                <li>이메일 발송 서비스: 회원 인증 및 알림 메일 발송</li>
                <li>SMS 발송 서비스: 인증번호 발송</li>
            </ul>

            <h3>1.6 개인정보의 파기</h3>
            <p>개인정보는 수집 및 이용 목적이 달성된 후에는 지체 없이 파기합니다. 전자적 파일 형태의 정보는 기록을 복구할 수 없는 기술적 방법을 사용하여 삭제하며, 기록물, 인쇄물, 서면 등은 분쇄하거나 소각합니다.</p>

            <h3>1.7 이용자 권리 및 행사 방법</h3>
            <p>이용자는 언제든지 다음의 권리를 행사할 수 있습니다:</p>
            <ul>
                <li>개인정보 열람 요구</li>
                <li>개인정보 정정·삭제 요구</li>
                <li>개인정보 처리정지 요구</li>
                <li>회원 탈퇴</li>
            </ul>
            <p>위 권리 행사는 이메일(podosangjeom@gmail.com)로 요청하시면 지체 없이 조치하겠습니다.</p>
        </div>

        <div class="section">
            <h2>2. 이용약관</h2>
            
            <h3>2.1 목적</h3>
            <p>이 약관은 다시(DASII)(이하 "회사")가 제공하는 다시 서비스(이하 "서비스")의 이용과 관련하여 회사와 이용자 간의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.</p>

            <h3>2.2 용어의 정의</h3>
            <ul>
                <li><strong>서비스:</strong> 회사가 제공하는 건강기능식품 정보 제공 및 리뷰 서비스</li>
                <li><strong>이용자:</strong> 이 약관에 따라 회사가 제공하는 서비스를 받는 회원 및 비회원</li>
                <li><strong>회원:</strong> 회사에 개인정보를 제공하여 회원등록을 한 자로서, 회사의 서비스를 계속하여 이용할 수 있는 자</li>
                <li><strong>비회원:</strong> 회원가입을 하지 않고 회사가 제공하는 서비스를 이용하는 자</li>
            </ul>

            <h3>2.3 약관의 게시와 개정</h3>
            <p>회사는 이 약관의 내용을 이용자가 쉽게 알 수 있도록 서비스 초기 화면에 게시합니다. 회사는 필요한 경우 관련 법령을 위배하지 않는 범위에서 이 약관을 개정할 수 있으며, 개정된 약관은 서비스 화면에 공지하거나 기타의 방법으로 회원에게 공지합니다.</p>

            <h3>2.4 회원가입</h3>
            <p>회원가입은 신청자가 온라인으로 회사가 제공하는 소정의 가입신청 양식에서 요구하는 사항을 기록하여 가입을 완료하는 것으로 성립됩니다. 회사는 다음 각 호에 해당하는 경우 회원가입을 거부할 수 있습니다:</p>
            <ul>
                <li>가입신청자가 이 약관에 의하여 이전에 회원자격을 상실한 적이 있는 경우</li>
                <li>실명이 아니거나 타인의 명의를 이용한 경우</li>
                <li>허위의 정보를 기재하거나 회사가 제시하는 내용을 기재하지 않은 경우</li>
                <li>기타 회원으로 등록하는 것이 회사의 기술상 현저히 지장이 있다고 판단되는 경우</li>
            </ul>

            <h3>2.5 서비스의 제공</h3>
            <p>회사는 다음과 같은 서비스를 제공합니다:</p>
            <ul>
                <li>건강기능식품 정보 제공</li>
                <li>상품 리뷰 작성 및 조회</li>
                <li>상품 검색 및 추천</li>
                <li>기타 회사가 추가 개발하거나 제휴계약 등을 통해 회원에게 제공하는 일체의 서비스</li>
            </ul>

            <h3>2.6 서비스의 변경 및 중단</h3>
            <p>회사는 기술상, 운영상의 필요에 따라 제공하는 서비스의 전부 또는 일부를 변경하거나 중단할 수 있습니다. 서비스의 내용, 이용방법, 이용시간에 대하여 변경 또는 중단이 있는 경우에는 사전에 공지하거나 통지합니다.</p>

            <h3>2.7 이용자의 의무</h3>
            <p>이용자는 다음 행위를 하여서는 안 됩니다:</p>
            <ul>
                <li>신청 또는 변경 시 허위내용의 등록</li>
                <li>타인의 정보 도용</li>
                <li>회사가 게시한 정보의 변경</li>
                <li>회사가 정한 정보 이외의 정보 등의 송신 또는 게시</li>
                <li>회사와 기타 제3자의 저작권 등 지적재산권에 대한 침해</li>
                <li>회사 및 기타 제3자의 명예를 손상시키거나 업무를 방해하는 행위</li>
                <li>외설 또는 폭력적인 메시지, 화상, 음성, 기타 공서양속에 반하는 정보를 공개 또는 게시하는 행위</li>
            </ul>

            <h3>2.8 개인정보보호</h3>
            <p>회사는 이용자의 개인정보 수집시 서비스제공을 위하여 필요한 범위에서 최소한의 개인정보를 수집합니다. 회사는 개인정보 처리방침에 따라 이용자의 개인정보를 보호하기 위해 노력합니다.</p>

            <h3>2.9 회원의 ID 및 비밀번호에 대한 의무</h3>
            <p>ID와 비밀번호에 관한 관리책임은 회원에게 있으며, 이를 제3자가 이용하도록 하여서는 안 됩니다. 회원은 자신의 ID 및 비밀번호를 도난당하거나 제3자가 사용하고 있음을 인지한 경우에는 바로 회사에 통보하고 회사의 안내가 있는 경우에는 그에 따라야 합니다.</p>

            <h3>2.10 회원 탈퇴</h3>
            <p>회원은 회사에 언제든지 탈퇴를 요청할 수 있으며, 회사는 지체 없이 회원탈퇴를 처리합니다. 회원탈퇴 시 회사가 보유한 해당 회원의 개인정보는 즉시 파기됩니다.</p>

            <h3>2.11 손해배상</h3>
            <p>회사는 천재지변 또는 이에 준하는 불가항력으로 인하여 서비스를 제공할 수 없는 경우에는 서비스 제공에 관한 책임이 면제됩니다. 회사는 회원의 귀책사유로 인한 서비스 이용의 장애에 대하여는 책임을 지지 않습니다.</p>

            <h3>2.12 분쟁의 해결</h3>
            <p>회사와 이용자 간에 발생한 전자상거래 분쟁에 관한 소송은 제소 당시의 이용자의 주소에 의하고, 주소가 없는 경우에는 거소를 관할하는 지방법원의 전속관할로 합니다.</p>
        </div>

        <div class="last-updated">
            <p>최종 수정일: 2024년 12월</p>
        </div>
    </div>
</body>
</html>
    """
    return HttpResponse(html_content, content_type="text/html; charset=utf-8")

