# -*- coding: utf-8 -*-
"""Courses / Lessons / Education API routes — FAZ 33 + FAZ 65 (COMING_SOON).

Endpoints:
  GET  /api/courses                — List courses
  GET  /api/course/<slug>          — Course detail
  POST /api/course                 — Create course
  PUT  /api/course/<id>            — Update course
  POST /api/course/<id>/publish    — Publish course
  POST /api/course/<id>/lesson     — Add lesson
  PUT  /api/lesson/<id>            — Update lesson
  GET  /api/course/<id>/lessons    — List lessons
  POST /api/course/<id>/enroll     — Enroll in course
  GET  /api/courses/my             — My enrolled courses
  POST /api/course/<id>/progress   — Update progress

Pages:
  GET  /courses                    — Courses listing page
  GET  /course/<slug>              — Course detail page
  GET  /my-courses                 — My courses page

Copilot:
  POST /api/copilot/courses        — Copilot course Q&A
"""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request, session

from app.blueprints.courses import courses_bp
from app.core import course_engine as ce

_logger = logging.getLogger("zkr_analiz.courses.routes")

# ── FAZ 65 — Feature Lock ─────────────────────────────────────
COMING_SOON = True

def _coming_soon_response():
    """Return 503 JSON for locked feature."""
    return jsonify({
        "ok": False,
        "error": "Kurs sistemi yakında aktif olacak.",
        "coming_soon": True,
    }), 503


def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401)
    return uid, None


def _require_mentor(uid):
    """Check if user is a mentor."""
    try:
        from app.core.mentor_engine import is_mentor
        if not is_mentor(uid):
            return jsonify({"ok": False, "error": "Mentor profiliniz bulunmuyor"}), 403
    except Exception:
        return jsonify({"ok": False, "error": "Mentor sistemi erişilemiyor"}), 500
    return None


# ══════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════════════════════════

@courses_bp.route("/courses")
def courses_page():
    return render_template("courses.html", coming_soon=COMING_SOON)


@courses_bp.route("/course/<slug>")
def course_detail_page(slug):
    return render_template("course_detail.html", course_slug=slug, coming_soon=COMING_SOON)


@courses_bp.route("/my-courses")
def my_courses_page():
    return render_template("my_courses.html", coming_soon=COMING_SOON)


# ══════════════════════════════════════════════════════════════════
# API — LIST & DETAIL
# ══════════════════════════════════════════════════════════════════

@courses_bp.route("/api/courses")
def api_list_courses():
    if COMING_SOON:
        return _coming_soon_response()
    market = request.args.get("market")
    level = request.args.get("level")
    pricing = request.args.get("pricing")
    mentor = request.args.get("mentor_user_id")
    sort = request.args.get("sort", "newest")
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = int(request.args.get("offset", 0))
    search = request.args.get("search")

    courses = ce.list_courses(
        market=market, level=level, pricing=pricing,
        mentor_user_id=mentor, sort=sort, limit=limit,
        offset=offset, search=search,
    )
    return jsonify({"ok": True, "courses": courses, "count": len(courses)})


@courses_bp.route("/api/marketplace/courses")
def api_marketplace_courses():
    """Marketplace Akademi Tabı — Published Courses"""
    from app.models import Course
    
    try:
        courses = Course.query.filter_by(is_published=True).all()
        return jsonify({
            "ok": True,
            "courses": [c.to_dict() for c in courses],
            "count": len(courses)
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@courses_bp.route("/api/marketplace/course/<slug>")
def api_marketplace_course_detail(slug):
    """Marketplace Akademi — Kurs Detayı & Modülleri"""
    from app.models import Course
    
    try:
        course = Course.query.filter_by(slug=slug, is_published=True).first()
        if not course:
            return jsonify({"ok": False, "error": "Kurs bulunamadı"}), 404
        
        data = course.to_dict()
        data["modules"] = [m.to_dict() for m in course.modules]
        return jsonify({"ok": True, "course": data}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@courses_bp.route("/api/course/<slug>")
def api_course_detail(slug):
    if COMING_SOON:
        return _coming_soon_response()
    uid = session.get("user_id")
    course = ce.get_course(slug, viewer_id=uid)
    if not course:
        return jsonify({"ok": False, "error": "Kurs bulunamadı"}), 404

    is_enrolled = course.get("is_enrolled", False)
    is_owner = uid and uid == course["mentor_user_id"]
    lessons = ce.list_lessons(course["id"], enrolled=is_enrolled or is_owner)

    return jsonify({
        "ok": True,
        "course": course,
        "lessons": lessons,
        "is_owner": is_owner,
    })


@courses_bp.route("/api/courses/featured")
def api_featured_courses():
    if COMING_SOON:
        return _coming_soon_response()
    limit = min(int(request.args.get("limit", 6)), 20)
    courses = ce.featured_courses(limit=limit)
    return jsonify({"ok": True, "courses": courses})


# ══════════════════════════════════════════════════════════════════
# API — CREATE / UPDATE / PUBLISH
# ══════════════════════════════════════════════════════════════════

@courses_bp.route("/api/course", methods=["POST"])
def api_create_course():
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err
    merr = _require_mentor(uid)
    if merr:
        return merr

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "Kurs başlığı gerekli"}), 400

    try:
        course = ce.create_course(
            mentor_user_id=uid,
            title=title,
            description=data.get("description", ""),
            level=data.get("level", "beginner"),
            market=data.get("market", ""),
            pricing_model=data.get("pricing_model", "free"),
            price=float(data.get("price", 0)),
            thumbnail_url=data.get("thumbnail_url", ""),
        )
        return jsonify({"ok": True, "course": course})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@courses_bp.route("/api/course/<course_id>", methods=["PUT"])
def api_update_course(course_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    try:
        course = ce.update_course(
            course_id=course_id,
            mentor_user_id=uid,
            title=data.get("title"),
            description=data.get("description"),
            level=data.get("level"),
            market=data.get("market"),
            pricing_model=data.get("pricing_model"),
            price=float(data["price"]) if "price" in data else None,
            thumbnail_url=data.get("thumbnail_url"),
        )
        return jsonify({"ok": True, "course": course})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@courses_bp.route("/api/course/<course_id>/publish", methods=["POST"])
def api_publish_course(course_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    try:
        course = ce.publish_course(course_id, uid)
        return jsonify({"ok": True, "course": course})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ══════════════════════════════════════════════════════════════════
# API — LESSONS
# ══════════════════════════════════════════════════════════════════

@courses_bp.route("/api/course/<course_id>/lesson", methods=["POST"])
def api_add_lesson(course_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "Ders başlığı gerekli"}), 400

    try:
        lesson = ce.add_lesson(
            course_id=course_id,
            mentor_user_id=uid,
            title=title,
            content_type=data.get("content_type", "article"),
            video_url=data.get("video_url", ""),
            content=data.get("content", ""),
            order_index=int(data["order_index"]) if "order_index" in data else None,
            duration_minutes=int(data.get("duration_minutes", 0)),
            is_preview=bool(data.get("is_preview", False)),
        )
        return jsonify({"ok": True, "lesson": lesson})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@courses_bp.route("/api/lesson/<lesson_id>", methods=["PUT"])
def api_update_lesson(lesson_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    try:
        lesson = ce.update_lesson(
            lesson_id=lesson_id,
            mentor_user_id=uid,
            title=data.get("title"),
            content_type=data.get("content_type"),
            video_url=data.get("video_url"),
            content=data.get("content"),
            order_index=int(data["order_index"]) if "order_index" in data else None,
            duration_minutes=int(data["duration_minutes"]) if "duration_minutes" in data else None,
            is_preview=data.get("is_preview"),
        )
        return jsonify({"ok": True, "lesson": lesson})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@courses_bp.route("/api/course/<course_id>/lessons")
def api_list_lessons(course_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid = session.get("user_id")
    # Check enrollment or ownership
    course = ce.get_course_by_id(course_id)
    if not course:
        return jsonify({"ok": False, "error": "Kurs bulunamadı"}), 404

    is_owner = uid and uid == course["mentor_user_id"]
    is_enrolled = False
    if uid and not is_owner:
        conn = ce._get_conn()
        try:
            erow = conn.execute(
                "SELECT 1 FROM course_enrollments WHERE course_id = ? AND user_id = ? AND status != 'cancelled'",
                (course_id, uid)
            ).fetchone()
            is_enrolled = erow is not None
        finally:
            conn.close()

    lessons = ce.list_lessons(course_id, enrolled=is_enrolled or is_owner)
    return jsonify({"ok": True, "lessons": lessons, "count": len(lessons)})


# ══════════════════════════════════════════════════════════════════
# API — ENROLLMENT & PROGRESS
# ══════════════════════════════════════════════════════════════════

@courses_bp.route("/api/course/<course_id>/enroll", methods=["POST"])
def api_enroll(course_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    # FAZ 36 — premium course access check
    course = ce.get_course_by_id(course_id)
    if course and course.get("pricing_model") in ("paid", "subscription"):
        from app.core.subscription_engine import can_access_premium_course
        check = can_access_premium_course(uid)
        if not check["allowed"]:
            return jsonify({"ok": False, "error": check["reason"], "upgrade_required": True, "required_plan": check.get("required_plan"), "locked": True}), 403

    try:
        enrollment = ce.enroll_user(course_id, uid)
        return jsonify({"ok": True, "enrollment": enrollment})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@courses_bp.route("/api/courses/my")
def api_my_courses():
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    courses = ce.get_my_courses(uid)
    return jsonify({"ok": True, "courses": courses, "count": len(courses)})


@courses_bp.route("/api/course/<course_id>/progress", methods=["POST"])
def api_progress(course_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    pct = float(data.get("progress_pct", 0))

    try:
        enrollment = ce.progress_course(course_id, uid, pct)
        return jsonify({"ok": True, "enrollment": enrollment})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ══════════════════════════════════════════════════════════════════
# COPILOT — COURSES
# ══════════════════════════════════════════════════════════════════

@courses_bp.route("/api/copilot/courses", methods=["POST"])
def api_copilot_courses():
    if COMING_SOON:
        return _coming_soon_response()
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Soru gerekli"}), 400

    featured = ce.featured_courses(limit=10)
    stats = ce.course_stats()

    context_parts = [
        f"KURS İSTATİSTİKLERİ: {stats['total_courses']} kurs, {stats['total_students']} öğrenci, {stats['total_mentors']} mentor",
        "ÖNE ÇIKAN KURSLAR:",
    ]
    for c in featured:
        context_parts.append(
            f"  - {c.get('title','?')} (mentor: {c.get('mentor_display_name','?')}): "
            f"level={c.get('level','')}, market={c.get('market','')}, "
            f"pricing={c.get('pricing_model','free')}, "
            f"students={c.get('students_count',0)}, lessons={c.get('lesson_count',0)}"
        )
    context_text = "\n".join(context_parts)

    try:
        from app.core.copilot_service import _SYSTEM_BASE, _call_llm, DEFAULT_MODEL
        _COURSE_PROMPT = (
            "\nBu yanıtı ZKR Analiz Eğitim/Kurs sistemi için veriyorsun.\n"
            "Context'te kurs istatistikleri, öne çıkan kurslar ve mentor bilgileri var.\n"
            "Kullanıcıya en uygun kursları, seviyeleri ve öğrenme yollarını öner.\n"
        )
        system = _SYSTEM_BASE + _COURSE_PROMPT
        prompt = f"[CONTEXT]\n{context_text}\n\n[KULLANICI SORUSU]\n{question}\n\nassistant:"
        result = _call_llm(DEFAULT_MODEL, system, prompt, {"courses": context_text})
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        _logger.warning("Copilot courses error: %s", e)
        return jsonify({
            "ok": True,
            "data": {
                "answer": f"Şu anda {stats['total_courses']} kurs mevcut, {stats['total_students']} öğrenci kayıtlı.",
                "summary": "Kurs sistemi özeti",
                "key_points": [f"{stats['total_courses']} aktif kurs"],
                "risk_points": [],
                "suggested_alerts": [],
            }
        })
