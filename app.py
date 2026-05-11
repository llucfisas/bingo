"""Party bingo Flask app — single-game mode.

There's always exactly one game (Game with id=1, auto-created on startup).
- Anyone who knows JOIN_PASSWORD can register with a name + password of their choice.
- Anyone who knows ADMIN_PASSWORD becomes admin (can also play).
- Admin controls phases and can reset the game to start a new one.
"""
import os
import random
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, abort
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)

from models import db, Game, User, BingoCard


def get_active_game():
    """Always returns the single active game (creating it on first run)."""
    g = db.session.get(Game, 1)
    if g is None:
        g = Game(id=1, code="MAIN", name="Bingo de festa")
        db.session.add(g)
        db.session.commit()
    return g


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me")

    db_url = os.environ.get("DATABASE_URL", "sqlite:///bingo.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager = LoginManager(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()
        get_active_game()

    # ---------- helpers ----------

    def admin_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin:
                abort(403)
            return f(*args, **kwargs)
        return wrapper

    def random_derangement(items):
        """Return a permutation where no element is in its original position."""
        n = len(items)
        if n < 2:
            return None
        for _ in range(200):
            perm = items[:]
            random.shuffle(perm)
            if all(perm[i] != items[i] for i in range(n)):
                return perm
        return items[1:] + items[:1]

    def assign_phase2(cards, players):
        """Assign each card to a player s.t. player != creator and player != target."""
        n = len(cards)
        if n != len(players):
            return None

        def backtrack(idx, used, assignment):
            if idx == n:
                return True
            card = cards[idx]
            options = [p for p in players
                       if p.id not in used
                       and p.id != card.creator_id
                       and p.id != card.target_id]
            random.shuffle(options)
            for p in options:
                used.add(p.id)
                assignment[card.id] = p.id
                if backtrack(idx + 1, used, assignment):
                    return True
                used.remove(p.id)
                del assignment[card.id]
            return False

        for _ in range(50):
            random.shuffle(cards)
            assignment = {}
            if backtrack(0, set(), assignment):
                return assignment
        return None

    # ---------- routes ----------

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("game"))
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            password = request.form.get("password", "")
            join_password = request.form.get("join_password", "")
            admin_password = request.form.get("admin_password", "")

            if not name or not password:
                flash("Omple nom i contrasenya.", "error")
                return redirect(url_for("register"))

            env_join_pw = os.environ.get("JOIN_PASSWORD", "")
            if not env_join_pw:
                flash("L'admin no ha configurat JOIN_PASSWORD. Avisa'l.", "error")
                return redirect(url_for("register"))
            if join_password != env_join_pw:
                flash("Contrasenya d'entrada incorrecta.", "error")
                return redirect(url_for("register"))

            g = get_active_game()

            if g.phase != 0:
                flash("La partida ja ha començat. Espera a la propera.", "error")
                return redirect(url_for("register"))

            existing = User.query.filter_by(game_id=g.id, name=name).first()
            if existing:
                flash("Ja existeix un jugador amb aquest nom.", "error")
                return redirect(url_for("register"))

            is_admin = False
            env_admin_pw = os.environ.get("ADMIN_PASSWORD", "")
            if admin_password:
                if env_admin_pw and admin_password == env_admin_pw:
                    is_admin = True
                else:
                    flash("Contrasenya d'admin incorrecta.", "error")
                    return redirect(url_for("register"))

            user = User(game_id=g.id, name=name, is_admin=is_admin)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("game"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            password = request.form.get("password", "")

            g = get_active_game()
            user = User.query.filter_by(game_id=g.id, name=name).first()
            if not user or not user.check_password(password):
                flash("Nom o contrasenya incorrectes.", "error")
                return redirect(url_for("login"))

            login_user(user)
            return redirect(url_for("game"))

        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("index"))

    @app.route("/game")
    @login_required
    def game():
        g = current_user.game

        if g.phase == 0:
            players = User.query.filter_by(game_id=g.id).order_by(User.created_at).all()
            return render_template("lobby.html", game=g, players=players)

        if g.phase == 1:
            my_card = BingoCard.query.filter_by(
                game_id=g.id, creator_id=current_user.id
            ).first()
            if not my_card:
                flash("Encara no tens cap encàrrec. Espera que l'admin assigni objectius.", "error")
                return redirect(url_for("index"))
            return render_template("fill_card.html", game=g, card=my_card)

        if g.phase in (2, 3):
            played = BingoCard.query.filter_by(
                game_id=g.id, player_id=current_user.id
            ).first()
            mine = BingoCard.query.filter_by(
                game_id=g.id, creator_id=current_user.id
            ).first()
            about_me = BingoCard.query.filter_by(
                game_id=g.id, target_id=current_user.id
            ).first()
            line_winner = db.session.get(User, g.line_winner_id) if g.line_winner_id else None
            full_winner = db.session.get(User, g.full_winner_id) if g.full_winner_id else None
            return render_template(
                "play_card.html",
                game=g,
                played=played,
                mine=mine,
                about_me=about_me,
                line_winner=line_winner,
                full_winner=full_winner,
            )

        return redirect(url_for("index"))

    @app.route("/card/submit", methods=["POST"])
    @login_required
    def submit_card():
        g = current_user.game
        if g.phase != 1:
            abort(400)

        card = BingoCard.query.filter_by(
            game_id=g.id, creator_id=current_user.id
        ).first()
        if not card:
            abort(404)

        slots = [request.form.get(f"slot_{i}", "").strip() for i in range(9)]
        if any(not s for s in slots):
            flash("Has d'omplir els 9 espais abans d'enviar.", "error")
            card.slots = slots
            db.session.commit()
            return redirect(url_for("game"))
        if any(len(s) > 120 for s in slots):
            flash("Cada acció ha de tenir 120 caràcters com a màxim.", "error")
            return redirect(url_for("game"))

        card.slots = slots
        card.submitted = True
        db.session.commit()
        flash("Cartró enviat! A esperar la resta…", "ok")
        return redirect(url_for("game"))

    @app.route("/card/save_draft", methods=["POST"])
    @login_required
    def save_draft():
        g = current_user.game
        if g.phase != 1:
            abort(400)
        card = BingoCard.query.filter_by(
            game_id=g.id, creator_id=current_user.id
        ).first()
        if not card or card.submitted:
            abort(400)
        slots = [request.form.get(f"slot_{i}", "")[:120] for i in range(9)]
        card.slots = slots
        db.session.commit()
        flash("Esborrany guardat.", "ok")
        return redirect(url_for("game"))

    @app.route("/card/mark", methods=["POST"])
        @login_required
        def mark_slot():
            g = current_user.game
            if g.phase != 2:
                return jsonify({"ok": False, "error": "Game not in playing phase"}), 400
    
            card = BingoCard.query.filter_by(
                game_id=g.id, player_id=current_user.id
            ).first()
            if not card:
                return jsonify({"ok": False, "error": "No card assigned"}), 404
    
            try:
                idx = int(request.form.get("idx", -1))
            except ValueError:
                return jsonify({"ok": False, "error": "Bad index"}), 400
            if not (0 <= idx < 9):
                return jsonify({"ok": False, "error": "Bad index"}), 400
    
            marks = card.marks
            # Un cop marcada, NO es pot desmarcar
            if not marks[idx]:
                marks[idx] = True
                card.marks = marks
    
                # Es continua trackant guanyadors per a la vista de l'admin,
                # pero ja no es notifica res als jugadors.
                if g.line_winner_id is None and card.has_line():
                    g.line_winner_id = current_user.id
                if g.full_winner_id is None and card.is_full():
                    g.full_winner_id = current_user.id
    
                db.session.commit()
    
            return jsonify({
                "ok": True,
                "marks": card.marks,
                "phase": g.phase,
            })

    @app.route("/state")
    @login_required
    def state():
        """Lightweight polling endpoint to detect phase changes & winners."""
        g = current_user.game
        line_w = db.session.get(User, g.line_winner_id) if g.line_winner_id else None
        full_w = db.session.get(User, g.full_winner_id) if g.full_winner_id else None
        return jsonify({
            "phase": g.phase,
            "line_winner": line_w.name if line_w else None,
            "full_winner": full_w.name if full_w else None,
        })

    # ---------- admin ----------

    @app.route("/admin")
    @login_required
    @admin_required
    def admin():
        g = current_user.game
        users = User.query.filter_by(game_id=g.id).order_by(User.created_at).all()
        cards = BingoCard.query.filter_by(game_id=g.id).all()
        submitted = sum(1 for c in cards if c.submitted)
        return render_template(
            "admin.html",
            game=g,
            users=users,
            cards=cards,
            submitted=submitted,
            n_users=len(users),
        )

    @app.route("/admin/start_phase1", methods=["POST"])
    @login_required
    @admin_required
    def start_phase1():
        g = current_user.game
        if g.phase != 0:
            flash("La fase 1 ja ha començat.", "error")
            return redirect(url_for("admin"))

        users = User.query.filter_by(game_id=g.id).order_by(User.created_at).all()
        if len(users) < 3:
            flash("Cal un mínim de 3 jugadors.", "error")
            return redirect(url_for("admin"))

        targets = random_derangement(users)
        for creator, target in zip(users, targets):
            card = BingoCard(
                game_id=g.id, creator_id=creator.id, target_id=target.id,
                slots_text=BingoCard.SLOT_SEP.join([""] * 9),
            )
            db.session.add(card)

        g.phase = 1
        db.session.commit()
        flash("Fase 1 iniciada! Cadascú té el seu objectiu.", "ok")
        return redirect(url_for("admin"))

    @app.route("/admin/start_phase2", methods=["POST"])
    @login_required
    @admin_required
    def start_phase2():
        g = current_user.game
        if g.phase != 1:
            flash("Has d'estar a la fase 1 per avançar.", "error")
            return redirect(url_for("admin"))

        cards = BingoCard.query.filter_by(game_id=g.id).all()
        if not all(c.submitted for c in cards):
            missing = [c.creator.name for c in cards if not c.submitted]
            flash(f"Falten per enviar: {', '.join(missing)}", "error")
            return redirect(url_for("admin"))

        users = User.query.filter_by(game_id=g.id).all()
        assignment = assign_phase2(list(cards), users)
        if assignment is None:
            flash("No s'ha pogut redistribuir cap combinació vàlida.", "error")
            return redirect(url_for("admin"))

        for card in cards:
            card.player_id = assignment[card.id]

        g.phase = 2
        db.session.commit()
        flash("Fase 2 iniciada! Que comenci la festa.", "ok")
        return redirect(url_for("admin"))

    @app.route("/admin/end_game", methods=["POST"])
    @login_required
    @admin_required
    def end_game():
        g = current_user.game
        g.phase = 3
        db.session.commit()
        flash("Partida acabada.", "ok")
        return redirect(url_for("admin"))

    @app.route("/admin/reset", methods=["POST"])
    @login_required
    @admin_required
    def reset_game():
        """Wipe the current game state (users, cards) so a new game can start."""
        g = current_user.game
        # IMPORTANT: clear FKs from Game to User BEFORE deleting users, otherwise
        # Postgres rejects the delete (Game.line_winner_id / full_winner_id still
        # reference the user). SQLite doesn't enforce FKs by default so this only
        # bites in production.
        g.phase = 0
        g.line_winner_id = None
        g.full_winner_id = None
        db.session.flush()
        BingoCard.query.filter_by(game_id=g.id).delete()
        User.query.filter_by(game_id=g.id).delete()
        db.session.commit()
        logout_user()
        flash("Partida reiniciada. Torneu-vos a registrar tots.", "ok")
        return redirect(url_for("index"))

    @app.route("/admin/kick/<int:user_id>", methods=["POST"])
    @login_required
    @admin_required
    def kick_user(user_id):
        g = current_user.game
        if g.phase != 0:
            flash("Només pots fer fora jugadors al lobby.", "error")
            return redirect(url_for("admin"))
        if user_id == current_user.id:
            flash("No et pots fer fora a tu mateix.", "error")
            return redirect(url_for("admin"))
        u = db.session.get(User, user_id)
        if u and u.game_id == g.id:
            db.session.delete(u)
            db.session.commit()
            flash(f"Has fet fora {u.name}.", "ok")
        return redirect(url_for("admin"))

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
