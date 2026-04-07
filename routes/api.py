from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from extensions import limiter
from services.transcription_service import TranscriptionService
from services.ai_service import AIService
from models import Favorite, User
from extensions import db, bcrypt

bp = Blueprint('api', __name__, url_prefix='/api')

# ==================== ТРАНСКРИПЦИЯ ====================

@bp.route('/transcribe', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
def save_transcription():
    """
    Сохраняет транскрипцию речи пользователя.
    ---
    tags:
      - Transcriptions
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            text:
              type: string
              description: Распознанный текст
              example: "Привет, как дела?"
            language:
              type: string
              description: Код языка (ru, kk, en)
              default: ru
            duration:
              type: integer
              description: Длительность записи в секундах
              default: 0
    responses:
      200:
        description: Транскрипция сохранена
        schema:
          type: object
          properties:
            status:
              type: string
              example: saved
            id:
              type: integer
      400:
        description: Нет текста
      429:
        description: Слишком много запросов
    """
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    trans_id = TranscriptionService.save_transcription(
        user_id=current_user.id,
        text=text,
        language=data.get('language', 'ru'),
        duration=data.get('duration', 0)
    )
    return jsonify({'status': 'saved', 'id': trans_id})


# ==================== ИСТОРИЯ ====================

@bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """
    Получить историю транскрипций с пагинацией, поиском и фильтром.
    ---
    tags:
      - History
    parameters:
      - name: page
        in: query
        type: integer
        description: Номер страницы
        default: 1
      - name: per_page
        in: query
        type: integer
        description: Записей на страницу
        default: 10
      - name: search
        in: query
        type: string
        description: Поиск по тексту
      - name: language
        in: query
        type: string
        description: Фильтр по языку (ru, kk, en)
    responses:
      200:
        description: Список транскрипций
        schema:
          type: object
          properties:
            items:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  text:
                    type: string
                  language:
                    type: string
                  created_at:
                    type: string
                  duration:
                    type: integer
                  word_count:
                    type: integer
                  accuracy:
                    type: number
            total:
              type: integer
            page:
              type: integer
            per_page:
              type: integer
            pages:
              type: integer
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '').strip()
    language = request.args.get('language', '').strip()
    
    pagination = TranscriptionService.get_user_history(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        search=search,
        language=language
    )
    
    return jsonify({
        'items': [{
            'id': t.id,
            'text': t.text,
            'language': t.language,
            'created_at': t.created_at.isoformat(),
            'duration': t.duration,
            'word_count': t.word_count,
            'accuracy': t.accuracy
        } for t in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@bp.route('/history/<int:id>', methods=['DELETE'])
@login_required
def delete_transcription(id):
    """
    Удалить транскрипцию по ID.
    ---
    tags:
      - History
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: ID транскрипции
    responses:
      200:
        description: Удалено
        schema:
          type: object
          properties:
            status:
              type: string
              example: deleted
      403:
        description: Нет прав
      404:
        description: Не найдено
    """
    success = TranscriptionService.delete_transcription(id, current_user.id)
    if not success:
        return jsonify({'error': 'Not found or unauthorized'}), 404
    return jsonify({'status': 'deleted'})


# ==================== ИЗБРАННОЕ ====================

@bp.route('/favorites', methods=['GET'])
@login_required
def get_favorites():
    """
    Получить список избранных транскрипций.
    ---
    tags:
      - Favorites
    responses:
      200:
        description: Список избранных
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              transcription_id:
                type: integer
              text:
                type: string
              language:
                type: string
              created_at:
                type: string
    """
    favs = Favorite.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': f.id,
        'transcription_id': f.transcription_id,
        'text': f.transcription.text,
        'language': f.transcription.language,
        'created_at': f.created_at.isoformat()
    } for f in favs])


@bp.route('/favorites/<int:transcription_id>', methods=['POST'])
@login_required
def add_favorite(transcription_id):
    """
    Добавить транскрипцию в избранное.
    ---
    tags:
      - Favorites
    parameters:
      - name: transcription_id
        in: path
        type: integer
        required: true
        description: ID транскрипции
    responses:
      200:
        description: Добавлено
        schema:
          type: object
          properties:
            status:
              type: string
              example: added
      403:
        description: Нет прав
      404:
        description: Транскрипция не найдена
    """
    from models import Transcription
    trans = Transcription.query.get_or_404(transcription_id)
    if trans.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if not Favorite.query.filter_by(user_id=current_user.id, transcription_id=transcription_id).first():
        fav = Favorite(user_id=current_user.id, transcription_id=transcription_id)
        db.session.add(fav)
        db.session.commit()
    return jsonify({'status': 'added'})


@bp.route('/favorites/<int:transcription_id>', methods=['DELETE'])
@login_required
def remove_favorite(transcription_id):
    """
    Удалить транскрипцию из избранного.
    ---
    tags:
      - Favorites
    parameters:
      - name: transcription_id
        in: path
        type: integer
        required: true
        description: ID транскрипции
    responses:
      200:
        description: Удалено
        schema:
          type: object
          properties:
            status:
              type: string
              example: removed
    """
    fav = Favorite.query.filter_by(user_id=current_user.id, transcription_id=transcription_id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
    return jsonify({'status': 'removed'})


# ==================== AI ФУНКЦИИ ====================

@bp.route('/ai/correct', methods=['POST'])
@limiter.limit("5 per minute")
@login_required
def ai_correct():
    """
    Исправить текст (автокоррекция).
    ---
    tags:
      - AI
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            text:
              type: string
              description: Исходный текст
    responses:
      200:
        description: Исправленный текст
        schema:
          type: object
          properties:
            result:
              type: string
      400:
        description: Текст слишком длинный
    """
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    result, error = AIService.correct_text(text)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'result': result})


@bp.route('/ai/paraphrase', methods=['POST'])
@limiter.limit("5 per minute")
@login_required
def ai_paraphrase():
    """
    Перефразировать текст.
    ---
    tags:
      - AI
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            text:
              type: string
    responses:
      200:
        description: Перефразированный текст
        schema:
          type: object
          properties:
            result:
              type: string
    """
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    result, error = AIService.paraphrase_text(text)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'result': result})


@bp.route('/ai/translate', methods=['POST'])
@limiter.limit("5 per minute")
@login_required
def ai_translate():
    """
    Перевести текст на указанный язык.
    ---
    tags:
      - AI
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            text:
              type: string
            target:
              type: string
              description: Целевой язык (ru, kk, en)
              default: ru
    responses:
      200:
        description: Переведённый текст
        schema:
          type: object
          properties:
            result:
              type: string
    """
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    target = data.get('target', 'ru')
    result, error = AIService.translate_text(text, target)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'result': result})


@bp.route('/ai/summarize', methods=['POST'])
@limiter.limit("5 per minute")
@login_required
def ai_summarize():
    """
    Сжать текст (суммаризация).
    ---
    tags:
      - AI
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            text:
              type: string
    responses:
      200:
        description: Краткое содержание
        schema:
          type: object
          properties:
            result:
              type: string
    """
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    result, error = AIService.summarize_text(text)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'result': result})


# ==================== СТАТИСТИКА ====================

@bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """
    Получить статистику пользователя.
    ---
    tags:
      - User
    responses:
      200:
        description: Объект со статистикой
        schema:
          type: object
          properties:
            total_sessions:
              type: integer
            total_words:
              type: integer
            total_duration:
              type: integer
            daily_stats:
              type: array
              items:
                type: object
                properties:
                  date:
                    type: string
                  words:
                    type: integer
    """
    from models import UserStats
    stats = current_user.stats
    if not stats:
        stats = UserStats(user_id=current_user.id)
        db.session.add(stats)
        db.session.commit()
    from datetime import datetime, timedelta
    daily = stats.daily_stats or {}
    last_7 = []
    for i in range(6, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
        last_7.append({'date': day, 'words': daily.get(day, 0)})
    return jsonify({
        'total_sessions': stats.total_sessions,
        'total_words': stats.total_words,
        'total_duration': stats.total_duration,
        'daily_stats': last_7
    })


# ==================== ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ ====================

@bp.route('/user', methods=['PUT'])
@login_required
def update_user():
    """
    Обновить данные пользователя (имя, email, пароль, аватар).
    ---
    tags:
      - User
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
            email:
              type: string
            password:
              type: string
            avatar:
              type: string
    responses:
      200:
        description: Обновлено
        schema:
          type: object
          properties:
            status:
              type: string
              example: updated
      400:
        description: Ошибка валидации
    """
    data = request.get_json(silent=True) or {}
    if 'username' in data:
        existing = User.query.filter_by(username=data['username']).first()
        if existing and existing.id != current_user.id:
            return jsonify({'error': 'Username taken'}), 400
        current_user.username = data['username']
    if 'email' in data:
        existing = User.query.filter_by(email=data['email']).first()
        if existing and existing.id != current_user.id:
            return jsonify({'error': 'Email taken'}), 400
        current_user.email = data['email']
    if 'password' in data and data['password']:
        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        current_user.password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    if 'avatar' in data:
        current_user.avatar = data['avatar']
    db.session.commit()
    return jsonify({'status': 'updated'})


# ==================== ЭКСПОРТ ТРАНСКРИПЦИИ ====================

@bp.route('/export/<int:id>')
@login_required
def export_text(id):
    """
    Экспорт транскрипции в текстовый файл.
    ---
    tags:
      - Export
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: ID транскрипции
    responses:
      200:
        description: Текстовый файл
        schema:
          type: string
      403:
        description: Нет прав
      404:
        description: Не найдено
    """
    from models import Transcription
    trans = Transcription.query.get_or_404(id)
    if trans.user_id != current_user.id:
        abort(403)
    from flask import Response
    response = Response(
        trans.text,
        status=200,
        mimetype='text/plain; charset=utf-8'
    )
    response.headers['Content-Disposition'] = f'attachment; filename=transcript_{id}.txt'
    return response