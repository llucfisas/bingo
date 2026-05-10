"""Database models for the party bingo app."""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Game(db.Model):
    __tablename__ = "games"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(12), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, default="Bingo de festa")
    # 0=lobby, 1=building cards, 2=playing, 3=ended
    phase = db.Column(db.Integer, nullable=False, default=0)
    line_winner_id = db.Column(db.Integer, db.ForeignKey("users.id", use_alter=True, name="fk_line_winner"), nullable=True)
    full_winner_id = db.Column(db.Integer, db.ForeignKey("users.id", use_alter=True, name="fk_full_winner"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("User", backref="game", lazy=True, foreign_keys="User.game_id")
    cards = db.relationship("BingoCard", backref="game", lazy=True)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("game_id", "name", name="uq_game_username"),)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class BingoCard(db.Model):
    """A bingo card. Created by `creator` for `target` in phase 1, played by `player` in phase 2."""
    __tablename__ = "bingo_cards"
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # assigned in phase 2
    # 9 slots stored as separator-joined string (simpler than JSON for portability)
    slots_text = db.Column(db.Text, nullable=False, default="|||||||||")
    marks_text = db.Column(db.String(40), nullable=False, default="000000000")  # 9 chars of 0/1
    submitted = db.Column(db.Boolean, default=False)

    creator = db.relationship("User", foreign_keys=[creator_id])
    target = db.relationship("User", foreign_keys=[target_id])
    player = db.relationship("User", foreign_keys=[player_id])

    SLOT_SEP = "§§"

    @property
    def slots(self):
        return self.slots_text.split(self.SLOT_SEP) if self.slots_text else [""] * 9

    @slots.setter
    def slots(self, values):
        assert len(values) == 9
        self.slots_text = self.SLOT_SEP.join(values)

    @property
    def marks(self):
        return [c == "1" for c in self.marks_text.ljust(9, "0")[:9]]

    @marks.setter
    def marks(self, values):
        assert len(values) == 9
        self.marks_text = "".join("1" if v else "0" for v in values)

    def has_line(self):
        m = self.marks
        # rows
        for r in range(3):
            if all(m[r * 3 + c] for c in range(3)):
                return True
        # cols
        for c in range(3):
            if all(m[r * 3 + c] for r in range(3)):
                return True
        # diagonals
        if m[0] and m[4] and m[8]:
            return True
        if m[2] and m[4] and m[6]:
            return True
        return False

    def is_full(self):
        return all(self.marks)
