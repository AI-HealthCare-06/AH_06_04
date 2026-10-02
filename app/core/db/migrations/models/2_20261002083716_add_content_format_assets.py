from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `content_format_assets` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guide_id` BIGINT NOT NULL,
    `format_type` VARCHAR(5) NOT NULL COMMENT 'AUDIO: AUDIO\nVIDEO: VIDEO\nIMAGE: IMAGE',
    `file_url` VARCHAR(500) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
        DROP TABLE IF EXISTS `reminder_settings`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `content_format_assets`;"""


MODELS_STATE = (
    "eJztme1vmzwQwP8VxKc9Ujc1NG/rN9LQjalJpi3d82jrhBxwiFWwGTbroqn/+2xDwjslVZ"
    "8lqfolhPMd3P18nM3xW/WJAz36RochslfqufJbxcCH/E9h5ERRQRCkciFgYOFJVZDqLCgL"
    "gc24dAk8CrnIgdQOUcAQwVyKI88TQmJzRYTdVBRh9COCFiMuZCsY8oFv37kYYQf+gnRzGt"
    "xaSwQ9J+cqcsS9pdxi60DKTMwupaK428KyiRf5OFUO1mxF8FYbYSakLsQwBAyKy7MwEu4L"
    "75I4NxHFnqYqsYsZGwcuQeSxTLgtGdgEC37cGyoDdMVdXmud7qA7POt3h1xFerKVDO7j8N"
    "LYY0NJYDpX7+U4YCDWkBhTbj9hSIVLJXgXKxBW08uYFBByx4sIN8CaGG4EKcQ0cZ6Iog9+"
    "WR7ELhMJrvV6Dcy+6J8u3uufXnGtf0Q0hCdznOPTZEiLxwTYFKR4NHaAmKgfJ8DO6WkLgF"
    "yrFqAcywPkd2QwfgbzED98nk2rIWZMCiCvMQ/wm4NsdqJ4iLLvh4m1gaKIWjjtU/rDy8J7"
    "NdH/K3K9uJqNJAVCmRvKq8gLjDhjUTKXt5mHXwgWwL69A6FjlUaIRup0y0O+5hclAANXsh"
    "IRi/iSReSayoJeWlykvHFpibgGPayVZYTcZ7S4vNW0s7OBdnrWH/a6g0FveLpdZcpDTcvN"
    "yHwnVpxcbj68BEEfIG+X2rk1OM7q2W1TPLv1tbNbKp0rQFfQsQJA6R0JK/K1nmWF6XFS7W"
    "jDNmuSNqxfk8RYHqw87kBzo3+cCLU2ianVJ6ZWSkwesROX9zJBA0e+pGhylwC2YYlmar1n"
    "nupEvzLOFfF7gy+N+Cw+qo/g3G+BuV9LuV+EvEAhWzlgXcY85nCqEzVrU4DL6zRkyIdvxJ"
    "/DTNsGfmN9bhT4BDw6aPFsW9SlYjWjot1xPtSdTpuy2Kmvip1iviFq8U0Y+llRGUeEeBDg"
    "mo1R1q4Ac8EN/y+a203TU+faaDa7ym3RR2Zh8zO9nowMjlfS5UqI5fZEeaaOjyrewx9Euj"
    "H7i0R33X3vBakHKLM84lZBHSc1rppq3rKpPIo/LSAnGXgYFXJuTozPc33yMcdZ1E0xoknp"
    "uiAtLUfbiyj/mvP3ijhVvs6mRvEldKs3/6oKn0DEiIXJHU/bbNgb8UaUbwyEUKC1QEVvoH"
    "ki85ZPMJH7qOY8BmeGvXWSR0cys0nKN05sFDiPnNi85cvE7nVipfMH0mW6iDuClyT0AdMp"
    "hUyt6DlVaJ00daCSPqO1lAYWEBYvHann25FyI+RAa1fMWauHYR9IEfqLvFO+yXMk6ZQQt+"
    "sNFC6x7waBfj02Z+eKPNzgL+bY4GfycIPNif7OOFfk4THtgjYfq+o/VZU+VC2RB60o3Knj"
    "mrU5ztfgXqtPVr2GT1a9ik9WLzvT57CBiXeme93B3P8BGCytmQ=="
)
