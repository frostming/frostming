import json
import os
import re
from subprocess import check_call
from typing import Literal, Union

from jinja2 import Template

from chess.gomoku import Game


class Runner:
    GAME_META = os.path.join(os.path.dirname(__file__), "gomoku.json")
    GAME_STATS = os.path.join(os.path.dirname(__file__), "stats.json")
    README = os.path.join(os.path.dirname(os.path.dirname(__file__)), "README.md")
    ROLES = {0: "white", 1: "black"}
    TEMPLATE = os.path.join(os.path.dirname(__file__), "readme_template.j2")

    def __init__(self) -> None:
        with open(self.GAME_META, encoding="utf-8") as f:
            self.meta = json.load(f)
        with open(self.GAME_STATS, encoding="utf-8") as f:
            self.stats = json.load(f)
        with open(self.README, encoding="utf-8") as f:
            self.readme = f.read()
        with open(self.TEMPLATE, encoding="utf-8") as f:
            self.template = Template(f.read())

    def play_game(
        self, role: Union[Literal[0], Literal[1]], pos: str, user: str
    ) -> None:
        """Title: gomoku|drop|black|b4"""
        game = Game()
        assert (
            role == self.meta["role"]
        ), f"Current player role doesn't match, should be {self.ROLES[self.meta['role']]}"
        game.load(self.meta["blacks"], self.meta["whites"])
        idx = game._pos_to_idx(pos)
        game.drop(idx, role)
        self.stats["all_players"][user] = self.stats["all_players"].get(user, 0) + 1
        self.meta["turn"] += 1
        self.meta["last_steps"].insert(
            0, {"user": user, "color": self.ROLES[role], "pos": pos}
        )
        self.meta["blacks"], self.meta["whites"] = game.dump()
        winner = game.check_field(idx)
        if winner is not None:
            self.meta["winner"] = winner
            self.stats["completed_games"] += 1
            if winner == role:
                self.stats["winning_players"][user] = (
                    self.stats["winning_players"].get(user, 0) + 1
                )
        else:
            self.meta["role"] ^= 1

    def dump(self):
        with open(self.GAME_META, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2)
        with open(self.GAME_STATS, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2)
        with open(self.README, "w", encoding="utf-8") as f:
            f.write(self.readme)

    def new_game(self):
        self.stats.update(
            turn=0, last_steps=[], blacks=[], whites=[], role=1, winner=None
        )

    def update_readme(self) -> None:
        game = Game()
        game.load(self.meta["blacks"], self.meta["whites"])
        top_wins = sorted(
            self.stats["winning_players"].items(), key=lambda x: x[1], reverse=True
        )[:10]
        context = {
            "total_players": len(self.stats["all_players"]),
            "total_moves": sum(self.stats["all_players"].values()),
            "completed_games": self.stats["completed_games"],
            "winner": self.ROLES.get(self.meta["winner"]),
            "dimension": game.DIMENSION,
            "field": game.field(),
            "color": self.ROLES.get(self.meta["role"]),
            "last_steps": self.meta["last_steps"],
            "top_wins": top_wins,
            "repo": os.getenv("REPO"),
        }
        self.readme = re.sub(
            r"(<\!--START_SECTION:gomoku-->\n)(.*)(\n<\!--END_SECTION:gomoku-->)",
            r"\1" + self.template.render(**context) + r"\3",
            self.readme,
            flags=re.DOTALL,
        )

    def commit_files(self, message: str):
        check_call(["git", "add", "-A", "."])
        check_call(["git", "commit", "-m", message])


def main():
    issue_title = os.getenv("ISSUE_TITLE")
    parts = issue_title.split("|")
    runner = Runner()
    user = os.getenv("PLAYER")
    if len(parts) < 4 and "new" in parts:
        runner.new_game()
        message = f"@{user} starts a new game"
    else:
        *_, color, pos = parts
        input_role = 1 if color == "black" else 0
        runner.play_game(input_role, pos, user)
        message = f"@{user} drops a {color} piece at {pos.upper()}"
    message += f"\nClose #{os.getenv('ISSUE_NUMBER')}"
    runner.update_readme()
    runner.dump()
    runner.commit_files(message)


if __name__ == "__main__":
    main()
    # os.environ["REPO"] = "frostming/frostming"
    # runner = Runner()
    # runner.update_readme()
    # runner.dump()
