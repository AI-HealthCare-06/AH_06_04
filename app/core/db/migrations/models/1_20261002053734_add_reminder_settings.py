from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `reminder_settings` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `reminder_type` VARCHAR(11) NOT NULL COMMENT 'MEDICATION: MEDICATION\nGUIDE_CHECK: GUIDE_CHECK',
    `schedule_time` DATETIME(6) NOT NULL,
    `repeat_rule` VARCHAR(20),
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_reminder_users_3af5dffb` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `reminder_settings`;"""


MODELS_STATE = (
    "eJztmltP4zoQgP9K1addac+KhlJ6eEvbsPRA2xWUPUd7UeQmJrVInKztLFut+t+P7dyvpK"
    "jQFvECyXgm8XyezIwNf9qOa0KbflQhQcayfdb608bAgfwiN/Kh1Qael8iFgIGFLVVBorOg"
    "jACDcekdsCnkIhNSgyCPIRdzKfZtWwhdgysibCUiH6OfPtSZa0G2hIQPfPvBxQib8Dek0a"
    "13r98haJuZqSJTvFvKdbbypGyM2blUFG9b6IZr+w5OlL0VW7o41kaYCakFMSSAQfF4Rnwx"
    "fTG70M/Io2CmiUowxZSNCe+Ab7OUuw0ZGC4W/PhsqHTQEm/5S+l0T7v94163z1XkTGLJ6T"
    "pwL/E9MJQEpvP2Wo4DBgINiTHh9gsSKqZUgDdcAlJOL2WSQ8gnnkcYAatjGAkSiEngbImi"
    "A37rNsQWEwGunJzUMPuiXg8v1Ot3XOu98MblwRzE+DQcUoIxATYBKT6NDSCG6ocJsHN01A"
    "Ag16oEKMeyAPkbGQy+wSzEf25m03KIKZMcyFvMHfxmIoN9aNmIsh/7ibWGovBaTNqh9Ked"
    "hvduov6X5zq8mg0kBZcyi8inyAcMOGORMu/uUx+/ECyAcf8AiKkXRlzFrdItDjmKk5cADC"
    "zJSngs/AuLyC2VCb1QXKS8trT4XIPuV2UZIOsVFZe/FeX4+FQ5Ou71T7qnpyf9o7jKFIfq"
    "ys1g/ElUnExsPl6CoAOQvUnujA0OM3t2myTPbnXu7BZS5xLQJTR1D1D64JKSeK1mWWJ6mF"
    "Q7Sr9JTVL61TVJjGXByt8b0Iz0DxOh0iQwlerAVAqByT02g/ReJKhh35EUx3xKABuwQDOx"
    "3jHP9kS90s5a4ud3fK4Fd8Hv9hM49xpg7lVS7uUhLxBhSxOsiphHHE55oKZtcnB5noYMOf"
    "CjuNjPsK3hN1LnWo6Px72DOo+2RVUoljPK2x3mR93pNEmLneqs2MnHG6I6b8LQr5LMOHBd"
    "GwJc0Ril7XIwF9zwuWjGTdO2Y20wm11lWvTBONf8TG8nA43jlXS5EmKZnijL1HRQyT78Ua"
    "SR2QsS3bT73glSG1Cm265VBnUU5rhyqlnLuvQoLhpADiNwPzLkfDzRbubq5HOGs8ibYkSR"
    "0lVOWihH8UNa/47nFy1x2/o6m2r5TWisN//aFnMCPnN17D7wsE27HYkjUfZggECBVgclZw"
    "P1C5m13MJC7iKbcx/MGbZXYRwdyMqGIV+7sL5nPnFhs5ZvC7vThZWT3+CUKQkAAh3Bl+gU"
    "MsZZ0ZLyFz7i/PIa2oCVnzuHR0nX4eNugqft57Kvo1iOpGmCz3X4lidTcg5XAq/6SK504d"
    "6O517l8Vy81hJWgXWzrXzhITvf0Wuj8VCdj2dTvq+Pr7/jT7fjkaYPL7Th5VkrdfOUff72"
    "t17UWELTt/mXgsoOpuqLZsH4MOvmgdTJRq0tgR7vUHXCV2WTk4mc2ZO+pZffkzz3YePbuc"
    "T2N9Fve69X0aKX7L0oL8ab9k4po8cbqD1ZwhfroQo7oCzsIulzl0Bk4Uu4KvRO5fub6E/l"
    "+0e5alPDxQQ8xF17OoC4e9wpGCSeoXozVEdae/2S/5uw/h87GHaW"
)
