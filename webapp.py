from flask import Flask, request, jsonify, render_template_string
from database import check_code, add_participant, get_user_codes_count, get_participants_count
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")

HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Розыгрыш Yamaguchi</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a1a;
            color: #fff;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .screen {
            display: none;
            min-height: 100vh;
            flex-direction: column;
            padding: 24px 16px;
            max-width: 480px;
            margin: 0 auto;
        }

        .screen.active { display: flex; }

        .sub-title {
            font-size: 26px;
            font-weight: 800;
            text-align: center;
            margin: 32px 0 8px;
            line-height: 1.2;
        }

        .sub-subtitle {
            font-size: 14px;
            color: rgba(255,255,255,0.5);
            text-align: center;
            margin-bottom: 28px;
            line-height: 1.5;
        }

        .channel-card {
            background: #2a2a2a;
            border-radius: 16px;
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 12px;
        }

        .channel-avatar {
            width: 56px;
            height: 56px;
            border-radius: 50%;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            font-weight: 800;
        }

        .channel-avatar.miratorg {
            background: #1a1a1a;
            color: #fff;
            font-size: 11px;
            text-align: center;
            line-height: 1.2;
            padding: 6px;
        }

        .channel-avatar.yamaguchi {
            background: #E31E24;
            color: #fff;
            font-size: 26px;
            font-weight: 900;
        }

        .channel-info { flex: 1; }

        .channel-name {
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 2px;
        }

        .channel-username {
            font-size: 13px;
            color: rgba(255,255,255,0.4);
        }

        .btn-subscribe {
            background: #E31E24;
            color: #fff;
            border: none;
            border-radius: 10px;
            padding: 10px 18px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: opacity 0.2s;
        }

        .btn-subscribe:active { opacity: 0.8; }
        .btn-subscribe.done {
            background: #2ecc71;
            pointer-events: none;
        }

        .btn-check {
            width: 100%;
            padding: 18px;
            background: #E31E24;
            border: none;
            border-radius: 14px;
            color: #fff;
            font-size: 17px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 20px;
            transition: opacity 0.2s;
        }

        .btn-check:active { opacity: 0.85; }

        .check-hint {
            font-size: 13px;
            color: rgba(255,255,255,0.35);
            text-align: center;
            margin-top: 10px;
        }

        .code-title {
            font-size: 26px;
            font-weight: 800;
            text-align: center;
            margin: 28px 0 8px;
            line-height: 1.2;
        }

        .code-subtitle {
            font-size: 14px;
            color: rgba(255,255,255,0.5);
            text-align: center;
            margin-bottom: 24px;
            line-height: 1.5;
        }

        .code-card {
            background: #E31E24;
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
            min-height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
        }

        .code-card::after {
            content: '';
            position: absolute;
            right: -20px;
            top: -20px;
            width: 160px;
            height: 160px;
            background: rgba(255,255,255,0.08);
            border-radius: 50%;
        }

        .code-card-brand {
            font-size: 13px;
            font-weight: 800;
            color: rgba(255,255,255,0.7);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        .code-card-label {
            font-size: 12px;
            color: rgba(255,255,255,0.6);
            margin-bottom: 4px;
        }

        .code-card-value {
            font-size: 17px;
            font-weight: 800;
            color: #fff;
            letter-spacing: 1px;
        }

        .code-input {
            width: 100%;
            padding: 18px 16px;
            background: #2a2a2a;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 14px;
            color: #fff;
            font-size: 16px;
            letter-spacing: 1px;
            text-transform: uppercase;
            outline: none;
            margin-bottom: 8px;
            transition: border-color 0.2s;
        }

        .code-input:focus { border-color: #E31E24; }
        .code-input::placeholder {
            letter-spacing: 0;
            text-transform: none;
            color: rgba(255,255,255,0.25);
        }

        .code-hint {
            font-size: 13px;
            color: rgba(255,255,255,0.35);
            text-align: center;
            margin-bottom: 20px;
        }

        .btn-register {
            width: 100%;
            padding: 18px;
            background: #E31E24;
            border: none;
            border-radius: 14px;
            color: #fff;
            font-size: 17px;
            font-weight: 700;
            cursor: pointer;
            transition: opacity 0.2s;
        }

        .btn-register:active { opacity: 0.85; }
        .btn-register:disabled { opacity: 0.4; cursor: not-allowed; }

        .error-msg {
            font-size: 13px;
            color: #ff6b6b;
            text-align: center;
            margin-top: 10px;
            min-height: 18px;
        }

        .success-title {
            font-size: 26px;
            font-weight: 800;
            text-align: center;
            margin: 28px 0 20px;
        }

        .prize-card {
            background: #E31E24;
            border-radius: 20px;
            padding: 28px 24px;
            text-align: center;
            margin-bottom: 16px;
            position: relative;
            overflow: hidden;
        }

        .prize-card::before {
            content: '';
            position: absolute;
            left: -40px;
            bottom: -40px;
            width: 180px;
            height: 180px;
            background: rgba(0,0,0,0.15);
            border-radius: 50%;
        }

        .prize-label {
            font-size: 13px;
            font-weight: 700;
            color: rgba(255,255,255,0.7);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }

        .prize-name {
            font-size: 24px;
            font-weight: 900;
            color: #fff;
            line-height: 1.2;
            text-transform: uppercase;
        }

        .entries-block {
            background: #2a2a2a;
            border-radius: 14px;
            padding: 18px;
            text-align: center;
            margin-bottom: 12px;
        }

        .entries-count {
            font-size: 17px;
            font-weight: 600;
            color: #fff;
        }

        .entries-add {
            font-size: 13px;
            color: rgba(255,255,255,0.4);
            margin-top: 4px;
        }

        .discount-block {
            background: #2a2a2a;
            border: 1px solid rgba(212,175,55,0.4);
            border-radius: 14px;
            padding: 18px;
            text-align: center;
            margin-bottom: 12px;
        }

        .discount-label {
            font-size: 13px;
            color: rgba(255,255,255,0.5);
            margin-bottom: 8px;
        }

        .discount-code {
            font-size: 22px;
            font-weight: 900;
            letter-spacing: 3px;
            color: #D4AF37;
            margin-bottom: 6px;
        }

        .discount-hint {
            font-size: 12px;
            color: rgba(255,255,255,0.35);
        }

        .success-hint {
            font-size: 13px;
            color: rgba(255,255,255,0.35);
            text-align: center;
            line-height: 1.5;
            margin-top: 4px;
        }

        .btn-add-code {
            width: 100%;
            padding: 18px;
            background: transparent;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 14px;
            color: #fff;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 16px;
            transition: background 0.2s;
        }

        .btn-add-code:active { background: rgba(255,255,255,0.05); }
    </style>
</head>
<body>

<!-- ЭКРАН 2: ПОДПИСКА -->
<div class="screen active" id="screen-sub">
    <div class="sub-title">Подпишитесь на 2 канала,<br>чтобы продолжить</div>
    <div class="sub-subtitle">Подписка на оба канала обязательна<br>для участия в розыгрыше</div>

    <div class="channel-card">
        <div class="channel-avatar miratorg">СТЕЙК &<br>БУРГЕР<br>МИРАТОРГ</div>
        <div class="channel-info">
            <div class="channel-name">Стейк & бургер Мираторг</div>
            <div class="channel-username">@burgers_by_miratorg</div>
        </div>
        <button class="btn-subscribe" id="btn-sub-1" onclick="openChannel('https://t.me/burgers_by_miratorg', 'btn-sub-1')">
            Подписаться
        </button>
    </div>

    <div class="channel-card">
        <div class="channel-avatar yamaguchi">Y</div>
        <div class="channel-info">
            <div class="channel-name">Yamaguchi</div>
            <div class="channel-username">@yamaguchi_ru</div>
        </div>
        <button class="btn-subscribe" id="btn-sub-2" onclick="openChannel('https://t.me/yamaguchi_ru', 'btn-sub-2')">
            Подписаться
        </button>
    </div>

    <button class="btn-check" onclick="checkSubscription()">Проверить подписку</button>
    <div class="check-hint">Проверяем, что вы подписаны на оба канала</div>
</div>

<!-- ЭКРАН 3: КОД -->
<div class="screen" id="screen-code">
    <div class="code-title">Зарегистрируй код</div>
    <div class="code-subtitle">Найди уникальный код на карточке<br>участника розыгрыша</div>

    <div class="code-card">
        <div class="code-card-brand">Yamaguchi × Мираторг</div>
        <div class="code-card-label">Уникальный код</div>
        <div class="code-card-value" id="cardCodeDisplay">XXXX-XXXX-XXXX</div>
    </div>

    <input
        type="text"
        class="code-input"
        id="codeInput"
        placeholder="Введите код"
        maxlength="30"
        oninput="updateCardDisplay(this.value)"
    />
    <div class="code-hint">1 код = 1 участие в розыгрыше</div>

    <button class="btn-register" id="submitBtn" onclick="submitCode()">Зарегистрировать</button>
    <div class="error-msg" id="errorMsg"></div>
</div>

<!-- ЭКРАН 4: УСПЕХ -->
<div class="screen" id="screen-success">
    <div class="success-title">Вы участвуете<br>в розыгрыше!</div>

    <div class="prize-card">
        <div class="prize-label">Главный приз</div>
        <div class="prize-name">Беговая дорожка<br>Yamaguchi</div>
    </div>

    <div class="entries-block">
        <div class="entries-count" id="entriesCount">Ваших участий: 1</div>
        <div class="entries-add">Добавьте ещё код, чтобы увеличить шансы</div>
    </div>

    <div class="discount-block">
        <div class="discount-label">🏷 Ваш промокод на скидку Yamaguchi</div>
        <div class="discount-code" id="discountCode"></div>
        <div class="discount-hint">Введите код при оформлении заказа на yamaguchi.ru</div>
    </div>

    <div class="success-hint">Следите за новостями в каналах<br>Итоги розыгрыша скоро!</div>

    <button class="btn-add-code" onclick="addAnotherCode()">+ Добавить ещё один код</button>
</div>

<script>
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();

    function showScreen(id) {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        document.getElementById(id).classList.add('active');
    }

    function openChannel(url, btnId) {
        window.open(url, '_blank');
        setTimeout(() => {
            const btn = document.getElementById(btnId);
            btn.textContent = '✓ Готово';
            btn.classList.add('done');
        }, 1500);
    }

    function checkSubscription() {
        showScreen('screen-code');
    }

    function updateCardDisplay(val) {
        const display = document.getElementById('cardCodeDisplay');
        display.textContent = val.trim().toUpperCase() || 'XXXX-XXXX-XXXX';
    }

    async function submitCode() {
        const code = document.getElementById('codeInput').value.trim().toUpperCase();
        const btn = document.getElementById('submitBtn');
        const err = document.getElementById('errorMsg');

        if (!code) {
            err.textContent = 'Введите код участника';
            return;
        }

        btn.disabled = true;
        btn.textContent = 'Проверяем...';
        err.textContent = '';

        try {
            const response = await fetch('/submit_code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code: code,
                    user: tg.initDataUnsafe.user || {}
                })
            });

            const data = await response.json();

            if (data.success) {
                document.getElementById('entriesCount').textContent = 'Ваших участий: ' + data.user_codes;
                document.getElementById('discountCode').textContent = data.discount_code;
                showScreen('screen-success');
            } else {
                err.textContent = data.message;
                btn.disabled = false;
                btn.textContent = 'Зарегистрировать';
            }
        } catch (e) {
            err.textContent = 'Ошибка соединения. Попробуйте ещё раз.';
            btn.disabled = false;
            btn.textContent = 'Зарегистрировать';
        }
    }

    function addAnotherCode() {
        document.getElementById('codeInput').value = '';
        document.getElementById('cardCodeDisplay').textContent = 'XXXX-XXXX-XXXX';
        document.getElementById('errorMsg').textContent = '';
        document.getElementById('submitBtn').disabled = false;
        document.getElementById('submitBtn').textContent = 'Зарегистрировать';
        showScreen('screen-code');
    }
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/submit_code', methods=['POST'])
def submit_code():
    data = request.get_json()
    code = data.get('code', '').strip().upper()
    user = data.get('user', {})

    user_id = user.get('id', 0)
    username = user.get('username', 'без username')
    full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()

    if not code:
        return jsonify({'success': False, 'message': 'Введите код'})

    if not check_code(code):
        return jsonify({'success': False, 'message': 'Код недействителен или уже использован'})

    success = add_participant(user_id, username, full_name, code)

    if not success:
        return jsonify({'success': False, 'message': 'Этот код уже использован'})

    user_codes = get_user_codes_count(user_id)

    return jsonify({
        'success': True,
        'user_codes': user_codes,
        'discount_code': os.getenv('DISCOUNT_CODE', 'YAMAGUCHI2024')
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)